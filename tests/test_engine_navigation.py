"""不启动浏览器地验证导航等待可中断且总超时预算不变。"""

import unittest
from unittest import mock

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from engines.base import BaseEngine


class _Clock:
    def __init__(self):
        self.now = 0.0


class _FakePage:
    def __init__(
        self,
        clock,
        succeed_after=None,
        timeout_during_commit=False,
        keep_initial_url=False,
        url_change_after_waits=None,
    ):
        self.clock = clock
        self.succeed_after = succeed_after
        self.timeout_during_commit = timeout_during_commit
        self.keep_initial_url = keep_initial_url
        self.url_change_after_waits = url_change_after_waits
        self.goto_calls = []
        self.wait_calls = []
        self.url = "about:blank"
        self.main_frame = object()
        self.listeners = {}
        self.url_wait_count = 0

    def on(self, event, callback):
        self.listeners[event] = callback

    def remove_listener(self, event, callback):
        self.listeners.pop(event, None)

    def goto(self, url, **kwargs):
        self.goto_calls.append((url, kwargs))
        if self.timeout_during_commit:
            self.clock.now += kwargs["timeout"] / 1000
            raise PlaywrightTimeoutError("commit slice timed out")
        if not self.keep_initial_url:
            self.url = url
        return "response"

    def wait_for_url(self, predicate, timeout):
        self.wait_calls.append(("url", timeout))
        self.url_wait_count += 1
        if (
            self.url_change_after_waits is not None
            and self.url_wait_count >= self.url_change_after_waits
        ):
            self.url = "https://example.test/redirected"
            return
        self.clock.now += timeout / 1000
        raise PlaywrightTimeoutError("URL slice timed out")

    def wait_for_timeout(self, timeout):
        self.wait_calls.append(("timeout", timeout))
        self.clock.now += timeout / 1000

    def wait_for_load_state(self, state, timeout):
        self.wait_calls.append((state, timeout))
        if self.succeed_after is not None and self.clock.now + timeout / 1000 >= self.succeed_after:
            self.clock.now = self.succeed_after
            return
        self.clock.now += timeout / 1000
        raise PlaywrightTimeoutError("load-state slice timed out")


class _FakeApp:
    def __init__(self, clock, stop_at=None, timeout_cap=None):
        self.clock = clock
        self.stop_at = stop_at
        self.navigation_timeout_cap_ms = timeout_cap
        self.logs = []

    def should_stop(self):
        return self.stop_at is not None and self.clock.now >= self.stop_at

    def log(self, message):
        self.logs.append(message)


class EngineNavigationTests(unittest.TestCase):
    def _run_with_clock(self, engine, page, clock, timeout=1000):
        with mock.patch("engines.base.time.monotonic", side_effect=lambda: clock.now):
            return engine.goto_with_stop(
                page, "https://example.test", wait_until="domcontentloaded", timeout=timeout
            )

    def test_stop_during_load_state_wait_returns_early_with_stop_log(self):
        clock = _Clock()
        app = _FakeApp(clock, stop_at=0.25)
        page = _FakePage(clock)

        engine = BaseEngine(app)
        result = self._run_with_clock(engine, page, clock)

        self.assertIsNone(result)
        self.assertTrue(engine.navigation_stopped)
        self.assertEqual(clock.now, 0.25)
        self.assertEqual(app.logs, ["用户停止，已中断页面导航"])
        self.assertEqual(page.goto_calls[0][1]["wait_until"], "commit")
        self.assertEqual(page.goto_calls[0][1]["timeout"], 250)
        self.assertEqual(sum(timeout for _, timeout in page.wait_calls), 250)

    def test_stop_during_commit_wait_returns_after_one_short_slice(self):
        clock = _Clock()
        app = _FakeApp(clock, stop_at=0.25)
        page = _FakePage(clock, timeout_during_commit=True)
        engine = BaseEngine(app)

        result = self._run_with_clock(engine, page, clock)

        self.assertIsNone(result)
        self.assertTrue(engine.navigation_stopped)
        self.assertEqual(clock.now, 0.25)
        self.assertEqual(page.goto_calls[0][1]["timeout"], 250)
        self.assertEqual(app.logs, ["用户停止，已中断页面导航"])

    def test_stop_during_followup_url_wait_is_logged_without_error(self):
        clock = _Clock()
        app = _FakeApp(clock, stop_at=0.25)
        page = _FakePage(clock)
        engine = BaseEngine(app)

        with mock.patch("engines.base.time.monotonic", side_effect=lambda: clock.now):
            engine.wait_for_url_with_stop(
                page, lambda current_url: "result" in current_url, timeout=12000
            )

        self.assertTrue(engine.navigation_stopped)
        self.assertEqual(clock.now, 0.25)
        self.assertEqual(app.logs, ["用户停止，已中断页面导航等待"])

    def test_navigation_success_keeps_wait_until_target(self):
        clock = _Clock()
        app = _FakeApp(clock)
        page = _FakePage(clock, succeed_after=0.4)
        engine = BaseEngine(app)

        response = self._run_with_clock(engine, page, clock)

        self.assertEqual(response, "response")
        self.assertFalse(engine.navigation_stopped)
        self.assertEqual(page.wait_calls[0], ("domcontentloaded", 250))
        self.assertEqual(clock.now, 0.4)
        self.assertEqual(app.logs, [])

    def test_response_does_not_accept_old_document_load_state(self):
        clock = _Clock()
        app = _FakeApp(clock)
        page = _FakePage(clock, keep_initial_url=True, succeed_after=0.0)
        engine = BaseEngine(app)

        with self.assertRaises(PlaywrightTimeoutError):
            self._run_with_clock(engine, page, clock, timeout=1000)

        self.assertEqual(clock.now, 1.0)
        self.assertEqual(page.url_wait_count, 4)
        self.assertFalse(any(state == "domcontentloaded" for state, _ in page.wait_calls))

    def test_response_and_load_state_suffice_when_target_is_current_url(self):
        clock = _Clock()
        app = _FakeApp(clock)
        page = _FakePage(clock, keep_initial_url=True, succeed_after=0.0)
        engine = BaseEngine(app)

        with mock.patch("engines.base.time.monotonic", side_effect=lambda: clock.now):
            response = engine.goto_with_stop(
                page, "about:blank", wait_until="domcontentloaded", timeout=1000
            )

        self.assertEqual(response, "response")
        self.assertEqual(page.url_wait_count, 0)
        self.assertEqual(clock.now, 0.0)

    def test_waits_for_url_change_before_loading_state_then_returns(self):
        clock = _Clock()
        app = _FakeApp(clock)
        page = _FakePage(
            clock,
            keep_initial_url=True,
            url_change_after_waits=2,
            succeed_after=0.4,
        )
        engine = BaseEngine(app)

        response = self._run_with_clock(engine, page, clock)

        self.assertEqual(response, "response")
        self.assertEqual(page.url_wait_count, 2)
        self.assertEqual(clock.now, 0.4)
        self.assertEqual(
            [state for state, _ in page.wait_calls if state == "domcontentloaded"],
            ["domcontentloaded"],
        )

    def test_timeout_uses_original_budget_in_bounded_slices(self):
        clock = _Clock()
        app = _FakeApp(clock)
        page = _FakePage(clock)
        engine = BaseEngine(app)

        with self.assertRaises(PlaywrightTimeoutError):
            self._run_with_clock(engine, page, clock, timeout=1000)

        self.assertAlmostEqual(clock.now, 1.0)
        self.assertEqual(sum(timeout for _, timeout in page.wait_calls), 1000)
        self.assertLessEqual(max(timeout for _, timeout in page.wait_calls), 250)

    def test_smoke_navigation_cap_is_limited_without_changing_regular_calls(self):
        clock = _Clock()
        app = _FakeApp(clock, timeout_cap=500)
        page = _FakePage(clock)
        engine = BaseEngine(app)

        with self.assertRaises(PlaywrightTimeoutError):
            self._run_with_clock(engine, page, clock, timeout=30000)

        self.assertEqual(sum(timeout for _, timeout in page.wait_calls), 500)


if __name__ == "__main__":
    unittest.main()
