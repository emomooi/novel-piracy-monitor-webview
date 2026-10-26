"""验证引擎随机等待可中断且保持原有总时长。"""

import threading
import unittest
from unittest import mock

import main

from engines.base import BaseEngine


class EngineWaitTests(unittest.TestCase):
    def _mock_clock(self):
        clock = [0.0]
        sleeps = []

        def sleep(seconds):
            sleeps.append(seconds)
            clock[0] += seconds

        patches = (
            mock.patch("engines.base.time.monotonic", side_effect=lambda: clock[0]),
            mock.patch("engines.base.time.sleep", side_effect=sleep),
            mock.patch("engines.base.random.uniform", return_value=0.65),
        )
        return clock, sleeps, patches

    def test_wait_without_stop_keeps_random_duration_and_limits_slices(self):
        clock, sleeps, patches = self._mock_clock()
        app = mock.Mock()
        app.should_stop.return_value = False
        with patches[0], patches[1], patches[2]:
            BaseEngine(app).wait_random(0.5, 1.0)

        self.assertAlmostEqual(sum(sleeps), 0.65, delta=0.001)
        self.assertAlmostEqual(clock[0], 0.65, delta=0.001)
        self.assertTrue(sleeps)
        self.assertLessEqual(max(sleeps), 0.25)
        self.assertTrue(all(sleep > 0 for sleep in sleeps))

    def test_wait_returns_early_when_stop_is_set(self):
        clock, sleeps, patches = self._mock_clock()
        app = mock.Mock()
        app.should_stop.side_effect = lambda: clock[0] >= 0.25
        with patches[0], patches[1], patches[2]:
            BaseEngine(app).wait_random(0.5, 1.0)

        self.assertEqual(sleeps, [0.25])
        self.assertLess(sum(sleeps), 0.65)

    def test_app_without_stop_method_is_safe(self):
        _, sleeps, patches = self._mock_clock()
        with patches[0], patches[1], patches[2]:
            BaseEngine(object()).wait_random(0.5, 1.0)

        self.assertAlmostEqual(sum(sleeps), 0.65, delta=0.001)

    def test_webview_adapter_reads_search_stop_event(self):
        adapter = main.WebViewAppAdapter("test", main.Api())
        stop_event = threading.Event()
        with mock.patch.object(main, "_stop_event", stop_event):
            self.assertFalse(adapter.should_stop())
            stop_event.set()
            self.assertTrue(adapter.should_stop())
