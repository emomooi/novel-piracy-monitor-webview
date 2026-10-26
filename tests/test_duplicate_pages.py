"""回归测试：相邻页内容相同时停止无意义翻页。"""

import threading
import unittest
from types import SimpleNamespace
from unittest import mock

import main


class DuplicatePageTests(unittest.TestCase):
    def _run_pages(self, results_by_page, max_pages=4):
        logs = []
        fetched_pages = []
        api = main.Api()
        api.push_log = logs.append
        api._emit_page_results = mock.Mock(return_value=(1, False))

        class FakeEngine:
            def __init__(self, adapter):
                pass

            def fetch(self, context, term, page_num=0, book_kw=""):
                fetched_pages.append(page_num)
                return results_by_page[page_num]

        adapter = SimpleNamespace(captcha_hit=False, keep_page=False)
        with (
            mock.patch.object(main, "ENGINE_MAP", {"test": FakeEngine}),
            mock.patch.object(main, "_stop_event", threading.Event()),
        ):
            result = api._run_one_engine(
                adapter,
                None,
                "test",
                "test",
                "测试来源",
                "搜索词",
                "作品名",
                max_pages,
                set(),
            )

        return result, logs, fetched_pages, api

    def test_repeated_page_stops_after_second_fetch(self):
        repeated_results = [
            {"title": "相同结果甲", "url": "https://example.test/a"},
            {"title": "相同结果乙", "url": "https://example.test/b"},
        ]
        result, logs, fetched_pages, api = self._run_pages(
            {
                0: repeated_results,
                1: [
                    {"title": "相同结果乙", "url": "https://other.test/b"},
                    {"title": "相同结果甲", "url": "https://other.test/a"},
                ],
                2: [{"title": "不应抓取", "url": "https://example.test/c"}],
                3: [{"title": "不应抓取", "url": "https://example.test/d"}],
            }
        )

        self.assertEqual(fetched_pages, [0, 1])
        self.assertEqual(result, (2, 1))
        self.assertEqual(
            logs,
            [
                "测试来源 第 2 页与上一页内容相同，停止翻页（该来源可能不支持翻页）"
            ],
        )
        self.assertEqual(api._emit_page_results.call_count, 1)

    def test_distinct_pages_continue_to_page_limit_without_repeat_log(self):
        results_by_page = {
            page_num: [
                {
                    "title": f"第 {page_num + 1} 页结果",
                    "url": f"https://example.test/{page_num}",
                }
            ]
            for page_num in range(4)
        }

        _, logs, fetched_pages, api = self._run_pages(results_by_page)

        self.assertEqual(fetched_pages, [0, 1, 2, 3])
        self.assertEqual(logs, [])
        self.assertEqual(api._emit_page_results.call_count, 4)

    def test_empty_second_page_is_not_reported_as_repeated(self):
        _, logs, fetched_pages, api = self._run_pages(
            {
                0: [{"title": "第一页结果", "url": "https://example.test/1"}],
                1: [],
                2: [{"title": "第三页结果", "url": "https://example.test/3"}],
            }
        )

        self.assertEqual(fetched_pages, [0, 1])
        self.assertFalse(any("内容相同" in line for line in logs))
        self.assertEqual(api._emit_page_results.call_count, 1)


if __name__ == "__main__":
    unittest.main()
