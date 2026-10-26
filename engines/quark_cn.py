# engines/quark_cn.py
"""夸克搜索入口：www.quark.cn（主程序用）

和 QuarkEngine 完全同一套解析逻辑，只是换了个搜索入口。
以前放在测试专用程序里做横向对比，现在直接进主程序（来源名显示成「夸克」）；
手动搜索入口由前端映射处理；测试专用程序里留 quark.sm.cn / m.sm.cn / so.m.sm.cn 等入口继续对比。
"""
from engines.quark import QuarkEngine
from config import QUARK_ENTRYPOINTS


class QuarkCnEngine(QuarkEngine):
    SOURCE_ID = 'quark_cn'
    SOURCE_LABEL = '夸克'
    ENTRYPOINT = QUARK_ENTRYPOINTS[SOURCE_ID]
    SEARCH_URL = ENTRYPOINT['search_url']
    HOME_BASE = ENTRYPOINT['home_base']
