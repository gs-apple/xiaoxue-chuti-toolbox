# yingyu_store.py — 英语数据的存储层（单文件 · 分节文本 · 原子写 · 零有损）
#
# 设计目标（替代原来的 yingyu_data.py 扁平字典 + exec 加载）：
#   1) 单文件：所有版本/年级/学期/单元都在一个 yingyu/data/yingyu_data.txt 里，
#      随程序目录一起分发，客户打开软件即可用，不需要任何额外数据目录。
#   2) 零有损：内存里保存的是每个内容块的「原始行列表」，写回时原样逐行输出，
#      不做「解析成结构再格式化回去」，所以 * 三会词标记、行内空格、|| 分隔
#      这些细节绝不会在存盘时被改写。
#   3) 原子写：先写同目录 .tmp 并 fsync，再 os.replace 原子替换；替换前把旧文件
#      复制成 .bak。任何一步失败都不会出现「写一半的残缺数据」。
#   4) 不执行代码：用行的逐行解析代替 exec()，手改出现笔误时最坏也只是该行被忽略，
#      不会让整个英语模块崩掉。
#
# 文件格式（见 _HEADER，与数据文件头部的说明保持一致）：
#
#   [人教版(PEP)] 三年级 上学期 Unit 1     ← 单元分节
#
#   .单词                                   ← 内容块（单词 / 课文 / 表达句）
#   *name /neɪm/ 名字
#
#   .课文
#   Hello! I'm Mike Black. || 你好！我是迈克·布莱克。

import os
import re
import shutil

from constants import BASE_DIR

BLOCK_WORDS = "单词"
BLOCK_TEXT = "课文"
BLOCK_EXPR = "表达句"
BLOCKS = (BLOCK_WORDS, BLOCK_TEXT, BLOCK_EXPR)

# 兼容旧代码里使用的中文键名（旧结构用的是 "words")
_KEY_ALIASES = {
    "words": BLOCK_WORDS,
    "课文": BLOCK_TEXT,
    "表达句": BLOCK_EXPR,
}

_HEADER = """\
# ══════════════════════════════════════════════════════════════════════
#  小学出题工具箱 · 英语数据（单词 / 课文 / 表达句）
# ══════════════════════════════════════════════════════════════════════
#
#  直接用记事本改就行，保存时保持 UTF-8 编码。改完重新打开软件即可生效。
#
#  ■ 单元分节标题：   [版本] 年级 学期 Unit N
#        例：  [人教版(PEP)] 三年级 上学期 Unit 1
#
#  ■ 三种内容块，每个单元按需写，没内容可以省略：
#
#        .单词       每行一个词：  单词 /音标/ 中文意思
#                    行首加 * 表示三会词
#                    例：  team /tiːm/ 队；组
#                          *name /neɪm/ 名字
#
#        .课文       每行一句：    英文 || 中文
#                    例：  Hello! I'm Mike Black. || 你好！我是迈克·布莱克。
#
#        .表达句     每行一句：    英文 || 中文
#
#  ■ 以 # 开头的是注释，空行会被忽略。
#
#  加一个词：找到对应单元的 .单词 块，在下面加一行。
#  加一个版本：加一个新的分节，或用软件里的「新增版本」按钮。
#
# ══════════════════════════════════════════════════════════════════════
"""

_UNIT_RE = re.compile(r"^\[(.+?)\]\s+(\S+)\s+(\S+?)\s+Unit\s*(\d+)\s*$")
_BLOCK_RE = re.compile(r"^\.\s*(单词|课文|表达句)\s*$")

_APP_NAME = "小学出题工具箱"
_REL_DATA = os.path.join("yingyu", "data", "yingyu_data.txt")

_CACHE = {}
_WRITE_CHECKED = {}


# ── 路径 ────────────────────────────────────────────────────
def _dir_writable(d):
    """目录（或可创建该目录的父目录）是否可写，结果缓存，避免反复建测试文件。"""
    if d in _WRITE_CHECKED:
        return _WRITE_CHECKED[d]
    ok = False
    try:
        if not os.path.isdir(d):
            os.makedirs(d, exist_ok=True)
        probe = os.path.join(d, ".__w_test")
        with open(probe, "w", encoding="utf-8") as f:
            f.write("x")
        os.remove(probe)
        ok = True
    except Exception:
        ok = False
    _WRITE_CHECKED[d] = ok
    return ok


def _appdata_dir():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, _APP_NAME)


def data_path():
    """数据文件的可写路径。

    优先顺序：
      1) 程序目录 yingyu/data/yingyu_data.txt —— 正常解压使用/开发时就是这里，
         跟 assets/stroke_data.json 一样随程序目录分发，客户开箱即用；
      2) 程序目录不可写（例如装在 Program Files）时，退到
         %APPDATA%\\小学出题工具箱\\yingyu_data.txt。
    """
    if "path" in _CACHE:
        return _CACHE["path"]
    primary = os.path.join(BASE_DIR, _REL_DATA)
    if _dir_writable(os.path.dirname(primary)):
        path = primary
    else:
        path = os.path.join(_appdata_dir(), "yingyu_data.txt")
    _CACHE["path"] = path
    return path


def data_path_kind():
    """返回 (路径, 'program' 或 'appdata')，UI 上用来提示用户去哪改数据。"""
    p = data_path()
    return p, ("program" if p.startswith(BASE_DIR) else "appdata")


# ── 解析 / 序列化 ───────────────────────────────────────────
def _empty_blocks():
    return {k: [] for k in BLOCKS}


def empty_unit():
    """一个空单元（三个内容块都为空）。新增版本时用来占位。"""
    return _empty_blocks()


def parse(text):
    """分节文本 → {版本: {年级: {学期: {Unit N: {"单词": [行...], ...}}}}}。

    内容行按 strip 后原样保存（不拆分、不重组），保证写回零有损。
    格式有误的行直接跳过，不会抛异常。
    """
    data = {}
    unit = None
    block = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = _UNIT_RE.match(line)
        if m:
            ver = m.group(1).strip()
            grade, semester = m.group(2).strip(), m.group(3).strip()
            uname = "Unit %d" % int(m.group(4))
            unit = (data.setdefault(ver, {})
                        .setdefault(grade, {})
                        .setdefault(semester, {})
                        .setdefault(uname, _empty_blocks()))
            block = None
            continue
        m = _BLOCK_RE.match(line)
        if m:
            block = m.group(1)
            continue
        if unit is not None and block is not None:
            unit[block].append(line)
    return data


def _unit_sort_key(name):
    m = re.search(r"(\d+)", name or "")
    return (0, int(m.group(1))) if m else (1, 0)


def serialize(data):
    """结构 → 分节文本。逐行原样输出，除注释与空行排版外不改动任何内容。

    单元即使三个块都为空也会保留分节标题 —— 这样「新增版本」建立但还没填内容的
    占位单元不会在下次保存时消失。
    """
    out = [_HEADER.rstrip("\n"), ""]
    for ver, gd in data.items():
        for grade, sd in gd.items():
            for semester, ud in sd.items():
                for uname in sorted(ud.keys(), key=_unit_sort_key):
                    blocks = ud[uname] or {}
                    body = []
                    for key in BLOCKS:
                        lines = [x for x in (blocks.get(key) or []) if str(x).strip()]
                        if not lines:
                            continue
                        body.append("." + key)
                        body.extend(str(x).strip() for x in lines)
                        body.append("")
                    out.append("[%s] %s %s %s" % (ver, grade, semester, uname))
                    out.append("")
                    out.extend(body)
    return "\n".join(out).rstrip("\n") + "\n"


# ── 读写 ────────────────────────────────────────────────────
def load(force=False):
    """读取数据（带缓存）。

    缓存会检查文件 mtime：如果用户用记事本改过数据文件并保存，这里能立刻感知到
    并自动重读，不需要重启软件。
    """
    if not force and "data" in _CACHE:
        try:
            if os.path.getmtime(_CACHE.get("path") or "") == _CACHE.get("mtime"):
                return _CACHE["data"]
        except Exception:
            pass
        # mtime 变了或取不到 → 落到下面重新读取
    p = data_path()
    if not os.path.exists(p):
        _CACHE["data"] = {}
        _CACHE["mtime"] = None
        return _CACHE["data"]
    try:
        with open(p, encoding="utf-8-sig") as f:
            text = f.read()
        _CACHE["mtime"] = os.path.getmtime(p)
    except Exception:
        _CACHE["data"] = {}
        _CACHE["mtime"] = None
        return _CACHE["data"]
    _CACHE["data"] = parse(text)
    return _CACHE["data"]


def save(data=None, path=None):
    """原子写回。返回实际写入路径。

    - 先写同目录 .tmp 并 fsync，成功后 os.replace 原子替换；
    - 替换前把旧文件保存为 .bak（只保留最近一份，不会越积越多）；
    - 任何异常都会清理 .tmp，原文件保持完好。
    """
    data = load() if data is None else data
    p = path or data_path()
    d = os.path.dirname(p)
    os.makedirs(d, exist_ok=True)
    text = serialize(data)
    tmp = p + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        if os.path.exists(p):
            try:
                shutil.copy2(p, p + ".bak")
            except Exception:
                pass
        os.replace(tmp, p)
    except Exception:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
        raise
    _CACHE["data"] = data
    _CACHE["path"] = p
    try:
        _CACHE["mtime"] = os.path.getmtime(p)
    except Exception:
        _CACHE["mtime"] = None
    return p


def clear_cache():
    _CACHE.pop("data", None)


# ── 对外兼容层：旧的 words/课文/表达句 字符串 ───────────────
def unit_to_legacy(unit_blocks):
    """单元块 → 旧结构 {"words": str, "课文": str, "表达句": str}。

    yingyu_core 里的 _parse_words / _parse_sentences 仍按旧契约接收字符串，
    这层适配让上层逻辑一行都不用改。
    """
    b = unit_blocks or {}
    return {
        "words": "\n".join(b.get(BLOCK_WORDS) or []),
        "课文": "\n".join(b.get(BLOCK_TEXT) or []),
        "表达句": "\n".join(b.get(BLOCK_EXPR) or []),
    }


def legacy_to_lines(text):
    """旧的多行字符串 → 行列表（用于迁移与批量导入）。"""
    return [ln.strip() for ln in (text or "").splitlines() if ln.strip()]


def block_of(unit_blocks, key):
    """按 "words" / "单词" / "课文" / "表达句" 取对应块的行列表。"""
    k = _KEY_ALIASES.get(key, key)
    return (unit_blocks or {}).get(k) or []


# ── 从旧 yingyu_data.py 迁移 ────────────────────────────────
def migrate_from_py(py_path=None, target=None):
    """把旧的 yingyu_data.py（ENGLISH_DATA 大字面量）转成新的单文件文本。

    返回 (写入路径, 单元数, 单词数, 句子数)。
    仅在一次性迁移时使用；迁移完成后运行期不再依赖旧 .py。
    """
    if py_path is None:
        py_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "yingyu_data.py")
    ns = {}
    with open(py_path, encoding="utf-8") as f:
        src = f.read()
    exec(compile(src, py_path, "exec"), ns)  # noqa: S102 —— 仅迁移时读一次本地旧数据
    old = ns.get("ENGLISH_DATA") or {}

    new = {}
    n_unit = n_word = n_sent = 0
    for ver, gd in old.items():
        for grade, sd in gd.items():
            for semester, ud in sd.items():
                for uname, unit in ud.items():
                    wl = legacy_to_lines(unit.get("words", ""))
                    tl = legacy_to_lines(unit.get("课文", ""))
                    el = legacy_to_lines(unit.get("表达句", ""))
                    # 空单元也保留：这样「六年级」这类纯占位的年级/学期不会从
                    # 下拉框里消失，用户随时可以往里补内容。
                    bucket = (new.setdefault(ver, {})
                                 .setdefault(grade, {})
                                 .setdefault(semester, {}))
                    bucket[uname] = {
                        BLOCK_WORDS: wl,
                        BLOCK_TEXT: tl,
                        BLOCK_EXPR: el,
                    }
                    if wl or tl or el:
                        n_unit += 1
                    n_word += len(wl)
                    n_sent += len(tl) + len(el)
    p = save(new, target or data_path())
    return p, n_unit, n_word, n_sent
