"""参数化验证码检测 helper 与各引擎特征快照。"""

import unittest
from unittest import mock

from engines import ALL_ENGINE_MAP
from engines.base import BaseEngine


CAPTCHA_FEATURE_SNAPSHOTS = {
    "baidu": {
        "CAPTCHA_URL_TOKENS": ("wappass", "verify", "captcha"),
    },
    "baidu_mobile": {
        "CAPTCHA_URL_TOKENS": ("wappass", "verify", "captcha", "/punish", "sec-bot"),
        "CAPTCHA_TEXT_TOKENS": ("安全验证", "人机验证", "请完成验证", "滑块验证", "验证码拦截"),
    },
    "zhidao": {
        "CAPTCHA_URL_TOKENS": ("wappass", "verify", "captcha", "passport"),
    },
    "zhidao_mobile": {
        "CAPTCHA_URL_TOKENS": ("wappass", "verify", "captcha", "passport"),
    },
    "tieba": {
        "CAPTCHA_URL_TOKENS": ("wappass", "verify", "captcha", "passport"),
    },
    "bing": {
        "CAPTCHA_URL_TOKENS": ("captcha", "verify", "security", "challenge"),
        "CAPTCHA_TEXT_TOKENS": (
            "请解决以下难题", "请验证", "安全验证", "人机验证",
            "verify you are human", "unusual traffic",
        ),
        "CAPTCHA_SECOND_TEXT_TOKENS": (
            "请解决以下难题", "请验证", "安全验证", "人机验证",
            "最后一步", "正在验证", "verify you are human", "unusual traffic",
        ),
    },
    "so360_pc": {
        "CAPTCHA_URL_TOKENS": ("captcha", "verify", "wappass"),
    },
    "so360_mobile": {
        "CAPTCHA_URL_TOKENS": ("captcha", "verify", "wappass"),
        "CAPTCHA_TEXT_TOKENS": ("验证码", "人机验证"),
    },
    "toutiao_pc": {
        "CAPTCHA_URL_TOKENS": ("captcha", "verify", "challenge", "secsdk"),
        "CAPTCHA_TEXTS": (
            "请完成下列验证", "请完成安全验证", "请完成验证",
            "完成下列验证后继续", "完成验证后继续", "人机验证",
            "安全验证", "滑动验证", "滑块验证", "拖动完成", "拖动滑块",
            "按住左边按钮拖动", "拼图", "请依次点击", "请按顺序点击",
        ),
        "CAPTCHA_DOM_SELECTORS": (
            ".captcha", "#captcha",
            ".captcha-verify", "#captcha-verify",
            ".secsdk-captcha", ".verify-wrap",
            ".captcha_verify_container", ".vc-container", ".verify-bar",
            'iframe[src*="captcha"]', 'iframe[src*="verify"]',
        ),
    },
    "toutiao_mobile": {
        "CAPTCHA_URL_TOKENS": ("captcha", "verify", "security"),
        "CAPTCHA_TEXT_TOKENS": ("人机验证",),
    },
    "sogou_mobile": {
        "CAPTCHA_URL_TOKENS": ("captcha", "verify", "antispider"),
        "CAPTCHA_TEXT_TOKENS": ("验证码", "人机验证"),
    },
    "sogou_pc": {
        "CAPTCHA_URL_TOKENS": ("captcha", "verify", "antispider"),
        "CAPTCHA_TEXT_TOKENS": (
            "验证码", "人机验证", "访问过于频繁",
            "403 forbidden", "forbidden", "反爬",
        ),
    },
    "sogou_weixin": {
        "JUMP_CAPTCHA_URL_TOKENS": ("antispider", "verify", "captcha"),
        "JUMP_CAPTCHA_TEXT_TOKENS": ("verifycode", "请输入验证码", "人机验证"),
        "SEARCH_CAPTCHA_URL_TOKENS": ("captcha", "verify"),
        "SEARCH_CAPTCHA_TEXT_TOKENS": ("验证码", "人机验证"),
    },
    "quark": {
        "CAPTCHA_URL_TOKENS": ("_____tmd_____", "/punish", "captcha", "verify", "wappass"),
        "CAPTCHA_TEXT_TOKENS": ("验证码拦截", "安全验证", "人机验证", "请完成验证", "滑块验证"),
    },
    "quark_cn": {
        "CAPTCHA_URL_TOKENS": ("_____tmd_____", "/punish", "captcha", "verify", "wappass"),
        "CAPTCHA_TEXT_TOKENS": ("验证码拦截", "安全验证", "人机验证", "请完成验证", "滑块验证"),
    },
    "quark_m": {
        "CAPTCHA_URL_TOKENS": ("_____tmd_____", "/punish", "captcha", "verify", "wappass"),
        "CAPTCHA_TEXT_TOKENS": ("验证码拦截", "安全验证", "人机验证", "请完成验证", "滑块验证"),
    },
    "quark_so": {
        "CAPTCHA_URL_TOKENS": ("_____tmd_____", "/punish", "captcha", "verify", "wappass"),
        "CAPTCHA_TEXT_TOKENS": ("验证码拦截", "安全验证", "人机验证", "请完成验证", "滑块验证"),
    },
    "weibo": {
        "CAPTCHA_URL_TOKENS": ("captcha", "verify"),
        "CAPTCHA_TEXT_TOKENS": ("验证码", "人机验证"),
    },
    "weibo_mobile": {},
}


class _Page:
    url = "https://example.test/captcha"

    def text_content(self, selector):
        return "请完成安全验证"

    def evaluate(self, script, selectors):
        return "#challenge" in selectors


class EngineCaptchaTests(unittest.TestCase):
    def test_engine_captcha_feature_snapshots(self):
        self.assertEqual(set(ALL_ENGINE_MAP), set(CAPTCHA_FEATURE_SNAPSHOTS))
        for source_id, expected_features in CAPTCHA_FEATURE_SNAPSHOTS.items():
            engine_class = ALL_ENGINE_MAP[source_id]
            with self.subTest(source=source_id):
                for name, expected in expected_features.items():
                    self.assertEqual(getattr(engine_class, name), expected)
                for name in (
                    "CAPTCHA_URL_TOKENS",
                    "CAPTCHA_TEXT_TOKENS",
                    "CAPTCHA_TEXTS",
                    "CAPTCHA_DOM_SELECTORS",
                    "CAPTCHA_SECOND_TEXT_TOKENS",
                    "JUMP_CAPTCHA_URL_TOKENS",
                    "JUMP_CAPTCHA_TEXT_TOKENS",
                    "SEARCH_CAPTCHA_URL_TOKENS",
                    "SEARCH_CAPTCHA_TEXT_TOKENS",
                ):
                    if name not in expected_features:
                        self.assertFalse(
                            hasattr(engine_class, name),
                            f"{source_id} unexpectedly defines {name}",
                        )

    def test_url_token_match(self):
        hits = BaseEngine(object()).detect_captcha(
            _Page(), url_tokens=("captcha",), text_tokens=()
        )

        self.assertEqual(hits, [("url", "captcha")])

    def test_text_token_match(self):
        hits = BaseEngine(object()).detect_captcha(
            _Page(),
            url_tokens=(),
            text_tokens=("安全验证",),
            url_text="https://example.test/",
        )

        self.assertEqual(hits, [("text", "安全验证")])

    def test_dom_selector_match(self):
        hits = BaseEngine(object()).detect_captcha(
            _Page(), url_tokens=(), text_tokens=(), dom_selectors=("#challenge",)
        )

        self.assertEqual(hits, [("dom", "#challenge")])

    def test_no_features_match(self):
        hits = BaseEngine(object()).detect_captcha(
            _Page(),
            url_tokens=("verify",),
            text_tokens=("验证码",),
            dom_selectors=(".captcha",),
            url_text="https://example.test/",
            body_text="正常页面",
        )

        self.assertEqual(hits, [])

    def test_suppress_callback_only_exempts_text_match_without_url_match(self):
        suppress = mock.Mock(return_value=True)
        page = _Page()
        hits = BaseEngine(object()).detect_captcha(
            page,
            url_tokens=("captcha",),
            text_tokens=("安全验证",),
            suppress_if=suppress,
        )

        self.assertEqual(
            hits, [("url", "captcha"), ("text", "安全验证")]
        )
        suppress.assert_not_called()

        hits = BaseEngine(object()).detect_captcha(
            page,
            url_tokens=("captcha",),
            text_tokens=("安全验证",),
            url_text="https://example.test/",
            suppress_if=suppress,
        )
        self.assertEqual(hits, [])
        suppress.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
