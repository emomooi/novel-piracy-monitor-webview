"""联网冒烟默认关闭；仅测试参数门控和报告格式，不访问网络。"""

import io
import unittest
from contextlib import redirect_stdout
from unittest import mock

from tests import network_smoke


class NetworkSmokeTests(unittest.TestCase):
    def test_network_is_not_started_without_explicit_flag(self):
        output = io.StringIO()
        with (
            mock.patch.object(network_smoke, "_run_network_smoke") as run,
            redirect_stdout(output),
        ):
            status = network_smoke.run_from_args(network_smoke.parse_args([]))

        self.assertEqual(status, 0)
        run.assert_not_called()
        self.assertIn("联网冒烟未启用", output.getvalue())

    def test_flag_is_parsed_and_report_format_is_readable(self):
        self.assertTrue(network_smoke.parse_args(["--run-network"]).run_network)
        report = network_smoke.format_source_report(
            "头条PC", "失败", "第 2 页仅解析到 0 条", (4, 0), ("标题甲", "标题乙")
        )

        self.assertEqual(
            report,
            "头条PC：失败；第 2 页仅解析到 0 条；抓取条数（页）：4/0；"
            "前两条标题：标题甲；标题乙",
        )


if __name__ == "__main__":
    unittest.main()
