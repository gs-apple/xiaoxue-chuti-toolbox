# zhenti_core.py — 真题试卷搜索 / 下载核心模块
#
# 实现方式：requests + 正则解析。五个目标站都是静态列表页，不需要 JS 渲染；
# 也没有引入 Scrapling 之类的反爬框架 —— 一次搜索 4~12 个请求的量级，
# 引入框架只换来打包体积和一层不可控的抽象。
#
# 设计约束（来自 2026-10-28 评审，改代码前先读）：
#   1. 年级/学科/平台三者的能力差异必须显式声明，不支持时给反馈，不许静默返回 0 条。
#   2. 年级只接受 constants.GRADES 里的标准名，任何推断结果都要落回值域。
#   3. 下载的文件名完全由远端控制，落盘路径必须离开源码目录，且只允许白名单扩展名。

import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from urllib.parse import unquote, urljoin, urlparse

from constants import (
    DEFAULT_HEADERS,
    GRADES,
    GRADE_MAP_REVERSE,
    REQUEST_TIMEOUT,
    ZHENTI_DOWNLOAD_DIR,
)

# requests 导入要 0.5s（拖慢整个软件启动），而它只在真正联网搜索/下载时才用
# 得上 —— 延迟到 _get_session() 首次调用时再导入；缺依赖时保持 None 不拖垮程序。
requests = None


# ══════════════════════════════════════════════════════════
#  下载相关常量
# ══════════════════════════════════════════════════════════

DOWNLOAD_TIMEOUT = 30                                 # 下载单独超时：REQUEST_TIMEOUT 是页面级
MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024                # 单文件上限 100MB

# 扩展名白名单：不在表里的一律拒绝，不做"猜一个能用的"回落。
ALLOWED_EXTENSIONS = frozenset({
    "rar", "zip", "7z", "doc", "docx", "pdf", "xls", "xlsx",
})

# Win32 保留设备名。不要只依赖 os.path.abspath 的归一化副作用兜住它们，
# 那是副作用，不是防线。
DEVICE_NAMES = frozenset(
    ["CON", "PRN", "AUX", "NUL"]
    + [f"COM{i}" for i in range(1, 10)]
    + [f"LPT{i}" for i in range(1, 10)]
)

# 内容嗅探：站点会用 HTTP 200 + 真实 Content-Length 回一张"防盗链"占位图，
# 或者直接回登录页 HTML —— 光比字节数发现不了（图片长度是真的）。
# 实测第一试卷网 /uploads/soft/.../x.rar：不带 Referer 时 Content-Type 是
# image/jpeg，落盘 85KB，扩展名 .rar，解压必报错；带上详情页 Referer 才是
# application/x-rar-compressed。所以下载必须（a）带 Referer（b）验文件头。
_REJECT_MAGIC = (
    (b"\xff\xd8\xff", "JPEG 图片"),
    (b"\x89PNG\r\n\x1a\n", "PNG 图片"),
    (b"GIF87a", "GIF 图片"),
    (b"GIF89a", "GIF 图片"),
    (b"<!DOCTYPE", "网页 HTML"),
    (b"<!doctype", "网页 HTML"),
    (b"<html", "网页 HTML"),
    (b"<HTML", "网页 HTML"),
    (b"<?xml", "XML 文档"),
)


def _reject_reason(head: bytes, content_type: str) -> str:
    """内容看起来不是可解压文件时返回原因，正常返回空串。

    只拦"明确不是文件"的（图片 / 网页 / JSON），不强制匹配 RAR/ZIP 头：
    有站点回 application/octet-stream 且头不规范，硬卡容器头会误伤能下的文件。
    """
    ct = (content_type or "").lower()
    if ct.startswith("text/html") or "json" in ct:
        return f"服务器返回的是网页（{ct}），不是试卷文件"
    if ct.startswith("image/"):
        return f"服务器返回的是图片（{ct}），不是试卷文件"
    if not head:
        return "服务器返回了空内容"
    for magic, label in _REJECT_MAGIC:
        if head.startswith(magic):
            return f"服务器返回的是{label}，不是试卷文件"
    return ""


def download_dir() -> str:
    """下载落盘目录（主程序根目录 BASE_DIR），不存在则创建。"""
    os.makedirs(ZHENTI_DOWNLOAD_DIR, exist_ok=True)
    return ZHENTI_DOWNLOAD_DIR


# ══════════════════════════════════════════════════════════
#  HTTP 基础
# ══════════════════════════════════════════════════════════

_SESSION = None


def _load_requests():
    """延迟导入 requests（导入要 0.5s，拖慢启动）。成功返回 True。"""
    global requests
    if requests is None:
        try:
            import requests as _requests
            requests = _requests
        except ImportError:
            return False
    return True


def _get_session():
    """模块级 Session：复用连接，握手开销从 548ms/次 降到 98ms/次。"""
    global _SESSION
    if _SESSION is None:
        if not _load_requests():
            raise RuntimeError("缺少 requests 依赖")
        session = requests.Session()
        session.headers.update(DEFAULT_HEADERS)
        _SESSION = session
    return _SESSION


_META_CHARSET_RE = re.compile(
    rb'<meta[^>]+charset\s*=\s*["\']?\s*([A-Za-z0-9_\-]+)', re.I)


def _normalize_encoding(name: str) -> str:
    """把站点声明的编码归一成 python 认识的超集名。

    gb2312/gbk 一律升到 gb18030：后者是超集，用 gb2312 解 GB18030 特有的字
    会静默出错字（标题变问号/怪字，且没有任何异常可捕获）。
    """
    n = (name or "").strip().lower()
    if not n:
        return ""
    if n in ("gb2312", "gbk", "gb18030", "gb_2312-80", "x-gbk"):
        return "gb18030"
    if n in ("utf8", "utf-8"):
        return "utf-8"
    return n


def _decode_response(resp, declared: str = "") -> str:
    """按 站点声明 > meta charset > 自动探测 的顺序解码。

    判据是"能不能严格解开"（UnicodeDecodeError 会真的抛），
    不是原先那个 `'html' in html.lower()`——错的编码下 ASCII 片段照样含 'html'，
    等于没校验。
    """
    candidates = []
    if declared:
        candidates.append(_normalize_encoding(declared))
    match = _META_CHARSET_RE.search(resp.content[:4096])
    if match:
        candidates.append(_normalize_encoding(match.group(1).decode("ascii", "ignore")))
    candidates.append(_normalize_encoding(resp.apparent_encoding))
    candidates.extend(["utf-8", "gb18030"])

    for enc in candidates:
        if not enc:
            continue
        try:
            return resp.content.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return resp.content.decode("utf-8", errors="ignore")


def _progress(callback, message: str) -> None:
    if callback:
        try:
            callback(message)
        except Exception:
            pass


def _stopped(stop_event) -> bool:
    return stop_event is not None and stop_event.is_set()


# ══════════════════════════════════════════════════════════
#  平台配置
# ══════════════════════════════════════════════════════════

@dataclass
class PlatformConfig:
    """平台能力声明。

    一个平台要新增/修改的信息都集中在这里；UI 的年级、学科下拉框、
    下载按钮可用性也全部由这份声明派生（单一事实来源）。
    """
    name: str                                       # 平台名称（界面显示）
    base_url: str                                   # 基础 URL
    link_pattern: str                               # 列表页链接正则（group1=href, group2=文本）
    grade_map: Dict[str, tuple]                     # 年级码 -> (url_path, 显示名)
    min_title_len: int = 8                          # 标题最小长度（清洗后再判）
    exclude_keywords: List[str] = field(default_factory=list)
    grade_display: Dict[str, str] = field(default_factory=dict)  # 别名 -> 标准年级名
    subject_path: Dict[str, str] = field(default_factory=dict)   # 学科 -> URL 模板（{g} 替换 url_path）
    subject_names: Tuple[str, ...] = ()             # 该站真实有的学科；空元组=未知，不做限制
    # 年级混合页模板（{g} 替换 url_path）。配了它之后，"全部学科"会把年级页和
    # 各学科栏目页一起抓：栏目页给的是全站最新，年级页给的是该年级的完整列表，
    # 两者互不覆盖（实测中小学试卷网三年级：年级页 15 条 + 栏目页 13 条，科学只在栏目页）。
    grade_page_url: str = ""
    # 学科 -> 该学科真实存在的年级显示名。**不在表里的学科代表全年级都有**。
    # 只有平台级 subject_names 是不够的：一年级也会把物理化学列进下拉。
    # 第一试卷网这张表是 2026-10-28 逐栏目实测出来的（sjwl/sjhx/sjsw/sjls/sjdl/sjzz）。
    subject_grades: Dict[str, Tuple[str, ...]] = field(default_factory=dict)
    detail_pattern: str = r"/\d+\.html$"            # 详情页 URL 形态；空串=不校验
    # 分页：列表页只给第一页（多数站每页 20~30 条），后面的存量要翻页才拿得到。
    # page_href_pattern 里的 {page} 会换成页码，在列表页 HTML 里搜，group1=该页 URL
    # （相对路径按列表页做 urljoin）。留空=该站不分页。
    page_href_pattern: str = ""
    # 翻页深度：第一试卷网只翻前 3 页（它的存量卷最多，翻深了就是 2023 年的老卷），
    # 其余平台一律翻到第 20 页，尽量把存量捞全（2026-10-29 用户指定）。
    max_pages: int = 20                             # 单个列表页最多抓几页（含首页）
    # 页面里没有分页链接（只有 JS 或无导航）时用这个按页码拼 URL：
    # {url}=列表页（带尾斜杠），{page}=页码。与 page_href_pattern 二选一即可。
    page_url_template: str = ""
    encoding: str = ""                              # 站点固定编码；空=按 meta/自动探测
    download_kind: str = "none"                     # direct / page / none
    download_patterns: Tuple[str, ...] = ()         # 详情页里定位下载链接的正则（group1=href）

    # 留空 exclude_keywords 的站点（shijuan1 / shijuan_net）实测噪声进不了结果：
    # link_pattern 精确形态 + 详情页 URL 形态 + 清洗后长度三重拦截已足够，
    # 补一套关键词反而会挡掉真实试卷名。


PLATFORM_CONFIGS = {
    "shijuan1": PlatformConfig(
        name="第一试卷网",
        base_url="https://www.shijuan1.com",
        link_pattern=r'<a[^>]+href="(/a/sj\w+/\d+\.html)"[^>]*>(.*?)</a>',
        # url_path 只用于填进学科模板：小学是 1-9，高中是 g1-g3
        grade_map={
            "1": ("1", "一年级"), "2": ("2", "二年级"), "3": ("3", "三年级"),
            "4": ("4", "四年级"), "5": ("5", "五年级"), "6": ("6", "六年级"),
            "7": ("7", "七年级"), "8": ("8", "八年级"), "9": ("9", "九年级"),
            "10": ("g1", "高一"), "11": ("g2", "高二"), "12": ("g3", "高三"),
        },
        subject_path={
            "语文": "a/sjyw{g}/",
            "数学": "a/sjsx{g}/",
            "英语": "a/sjyy{g}/",
            "物理": "a/sjwl{g}/",
            "化学": "a/sjhx{g}/",
            "生物": "a/sjsw{g}/",
            "历史": "a/sjls{g}/",
            "地理": "a/sjdl{g}/",
            "政治": "a/sjzz{g}/",
        },
        subject_names=("语文", "数学", "英语", "物理", "化学", "生物",
                       "历史", "地理", "政治"),
        # 2026-10-28 逐栏目探测结果（每格都是 15~25 条真实链接，不是猜的）：
        #   小学 1-6 只有语数英，没有科学栏目（sjkx* 全 404）；
        #   7 年级起有生物/历史/地理/政治，没有物理化学；
        #   8 年级加物理；9 年级加化学，生物和地理已结课（sjsw9/sjdl9 全 404）；
        #   高中九科全开。语数英不在表里 = 1~12 年级全有。
        subject_grades={
            "物理": ("八年级", "九年级", "高一", "高二", "高三"),
            "化学": ("九年级", "高一", "高二", "高三"),
            "生物": ("七年级", "八年级", "高一", "高二", "高三"),
            "历史": ("七年级", "八年级", "九年级", "高一", "高二", "高三"),
            "地理": ("七年级", "八年级", "高一", "高二", "高三"),
            "政治": ("七年级", "八年级", "九年级", "高一", "高二", "高三"),
        },
        grade_display={
            "初一": "七年级", "初二": "八年级", "初三": "九年级",
            "七年级": "七年级", "八年级": "八年级", "九年级": "九年级",
        },
        encoding="gb18030",                          # DedeCMS + gb2312 页面
        # 分页形如 list_116_2.html —— 116 是站内栏目号，写死会因改版失效，
        # 所以让正则从列表页里带出来
        page_href_pattern=r'["\'](list_\d+_{page}\.html)["\']',
        max_pages=3,                                 # 只有这家限 3 页，其余走默认 20
        download_kind="direct",
        # 锚定 downurllist 容器：站点改版时是"明确失败"，而不是从别处捡一个链接下载错文件。
        download_patterns=(
            r'<ul[^>]+class="[^"]*downurllist[^"]*"[^>]*>.*?href="(/uploads/[^"]+\.(?:rar|zip|7z|doc|docx|pdf|xls|xlsx))"',
        ),
    ),
    "szxuexiao": PlatformConfig(
        name="中小学试卷网",
        base_url="https://appsj.szxuexiao.com",
        link_pattern=r'<a[^>]+href="([^"]+\.html)"[^>]*>(.*?)</a>',
        grade_map={
            "1": ("yinianji", "一年级"), "2": ("ernianji", "二年级"),
            "3": ("sannianji", "三年级"), "4": ("sinianji", "四年级"),
            "5": ("wunianji", "五年级"), "6": ("liunianji", "六年级"),
        },
        # 年级页不分子学科目录（/sinianji/yuwen/ 等全 404），但站内有按学科汇总的栏目页：
        # /yuwen/ /shuxue/ /yingyu/ /kexue/ 各 25 条（2026-10-28 实测）。
        # 科学必须走 /kexue/：年级页里科学卷被语数英挤掉，三年级一条都抓不到，
        # 而栏目页里有 4 条三年级科学卷。
        subject_path={
            "语文": "yuwen/",
            "数学": "shuxue/",
            "英语": "yingyu/",
            "科学": "kexue/",
        },
        grade_page_url="{g}/",
        subject_names=("语文", "数学", "英语", "科学"),
        # 栏目页 /shuxue/ 的分页是 index_2.html（相对路径）。页脚分页条只列到第 5 页，
        # 但 2026-10-29 实测 index_6 / index_20 都是 200 且有 53 条链接，
        # 所以按页码直接拼，翻到平台默认的 20 页。
        page_url_template="index_{page}.html",
        min_title_len=8,
        # 注意：不要放「人教」「部编」「统编」——那是教材版本前缀，几乎每份卷子都带。
        # 2026-10-28 实测这 3 个词挡掉了 47 条真实试卷（全是「统编版2026三年级语文…」这类）。
        exclude_keywords=["备案", "Copyright", "http://", "javascript:", "登录", "注册",
                          "网站首页", "上一页", "下一页", "小学试卷网", "中小学试卷网",
                          "粤ICP备", "京ICP备", "沪ICP备", "浙ICP备"],
        # 实测：详情页 52 个 href 里含 rar/zip/doc/pdf 的 0 个、含 download/file 的 0 个，
        # 原先那条正则必然空跑。这里明确声明"无直链"，UI 据此禁用下载按钮。
        download_kind="none",
    ),
    "yishijuan": PlatformConfig(
        name="新一试卷",
        base_url="https://www.yishijuan.com",
        link_pattern=r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
        grade_map={
            "1": ("xiaoxueshijuan", "一年级"), "2": ("xiaoxueshijuan", "二年级"),
            "3": ("xiaoxueshijuan", "三年级"), "4": ("xiaoxueshijuan", "四年级"),
            "5": ("xiaoxueshijuan", "五年级"), "6": ("xiaoxueshijuan", "六年级"),
            "7": ("chuzhongshijuan", "七年级"), "8": ("chuzhongshijuan", "八年级"),
            "9": ("chuzhongshijuan", "九年级"),
            "10": ("gaozhongshijuan", "高一"), "11": ("gaozhongshijuan", "高二"),
            "12": ("gaozhongshijuan", "高三"),
        },
        subject_path={},
        subject_names=("语文", "数学", "英语", "物理", "化学", "生物",
                       "历史", "地理", "政治"),
        # 列表页里没有分页链接（2026-10-28 实测 6 种常见形态都抓不到 href），
        # 但 /xiaoxueshijuan/2.html 确实是第二页：78 条链接里 27 条合格、全是首页没有的。
        # 第 3 页起每页只多 1 条（与前面重复），去重后不影响结果，页数走平台默认值。
        page_url_template="{url}{page}.html",
        exclude_keywords=["备案", "Copyright", "收藏", "登录", "注册", "关于", "帮助", "javascript"],
        detail_pattern="",                           # 该站链接形态杂，不做详情页校验
        download_kind="none",
    ),
    "shijuan_net": PlatformConfig(
        name="试卷网",
        base_url="https://www.shijuan.net",
        link_pattern=r'<a[^>]+href="([^"]+\.html)"[^>]*>(.*?)</a>',
        grade_map={
            "1": ("yinianji", "一年级"), "2": ("ernianji", "二年级"),
            "3": ("sannianji", "三年级"), "4": ("sinianji", "四年级"),
            "5": ("wunianji", "五年级"), "6": ("liunianji", "六年级"),
            "7": ("qinianji", "七年级"), "8": ("banianji", "八年级"),
            "9": ("jiunianji", "九年级"),
        },
        subject_path={
            "语文": "{g}/yuwen/",
            "数学": "{g}/shuxue/",
            "英语": "{g}/yingyu/",
        },
        subject_names=("语文", "数学", "英语"),
        min_title_len=5,
        # 分页是 /wunianji/shuxue/index_2.html。页脚只列到第 10 页，但 2026-10-29
        # 实测 index_11 / index_20 都是 200 且有 104 条链接，按页码直接拼到默认 20 页。
        page_url_template="index_{page}.html",
        # 2026-10-28 实测：详情页里没有任何本地附件，只有一个蓝奏云分享链接，
        # 文件要提取码（只有关注公众号才发）。2026-10-29 按用户拍板：点「下载」
        # 直接打开试卷详情页，让用户在页面里扫码关注公众号拿码、再去网盘下载，
        # 程序不再代开网盘直链。
        download_kind="page",
        download_patterns=(),
    ),
    "xbjy": PlatformConfig(
        name="心标教育",
        base_url="https://www.xbjy.com",
        link_pattern=r'<a[^>]+href="(/xhtml/[^"]+\.html)"[^>]*>(.*?)</a>',
        # 该站小学语文只分到「学科总页」，四年级语文 /fnjscyw/ 等实测全 404，
        # 因此年级不从 URL 取，改由标题识别（_identify_grade 优先用标题里的年级）
        grade_map={
            "1": ("", "一年级"), "2": ("", "二年级"), "3": ("", "三年级"),
            "4": ("", "四年级"), "5": ("", "五年级"), "6": ("", "六年级"),
        },
        subject_path={
            "语文": "/s/xxyw/",
            "数学": "/s/xxsx/",
            "英语": "/s/xxyy/",
            "科学": "/s/xxkx/",
        },
        subject_names=("语文", "数学", "英语", "科学"),
        min_title_len=10,
        exclude_keywords=["备案", "Copyright", "登录", "注册", "关于我们", "帮助中心",
                          "javascript", "网站地图", "免责声明", "上一页", "下一页"],
        download_kind="none",
    ),
}

# 中文名 / URL -> 平台码（由 PLATFORM_CONFIGS 派生，不再各处硬编码）
PLATFORM_BY_NAME = {cfg.name: key for key, cfg in PLATFORM_CONFIGS.items()}
PLATFORM_BY_URL = {cfg.base_url: key for key, cfg in PLATFORM_CONFIGS.items()}


def resolve_platform_key(platform: str) -> str:
    """把平台码 / 中文名 / 站点 URL 统一成平台码，认不出返回空串。"""
    p = (platform or "").strip()
    if p in PLATFORM_CONFIGS:
        return p
    if p in PLATFORM_BY_NAME:
        return PLATFORM_BY_NAME[p]
    if p in PLATFORM_BY_URL:
        return PLATFORM_BY_URL[p]
    return ""


def platform_grade_names(platform_key: str) -> List[str]:
    """该平台支持的年级显示名（UI 用来提示/过滤）。"""
    config = PLATFORM_CONFIGS.get(platform_key)
    if not config:
        return []
    return [info[1] for info in config.grade_map.values()]


def platform_supports_grade(platform_key: str, grade_name: str) -> bool:
    return grade_name in platform_grade_names(platform_key)


def platform_subjects(platform_key: str, grade_name: str = "") -> Tuple[str, ...]:
    """该平台（可指定年级）真实有的学科；空元组表示未声明，不做限制。

    传了 grade_name 就按 subject_grades 过滤：一年级不会再列出物理化学，
    九年级也不会再列出已经结课的生物地理。学科不在 subject_grades 表里
    代表"该平台全年级都有"（语数英就是这种情况）。
    """
    config = PLATFORM_CONFIGS.get(platform_key)
    if not config:
        return ()
    if not grade_name or not config.subject_grades:
        return config.subject_names
    return tuple(
        subject for subject in config.subject_names
        if subject not in config.subject_grades
        or grade_name in config.subject_grades[subject]
    )


def platforms_with_subject(subject: str, grade_name: str = "") -> List[str]:
    """哪些平台（且该年级）有这个学科，按 PLATFORM_CONFIGS 声明顺序。

    UI 用它做两件事：学科下拉里标注"本平台没有"，以及用户选了本平台没有的
    学科时给出"可以换到哪些平台"。返回空列表表示所有平台都没有这科。
    """
    if not subject:
        return []
    found = []
    for key, config in PLATFORM_CONFIGS.items():
        if subject not in platform_subjects(key, grade_name):
            continue
        if grade_name and not platform_supports_grade(key, grade_name):
            continue
        found.append(key)
    return found


def _alt_platform_hint(current_key: str, subject: str, grade_name: str = "") -> str:
    """「，可用 中小学试卷网 搜科学」这样的补语；没有别家可选时返回空串。

    提示里必须给出路：只说"本平台没有科学"，用户下一步只能自己一个个试平台。
    """
    names = [PLATFORM_CONFIGS[key].name
             for key in platforms_with_subject(subject, grade_name)
             if key != current_key]
    if not names:
        return ""
    return f"，可用 {'、'.join(names)} 搜{subject}"


def platform_download_kind(platform_key: str) -> str:
    config = PLATFORM_CONFIGS.get(platform_key)
    return config.download_kind if config else "none"


def _config_for_url(url: str) -> Optional[PlatformConfig]:
    u = (url or "").strip()
    if not u:
        return None
    for config in PLATFORM_CONFIGS.values():
        host = urlparse(config.base_url).netloc
        if host and host in u:
            return config
    return None


# ══════════════════════════════════════════════════════════
#  年级 / 年份 / 学科 解析
# ══════════════════════════════════════════════════════════

# 「初一/初二/初三」是站点常见别名，统一折算成标准名
_GRADE_ALIAS = {"初一": "七年级", "初二": "八年级", "初三": "九年级"}

# 长词优先：先匹配「道德与法治」再匹配「政治」，否则前半截会被抢走
_SUBJECT_WORDS = [
    ("道德与法治", "道德与法治"), ("道法", "道德与法治"),
    ("语文", "语文"), ("数学", "数学"), ("英语", "英语"),
    ("物理", "物理"), ("化学", "化学"), ("生物", "生物"),
    ("历史", "历史"), ("地理", "地理"), ("政治", "政治"),
    ("科学", "科学"),
]

_YEAR_RE = re.compile(r'(20\d{2})')


def canonical_grade(text: str) -> str:
    """把任意写法的年级折算成 constants.GRADES 里的标准名，认不出返回空串。"""
    t = (text or "").strip()
    if not t:
        return ""
    t = _GRADE_ALIAS.get(t, t)
    return t if t in GRADES else ""


def years_in_title(title: str) -> set:
    """标题里出现的四位年份集合。

    用"抽取后比对"而不是 `year in title`：后者传 "24" 会命中 "2024"，
    传 "2024" 也会命中 "12024"。
    """
    return set(_YEAR_RE.findall(title or ""))


def year_label(title: str) -> str:
    """年份列显示值：单年份原样，「2023-2024」折成「2023-24」。

    学年卷标题里天然有两个年份，筛选按"命中任一年"算，显示成区间才不会
    出现"筛 2024 却看到 2023"的矛盾。
    """
    years = sorted(years_in_title(title))
    if not years:
        return ""
    if len(years) == 1:
        return years[0]
    return f"{years[0]}-{years[-1][2:]}"


# ══════════════════════════════════════════════════════════
#  爬虫
# ══════════════════════════════════════════════════════════

class PaperScraper:
    """真题试卷爬虫（requests + 正则）。

    原先叫 ScraplingScraper，但全仓没有任何 scrapling 的 import —— 名实不符，
    改名时顺手把"反反爬"的注释也删了：这里就是普通的静态页抓取。
    """

    # 标题尾部站点噪声，循环剥离直到干净
    _TITLE_NOISE = [
        r'\d+\s*页\s*立即阅读\s*$',
        r'立即阅读\s*$',
        r'[（(]附参考答案[）)]\s*$',
        r'[（(]附答案[）)]\s*$',
        r'[（(]含答案[）)]\s*$',
        r'[（(]含答案解析[）)]\s*$',
        r'[（(]有答案[）)]\s*$',
        r'PDF\s*电子版下载\s*$',
        r'电子版下载\s*$',
        r'免费下载\s*$',
        r'打包下载\s*$',
    ]

    _ANSWER_RE = re.compile(r'(附参考答案|附答案|含答案|有答案|答案)')

    _GRADE_RE = (r'(初一|初二|初三|一年级|二年级|三年级|四年级|五年级|六年级|'
                 r'七年级|八年级|九年级|高一|高二|高三)')

    # ── 抓页面 ───────────────────────────────────────────

    def _safe_get(self, url: str, timeout: int = REQUEST_TIMEOUT,
                  declared_encoding: str = "") -> Tuple[Optional[str], Optional[str]]:
        """取页面，返回 (html, error)。"""
        if not _load_requests():
            return None, "缺少 requests 依赖"
        try:
            resp = _get_session().get(url, timeout=timeout)
        except Exception as e:                        # 连接/超时/SSL 一律当失败处理
            return None, str(e)
        if resp.status_code != 200:
            return None, f"HTTP {resp.status_code}"
        return _decode_response(resp, declared_encoding), None

    # ── 解析 ─────────────────────────────────────────────

    @staticmethod
    def _build_url(base: str, path: str, add_slash: bool = False) -> str:
        p = (path or "").strip()
        if p.startswith("http"):
            return p
        p = p.lstrip("/")
        url = base if not p else base + "/" + p
        if add_slash and not url.endswith("/"):
            url += "/"
        return url

    def _extract_links(self, html: str, pattern: str, base_url: str) -> List[Tuple[str, str]]:
        links = []
        for match in re.finditer(pattern, html, re.DOTALL):
            href = match.group(1)
            text = match.group(2) if len(match.groups()) > 1 else ""
            title = re.sub(r'<[^>]+>', '', text).strip()

            # 有些站的锚里是 <h2>标题</h2><p>整段摘要</p>，正文会混进标题。
            # 这类站把干净标题放在 a 标签的 title 属性上，优先用它。
            attr = re.search(r'\btitle="([^"]{4,150})"', match.group(0))
            if attr:
                candidate = attr.group(1).strip()
                if candidate and len(candidate) >= 4:
                    title = candidate

            if href.startswith("/"):
                full_url = base_url + href
            elif href.startswith("http"):
                full_url = href
            else:
                full_url = base_url + "/" + href
            links.append((full_url, title))
        return links

    @staticmethod
    def _clean_title(title: str) -> str:
        """去掉「11页立即阅读」「免费下载（附参考答案）」这类后缀。"""
        t = (title or "").strip()
        changed = True
        while changed:
            changed = False
            for pat in PaperScraper._TITLE_NOISE:
                new = re.sub(pat, "", t).strip()
                if new != t:
                    t, changed = new, True
        return t

    def _page_urls(self, html: str, list_url: str,
                   config: PlatformConfig, max_pages: int) -> List[str]:
        """列表页第 2..max_pages 页的 URL。

        优先用 page_url_template 拼（页面里没分页链接的站），否则从 HTML 里抽。
        抽不到就到此为止 —— 不猜未知页长什么样：站点改版时宁可只给一页，
        也不让搜索结果里出现假链接。
        """
        if max_pages <= 1 or (not config.page_href_pattern
                              and not config.page_url_template):
            return []
        if config.page_url_template:
            base = list_url if list_url.endswith("/") else list_url + "/"
            urls = []
            for page in range(2, max_pages + 1):
                text = config.page_url_template.format(url=base, page=page)
                # 模板可以写绝对形态（{url}2.html），也可以只写相对文件名（index_2.html）
                urls.append(text if text.startswith("http") else urljoin(base, text))
            return urls
        urls: List[str] = []
        for page in range(2, max_pages + 1):
            found = re.search(config.page_href_pattern.format(page=page), html, re.S)
            if not found:
                break
            full = urljoin(list_url, found.group(1))
            if full != list_url and full not in urls:
                urls.append(full)
        return urls

    def _filter_title(self, title: str, config: PlatformConfig) -> Optional[str]:
        """长度与排除词过滤（不含年份/关键词，那两个在清洗后再判）。"""
        if not title or len(title) < config.min_title_len:
            return None
        if any(x in title for x in config.exclude_keywords):
            return None
        return title

    def _identify_grade(self, title: str, url_grade: str,
                        config: PlatformConfig, fallback: str = "") -> str:
        """识别年级，结果保证落在 constants.GRADES 值域内。

        优先用标题里的年级；标题没写时按 URL 段推断（数字年级 / g1-g3 高中）。
        原先 URL 兜底返回 f"高{url_grade[1:]}" → "高1"，而 "高1" 不在 GRADES 里，
        会一路污染结果列和收藏夹。这里统一走 GRADE_MAP_REVERSE（12 项完整）。
        """
        match = re.search(self._GRADE_RE, title or "")
        if match:
            canonical = canonical_grade(config.grade_display.get(match.group(1), match.group(1)))
            if canonical:
                return canonical

        key = ""
        url_grade = (url_grade or "").strip()
        if url_grade.startswith("g") and url_grade[1:].isdigit():
            key = str(9 + int(url_grade[1:]))          # g1 -> 10 高一
        elif url_grade.isdigit():
            key = url_grade
        return GRADE_MAP_REVERSE.get(key, "") or fallback

    def _grades_in_title(self, title: str) -> set:
        """标题里出现的所有标准年级名（用于判断这条是不是别的年级混进来的）。"""
        return {g for g in (canonical_grade(x) for x in re.findall(self._GRADE_RE, title or "")) if g}

    def _detect_subject(self, title: str, requested_subject: str,
                        config: PlatformConfig, strict: bool = False) -> Optional[str]:
        """判定学科。

        - 指定了学科：标题写明是别的学科 -> 返回 None（调用方丢弃该条）；
          标题没写学科（如「统编版四年级上册期中测试卷」）-> 按请求的学科归类。
        - 没指定学科：用标题里检测到的学科，检测不到算「综合」。

        strict=True 只对"年级混合页"用：那一页的学科是靠标题猜的，
        标题没写学科就无从判断，硬按请求学科归类会造出"三年级科学·数学卷"。
        学科栏目页不需要 strict，因为整页都是该学科。
        """
        detected = None
        for kw, subj in _SUBJECT_WORDS:
            if kw in title:
                detected = subj
                break

        if requested_subject:
            if detected and detected != requested_subject:
                return None
            if strict and not detected:
                return None
            return requested_subject
        return detected or "综合"

    # ── 搜索 ─────────────────────────────────────────────

    def _resolve_targets(self, config: PlatformConfig, url_path: str,
                         subject: str) -> List[Tuple[str, str]]:
        """该年级这次要访问的地址：[(url, 该地址对应的学科 or "")]。

        subject 为空（全部学科）时，栏目页和年级混合页都要抓：
        栏目页是"全站最新 25 条"，年级页是"该年级的完整列表"，两者只部分重叠。
        实测中小学试卷网三年级：年级页 15 条三年级卷（0 条科学），
        四个栏目页合计 13 条三年级卷（含 3 条科学），合并才不漏。
        """
        grade_url = self._build_url(config.base_url, url_path, add_slash=True)

        if not config.subject_path:
            # 没有学科子栏目：年级页是混合列表，学科只能靠标题判断
            return [(grade_url, "")]

        mixed_page = ""
        if config.grade_page_url:
            mixed_page = self._build_url(
                config.base_url, config.grade_page_url.format(g=url_path), add_slash=True)

        if subject:
            targets = []
            if mixed_page:
                # 年级页里也有该学科的卷子（三年级语文：栏目页 2 条、年级页 5 条，互不包含），
                # 只抓栏目页会漏。这里 target_subject 留空，靠标题严格判学科。
                targets.append((mixed_page, ""))
            template = config.subject_path.get(subject)
            if template:
                targets.append(
                    (self._build_url(config.base_url, template.format(g=url_path)), subject))
            return targets       # 两边都没配就是 []，由调用方跳过

        targets = [(self._build_url(config.base_url, tpl.format(g=url_path)), subj)
                   for subj, tpl in config.subject_path.items()]
        if mixed_page and mixed_page not in [u for u, _ in targets]:
            targets.insert(0, (mixed_page, ""))
        return targets

    def search(self, platform_key: str, subject: str = "", grade: str = "",
               year: str = "", keyword: str = "", result_callback=None,
               stop_event=None, progress_callback=None,
               all_grades: bool = False, max_pages: int = 0) -> List[Dict]:
        """搜索单个平台。

        grade 是 GRADE_MAP 的数字码（"1".."12"）。空 grade 不再隐式退化为
        「全平台全年级」——那会从 4 次请求放大到 105 次（评审 ABILITY-004）。
        需要全年级时必须显式传 all_grades=True。

        max_pages 覆盖平台默认的单列表页抓取页数（0=沿用 PlatformConfig.max_pages）。
        """
        config = PLATFORM_CONFIGS.get(platform_key)
        if not config:
            _progress(progress_callback, f"未知平台: {platform_key}")
            return []

        grade_key = str(grade).strip() if grade not in (None, "") else ""
        if not grade_key and not all_grades:
            _progress(progress_callback, f"{config.name}: 未指定年级，已跳过")
            return []
        if grade_key and grade_key not in config.grade_map:
            names = platform_grade_names(platform_key)
            scope = f"{names[0]}～{names[-1]}" if len(names) > 1 else "无"
            _progress(progress_callback, f"{config.name}没有该年级（仅{scope}）")
            return []
        if subject and config.subject_names and subject not in config.subject_names:
            grade_display = config.grade_map.get(grade_key, ("", ""))[1] if grade_key else ""
            _progress(progress_callback,
                      f"{config.name}: 没有{subject}栏目（本平台仅 {'、'.join(config.subject_names)}）"
                      + _alt_platform_hint(platform_key, subject, grade_display))
            return []
        if subject and grade_key:
            grade_display = config.grade_map[grade_key][1]
            allowed = platform_subjects(platform_key, grade_display)
            if allowed and subject not in allowed:
                _progress(progress_callback,
                          f"{config.name}: {grade_display}没有{subject}"
                          f"（该年级可选 {'、'.join(allowed)}）"
                          + _alt_platform_hint(platform_key, subject, grade_display))
                return []

        keyword = (keyword or "").strip()
        year = (year or "").strip()

        results: List[Dict] = []
        seen_urls = set()
        grades_to_crawl = [grade_key] if grade_key else list(config.grade_map.keys())

        _progress(progress_callback, f"{config.name}: 开始搜索...")

        for gk in grades_to_crawl:
            if _stopped(stop_event):
                break
            url_path, grade_name = config.grade_map[gk]

            for url, target_subject in self._resolve_targets(config, url_path, subject):
                if _stopped(stop_event):
                    break

                html, error = self._safe_get(url, declared_encoding=config.encoding)
                if error:
                    _progress(progress_callback, f"{config.name}: {error}")
                    continue

                # 翻页：列表页只给第一页，存量在后面。没配分页规则的站 pages_html 就只有首页。
                limit = max_pages if isinstance(max_pages, int) and max_pages > 0 else config.max_pages
                pages_html = [html]
                for page_no, page_url in enumerate(
                        self._page_urls(html, url, config, limit), start=2):
                    if _stopped(stop_event):
                        break
                    # 翻页可能到 20 页，状态栏不动会被当成卡死
                    _progress(progress_callback,
                              f"{config.name}: 读取{grade_name}{target_subject}第{page_no}页...")
                    p_html, p_error = self._safe_get(page_url,
                                                     declared_encoding=config.encoding)
                    if p_error:
                        # 翻到底了（多数站超页返回 404）：静默收工，不把 404 当故障报
                        break
                    pages_html.append(p_html)

                page_word = f"共{len(pages_html)}页" if len(pages_html) > 1 else ""
                _progress(progress_callback,
                          f"{config.name}: 解析 {grade_name}{target_subject}列表{page_word}")

                for p_html in pages_html:
                    for full_url, raw_title in self._extract_links(
                            p_html, config.link_pattern, config.base_url):
                        if _stopped(stop_event):
                            break

                        try:
                            if config.detail_pattern and not re.search(config.detail_pattern, full_url):
                                continue

                            title = self._filter_title(raw_title, config)
                            if not title:
                                continue

                            has_answer = bool(self._ANSWER_RE.search(title))

                            # 先清洗再复查长度：原先长度在清洗前判，
                            # 「免费下载（附参考答案）」这类 11 字噪声被洗成 "" 后照样入列。
                            title = self._clean_title(title)
                            if len(title) < config.min_title_len:
                                continue
                            if keyword and keyword not in title:
                                continue
                            if year and year not in years_in_title(title):
                                continue

                            # 学科判定必须在写进 seen_urls 之前：被语文路径丢掉的数学卷
                            # 不该占掉去重名额，否则轮到数学路径时它就被跳过。
                            # target_subject 为空且用户指定了学科 = 这是年级混合页，
                            # 学科只能靠标题严格判，不许"没写学科就归过来"。
                            subject_text = self._detect_subject(
                                title, target_subject or subject, config,
                                strict=bool(subject) and not target_subject)
                            if subject_text is None:
                                continue

                            if full_url in seen_urls:
                                continue

                            # 年级页里常混着别的年级的推荐位：标题只写了唯一一个别的年级就丢掉
                            # （写「1-6年级」这种范围的不管）
                            in_title = self._grades_in_title(title)
                            if grade_key and len(in_title) == 1 and grade_name not in in_title:
                                continue

                            grade_text = self._identify_grade(
                                title, url_path, config, fallback=grade_name)
                            if grade_text not in GRADES:       # 值域兜底，绝不许出现「高1」
                                grade_text = grade_name

                            seen_urls.add(full_url)
                            item = {
                                "platform": config.name,
                                "title": title[:100],
                                "subject": subject_text,
                                "grade": grade_text,
                                "year": year_label(title),
                                "has_answer": has_answer,
                                "url": full_url,
                            }
                            results.append(item)
                            if result_callback:
                                result_callback(item)
                        except Exception:
                            continue

        _progress(progress_callback, f"{config.name}完成，共 {len(results)} 个结果")
        return results

    # ── 下载 ─────────────────────────────────────────────

    def get_download_info(self, url: str) -> Dict[str, str]:
        """解析详情页里的下载链接。

        type: direct（可直下）/ page（交给浏览器打开详情页）/ none（该平台没有可用直链）
        """
        config = _config_for_url(url)
        if config is None:
            return {"type": "none", "url": "", "filename": "",
                    "message": "未知平台，无法解析下载链接"}

        if config.download_kind == "none":
            return {"type": "none", "url": "", "filename": "",
                    "message": f"{config.name}不提供直链下载，试卷只能在网页里查看"}

        if config.download_kind == "page":
            # 网盘/提取码类站点：不解析直链，直接把详情页交给浏览器，
            # 用户在页面上能同时看到二维码、暗号和下载入口。
            return {"type": "page", "url": url, "filename": "",
                    "message": f"请在打开的{config.name}页面上获取下载文件"}

        html, error = self._safe_get(url, declared_encoding=config.encoding)
        if error or html is None:
            return {"type": "none", "url": "", "filename": "",
                    "message": f"无法访问页面: {error}"}

        href = ""
        for pattern in config.download_patterns:
            match = re.search(pattern, html, re.I | re.S)
            if match:
                href = match.group(1)
                break
        if not href:
            return {"type": "none", "url": "", "filename": "",
                    "message": "页面里没有找到可用的下载链接"}

        full_url = href if href.startswith("http") else config.base_url + href
        filename = unquote(urlparse(full_url).path.split("/")[-1])
        if not is_allowed_file(filename):
            return {"type": "none", "url": "", "filename": "",
                    "message": f"不支持的下载文件类型: {filename or '未知'}"}
        return {"type": "direct", "url": full_url, "filename": filename,
                "referer": url,
                "message": f"找到下载链接: {filename}"}

    @staticmethod
    def _extract_filename(resp, url: str) -> str:
        """从 Content-Disposition 取文件名，支持 RFC5987 的 filename*。

        原先的正则把 ' 当终止符，filename*=UTF-8''%E8%AF%95%E5%8D%B7.pdf
        会解析成 "UTF-8"（还丢了扩展名）。
        """
        cd = resp.headers.get("Content-Disposition", "") or ""
        name = ""
        if cd:
            match = re.search(r"filename\*\s*=\s*([\w\-]+)''([^;]+)", cd, re.I)
            if match:
                charset = match.group(1) or "utf-8"
                try:
                    name = unquote(match.group(2).strip(), encoding=charset)
                except Exception:
                    name = unquote(match.group(2).strip())
            else:
                match = (re.search(r'filename\s*=\s*"([^"]*)"', cd, re.I)
                         or re.search(r"filename\s*=\s*([^;]+)", cd, re.I))
                if match:
                    name = unquote(match.group(1).strip())
        if not name:
            name = unquote(urlparse(url).path.split("/")[-1])
        return name

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """清洗远端给的文件名，不合法返回空串。

        要点：剥目录 → 去非法字符 → 去尾部点与空格（Win32 会静默吃掉，
        导致"返回给界面的名字"和"实际文件名"不一致）→ 拒绝设备名。
        """
        n = (name or "").replace("\\", "/")
        n = unquote(n).split("/")[-1]
        n = n.replace("..", "")
        n = "".join(c for c in n if c not in '<>:"|?*\x00')
        n = n.rstrip(" .")
        if not n or n in (".", ".."):
            return ""
        stem = n.rsplit(".", 1)[0].strip().upper()
        if stem in DEVICE_NAMES:
            return ""
        return n

    @staticmethod
    def _unique_path(dirpath: str, filename: str) -> str:
        """重名不覆盖：追加 (1)(2)... 日常用会重复下同一份卷子，覆盖比报错更糟。"""
        stem, ext = os.path.splitext(filename)
        candidate = os.path.join(dirpath, filename)
        index = 1
        while os.path.exists(candidate):
            candidate = os.path.join(dirpath, f"{stem}({index}){ext}")
            index += 1
        return candidate

    def download_file(self, url: str, save_dir: str = "", referer: str = "",
                      progress_callback=None, stop_event=None) -> dict:
        """下载文件。返回 {"success": bool, "filepath": str, "message": str}。

        referer 传详情页 URL：第一试卷网等站的 /uploads 目录有防盗链，
        不带 Referer 会回一张 JPEG 占位图（HTTP 200、长度正常），落盘就是坏压缩包。
        """
        if not _load_requests():
            return {"success": False, "filepath": "", "message": "缺少 requests 依赖"}

        # URL 里带明确扩展名且不在白名单的，先拒掉（省一次请求）。
        # 没扩展名（down.php?id=1 之类）不在这里判，交给落盘时的真实文件名判。
        url_name = unquote(urlparse(url or "").path.split("/")[-1])
        if "." in url_name and not is_allowed_file(url_name):
            return {"success": False, "filepath": "",
                    "message": f"不支持的下载文件类型: {url_name}"}

        save_dir_abs = os.path.abspath(save_dir or download_dir())
        try:
            os.makedirs(save_dir_abs, exist_ok=True)
        except OSError as e:
            return {"success": False, "filepath": "", "message": f"无法创建下载目录: {e}"}

        _progress(progress_callback, "正在下载...")
        req_headers = {}
        if referer:
            # 防盗链站点靠这一行区分"从详情页点的下载"和"直接扒链接"
            req_headers["Referer"] = referer
        try:
            resp = _get_session().get(url, headers=req_headers,
                                      timeout=DOWNLOAD_TIMEOUT, stream=True)
        except Exception as e:
            return {"success": False, "filepath": "", "message": f"下载失败: {e}"}

        if resp.status_code != 200:
            return {"success": False, "filepath": "",
                    "message": f"下载失败: HTTP {resp.status_code}"}

        filename = self._sanitize_filename(self._extract_filename(resp, url))
        if not filename:
            return {"success": False, "filepath": "",
                    "message": "远端文件名非法（路径穿越 / 设备名 / 空名），已拒绝保存"}
        if not is_allowed_file(filename):
            return {"success": False, "filepath": "",
                    "message": f"不支持的下载文件类型: {filename}"}

        filepath = self._unique_path(save_dir_abs, filename)
        # 二次校验：最终路径必须落在 save_dir 内。
        # 这一行同时承担设备名（CON/NUL/COM1）防御：abspath 在 Win32 下会把
        # "CON" 归一化成 "\\.\CON"，前缀必然不符 —— 别当它是冗余代码删掉。
        if not _within_dir(filepath, save_dir_abs):
            return {"success": False, "filepath": "", "message": "非法文件名，已拒绝保存"}

        declared = 0
        try:
            declared = int(resp.headers.get("Content-Length") or 0)
        except (TypeError, ValueError):
            declared = 0
        if declared > MAX_DOWNLOAD_BYTES:
            return {"success": False, "filepath": "",
                    "message": f"文件超过 {MAX_DOWNLOAD_BYTES // 1048576}MB 上限，已拒绝下载"}

        tmp_path = filepath + ".part"
        written = 0
        try:
            with open(tmp_path, "wb") as f:
                first = True
                for chunk in resp.iter_content(chunk_size=8192):
                    if _stopped(stop_event):
                        raise _DownloadCancelled()
                    if not chunk:
                        continue
                    if first:
                        first = False
                        # 首块就判内容真伪，别等 85KB 图片落完盘再说
                        reason = _reject_reason(chunk, resp.headers.get("Content-Type", ""))
                        if reason:
                            raise _NotAFile(reason)
                    written += len(chunk)
                    if written > MAX_DOWNLOAD_BYTES:
                        raise _DownloadTooLarge()
                    f.write(chunk)
                    if declared and progress_callback:
                        pct = min(99, written * 100 // declared)
                        _progress(progress_callback, f"下载中 {pct}%")
            if declared and written != declared:
                raise _DownloadIncomplete(written, declared)
            os.replace(tmp_path, filepath)
        except _DownloadCancelled:
            _remove_quietly(tmp_path)
            return {"success": False, "filepath": "", "message": "下载已取消"}
        except _NotAFile as e:
            _remove_quietly(tmp_path)
            return {"success": False, "filepath": "",
                    "message": f"{e}。站点可能有防盗链或需要登录，"
                               f"可用浏览器打开试卷页面手动下载"}
        except _DownloadTooLarge:
            _remove_quietly(tmp_path)
            return {"success": False, "filepath": "",
                    "message": f"文件超过 {MAX_DOWNLOAD_BYTES // 1048576}MB 上限，已中止"}
        except _DownloadIncomplete as e:
            _remove_quietly(tmp_path)
            return {"success": False, "filepath": "", "message": f"下载不完整（{e}）"}
        except Exception as e:
            _remove_quietly(tmp_path)
            return {"success": False, "filepath": "", "message": f"下载失败: {e}"}

        return {"success": True, "filepath": filepath, "message": f"下载成功: {os.path.basename(filepath)}"}


class _DownloadCancelled(Exception):
    pass


class _NotAFile(Exception):
    """服务器回的是图片/网页，不是可解压文件。"""


class _DownloadTooLarge(Exception):
    pass


class _DownloadIncomplete(Exception):
    def __init__(self, written: int, declared: int):
        super().__init__(f"{written}/{declared} 字节")
        self.written = written
        self.declared = declared


def _remove_quietly(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


def _within_dir(path: str, dirpath: str) -> bool:
    path_abs = os.path.abspath(path)
    return path_abs == dirpath or path_abs.startswith(dirpath + os.sep)


def is_allowed_file(name: str) -> bool:
    """扩展名白名单。注意：判断的是最后一段扩展名，不接受任何例外回落。"""
    if not name or "." not in os.path.basename(name):
        return False
    ext = os.path.basename(name).rsplit(".", 1)[-1].lower()
    return ext in ALLOWED_EXTENSIONS


# 全局爬虫实例（保留 _get_scraper 名字：已有工具脚本在用）
_scraper: Optional[PaperScraper] = None


def _get_scraper() -> PaperScraper:
    global _scraper
    if _scraper is None:
        _scraper = PaperScraper()
    return _scraper


def search_papers(platform, subject="", grade="", year="", keyword="",
                  result_callback=None, stop_event=None, progress_callback=None,
                  all_grades=False, max_pages=0) -> List[Dict]:
    """搜索真题试卷。

    Args:
        platform: 平台码 / 中文名 / 站点 URL
        subject: 中文学科名（"" 或 None 表示全部）
        grade: GRADE_MAP 的数字码（"1".."12"）；空值需配合 all_grades=True
        year: 四位年份字符串，"" 表示不限
        all_grades: True 时才允许空 grade 爬全部年级
        max_pages: 单列表页最多抓几页（0=各平台默认：第一试卷网 3，其余 20）
    """
    platform_key = resolve_platform_key(platform)
    if not platform_key:
        _progress(progress_callback, f"未知平台: {platform}")
        return []
    try:
        return _get_scraper().search(
            platform_key, subject=subject, grade=grade, year=year, keyword=keyword,
            result_callback=result_callback, stop_event=stop_event,
            progress_callback=progress_callback, all_grades=all_grades,
            max_pages=max_pages)
    except Exception as e:
        _progress(progress_callback, f"爬取出错: {e}")
        return []
