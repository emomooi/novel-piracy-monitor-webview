"""手动运行的真实站点解析冒烟测试；默认不触发网络访问。"""

import argparse
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


SMOKE_SOURCES = (
    (
        "toutiao_pc",
        "头条PC",
        "ToutiaoPCEngine",
        ("so.toutiao.com", "article.zlink.toutiao.com"),
    ),
    (
        "toutiao_mobile",
        "头条移动",
        "ToutiaoMobileEngine",
        ("so.toutiao.com", "article.zlink.toutiao.com"),
    ),
    ("bing", "必应", "BingEngine", ("bing.com", "microsoft.com", "msn.com")),
    ("sogou_pc", "搜狗PC", "SogouPCEngine", ("sogou.com",)),
)
DEFAULT_TERM = "网络小说 作品推荐"
TOTAL_TIMEOUT_SECONDS = 240
NAVIGATION_TIMEOUT_MS = 30000


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="手动联网检查搜索引擎解析是否仍有效")
    parser.add_argument(
        "--run-network",
        action="store_true",
        help="显式启用真实浏览器与网络请求",
    )
    return parser.parse_args(argv)


def format_source_report(label, status, reason, page_counts=(), titles=()):
    counts = "/".join(str(count) for count in page_counts) or "-"
    first_titles = "；".join(title for title in titles[:2] if title) or "无"
    detail = f"{label}：{status}；{reason}；抓取条数（页）：{counts}；前两条标题：{first_titles}"
    return detail


class _SmokeAdapter:
    keep_page = False
    navigation_timeout_cap_ms = 20000

    def __init__(self, deadline):
        self.deadline = deadline
        self.captcha_hit = False
        self.logs = []
        self.pause_reason = ""

    def should_stop(self):
        return time.monotonic() >= self.deadline

    def log(self, message):
        self.logs.append(str(message))

    def pause_for_user(self, reason):
        self.pause_reason = str(reason)
        self.captcha_hit = True


def _is_external_result(url, blocked_domains):
    parsed = urlparse(str(url or ""))
    host = (parsed.hostname or "").lower().rstrip(".")
    return (
        parsed.scheme in ("http", "https")
        and bool(host)
        and not any(host == domain or host.endswith("." + domain) for domain in blocked_domains)
    )


def _run_network_smoke():
    from playwright.sync_api import sync_playwright

    from engines.bing import BingEngine
    from engines.sogou_pc import SogouPCEngine
    from engines.toutiao_mobile import ToutiaoMobileEngine
    from engines.toutiao_pc import ToutiaoPCEngine
    from main import BROWSER_UA

    engine_classes = {
        "ToutiaoPCEngine": ToutiaoPCEngine,
        "ToutiaoMobileEngine": ToutiaoMobileEngine,
        "BingEngine": BingEngine,
        "SogouPCEngine": SogouPCEngine,
    }
    reports = []
    deadline = time.monotonic() + TOTAL_TIMEOUT_SECONDS

    try:
        with tempfile.TemporaryDirectory(prefix="author-toolkit-smoke-") as profile:
            with sync_playwright() as playwright:
                context = playwright.chromium.launch_persistent_context(
                    user_data_dir=profile,
                    headless=True,
                    channel="msedge",
                    timeout=15000,
                    args=["--disable-blink-features=AutomationControlled"],
                    user_agent=BROWSER_UA,
                    viewport={"width": 1920, "height": 1080},
                    locale="zh-CN",
                    timezone_id="Asia/Shanghai",
                )
                context.set_default_timeout(10000)
                context.set_default_navigation_timeout(NAVIGATION_TIMEOUT_MS)
                try:
                    for _, label, class_name, blocked_domains in SMOKE_SOURCES:
                        counts = []
                        titles = []
                        reasons = []
                        try:
                            app = _SmokeAdapter(deadline)
                            engine = engine_classes[class_name](app)
                            page_titles = []
                            for page_num in range(2):
                                if app.should_stop():
                                    reasons.append("达到整体 4 分钟时限")
                                    break
                                rows = engine.fetch(
                                    context,
                                    DEFAULT_TERM,
                                    page_num=page_num,
                                    book_kw="网络小说",
                                )
                                rows = rows or []
                                counts.append(len(rows))
                                page_titles.append({
                                    str(row.get("title", "")).strip()
                                    for row in rows
                                    if isinstance(row, dict) and row.get("title")
                                })
                                if page_num == 0:
                                    titles.extend(
                                        row.get("title", "").strip()
                                        for row in rows[:2]
                                        if isinstance(row, dict)
                                    )
                                if app.captcha_hit:
                                    reasons.append(
                                        f"站点要求验证/登录：{app.pause_reason or '需要人工验证'}"
                                    )
                                external_count = sum(
                                    _is_external_result(row.get("url"), blocked_domains)
                                    for row in rows
                                    if isinstance(row, dict)
                                )
                                if len(rows) < 3:
                                    reasons.append(f"第 {page_num + 1} 页仅解析到 {len(rows)} 条（要求至少 3 条）")
                                if external_count < len(rows):
                                    bad_hosts = sorted({
                                        urlparse(str(row.get("url") or "")).hostname or "无有效主机名"
                                        for row in rows
                                        if isinstance(row, dict)
                                        and not _is_external_result(row.get("url"), blocked_domains)
                                    })
                                    reasons.append(
                                        f"第 {page_num + 1} 页有 {len(rows) - external_count} 条链接不是可确认的站外真实地址"
                                        f"（主机名：{', '.join(bad_hosts[:3])}）"
                                    )
                                if app.logs and not rows:
                                    reasons.append(app.logs[-1])

                            if (
                                len(page_titles) >= 2
                                and page_titles[0]
                                and page_titles[1]
                                and page_titles[0] == page_titles[1]
                            ):
                                reasons.append("第 2 页标题集合与第 1 页完全相同")
                        except Exception as exc:
                            reasons.append(f"{type(exc).__name__}: {exc}")

                        status = "通过" if not reasons and len(counts) == 2 else "失败"
                        reports.append(
                            format_source_report(
                                label,
                                status,
                                "；".join(dict.fromkeys(reasons)) or "两页解析正常且链接为站外地址",
                                counts,
                                titles,
                            )
                        )
                finally:
                    context.close()
    except Exception as exc:
        reason = (
            "无法启动 Microsoft Edge/Playwright；请确认已安装 Edge 且 Playwright 可用"
            if "executable" in str(exc).lower() or "msedge" in str(exc).lower()
            else f"{type(exc).__name__}: {exc}"
        )
        reports = [
            format_source_report(label, "失败", reason)
            for _, label, _, _ in SMOKE_SOURCES
        ]

    for report in reports:
        print(report)
    passed = sum("：通过；" in report for report in reports)
    print(f"联网冒烟总结：{passed}/{len(SMOKE_SOURCES)} 个来源通过")
    return 0 if passed == len(SMOKE_SOURCES) else 1


def run_from_args(args):
    if not args.run_network:
        print("联网冒烟未启用；如需运行，请添加 --run-network。")
        return 0
    return _run_network_smoke()


if __name__ == "__main__":
    raise SystemExit(run_from_args(parse_args()))
