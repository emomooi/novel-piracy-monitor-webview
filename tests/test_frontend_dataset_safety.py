"""Static guards for dataset access in the frontend's vulnerable callbacks."""

import re
import unittest
from html.parser import HTMLParser
from pathlib import Path


INDEX_HTML = Path(__file__).resolve().parents[1] / "index.html"
DIRECT_DATASET_ACCESS = re.compile(r"\b(?:r|a|b|row|cb|el)\.dataset(?:\.|\b)")


class ScriptSourceParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.sources = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "script":
            attributes = dict(attrs)
            if attributes.get("src"):
                self.sources.append(attributes["src"])


class FrontendDatasetSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = INDEX_HTML.read_text(encoding="utf-8")
        parser = ScriptSourceParser()
        parser.feed(cls.html)
        cls.js_source = "\n".join(
            (INDEX_HTML.parent / source).resolve().read_text(encoding="utf-8")
            for source in parser.sources
        )

    def source_between(self, start, end):
        start_index = self.js_source.index(start)
        end_index = self.js_source.index(end, start_index)
        return self.js_source[start_index:end_index]

    def test_dataset_helper_checks_element_and_dataset(self):
        self.assertRegex(
            self.js_source,
            re.compile(
                r"function getDataset\(element\)\s*\{\s*"
                r"return element && element\.dataset \? element\.dataset : \{\};\s*\}"
            ),
        )

    def test_targeted_callbacks_do_not_read_dataset_directly(self):
        guarded_regions = (
            ("function collectRowItems(rows) {", "  /* 「复制链接」"),
            (
                "function compareRowsByDisplayOrder(a, b) {",
                "  /* 白名单行沉底 +",
            ),
            ("function sortByDateDesc(rows) {", "    sortByDateDesc(normalRows);"),
            ("function applyFilterToRow(r) {", "  window.applyFilters = function () {"),
            ("var btnTbExport = document.getElementById", "var btnTbOpen ="),
            ("window.applyWhitelistWords = function () {", "  /* ==================== 验证码弹窗"),
            ("popup.querySelectorAll('.sf-cb')", "    // 新增"),
        )
        for start, end in guarded_regions:
            with self.subTest(region=start):
                source = self.source_between(start, end)
                self.assertIn("getDataset(", source)
                self.assertIsNone(DIRECT_DATASET_ACCESS.search(source))


if __name__ == "__main__":
    unittest.main()
