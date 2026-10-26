"""Static guards for dataset access in the frontend's vulnerable callbacks."""

import re
import unittest
from pathlib import Path


INDEX_HTML = Path(__file__).resolve().parents[1] / "index.html"
DIRECT_DATASET_ACCESS = re.compile(r"\b(?:r|a|b|row|cb|el)\.dataset(?:\.|\b)")


class FrontendDatasetSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = INDEX_HTML.read_text(encoding="utf-8")

    def source_between(self, start, end):
        start_index = self.html.index(start)
        end_index = self.html.index(end, start_index)
        return self.html[start_index:end_index]

    def test_dataset_helper_checks_element_and_dataset(self):
        self.assertRegex(
            self.html,
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
