"""锁定来源标签、引擎映射及用户可见顺序的改前契约。"""

import unittest

import main
from config import (
    DISPLAY_SOURCE_GROUP,
    MANUAL_SOURCE_COLUMNS,
    MANUAL_SOURCE_LABEL,
    MANUAL_SOURCE_ORDER,
    MAIN_ENGINE_ORDER,
    SRC_LABEL,
    SOURCE_GROUPS,
    VISIBLE_SRC_ORDER,
    WORKING_SRC_ORDER,
)
from engines import (
    ALL_ENGINE_MAP,
    ENGINE_MAP,
    MANUAL_SEARCH_ENGINE_MAP,
    TEST_ENGINE_MAP,
)


EXPECTED_SOURCE_LABELS = {
    "quark_cn": "夸克",
    "baidu": "百度",
    "baidu_mobile": "百度移动版",
    "zhidao": "知道",
    "zhidao_mobile": "知道移动版",
    "tieba": "贴吧",
    "bing": "必应",
    "toutiao_pc": "头条",
    "toutiao_mobile": "头条移动版",
    "sogou_pc": "搜狗",
    "sogou_mobile": "搜狗移动版",
    "so360_pc": "360",
    "so360_mobile": "360移动版",
    "sogou_weixin": "微信",
    "weibo_mobile": "微博",
}

EXPECTED_VISIBLE_ORDER = (
    "quark_cn", "baidu", "baidu_mobile", "zhidao", "zhidao_mobile",
    "tieba", "bing", "toutiao_pc", "toutiao_mobile", "sogou_pc",
    "sogou_mobile", "so360_pc", "so360_mobile", "sogou_weixin", "weibo_mobile",
)
EXPECTED_WORKING_ORDER = (
    "quark_cn", "baidu_mobile", "baidu", "zhidao_mobile", "zhidao", "tieba", "bing",
    "toutiao_pc", "toutiao_mobile", "sogou_mobile", "sogou_pc", "so360_mobile",
    "so360_pc", "sogou_weixin",
)
EXPECTED_MANUAL_ORDER = (
    "baidu", "baidu_mobile", "zhidao", "zhidao_mobile", "tieba", "bing",
    "quark_cn", "quark", "toutiao_pc", "toutiao_mobile", "weibo", "weibo_mobile",
    "sogou_pc", "sogou_mobile", "so360_pc", "so360_mobile", "sogou_weixin",
)
EXPECTED_MAIN_ENGINE_KEYS = {
    "quark_cn", "baidu_mobile", "baidu", "zhidao_mobile", "zhidao", "tieba", "bing",
    "so360_mobile", "so360_pc", "toutiao_mobile", "toutiao_pc", "sogou_mobile",
    "sogou_pc", "sogou_weixin", "weibo", "weibo_mobile",
}
EXPECTED_TEST_ENGINE_KEYS = {
    "quark", "quark_m", "quark_so", "quark_cn", "weibo", "weibo_mobile",
    "sogou_mobile", "toutiao_mobile", "so360_mobile",
}
EXPECTED_MANUAL_ENGINE_KEYS = {
    "baidu", "baidu_mobile", "zhidao", "zhidao_mobile", "tieba", "bing",
    "so360_mobile", "so360_pc", "toutiao_mobile", "toutiao_pc", "sogou_mobile",
    "sogou_pc", "sogou_weixin", "quark", "quark_cn", "weibo", "weibo_mobile",
}
EXPECTED_ALL_ENGINE_KEYS = {
    "baidu", "baidu_mobile", "zhidao", "zhidao_mobile", "tieba", "bing",
    "so360_mobile", "so360_pc", "toutiao_mobile", "toutiao_pc", "sogou_mobile",
    "sogou_pc", "sogou_weixin", "quark", "quark_m", "quark_so", "quark_cn",
    "weibo", "weibo_mobile",
}


class SourceRegistryTests(unittest.TestCase):
    def test_source_labels_match_captured_values_and_main_alias(self):
        self.assertEqual(SRC_LABEL, EXPECTED_SOURCE_LABELS)
        self.assertEqual(main.SOURCE_LABELS, SRC_LABEL)
        self.assertIs(main.SOURCE_LABELS, SRC_LABEL)

    def test_source_groups_reference_registered_engines(self):
        for group_id, engine_ids in SOURCE_GROUPS.items():
            with self.subTest(group_id=group_id):
                self.assertTrue(engine_ids)
                self.assertTrue(set(engine_ids).issubset(ALL_ENGINE_MAP))

    def test_engine_map_keys_match_captured_sets(self):
        self.assertEqual(set(ALL_ENGINE_MAP), EXPECTED_ALL_ENGINE_KEYS)
        self.assertEqual(set(ENGINE_MAP), EXPECTED_MAIN_ENGINE_KEYS)
        self.assertEqual(set(TEST_ENGINE_MAP), EXPECTED_TEST_ENGINE_KEYS)
        self.assertEqual(set(MANUAL_SEARCH_ENGINE_MAP), EXPECTED_MANUAL_ENGINE_KEYS)
        self.assertEqual(tuple(ENGINE_MAP), tuple(MAIN_ENGINE_ORDER))

    def test_display_and_manual_orders_match_captured_values(self):
        self.assertEqual(tuple(VISIBLE_SRC_ORDER), EXPECTED_VISIBLE_ORDER)
        self.assertEqual(tuple(WORKING_SRC_ORDER), EXPECTED_WORKING_ORDER)
        self.assertEqual(tuple(MANUAL_SOURCE_ORDER), EXPECTED_MANUAL_ORDER)
        self.assertEqual(MANUAL_SOURCE_COLUMNS, 2)

    def test_specialized_source_labels_and_groups_remain_unchanged(self):
        self.assertEqual(
            MANUAL_SOURCE_LABEL,
            {
                "baidu": "百度",
                "baidu_mobile": "百度m",
                "bing": "必应",
                "so360_pc": "360",
                "so360_mobile": "360",
                "toutiao_pc": "头条",
                "toutiao_mobile": "头条",
                "sogou_pc": "搜狗",
                "sogou_mobile": "搜狗",
                "weibo": "微博",
                "weibo_mobile": "微博",
                "sogou_weixin": "微信",
                "zhidao": "知道",
                "zhidao_mobile": "知道m",
                "tieba": "贴吧",
                "quark": "夸克",
                "quark_cn": "夸克",
            },
        )
        self.assertEqual(
            DISPLAY_SOURCE_GROUP,
            {
                "quark_cn": "quark",
                "baidu_mobile": "baidu",
                "zhidao_mobile": "zhidao",
                "sogou_mobile": "sogou",
                "sogou_pc": "sogou",
                "toutiao_mobile": "toutiao",
                "toutiao_pc": "toutiao",
                "so360_mobile": "so360",
                "so360_pc": "so360",
                "sogou_weixin": "sogou_weixin",
                "weibo_mobile": "weibo",
            },
        )


if __name__ == "__main__":
    unittest.main()
