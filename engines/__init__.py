# engines/__init__.py
from config import MAIN_ENGINE_ORDER, MANUAL_HIDDEN_SOURCES, TEST_SRC_ORDER
from engines.baidu import BaiduEngine
from engines.baidu_mobile import BaiduMobileEngine
from engines.zhidao import ZhidaoEngine
from engines.zhidao_mobile import ZhidaoMobileEngine
from engines.tieba import TiebaEngine
from engines.bing import BingEngine
from engines.so360_mobile import So360MobileEngine
from engines.so360_pc import So360PCEngine
from engines.toutiao_mobile import ToutiaoMobileEngine
from engines.toutiao_pc import ToutiaoPCEngine
from engines.sogou_mobile import SogouMobileEngine
from engines.sogou_pc import SogouPCEngine
from engines.sogou_weixin import SogouWeixinEngine
from engines.quark import QuarkEngine
from engines.quark_m import QuarkMEngine
from engines.quark_so import QuarkSoEngine
from engines.quark_cn import QuarkCnEngine
from engines.weibo import WeiboEngine
from engines.weibo_mobile import WeiboMobileEngine

ALL_ENGINE_MAP = {
    'baidu': BaiduEngine,
    'baidu_mobile': BaiduMobileEngine,
    'zhidao': ZhidaoEngine,
    'zhidao_mobile': ZhidaoMobileEngine,
    'tieba': TiebaEngine,
    'bing': BingEngine,
    'so360_mobile': So360MobileEngine,
    'so360_pc': So360PCEngine,
    'toutiao_mobile': ToutiaoMobileEngine,
    'toutiao_pc': ToutiaoPCEngine,
    'sogou_mobile': SogouMobileEngine,
    'sogou_pc': SogouPCEngine,
    'sogou_weixin': SogouWeixinEngine,
    'quark': QuarkEngine,
    'quark_m': QuarkMEngine,
    'quark_so': QuarkSoEngine,
    'quark_cn': QuarkCnEngine,
    'weibo': WeiboEngine,
    'weibo_mobile': WeiboMobileEngine,
}

# 主程序：只保留已跑通的来源
ENGINE_MAP = {
    src_id: ALL_ENGINE_MAP[src_id]
    for src_id in MAIN_ENGINE_ORDER
    if src_id in ALL_ENGINE_MAP
}

# 测试专用程序：只保留待测来源（顺序与 TEST_SRC_ORDER 一致）
# 夸克 4 个入口一起对比；微博 + 移动端；搜狗/头条/360 的移动版
TEST_ENGINE_MAP = {
    src_id: ALL_ENGINE_MAP[src_id]
    for src_id in TEST_SRC_ORDER
    if src_id in ALL_ENGINE_MAP
}


# 手动搜索：按 MANUAL_SOURCE_ORDER 排序展示；
# 手动搜索保留 quark.sm.cn（夸克m）+ quark_cn 两个入口；主程序抓取 quark_cn 使用 www.quark.cn
# quark_m / quark_so 不显示
MANUAL_SEARCH_ENGINE_MAP = {
    sid: cls for sid, cls in ALL_ENGINE_MAP.items()
    if sid not in MANUAL_HIDDEN_SOURCES
}
