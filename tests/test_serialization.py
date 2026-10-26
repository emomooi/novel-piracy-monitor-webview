"""确保白名单与历史 JSON 序列化契约不变；所有文件均写入临时目录。

为避免导入主程序的桌面与浏览器依赖，本测试用 AST 隔离执行 main.py 中的
真实保存函数；它验证函数体与序列化形状，但不覆盖主程序模块的初始化过程。
"""

import ast
import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path

from utils import save_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_function_from_main(function_name, namespace):
    source = (PROJECT_ROOT / "main.py").read_text(encoding="utf-8")
    module = ast.parse(source)
    function_node = next(
        node for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name == function_name
    )
    isolated_module = ast.Module(body=[function_node], type_ignores=[])
    exec(compile(isolated_module, "main.py", "exec"), namespace)
    return namespace[function_name]


class SerializationTests(unittest.TestCase):
    def test_whitelist_remains_a_sorted_string_array(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "monitor_whitelist_common.json"
            save_whitelist = _load_function_from_main(
                "_save_whitelist",
                {
                    "WHITELIST_COMMON_FILE": str(target),
                    "_whitelist_common": {"https://z.example", "https://a.example"},
                    "_wl_lock": threading.RLock(),
                    "save_json": save_json,
                    "sys": sys,
                },
            )
            save_whitelist()

            self.assertEqual(
                json.loads(target.read_text(encoding="utf-8")),
                ["https://a.example", "https://z.example"],
            )

    def test_seen_history_remains_url_to_book_source_object(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "seen_urls.json"
            history = {
                "https://example.test/chapter": {
                    "book": "测试作品",
                    "source": "百度",
                }
            }
            save_history = _load_function_from_main(
                "_save_seen_urls",
                {
                    "SEEN_URLS_FILE": str(target),
                    "_seen_urls": history,
                    "_seen_urls_lock": threading.RLock(),
                    "json": json,
                    "os": os,
                    "sys": sys,
                },
            )
            save_history()

            saved = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(saved, history)
            self.assertEqual(
                set(saved["https://example.test/chapter"]),
                {"book", "source"},
            )


if __name__ == "__main__":
    unittest.main()
