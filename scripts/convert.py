#!/usr/bin/env python3
"""Export V2Fly domain lists as plain-text files."""

import argparse
import ipaddress
import json
import re
import shutil
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
SUPPORTED = {"domain", "full"}
RULE_TYPES = SUPPORTED | {"regexp", "keyword"}


@dataclass(frozen=True)
class Rule:
    kind: str
    value: str
    attributes: frozenset[str]


@dataclass(frozen=True)
class Include:
    source: str
    required: frozenset[str]
    excluded: frozenset[str]


def valid_domain(value: str) -> bool:
    if not 1 < len(value) <= 253 or "." not in value:
        return False
    if not all(LABEL.fullmatch(part) for part in value.split(".")):
        return False
    try:
        ipaddress.ip_address(value)
        return False
    except ValueError:
        return True


def load_lists(source: Path) -> tuple[dict[str, set[Rule]], dict[str, list[Include]]]:
    if not source.is_dir():
        raise ValueError(f"Source data directory does not exist: {source}")
    rules: dict[str, set[Rule]] = defaultdict(set)
    includes: dict[str, list[Include]] = defaultdict(list)
    files = sorted(p for p in source.iterdir() if p.is_file())
    if not files:
        raise ValueError(f"No source files found in {source}")
    if len({p.name.lower() for p in files}) != len(files):
        raise ValueError("Multiple files differ only by capitalization")

    for path in files:
        name = path.name.lower()
        rules[name]
        for number, original in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
            line = original.split("#", 1)[0].strip()
            if not line:
                continue
            parts = line.split()
            token, extra = parts[0], parts[1:]
            kind, sep, value = token.partition(":")
            if not sep:
                kind, value = "domain", kind
            kind = kind.lower()
            if kind == "include":
                required = frozenset(x[1:].lower() for x in extra if x.startswith("@") and not x.startswith("@-"))
                excluded = frozenset(x[2:].lower() for x in extra if x.startswith("@-"))
                if not value or any(not x.startswith("@") for x in extra):
                    raise ValueError(f"Invalid include directive: {path}:{number}")
                includes[name].append(Include(value.lower(), required, excluded))
                continue
            if kind not in RULE_TYPES:
                raise ValueError(f"Unknown rule kind {kind!r}: {path}:{number}")
            if any(not x.startswith(("@", "&")) or len(x) < 2 for x in extra):
                raise ValueError(f"Invalid rule attributes: {path}:{number}")
            attrs = frozenset(x[1:].lower() for x in extra if x.startswith("@"))
            rule = Rule(kind, value.lower(), attrs)
            rules[name].add(rule)
            for affiliate in (x[1:].lower() for x in extra if x.startswith("&")):
                rules[affiliate].add(rule)
    return rules, includes


def resolve_all(rules: dict[str, set[Rule]], includes: dict[str, list[Include]]) -> dict[str, frozenset[Rule]]:
    resolved: dict[str, frozenset[Rule]] = {}
    visiting: set[str] = set()

    def resolve(name: str) -> frozenset[Rule]:
        if name in resolved:
            return resolved[name]
        if name in visiting:
            raise ValueError(f"Circular include detected involving {name}")
        if name not in rules:
            raise ValueError(f"Included list not found: {name}")
        visiting.add(name)
        combined = set(rules[name])
        for incl in includes.get(name, []):
            for rule in resolve(incl.source):
                if incl.required <= rule.attributes and not (incl.excluded & rule.attributes):
                    combined.add(rule)
        visiting.remove(name)
        resolved[name] = frozenset(combined)
        return resolved[name]

    for name in sorted(rules):
        resolve(name)
    return resolved


def export(source: Path, output: Path, manifest: Path, catalog: Path, revision: str) -> dict:
    all_rules = resolve_all(*load_lists(source))
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    metadata = {}
    published = 0

    for name, entries in sorted(all_rules.items()):
        domains = sorted({r.value for r in entries if r.kind in SUPPORTED and valid_domain(r.value)})
        if domains:
            (output / f"{name}.txt").write_text("\n".join(domains) + "\n", encoding="utf-8")
            published += 1
        metadata[name] = {
            "status": "published" if domains else "no-compatible-domains",
            "domain_count": len(domains),
            "skipped_regex": sum(r.kind == "regexp" for r in entries),
            "skipped_keyword": sum(r.kind == "keyword" for r in entries),
            "skipped_invalid_or_single_label": sum(r.kind in SUPPORTED and not valid_domain(r.value) for r in entries),
        }

    report = {
        "upstream": "https://github.com/v2fly/domain-list-community",
        "upstream_revision": revision,
        "total_lists": len(all_rules),
        "published_lists": published,
        "omitted_lists": len(all_rules) - published,
        "lists": metadata,
    }
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# Available UniFi External Lists", "",
        "Generated from [V2Fly domain-list-community](https://github.com/v2fly/domain-list-community).",
        "Unsupported regexes and keywords are omitted.", "",
        f"Published lists: **{published}** of **{len(all_rules)}**.", "",
        "| List | Domains | Skipped regex | Skipped keyword |",
        "| --- | ---: | ---: | ---: |",
    ]
    for name, data in metadata.items():
        if data["status"] == "published":
            lines.append(f"| [{name}](lists/{name}.txt) | {data['domain_count']} | {data['skipped_regex']} | {data['skipped_keyword']} |")
    catalog.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("lists"))
    parser.add_argument("--manifest", type=Path, default=Path("manifest.json"))
    parser.add_argument("--catalog", type=Path, default=Path("LISTS.md"))
    parser.add_argument("--revision", default="unknown")
    args = parser.parse_args()
    result = export(args.source, args.output, args.manifest, args.catalog, args.revision)
    print(f"Exported {result['published_lists']} of {result['total_lists']} lists ({result['omitted_lists']} empty/incompatible).")


if __name__ == "__main__":
    main()
