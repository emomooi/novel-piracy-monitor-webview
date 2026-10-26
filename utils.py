import os
import json
import re
import sys
import tempfile
from config import *

def log_suppressed_error(context, error):
    print(
        f"[suppressed] {context}: {type(error).__name__}: {error}",
        file=sys.stderr,
    )


try:
    from PIL import Image, ImageDraw
    HAS_TRAY = True
except ImportError as exc:
    HAS_TRAY = False
    log_suppressed_error("Pillow unavailable; tray icon support disabled", exc)

def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            log_suppressed_error(f"读取 JSON {path} 失败，使用默认值", exc)
            pass
    return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def migrate_old_files(log_callback=None):
    """幂等归档旧记录及白名单；白名单合并成功后才归档源文件。"""
    def log(message, error=False):
        if log_callback:
            try:
                log_callback(message)
                return
            except Exception as exc:
                log_suppressed_error("迁移日志回调失败，改用标准输出", exc)
                pass
        print(message, file=sys.stderr if error else sys.stdout)

    # 这些旧记录文件没有运行时读取路径，仅归档保留，不写入新文件。
    old_seen_files = (
        os.path.join(BASE_DIR, "monitor_seen.json"),
        os.path.join(BASE_DIR, "monitor_seen_zhinengti.json"),
        SEEN_SOGOU_LEGACY_FILE,
        SEEN_SO360_LEGACY_FILE,
        SEEN_TOUTIAO_LEGACY_FILE,
    )
    for old_path in old_seen_files:
        if os.path.isfile(old_path):
            archive_path = _archive_legacy_file(old_path, log)
            if archive_path:
                log(f"[migration] 已归档旧记录：{archive_path}")

    _merge_legacy_whitelists(log)


def _archive_legacy_file(old_path, log):
    base_path = old_path + ".migrated"
    index = 0
    while True:
        archive_path = base_path if index == 0 else f"{base_path}.{index}"
        if os.path.lexists(archive_path):
            index += 1
            continue
        try:
            # Windows os.rename 不覆盖已有目标；遇到并发占用时换下一个归档名。
            os.rename(old_path, archive_path)
            return archive_path
        except OSError as exc:
            if os.path.lexists(archive_path):
                index += 1
                continue
            log(
                f"[migration] 归档失败，下次启动将重试；原文件保留：{old_path}: {exc}",
            )
            return None


def _read_json_array(path, description, log):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        log(f"[migration] 读取{description}失败，保留原文件：{path}: {exc}", error=True)
        return None
    if not isinstance(data, list):
        log(f"[migration] {description}不是 JSON 数组，保留原文件并跳过：{path}", error=True)
        return None
    if not all(isinstance(item, str) for item in data):
        log(f"[migration] {description}数组包含非字符串项目，保留原文件并跳过：{path}", error=True)
        return None
    return data


def _merge_legacy_whitelists(log):
    for old_path in WHITELIST_LEGACY_FILES:
        if not os.path.isfile(old_path):
            continue

        legacy_entries = _read_json_array(old_path, "旧白名单", log)
        if legacy_entries is None:
            continue

        if os.path.exists(WHITELIST_COMMON_FILE):
            current = _read_json_array(WHITELIST_COMMON_FILE, "现有白名单", log)
            if current is None:
                continue
        else:
            current = []

        merged = list(current)
        for item in legacy_entries:
            if item not in merged:
                merged.append(item)
        merged.sort()

        staged_path = None
        try:
            if merged != current:
                target_dir = os.path.dirname(WHITELIST_COMMON_FILE) or "."
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding="utf-8",
                    dir=target_dir,
                    prefix=".whitelist-migration-",
                    suffix=".tmp",
                    delete=False,
                ) as staged_file:
                    staged_path = staged_file.name
                    json.dump(merged, staged_file, ensure_ascii=False, indent=2)
        except OSError as exc:
            log(f"[migration] 准备白名单合并失败，保留原文件以便下次重试：{old_path}: {exc}", error=True)
            _remove_staged_file(staged_path, log)
            continue

        # 不变量：必须先确认合并结果写入目标，再归档旧文件；归档前目标已包含全部旧白名单。
        if staged_path:
            try:
                os.replace(staged_path, WHITELIST_COMMON_FILE)
                staged_path = None
            except OSError as exc:
                log(f"[migration] 写入合并白名单失败，保留原文件以便下次重试：{WHITELIST_COMMON_FILE}: {exc}", error=True)
                _remove_staged_file(staged_path, log)
                continue

        archive_path = _archive_legacy_file(old_path, log)
        if archive_path:
            log(f"[migration] 已合并并归档旧白名单：{archive_path}")
        else:
            log(f"[migration] 白名单已合并；旧文件仍在原位，归档失败，下次启动将重试：{old_path}")


def _remove_staged_file(path, log):
    if not path or not os.path.exists(path):
        return
    try:
        os.remove(path)
    except OSError as exc:
        log(f"[migration] 清理临时文件失败：{path}: {exc}", error=True)

def generate_icon():
    if not HAS_TRAY:
        return None
    # 优先读 app_icon.ico（用户自定义图标）—— 直接读文件，不调 ensure_ico 避免递归
    try:
        if os.path.exists(ICON_FILE):
            return Image.open(ICON_FILE).copy()
    except Exception as exc:
        log_suppressed_error(f"读取图标 {ICON_FILE} 失败，使用绘制图标", exc)
        pass
    # 兜底：原来的手绘逻辑
    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((2, 2, 62, 62), fill=(42, 157, 143, 255))
    d.ellipse((16, 16, 48, 48), fill=(255, 255, 255, 255))
    d.ellipse((24, 24, 40, 40), fill=(230, 57, 70, 255))
    return img

def ensure_ico():
    if os.path.exists(ICON_FILE):
        return ICON_FILE
    img = generate_icon()
    if img is None:
        return None
    try:
        img.save(ICON_FILE, format='ICO', sizes=[(64, 64)])
        return ICON_FILE
    except Exception as exc:
        log_suppressed_error(f"保存图标 {ICON_FILE} 失败", exc)
        return None

# ==================== 后缀数据结构 ====================
def normalize_suffixes(sufs):
    out = []
    seen = set()
    for s in sufs or []:
        if isinstance(s, dict):
            text = str(s.get("text", "") or "").strip()
            enabled = bool(s.get("enabled", True))
        else:
            text = str(s or "").strip()
            enabled = True
        if text in seen:
            continue
        seen.add(text)
        out.append({"text": text, "enabled": enabled})
    if "" not in seen:
        out.insert(0, {"text": "", "enabled": True})
    out.sort(key=lambda x: 0 if x["text"] == "" else 1)
    return out

def fmt_suffixes(sufs):
    if not sufs:
        return "（无）"
    enabled = []
    disabled = []
    for s in sufs:
        if isinstance(s, dict):
            text = s.get("text", "")
            on = s.get("enabled", True)
        else:
            text = str(s or "")
            on = True
        (enabled if on else disabled).append(text)
    parts = [(t if t else "（无后缀）") for t in enabled]
    txt = "、".join(parts) if parts else "（无）"
    if disabled:
        dn = [(t if t else "（无后缀）") for t in disabled]
        txt += f"  [未选: {'、'.join(dn)}]"
    return txt

def enabled_suffix_texts(sufs):
    out = []
    for s in sufs or []:
        if isinstance(s, dict):
            if s.get("enabled", True):
                out.append(str(s.get("text", "") or ""))
        else:
            out.append(str(s or ""))
    return out

def fmt_hms(seconds):
    """秒数 → 小时:分钟:秒（如 01:23:45），用来显示「本轮用时」"""
    try:
        total = int(round(float(seconds or 0)))
    except Exception as exc:
        log_suppressed_error("格式化耗时失败，使用 0 秒", exc)
        total = 0
    if total < 0:
        total = 0
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

# ==================== 工具函数 ====================
def is_relative_date(date_str):
    s = str(date_str)
    return any(re.search(p, s) for p in RELATIVE_DATE_PATTERNS)

def normalize_date(date_str):
    if not date_str:
        return "未知"
    s = str(date_str).strip()
    if is_relative_date(s):
        return re.sub(r'\s+', '', s)
    nums = re.findall(r'\d+', s)
    if len(nums) >= 3:
        try:
            y, m, d = int(nums[0]), int(nums[1]), int(nums[2])
            return f"{y}/{m:02d}/{d:02d}"
        except Exception as exc:
            log_suppressed_error("解析日期失败，返回未知日期", exc)
            pass
    return "未知"

def strip_date_from_text(text):
    if not text:
        return ""
    for p in DATE_PATTERNS:
        text = re.sub(p, '', text)
    for p in RELATIVE_DATE_PATTERNS:
        text = re.sub(p, '', text)
    text = re.sub(r'^[·•\-\–\—\s\.]+', '', text)
    return re.sub(r'\s+', ' ', text).strip()

def filter_summary(summary):
    if not summary:
        return "（无摘要，双击打开查看）"
    s = summary.strip()
    footer_hits = sum(1 for kw in FOOTER_KEYWORDS if kw in s)
    if footer_hits >= 3:
        return "（页脚噪音，双击打开查看）"
    for _ in range(3):
        old = s
        s = re.sub(r'^《[^》]{1,40}》\s*作者[:：]\s*[^，,。；;、\s]{1,25}[，,。；;、\s]*', '', s)
        s = re.sub(r'^《[^》]{1,40}》\s*[，,。；;、\s]*', '', s)
        s = re.sub(r'^[，,。；;：:\s·•\-]+', '', s)
        if s == old:
            break
    parts = re.split(r'([。！？])', s)
    kept = []
    for i in range(0, len(parts), 2):
        sentence = parts[i]
        if not sentence.strip():
            continue
        if any(kw in sentence for kw in FOOTER_KEYWORDS):
            continue
        kept.append(sentence + (parts[i+1] if i+1 < len(parts) else ''))
    s = ''.join(kept).strip()
    for _ in range(2):
        old = s
        s = re.sub(r'^《[^》]{1,40}》\s*[，,。；;、\s]*', '', s)
        s = re.sub(r'^[，,。；;：:\s·•\-]+', '', s)
        if s == old:
            break
    s = re.sub(r'\s+', ' ', s).strip()
    if len(s) < 8:
        return "（摘要过短，双击打开查看完整内容）"
    if len(s) > 400:
        s = s[:400] + '...'
    return s

def date_sort_key(date_str):
    s = str(date_str).strip()
    if '刚刚' in s or ('秒' in s and '前' in s):
        return (10001, 0, 0)
    if '分钟' in s and '前' in s:
        return (10000, 0, 0)
    if '小时' in s and '前' in s:
        return (9999, 0, 0)
    if '今天' in s:
        return (9998, 0, 0)
    if '昨天' in s:
        return (9997, 0, 0)
    if '前天' in s:
        return (9996, 0, 0)
    m = re.search(RELDATE_NUM_PATTERNS['day'], s)
    if m:
        return (9000 - int(m.group(1)), 0, 0)
    m = re.search(RELDATE_NUM_PATTERNS['week'], s)
    if m:
        return (8000 - int(m.group(1)), 0, 0)
    m = re.search(RELDATE_NUM_PATTERNS['month'], s)
    if m:
        return (7000 - int(m.group(1)), 0, 0)
    m = re.search(RELDATE_NUM_PATTERNS['year'], s)
    if m:
        return (6000 - int(m.group(1)), 0, 0)
    m = re.match(r'(\d{4})/(\d{2})/(\d{2})', s)
    if m:
        return (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return (0, 0, 0)

def is_subsequence(needle, haystack):
    it = iter(haystack)
    return all(c in it for c in needle)

def title_matches(title, keyword):
    if not title or not keyword:
        return True
    t = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', title)
    k = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', keyword)
    if not k:
        return True
    return is_subsequence(k, t)


def title_or_summary_matches(keyword, title='', summary='', *extra_urls):
    if not keyword:
        return True
    if title_matches(title, keyword):
        return True
    if title_matches(summary, keyword):
        return True
    for extra in extra_urls:
        if not extra:
            continue
        if isinstance(extra, (list, tuple, set)):
            for item in extra:
                if title_matches(str(item), keyword):
                    return True
            continue
        if title_matches(str(extra), keyword):
            return True
    return False