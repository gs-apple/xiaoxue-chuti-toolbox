# yingyu_store.py — 英语数据的存储层（按「版本 / 年级」分文件 · 分节文本 · 原子写 · 零有损）
#
# 目录结构（随程序目录一起分发，客户开箱即用）：
#
#   yingyu/data/
#       人教版PEP/
#           三年级.txt        ← 一个文件 = 一个版本的一个年级，含上学期 + 下学期
#           四年级.txt
#           五年级.txt
#           六年级.txt
#       陕旅版/
#           三年级.txt
#           ...
#       .bak/                 ← 每次保存前自动留一份上一版，只保留最近一份
#
# 单个文件内容格式（见 _header()，与文件头部的说明保持一致）：
#
#   [上学期] Unit 1           ← 单元分节：学期 + 单元号
#   .单词                     ← 内容块（单词 / 课文 / 表达句）
#   *name /neɪm/ 名字
#   .课文
#   Hello! I'm Mike Black. || 你好！我是迈克·布莱克。
#
# 设计要点：
#   1) 按版本+年级分文件：找内容只需打开一个 10~25KB 的文本，不必在 135KB 里翻。
#   2) 零有损：内存里保存的是每个内容块的「原始行列表」，写回时原样逐行输出，
#      不做「解析成结构再格式化回去」，所以 * 三会词标记、行内空格、|| 分隔
#      这些细节绝不会在存盘时被改写。
#   3) 原子写：先写同目录 .tmp 并 fsync，再 os.replace 原子替换；替换前把旧文件
#      备份到 .bak/。任何一步失败都不会出现「写一半的残缺数据」。
#   4) 只写有变化的文件：保存时逐个年级比对内容，没改动的文件不重写、不轮换备份。
#   5) 不执行代码：逐行解析，手改出现笔误时最坏也只是该行被忽略，不会让模块崩掉。

import os
import re
import shutil

from constants import BASE_DIR

BLOCK_WORDS = "单词"
BLOCK_TEXT = "课文"
BLOCK_EXPR = "表达句"
BLOCKS = (BLOCK_WORDS, BLOCK_TEXT, BLOCK_EXPR)

# 兼容旧代码里使用的中文/英文键名（旧结构用的是 "words")
_KEY_ALIASES = {
    "words": BLOCK_WORDS,
    "课文": BLOCK_TEXT,
    "表达句": BLOCK_EXPR,
}

_APP_NAME = "小学出题工具箱"
_REL_DATA_DIR = os.path.join("yingyu", "data")
_LEGACY_NAME = "yingyu_data.txt"     # 上一版的单文件数据，仅用于自动迁移
_BAK_DIR = ".bak"

# 年级顺序（汉字按拼音排不对，必须显式指定；不认识的年级排到最后）
_GRADE_ORDER = {"一年级": 1, "二年级": 2, "三年级": 3,
                "四年级": 4, "五年级": 5, "六年级": 6}
_SEM_ORDER = {"上学期": 0, "下学期": 1}

# 分节标题：完整格式（兼容旧单文件，粘贴过来也能认）与按年级文件的简写格式
_UNIT_FULL_RE = re.compile(r"^\[(.+?)\]\s+(\S+)\s+(\S+?)\s+Unit\s*(\d+)\s*$")
_UNIT_GRADE_RE = re.compile(r"^\[(.+?)\]\s+Unit\s*(\d+)\s*$")
_BLOCK_RE = re.compile(r"^\.\s*(单词|课文|表达句)\s*$")

# Windows 文件名非法字符（版本名/年级名用作目录名、文件名时要替换掉）
_BAD_NAME_CHARS = '\\/:*?"<>|'

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


def _safe_name(name):
    """把版本名/年级名变成合法的文件（夹）名。"""
    s = "".join("_" if c in _BAD_NAME_CHARS else c for c in str(name or ""))
    return s.strip().strip(".") or "_"


def data_root():
    """数据根目录（其下按版本分文件夹，文件夹里按年级放 .txt）。

    优先顺序：
      1) 程序目录 yingyu/data —— 正常解压使用/开发时就是这里，
         跟 assets/stroke_data.json 一样随程序目录分发，客户开箱即用；
      2) 程序目录不可写（例如装在 Program Files）时，退到
         %APPDATA%\\小学出题工具箱\\yingyu\\。
    """
    if "root" in _CACHE:
        return _CACHE["root"]
    primary = os.path.join(BASE_DIR, _REL_DATA_DIR)
    if _dir_writable(primary):
        root = primary
    else:
        root = os.path.join(_appdata_dir(), "yingyu")
        os.makedirs(root, exist_ok=True)
    _CACHE["root"] = root
    return root


def data_path():
    """兼容旧调用：返回数据根目录（不是单个文件）。"""
    return data_root()


def data_path_kind():
    """返回 (数据根目录, 'program' 或 'appdata')，UI 上用来提示用户去哪改数据。"""
    root = data_root()
    return root, ("program" if root.startswith(BASE_DIR) else "appdata")


def version_dir(version):
    """某版本的数据文件夹，如 yingyu/data/人教版PEP。"""
    return os.path.join(data_root(), _safe_name(version))


def data_file(version, grade):
    """某版本某年级的数据文件，如 yingyu/data/人教版PEP/四年级.txt。"""
    return os.path.join(version_dir(version), _safe_name(grade) + ".txt")


# 旧名兼容
unit_file = data_file


def _bak_path(path):
    """备份文件位置：data/.bak/<版本>__<年级>.txt.bak。"""
    ver = os.path.basename(os.path.dirname(path))
    name = os.path.splitext(os.path.basename(path))[0]
    return os.path.join(data_root(), _BAK_DIR, "%s__%s.txt.bak" % (ver, name))


# ── 解析 / 序列化 ───────────────────────────────────────────
def _empty_blocks():
    return {k: [] for k in BLOCKS}


def empty_unit():
    """一个空单元（三个内容块都为空）。新增版本时用来占位。"""
    return _empty_blocks()


def _unit_sort_key(name):
    m = re.search(r"(\d+)", name or "")
    return (0, int(m.group(1))) if m else (1, 0)


def parse_file(text, version="", grade=""):
    """单个年级文件 → {学期: {"Unit N": {"单词": [行...], ...}}}。

    内容行按 strip 后原样保存（不拆分、不重组），保证写回零有损。
    格式有误的行直接跳过，不会抛异常。
    """
    sems = {}
    cur = None
    block = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = _UNIT_FULL_RE.match(line)
        if m:
            sem = m.group(3).strip()
            uname = "Unit %d" % int(m.group(4))
            cur = sems.setdefault(sem, {}).setdefault(uname, _empty_blocks())
            block = None
            continue
        m = _UNIT_GRADE_RE.match(line)
        if m:
            sem = m.group(1).strip()
            uname = "Unit %d" % int(m.group(2))
            cur = sems.setdefault(sem, {}).setdefault(uname, _empty_blocks())
            block = None
            continue
        m = _BLOCK_RE.match(line)
        if m:
            block = m.group(1)
            continue
        if cur is not None and block is not None:
            cur[block].append(line)
    return sems


def parse(text):
    """完整分节文本（旧单文件格式）→
    {版本: {年级: {学期: {"Unit N": {"单词": [行...], ...}}}}}。

    仅在迁移旧数据时使用；运行期的解析入口是 parse_file()。
    """
    data = {}
    cur = None
    block = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = _UNIT_FULL_RE.match(line)
        if m:
            ver = m.group(1).strip()
            grade, sem = m.group(2).strip(), m.group(3).strip()
            uname = "Unit %d" % int(m.group(4))
            cur = (data.setdefault(ver, {})
                       .setdefault(grade, {})
                       .setdefault(sem, {})
                       .setdefault(uname, _empty_blocks()))
            block = None
            continue
        m = _UNIT_GRADE_RE.match(line)
        if m and cur is not None:
            # 简写格式没带版本/年级，沿用上一条完整分节的归属
            block = None
            continue
        if _BLOCK_RE.match(line):
            block = _BLOCK_RE.match(line).group(1)
            continue
        if cur is not None and block is not None:
            cur[block].append(line)
    return data


def _header(version, grade):
    bar = "# " + "═" * 62
    return "\n".join([
        bar,
        "#  %s · %s   （上学期 + 下学期）" % (version, grade),
        bar,
        "#  直接用记事本改，保存为 UTF-8；改完切回软件即生效，不需要重启。",
        "#",
        "#  [上学期] Unit 1           单元分节：学期 + 单元号",
        "#  .单词 / .课文 / .表达句    内容块，没内容可以整块不写",
        "#  team /tiːm/ 队；组         单词行：单词 /音标/ 中文意思",
        "#  *name /neɪm/ 名字          行首 * = 三会词",
        "#  Hello! || 你好！            句子行：英文 || 中文",
        "#",
        "#  加内容 = 在对应块下面加一行；加单元 = 新起一个 [学期] Unit N 分节。",
        "#  以 # 开头的是注释，空行会被忽略。",
        bar,
    ])


def serialize_grade(version, grade, sems):
    """一个年级的结构 → 单文件文本。逐行原样输出，除注释与空行排版外不改动内容。

    单元即使三个块都为空也会保留分节标题 —— 这样「新增版本」建立但还没填内容的
    占位单元不会在下次保存时消失。
    """
    out = [_header(version, grade), ""]
    order = sorted(sems.keys(), key=lambda s: (_SEM_ORDER.get(s, 99), s))
    for sem in order:
        ud = sems.get(sem) or {}
        for uname in sorted(ud.keys(), key=_unit_sort_key):
            blocks = ud[uname] or {}
            out.append("[%s] %s" % (sem, uname))
            out.append("")
            for key in BLOCKS:
                lines = [str(x).strip() for x in (blocks.get(key) or []) if str(x).strip()]
                if not lines:
                    continue
                out.append("." + key)
                out.extend(lines)
                out.append("")
    return "\n".join(out).rstrip("\n") + "\n"


def serialize(data):
    """整份结构 → 单文件文本（仅用于导出/调试，运行期按年级分别写）。"""
    out = []
    for ver, gd in data.items():
        for grade, sd in gd.items():
            out.append(serialize_grade(ver, grade, sd))
    return "\n".join(out)


# ── 文件遍历 / 读写 ─────────────────────────────────────────
def _iter_files(root):
    """遍历 <root>/<版本>/<年级>.txt。"""
    try:
        names = sorted(os.listdir(root))
    except Exception:
        return []
    files = []
    for n in names:
        if n.startswith("."):
            continue
        vd = os.path.join(root, n)
        if not os.path.isdir(vd):
            continue
        try:
            subs = sorted(os.listdir(vd))
        except Exception:
            continue
        for f in subs:
            if f.lower().endswith(".txt") and not f.startswith("."):
                files.append(os.path.join(vd, f))
    return files


def _scan_sig(root):
    """{文件路径: mtime} —— 用来判断数据是否被外部改动过。"""
    sig = {}
    for p in _iter_files(root):
        try:
            sig[p] = os.path.getmtime(p)
        except Exception:
            sig[p] = 0
    return sig


def _atomic_write(path, text):
    """原子写：.tmp + fsync + os.replace；替换前把旧文件备份到 .bak/。"""
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        if os.path.exists(path):
            try:
                bak = _bak_path(path)
                os.makedirs(os.path.dirname(bak), exist_ok=True)
                shutil.copy2(path, bak)
            except Exception:
                pass
        os.replace(tmp, path)
    except Exception:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
        raise
    return path


def _write_if_changed(path, text):
    """内容没变就不写（避免每次保存都轮换备份、也少一次磁盘操作）。"""
    try:
        if os.path.exists(path):
            with open(path, encoding="utf-8-sig") as f:
                if f.read() == text:
                    return False
    except Exception:
        pass
    _atomic_write(path, text)
    return True


# ── 旧单文件自动迁移 ────────────────────────────────────────
def _auto_migrate(root):
    """把上一版的 yingyu/data/yingyu_data.txt 自动拆成按版本+年级的文件。

    只在「旧文件存在 且 还没有任何按年级的文件」时执行一次；旧文件改名成
    yingyu_data.txt.old 留在原处，不删（万一要回滚）。
    """
    legacy = os.path.join(root, _LEGACY_NAME)
    if not os.path.exists(legacy):
        return False
    others = _iter_files(root)
    if others:
        # 已经迁移过（或用户已手工建了新文件）→ 只把旧文件挪开，不覆盖新数据
        try:
            os.replace(legacy, legacy + ".old")
        except Exception:
            pass
        return False
    try:
        with open(legacy, encoding="utf-8-sig") as f:
            text = f.read()
    except Exception:
        return False
    data = parse(text)
    for ver, gd in data.items():
        for grade, sd in gd.items():
            _atomic_write(data_file(ver, grade), serialize_grade(ver, grade, sd))
    # 旧的单文件备份也挪进 .bak/，保持数据目录干净
    old_bak = legacy + ".bak"
    if os.path.exists(old_bak):
        try:
            os.makedirs(os.path.join(root, _BAK_DIR), exist_ok=True)
            os.replace(old_bak, os.path.join(root, _BAK_DIR, "yingyu_data_单文件版.txt.bak"))
        except Exception:
            pass
    try:
        os.replace(legacy, legacy + ".old")
    except Exception:
        pass
    _CACHE.pop("sig", None)
    return True


# ── 读取 ────────────────────────────────────────────────────
def load(force=False):
    """读取全部数据（带缓存）。

    结构：{版本: {年级: {学期: {"Unit N": {"单词": [行...], "课文": [...], "表达句": [...]}}}}}

    缓存会比对所有数据文件的 mtime：用户用记事本改过任意一个文件并保存，
    这里能立刻感知到并自动重读，不需要重启软件。
    """
    root = data_root()
    _auto_migrate(root)
    sig = _scan_sig(root)
    if not force and "data" in _CACHE and _CACHE.get("sig") == sig:
        return _CACHE["data"]

    items = []
    for path in _iter_files(root):
        ver = os.path.basename(os.path.dirname(path))
        grade = os.path.splitext(os.path.basename(path))[0]
        items.append((ver, grade, path))
    # 版本按名字排，年级按 1~6 的学段顺序排（汉字 unicode 排序是错的）
    items.sort(key=lambda t: (t[0], _GRADE_ORDER.get(t[1], 99), t[1]))

    data = {}
    for ver, grade, path in items:
        try:
            with open(path, encoding="utf-8-sig") as f:
                text = f.read()
        except Exception:
            continue
        sems = parse_file(text, ver, grade)
        if not sems:
            continue
        data.setdefault(ver, {})[grade] = sems

    _CACHE["data"] = data
    _CACHE["sig"] = sig
    return data


def read_grade_text(version, grade):
    """读某个年级文件的原始文本（文件不存在时返回仅含表头的空模板）。"""
    p = data_file(version, grade)
    try:
        with open(p, encoding="utf-8-sig") as f:
            return f.read()
    except Exception:
        return serialize_grade(version, grade, {})


def save_grade_text(version, grade, text):
    """把某个年级文件的完整文本写回（供内置编辑器保存用），返回写入路径。

    写前会把文本解析一遍做校验：如果解析不出任何单元分节，说明用户把结构改坏了，
    直接抛 ValueError，不落盘，原文件保持完好。
    """
    sems = parse_file(text, version, grade)
    if not sems:
        raise ValueError("没有解析到任何单元分节（形如 [上学期] Unit 1），已取消保存。")
    p = data_file(version, grade)
    _atomic_write(p, text if text.endswith("\n") else text + "\n")
    _CACHE.pop("sig", None)   # 强制下次 load 重新扫描
    return p


def save_grade(version, grade, sems):
    """把某个年级的结构写回文件（内部用）。"""
    return _atomic_write(data_file(version, grade),
                         serialize_grade(version, grade, sems))


# ── 写入 ────────────────────────────────────────────────────
def save(data=None):
    """整份写回。按 (版本, 年级) 拆开，只重写内容有变化的文件。

    返回真正写过的文件路径列表（全部没变化时返回空列表）。
    """
    data = load() if data is None else data
    written = []
    for ver, gd in data.items():
        for grade, sd in gd.items():
            if not sd:
                continue
            if _write_if_changed(data_file(ver, grade), serialize_grade(ver, grade, sd)):
                written.append(data_file(ver, grade))
    _CACHE["data"] = data
    _CACHE.pop("sig", None)
    _CACHE["sig"] = _scan_sig(data_root())
    return written


def clear_cache():
    _CACHE.pop("data", None)
    _CACHE.pop("sig", None)


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


# ── 从旧 yingyu_data.py 迁移（历史遗留，已无调用方） ────────
def migrate_from_py(py_path=None):
    """把更旧的 yingyu_data.py（ENGLISH_DATA 大字面量）转成新的分文件结构。

    返回 (数据根目录, 单元数, 单词数, 句子数)。仅在一次性迁移时使用。
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
    save(new)
    return data_root(), n_unit, n_word, n_sent
