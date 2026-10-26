"""使用 Node 内置运行时比较真实前端行逻辑与原有逐行刷新路径。"""

import shutil
import subprocess
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HARNESS = Path(__file__).with_name("frontend_results_harness.js")


@unittest.skipUnless(shutil.which("node"), "Node.js is required for frontend logic tests")
class FrontendResultsTests(unittest.TestCase):
    def test_incremental_rows_match_full_refresh_behavior(self):
        result = subprocess.run(
            [
                shutil.which("node"),
                str(HARNESS),
                str(PROJECT_ROOT / "index.html"),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        self.assertEqual(result.returncode, 0, (result.stdout or "") + (result.stderr or ""))
        self.assertIn("frontend row equivalence: OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
