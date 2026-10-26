"""验证历史记录加载时按 common 白名单补充加白状态。"""

import threading
import unittest
from unittest import mock

import main


class HistoryWhitelistTests(unittest.TestCase):
    def test_load_history_marks_urls_in_common_whitelist(self):
        history = {
            "https://example.test/white": {"book": "加白作品", "source": "百度"},
            "https://example.test/plain": {"book": "普通作品", "source": "知道"},
            "https://example.test/white-word": {"book": "白名单词作品", "source": "搜狗"},
        }
        common_whitelist = {
            "https://example.test/white",
            "https://example.test/white-word",
        }
        api = main.Api()

        with (
            mock.patch.object(main, "_load_seen_urls") as load_seen,
            mock.patch.object(main, "_load_whitelist") as load_whitelist,
            mock.patch.object(main, "_seen_urls", history),
            mock.patch.object(main, "_seen_urls_lock", threading.RLock()),
            mock.patch.object(main, "_whitelist_common", common_whitelist),
            mock.patch.object(main, "_wl_lock", threading.RLock()),
            mock.patch("builtins.print"),
        ):
            records = api.load_history()

        load_seen.assert_called_once_with()
        load_whitelist.assert_called_once_with()
        self.assertEqual(
            {record["url"]: record["is_white"] for record in records},
            {
                "https://example.test/white": True,
                "https://example.test/plain": False,
                "https://example.test/white-word": True,
            },
        )
        self.assertTrue(all(isinstance(record["is_white"], bool) for record in records))


if __name__ == "__main__":
    unittest.main()
