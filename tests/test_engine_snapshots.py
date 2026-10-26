"""通过各引擎真实 URL 构造方法锁定当前地址，不启动浏览器或访问网络。"""

import unittest
from urllib.parse import urlsplit

from engines import ENGINE_MAP
from engines.baidu import BaiduEngine
from engines.baidu_mobile import BaiduMobileEngine
from engines.bing import BingEngine
from engines.quark import QuarkEngine
from engines.so360_mobile import So360MobileEngine
from engines.so360_pc import So360PCEngine
from engines.sogou_pc import SogouPCEngine
from engines.sogou_weixin import SogouWeixinEngine
from engines.tieba import TiebaEngine
from engines.toutiao_mobile import ToutiaoMobileEngine
from engines.toutiao_pc import ToutiaoPCEngine
from engines.weibo import WeiboEngine
from engines.zhidao import ZhidaoEngine
from engines.zhidao_mobile import ZhidaoMobileEngine


TERM = "星河 书名"
PAGE_NUMS = (0, 1, 2, 999)

# 各地址是在引入测试接缝前按现有 fetch 代码的实际 URL 固化的快照。
URL_SNAPSHOTS = {
    BaiduEngine: (
        "https://www.baidu.com/s?wd=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&pn=0",
        "https://www.baidu.com/s?wd=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&pn=10",
        "https://www.baidu.com/s?wd=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&pn=20",
        "https://www.baidu.com/s?wd=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&pn=9990",
    ),
    BaiduMobileEngine: (
        "https://m.baidu.com/s?word=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&pn=0",
        "https://m.baidu.com/s?word=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&pn=10",
        "https://m.baidu.com/s?word=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&pn=20",
        "https://m.baidu.com/s?word=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&pn=9990",
    ),
    ZhidaoEngine: (
        "https://zhidao.baidu.com/search?word=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&pn=0",
        "https://zhidao.baidu.com/search?word=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&pn=10",
        "https://zhidao.baidu.com/search?word=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&pn=20",
        "https://zhidao.baidu.com/search?word=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&pn=9990",
    ),
    ZhidaoMobileEngine: (
        "https://zhidao.baidu.com/index/?fr=&word=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D",
        "https://zhidao.baidu.com/index/?fr=&word=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&pn=10",
        "https://zhidao.baidu.com/index/?fr=&word=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&pn=20",
        "https://zhidao.baidu.com/index/?fr=&word=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&pn=9990",
    ),
    So360PCEngine: (
        "https://www.so.com/s?q=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&pn=0",
        "https://www.so.com/s?q=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&pn=10",
        "https://www.so.com/s?q=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&pn=20",
        "https://www.so.com/s?q=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&pn=9990",
    ),
    So360MobileEngine: (
        "https://m.so.com/s?q=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&pn=0",
        "https://m.so.com/s?q=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&pn=10",
        "https://m.so.com/s?q=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&pn=20",
        "https://m.so.com/s?q=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&pn=9990",
    ),
    BingEngine: (
        "https://www.bing.com/search?q=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&first=1",
        "https://www.bing.com/search?q=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&first=11",
        "https://www.bing.com/search?q=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&first=21",
        "https://www.bing.com/search?q=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&first=9991",
    ),
    ToutiaoPCEngine: (
        "https://so.toutiao.com/search?dvpf=pc&source=input&keyword=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&offset=0&enable_druid_v2=1",
        "https://so.toutiao.com/search?dvpf=pc&source=input&keyword=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&offset=10&enable_druid_v2=1",
        "https://so.toutiao.com/search?dvpf=pc&source=input&keyword=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&offset=20&enable_druid_v2=1",
        "https://so.toutiao.com/search?dvpf=pc&source=input&keyword=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&offset=9990&enable_druid_v2=1",
    ),
    ToutiaoMobileEngine: (
        "https://so.toutiao.com/search?keyword=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&offset=0",
        "https://so.toutiao.com/search?keyword=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&offset=10",
        "https://so.toutiao.com/search?keyword=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&offset=20",
        "https://so.toutiao.com/search?keyword=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&offset=9990",
    ),
    QuarkEngine: (
        "https://quark.sm.cn/s?q=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&offset=0",
        "https://quark.sm.cn/s?q=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&offset=10",
        "https://quark.sm.cn/s?q=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&offset=20",
        "https://quark.sm.cn/s?q=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&offset=9990",
    ),
    SogouPCEngine: (
        "https://www.sogou.com/web?query=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&page=1",
        "https://www.sogou.com/web?query=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&page=2",
        "https://www.sogou.com/web?query=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&page=3",
        "https://www.sogou.com/web?query=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&page=1000",
    ),
    SogouWeixinEngine: (
        "https://weixin.sogou.com/weixin?query=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&type=2&ie=utf8&page=1",
        "https://weixin.sogou.com/weixin?query=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&type=2&ie=utf8&page=2",
        "https://weixin.sogou.com/weixin?query=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&type=2&ie=utf8&page=3",
        "https://weixin.sogou.com/weixin?query=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&type=2&ie=utf8&page=1000",
    ),
    TiebaEngine: (
        "https://tieba.baidu.com/f/search/res?ie=utf-8&qw=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&pn=0",
        "https://tieba.baidu.com/f/search/res?ie=utf-8&qw=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&pn=1",
        "https://tieba.baidu.com/f/search/res?ie=utf-8&qw=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&pn=2",
        "https://tieba.baidu.com/f/search/res?ie=utf-8&qw=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&pn=999",
    ),
    WeiboEngine: (
        "https://s.weibo.com/realtime?q=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&rd=realtime&tw=realtime&Refer=weibo_realtime",
        "https://s.weibo.com/realtime?q=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&rd=realtime&tw=realtime&Refer=weibo_realtime",
        "https://s.weibo.com/realtime?q=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&rd=realtime&tw=realtime&Refer=weibo_realtime",
        "https://s.weibo.com/realtime?q=%E6%98%9F%E6%B2%B3%20%E4%B9%A6%E5%90%8D&rd=realtime&tw=realtime&Refer=weibo_realtime",
    ),
}


class EngineSnapshotTests(unittest.TestCase):
    def test_search_url_snapshots(self):
        for engine_class, expected_urls in URL_SNAPSHOTS.items():
            with self.subTest(engine=engine_class.__name__):
                engine = engine_class(None)
                for page_num, expected in zip(PAGE_NUMS, expected_urls):
                    with self.subTest(page_num=page_num):
                        self.assertEqual(
                            engine._build_search_url(TERM, page_num),
                            expected,
                        )

    def test_main_quark_source_uses_quark_sm_cn(self):
        quark_cn_engine = ENGINE_MAP["quark_cn"]
        self.assertEqual(urlsplit(quark_cn_engine.SEARCH_URL).hostname, "quark.sm.cn")


if __name__ == "__main__":
    unittest.main()
