# UniFi External Lists

Automatically updated domain lists for **UniFi Network 11.0.81+**.

UniFi Network 11.0 introduced External Network Lists, making it possible to load domain lists from external URLs. This repository provides plain-text lists converted from [V2Fly's Domain List Community](https://github.com/v2fly/domain-list-community).

## Usage

1. Browse the [available lists](LISTS.md).
2. Copy the raw URL of the list you want.
3. Add the URL as a domain-based **External Network List** in UniFi.

**Example: Netflix**

```text
https://raw.githubusercontent.com/MiranoVerhoef/unifi-external-lists/main/lists/netflix.txt
```

Other examples: [YouTube](lists/youtube.txt) · [Disney](lists/disney.txt) · [Google](lists/google.txt)

## Updates

GitHub Actions checks for updates every **6 hours**. Changes to existing lists and newly added upstream lists are published automatically. UniFi refreshes the URLs on its own schedule.

See [all available lists](LISTS.md) for the generated list index.

## Compatibility

- **UniFi Network 11.0.81+** and **UniFi OS 6.0.10+** are required for External Network Lists.
- Outputs contain one domain per line. Unsupported matching rules are omitted, so conversions may not exactly match the original lists.
- Large lists may exceed device limits. Import only lists needed for your rules.
- Domain-list import and policy compatibility should be verified with your UniFi version.

## Source

Domain data: [v2fly/domain-list-community](https://github.com/v2fly/domain-list-community) (MIT License; see [UPSTREAM_LICENSE](UPSTREAM_LICENSE)). This project is not affiliated with Ubiquiti or V2Fly.
