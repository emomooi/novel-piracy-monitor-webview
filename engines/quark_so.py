# engines/quark_so.py
"""夸克搜索入口对比用：so.m.sm.cn

和 QuarkEngine 完全同一套解析逻辑，只是换了个搜索入口，
方便在测试专用程序里横向比较哪个入口抓得又多又准。
"""
from engines.quark import QuarkEngine
from config import QUARK_ENTRYPOINTS


class QuarkSoEngine(QuarkEngine):
    SOURCE_ID = 'quark_so'
    SOURCE_LABEL = '夸克 so.m.sm.cn'
    ENTRYPOINT = QUARK_ENTRYPOINTS[SOURCE_ID]
    SEARCH_URL = ENTRYPOINT['search_url']
    HOME_BASE = ENTRYPOINT['home_base']
