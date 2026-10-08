import json
import tempfile
import unittest
from pathlib import Path

from scripts.convert import export, load_lists, resolve_all, valid_domain


class ConverterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.data = self.base / "data"
        self.data.mkdir()

    def add(self, name, contents):
        (self.data / name).write_text(contents, encoding="utf-8")

    def test_domains_includes_and_attributes(self):
        self.add("netflix", "netflix.com\nfull:netflix.com.edgesuite.net\nregexp:^whatever$\nkeyword:nflx\n")
        self.add("source", "domain:ads.example.com @ads &affiliate\nfull:clean.example.com @good\nfoo.example.com\n")
        self.add("filtered", "include:source @good\ninclude:source @-ads\n")
        report = export(self.data, self.base / "lists", self.base / "manifest.json", self.base / "LISTS.md", "test-sha")
        self.assertEqual((self.base / "lists/netflix.txt").read_text(), "netflix.com\nnetflix.com.edgesuite.net\n")
        self.assertEqual((self.base / "lists/filtered.txt").read_text(), "clean.example.com\nfoo.example.com\n")
        self.assertEqual((self.base / "lists/affiliate.txt").read_text(), "ads.example.com\n")
        self.assertEqual(report["lists"]["netflix"]["skipped_regex"], 1)
        self.assertEqual(report["lists"]["netflix"]["skipped_keyword"], 1)
        self.assertEqual(json.loads((self.base / "manifest.json").read_text())["upstream_revision"], "test-sha")

    def test_unsupported_and_invalid_domain_skipped(self):
        self.add("only-regexp", "regexp:^ads.*$\n")
        self.add("bad", "localhost\ndomain:sub.example.org\nfull:192.168.1.1\n")
        report = export(self.data, self.base / "lists", self.base / "manifest.json", self.base / "LISTS.md", "test")
        self.assertFalse((self.base / "lists/only-regexp.txt").exists())
        self.assertEqual((self.base / "lists/bad.txt").read_text(), "sub.example.org\n")
        self.assertEqual(report["omitted_lists"], 1)
        self.assertEqual(report["lists"]["bad"]["skipped_invalid_or_single_label"], 2)

    def test_detect_missing_include(self):
        self.add("a", "include:missing\n")
        with self.assertRaisesRegex(ValueError, "not found"):
            resolve_all(*load_lists(self.data))

    def test_detect_circular_include(self):
        self.add("a", "include:b\n")
        self.add("b", "include:a\n")
        with self.assertRaisesRegex(ValueError, "Circular include"):
            resolve_all(*load_lists(self.data))

    def test_valid_domain(self):
        self.assertTrue(valid_domain("fast.com"))
        self.assertFalse(valid_domain("a..com"))
        self.assertFalse(valid_domain("*.com"))
        self.assertFalse(valid_domain("127.0.0.1"))
        self.assertFalse(valid_domain("com"))


if __name__ == "__main__":
    unittest.main()
