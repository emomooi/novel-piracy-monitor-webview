"""并发访问共享历史与白名单状态的隔离测试。"""

import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

import main


class _ApiStub:
    def push_log(self, message):
        return "ok"


class SharedStateConcurrencyTests(unittest.TestCase):
    def test_seen_updates_and_locked_saves_remain_valid_and_complete(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "seen_urls.json"
            errors = []
            stop_reader = threading.Event()
            barrier = threading.Barrier(7)

            with (
                mock.patch.object(main, "SEEN_URLS_FILE", str(target)),
                mock.patch.object(main, "_seen_urls", {}),
                mock.patch.object(main, "_seen_urls_loaded", True),
                mock.patch.object(main, "_seen_urls_lock", threading.RLock()),
            ):
                main._save_seen_urls()

                def write_history(worker_id):
                    barrier.wait()
                    for index in range(30):
                        url = f"https://example.test/{worker_id}/{index}"
                        main._mark_seen(url, f"book-{worker_id}", "测试来源")
                        main._save_seen_urls()

                def read_file():
                    barrier.wait()
                    while not stop_reader.is_set():
                        try:
                            with main._seen_urls_lock:
                                with target.open("r", encoding="utf-8") as stream:
                                    loaded = json.load(stream)
                            if not isinstance(loaded, dict):
                                errors.append("history JSON was not an object")
                        except Exception as exc:
                            errors.append(f"{type(exc).__name__}: {exc}")
                            stop_reader.set()

                reader = threading.Thread(target=read_file)
                writers = [
                    threading.Thread(target=write_history, args=(worker_id,))
                    for worker_id in range(6)
                ]
                reader.start()
                for writer in writers:
                    writer.start()
                for writer in writers:
                    writer.join()
                stop_reader.set()
                reader.join()

                main._save_seen_urls()
                saved = json.loads(target.read_text(encoding="utf-8"))

            self.assertEqual(errors, [])
            self.assertEqual(len(saved), 6 * 30)
            self.assertTrue(all(set(item) == {"book", "source"} for item in saved.values()))
            self.assertEqual(list(Path(temp_dir).iterdir()), [target])

    def test_whitelist_concurrent_api_changes_and_reads_are_safe(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "monitor_whitelist_common.json"
            errors = []
            barrier = threading.Barrier(9)
            api = main.Api()
            api.push_log = _ApiStub().push_log
            engine_app = main.WebViewAppAdapter("test", api)

            with (
                mock.patch.object(main, "WHITELIST_COMMON_FILE", str(target)),
                mock.patch.object(main, "_whitelist_common", set()),
                mock.patch.object(main, "_wl_loaded", True),
                mock.patch.object(main, "_whitelist_words", {"keep"}),
                mock.patch.object(main, "_wlw_loaded", True),
                mock.patch.object(main, "_wl_lock", threading.RLock()),
            ):
                engine_app.whitelist_common = main._whitelist_common
                main._save_whitelist()

                def update(worker_id):
                    try:
                        barrier.wait()
                        for index in range(60):
                            url = f"https://example.test/{index % 10}"
                            if (index + worker_id) % 2:
                                api.add_to_whitelist([url])
                            else:
                                api.remove_from_whitelist([url])
                            api.get_whitelist_words()
                            api.check_whitelist_word(url)
                            engine_app.is_whitelisted(url)
                    except Exception as exc:
                        errors.append(f"{type(exc).__name__}: {exc}")

                threads = [
                    threading.Thread(target=update, args=(worker_id,))
                    for worker_id in range(8)
                ]
                for thread in threads:
                    thread.start()
                with mock.patch("builtins.print"):
                    barrier.wait()
                    for thread in threads:
                        thread.join()

                self.assertEqual(errors, [])
                final_set = set(main._whitelist_common)
                saved = json.loads(target.read_text(encoding="utf-8"))

            self.assertEqual(errors, [])
            self.assertTrue(all(isinstance(value, str) for value in final_set))
            self.assertEqual(saved, sorted(final_set))

    def test_bookmark_api_mutations_and_reads_are_safe(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "bookmarks.json"
            errors = []
            barrier = threading.Barrier(5)
            api = main.Api()
            api.push_log = _ApiStub().push_log
            api._push_bookmarks_changed = lambda: None

            with (
                mock.patch.object(main, "BOOKMARKS_FILE", str(target)),
                mock.patch.object(main, "_bookmarks", []),
                mock.patch.object(main, "_bm_loaded", True),
                mock.patch.object(main, "_bm_lock", threading.RLock()),
            ):
                def update(worker_id):
                    try:
                        barrier.wait()
                        for index in range(25):
                            api.add_bookmark(f"book-{worker_id}-{index}")
                            api.get_bookmarks()
                    except Exception as exc:
                        errors.append(f"{type(exc).__name__}: {exc}")

                threads = [
                    threading.Thread(target=update, args=(worker_id,))
                    for worker_id in range(4)
                ]
                for thread in threads:
                    thread.start()
                barrier.wait()
                for thread in threads:
                    thread.join()

                self.assertEqual(errors, [])
                saved = json.loads(target.read_text(encoding="utf-8"))

            self.assertEqual(len(saved), 4 * 25)
            self.assertTrue(all(isinstance(item, dict) for item in saved))


if __name__ == "__main__":
    unittest.main()
