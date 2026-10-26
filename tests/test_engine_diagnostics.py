"""验证引擎诊断只在空页时转发到界面日志。"""

import threading
import unittest
from types import SimpleNamespace
from unittest import mock

import main


class EngineDiagnosticsTests(unittest.TestCase):
    def _run_fake_engine(self, diagnostics, page_results, matched_count=1):
        logs = []

        class FakeEngine:
            def __init__(self, adapter):
                self.diagnostics = list(diagnostics)

            def fetch(self, context, term, page_num=0, book_kw=""):
                return page_results

        api = main.Api()
        api.push_log = logs.append
        api._emit_page_results = mock.Mock(return_value=(matched_count, False))
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
                1,
                set(),
            )

        return result, logs, api

    def test_empty_page_with_diagnostics_pushes_log(self):
        result, logs, _ = self._run_fake_engine(
            ["未解析到结果卡片"], []
        )

        self.assertEqual(result, (0, 0))
        self.assertEqual(
            logs,
            ["测试来源 第 1 页诊断：未解析到结果卡片"],
        )

    def test_empty_page_without_diagnostics_does_not_push_log(self):
        result, logs, _ = self._run_fake_engine([], [])

        self.assertEqual(result, (0, 0))
        self.assertEqual(logs, [])

    def test_duplicate_diagnostics_are_pushed_once(self):
        result, logs, _ = self._run_fake_engine(
            ["首条诊断", "重复诊断", "重复诊断", "末条诊断"], []
        )

        self.assertEqual(result, (0, 0))
        self.assertEqual(
            logs,
            [
                "测试来源 第 1 页诊断：首条诊断",
                "测试来源 第 1 页诊断：重复诊断",
                "测试来源 第 1 页诊断：末条诊断",
            ],
        )

    def test_page_with_results_does_not_push_diagnostic_log(self):
        result, logs, api = self._run_fake_engine(
            ["此前诊断"], [{"title": "结果", "url": "https://example.test"}]
        )

        self.assertEqual(result, (1, 1))
        self.assertEqual(logs, [])
        api._emit_page_results.assert_called_once()

    def test_zero_matches_keeps_existing_log_and_appends_diagnostic(self):
        result, logs, _ = self._run_fake_engine(
            ["结果未匹配"], [{"title": "结果", "url": "https://example.test"}],
            matched_count=0,
        )

        self.assertEqual(result, (1, 0))
        self.assertEqual(
            logs,
            [
                "测试来源 第 1 页 0 命中，停止翻页",
                "测试来源 第 1 页诊断：结果未匹配",
            ],
        )


if __name__ == "__main__":
    unittest.main()
