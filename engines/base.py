# engines/base.py
import math
import re
import random
import time
from urllib.parse import urlsplit

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from utils import filter_summary, normalize_date, strip_date_from_text

_UNSET = object()


class BaseEngine:
    """所有搜索引擎的基类"""
    SOURCE_ID = ""       # 内部标识，如 'baidu'
    SOURCE_LABEL = ""    # 界面显示名，如 '百度搜索'
    SEARCH_URL = ""      # 手动搜索用的 URL 模板，用 {kw} 占位
    EXTRA_URL = ""       # 手动搜索时附带打开的链接（可为空）

    def __init__(self, app):
        self.app = app
        self.diagnostics = []
        self._navigation_stopped = False

    def note(self, text):
        self.diagnostics.append(str(text))

    def log(self, msg):
        self.app.log(msg)

    def pause_for_user(self, reason):
        self.app.pause_for_user(reason)

    def detect_captcha(
        self,
        page,
        url_tokens=(),
        text_tokens=(),
        dom_selectors=(),
        suppress_if=None,
        *,
        url_text=_UNSET,
        body_text=_UNSET,
    ):
        """Return matching (kind, feature) pairs without imposing site policy."""
        hits = []
        if url_tokens:
            current_url = page.url if url_text is _UNSET else url_text
            current_url = str(current_url or "").lower()
            hits.extend(
                ("url", token)
                for token in url_tokens
                if token.lower() in current_url
            )

        if text_tokens:
            current_text = (
                page.text_content("body") if body_text is _UNSET else body_text
            )
            current_text = str(current_text or "").lower()
            text_hits = [
                ("text", token)
                for token in text_tokens
                if token.lower() in current_text
            ]
            if text_hits and not hits and suppress_if and suppress_if():
                return []
            hits.extend(text_hits)

        if dom_selectors:
            found = page.evaluate(
                """selectors => selectors.some(selector =>
                    Array.from(document.querySelectorAll(selector))
                        .some(element => element.offsetParent !== null)
                )""",
                list(dom_selectors),
            )
            if found:
                hits.extend(("dom", selector) for selector in dom_selectors)

        return hits

    def should_stop(self):
        should_stop = getattr(self.app, "should_stop", None)
        return bool(callable(should_stop) and should_stop())

    @property
    def navigation_stopped(self):
        return self._navigation_stopped

    def goto_with_stop(self, page, url, wait_until="load", timeout=30000, **kwargs):
        """Navigate once, then wait for the requested load state in interruptible slices."""
        self._navigation_stopped = False
        timeout_cap = getattr(self.app, "navigation_timeout_cap_ms", None)
        if timeout_cap is not None:
            timeout = min(timeout, timeout_cap)
        deadline = time.monotonic() + timeout / 1000
        initial_url = page.url or ""
        navigation_response = [None]

        def remember_navigation_response(response):
            request = response.request
            if request.is_navigation_request() and request.frame == page.main_frame:
                navigation_response[0] = response

        page.on("response", remember_navigation_response)

        def stop_navigation():
            self._navigation_stopped = True
            self.log("用户停止，已中断页面导航")
            return None

        def remaining_timeout_ms():
            return math.ceil((deadline - time.monotonic()) * 1000)

        try:
            if self.should_stop():
                return stop_navigation()

            if wait_until == "commit":
                try:
                    return page.goto(
                        url, wait_until="commit", timeout=timeout, **kwargs
                    )
                except Exception:
                    if self.should_stop():
                        return stop_navigation()
                    raise

            response = None
            try:
                response = page.goto(
                    url,
                    wait_until="commit",
                    timeout=min(250, timeout),
                    **kwargs,
                )
            except PlaywrightTimeoutError:
                if self.should_stop():
                    return stop_navigation()
            except Exception:
                if self.should_stop():
                    return stop_navigation()
                raise

            if response is None:
                response = navigation_response[0]

            if response is None and (page.url or "") == initial_url:
                while True:
                    if self.should_stop():
                        return stop_navigation()
                    remaining_ms = remaining_timeout_ms()
                    if remaining_ms <= 0:
                        raise PlaywrightTimeoutError(
                            f"Navigation to {url} did not commit within {timeout}ms"
                        )
                    try:
                        page.wait_for_url(
                            lambda current_url: current_url != initial_url,
                            timeout=min(250, remaining_ms),
                        )
                    except PlaywrightTimeoutError:
                        if self.should_stop():
                            return stop_navigation()
                        if remaining_timeout_ms() <= 0:
                            raise
                    except Exception:
                        if self.should_stop():
                            return stop_navigation()
                        raise

            while True:
                if self.should_stop():
                    return stop_navigation()
                remaining_ms = remaining_timeout_ms()
                if remaining_ms <= 0:
                    raise PlaywrightTimeoutError(
                        f"Navigation to {url} did not reach {wait_until} within {timeout}ms"
                    )
                response = (
                    response
                    if response is not None
                    else navigation_response[0]
                )
                if url != initial_url and (page.url or "") == initial_url:
                    try:
                        page.wait_for_url(
                            lambda current_url: current_url != initial_url,
                            timeout=min(250, remaining_ms),
                        )
                    except PlaywrightTimeoutError:
                        if self.should_stop():
                            return stop_navigation()
                        if remaining_timeout_ms() <= 0:
                            raise
                    except Exception:
                        if self.should_stop():
                            return stop_navigation()
                        raise
                    continue
                if url == initial_url and response is None:
                    page.wait_for_timeout(min(250, remaining_ms))
                    continue
                try:
                    page.wait_for_load_state(
                        wait_until,
                        timeout=min(250, remaining_ms),
                    )
                    return response
                except PlaywrightTimeoutError:
                    if self.should_stop():
                        return stop_navigation()
                    if remaining_timeout_ms() <= 0:
                        raise
                except Exception:
                    if self.should_stop():
                        return stop_navigation()
                    raise
        finally:
            page.remove_listener("response", remember_navigation_response)

    def wait_for_url_with_stop(self, page, url, timeout=30000):
        """Wait for a URL in bounded slices so an explicit stop is observed promptly."""
        self._navigation_stopped = False
        deadline = time.monotonic() + timeout / 1000
        while True:
            if self.should_stop():
                self._navigation_stopped = True
                self.log("用户停止，已中断页面导航等待")
                return
            remaining_ms = math.ceil((deadline - time.monotonic()) * 1000)
            if remaining_ms <= 0:
                raise PlaywrightTimeoutError(
                    f"URL did not match {url!r} within {timeout}ms"
                )
            try:
                page.wait_for_url(url, timeout=min(250, remaining_ms))
                return
            except PlaywrightTimeoutError:
                if self.should_stop():
                    self._navigation_stopped = True
                    self.log("用户停止，已中断页面导航等待")
                    return
                if time.monotonic() >= deadline:
                    raise
            except Exception:
                if self.should_stop():
                    self._navigation_stopped = True
                    self.log("用户停止，已中断页面导航等待")
                    return
                raise

    @staticmethod
    def page_offset(page_num, per_page, page_base):
        """按引擎提供的页大小与基数计算页码参数，不处理输入或翻页策略。"""
        if per_page == 1 and page_base == 0:
            return page_num
        if page_base == 0:
            return page_num * per_page
        return page_num * per_page + page_base

    def wait_random(self, min_seconds, max_seconds):
        """在指定秒数范围内随机等待，并在停止时尽快中断。"""
        remaining = random.uniform(min_seconds, max_seconds)
        deadline = time.monotonic() + remaining
        should_stop = getattr(self.app, "should_stop", None)
        while remaining > 0:
            if callable(should_stop) and should_stop():
                return
            sleep_seconds = min(remaining, 0.25)
            time.sleep(sleep_seconds)
            remaining = max(0, deadline - time.monotonic())

    # 这些页面的定位信息就在查询串里，截断后就打不开了
    KEEP_QUERY_PREFIXES = (
        'https://mp.weixin.qq.com/s',
        'http://mp.weixin.qq.com/s',
    )

    @staticmethod
    def clean_url(url):
        """统一清理链接，只保留真正能用的 URL"""
        if not url:
            return ""
        url = str(url).strip()
        if not url or url == 'about:blank':
            return ""
        if url.startswith('//'):
            url = 'https:' + url
        if not url.startswith(('http://', 'https://')):
            if url.startswith('/'):
                return url
            return url
        head = url.split('#')[0]
        low = head.lower()
        if any(low.startswith(p) for p in BaseEngine.KEEP_QUERY_PREFIXES):
            return head
        return head.split('?')[0]

    @staticmethod
    def clean_content_url(url):
        """源链接专用清理：保留完整地址（含查询串）。

        跳转壳链接（如 so.com/jump?u=... / weixin.sogou.com/link?url=...）
        的价值全在查询串里，截断后就废了，所以这里只做最基本的清洗。
        """
        if not url:
            return ''
        v = str(url).strip()
        if not v or v == 'about:blank':
            return ''
        if v.startswith('//'):
            v = 'https:' + v
        return v

    @staticmethod
    def normalize_title(title):
        if title is None:
            return ""
        return str(title).strip()

    @staticmethod
    def normalize_summary(summary, fallback='（无摘要，双击打开查看）'):
        text = str(summary or '').strip()
        if not text:
            return fallback
        cleaned = strip_date_from_text(text)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        if not cleaned:
            return fallback
        return filter_summary(cleaned)

    @staticmethod
    def normalize_date(date_text, fallback='未知'):
        text = str(date_text or '').strip()
        if not text:
            return fallback
        value = normalize_date(text)
        return value if value and value != '未知' else fallback

    def normalize_result(self, source, title, url, summary='', date='未知', author='',
                        content_url='', long_url='', is_new=False, is_white=False,
                        is_zhinengti=False):
        """统一返回结构：以后所有引擎都按这个格式输出，UI 只看这个格式。"""
        clean_url = self.clean_url(url)
        clean_content = self.clean_content_url(content_url or long_url)
        if not clean_url and clean_content:
            clean_url = self.clean_url(clean_content)

        result = {
            'source': source,
            'title': self.normalize_title(title),
            'url': clean_url,
            'summary': self.normalize_summary(summary),
            'date': self.normalize_date(date),
            'author': str(author or '').strip() or '未知来源',
            'content_url': clean_content,
            'long_url': clean_content or clean_url,
            'is_new': bool(is_new),
            'is_white': bool(is_white),
            'is_zhinengti': bool(is_zhinengti),
            'checked': False,
        }

        if not result['title'] and result['url']:
            result['title'] = result['url']

        return result

    def _create_stealth_page(self, context):
        """创建一个带反爬虫伪装的新页面（公共方法）"""
        page = context.new_page()
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = {runtime: {}};
            Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN','zh']});
            Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
        """)
        return page

    def fetch(self, context, term, page_num, book_kw=''):
        """核心抓取方法，子类必须重写"""
        raise NotImplementedError