# yingyu_core.py — 英语练习生成与导出
import os
import re
import datetime
import random

from constants import BASE_DIR

# ── 数据层 ───────────────────────────────────────────────────
# 数据按「版本 / 年级」分成纯文本文件（随程序目录分发，客户开箱即用）：
#   yingyu/data/人教版PEP/四年级.txt      ← 一个文件 = 一个版本的一个年级，
#                                            里面按学期分节，含上学期 + 下学期
# 单个文件内的格式是「分节 + 行式」，记事本可直接编辑：
#   [上学期] Unit 1              ← 单元分节
#   .单词 / .课文 / .表达句       ← 内容块
#   词行：  单词 /音标/ 中文意思
#   句行：  英文 || 中文
# 解析/写回/原子保存在 yingyu_store.py；内存里保留原始行，写回时原样输出，
# 因此 * 三会词标记、行内空格、|| 分隔等在存盘时绝不会被改写。
try:
    from yingyu import yingyu_store as _store
except ImportError:  # 直接以脚本方式运行时
    import yingyu_store as _store

import os as _os


# 单元名（前 6 个与学期字典的 Unit 1~6 对应；"全部单元" 为汇总项）
UNIT_NAMES = ["Unit 1", "Unit 2", "Unit 3", "Unit 4", "Unit 5", "Unit 6", "全部单元"]

def _reload():
    """从数据文件重新读取（yingyu/data/<版本>/<年级>.txt），返回最新结构。

    结构：{版本: {年级: {学期: {"Unit N": {"单词": [行...], "课文": [...], "表达句": [...]}}}}}
    """
    return _store.load(force=True)

def _get_data():
    return _store.load()

# 词行解析：
#   带音标：  [可选*]单词（可含空格） /音标（可含空格）/ 中文意思
#   无音标：  [可选*]单词（可含空格） 中文意思
#   —— 支持多词单词（ice cream / pull up / take care of 等）与 * 三会词标记（仅展示时去掉）
#
# 音标正则分两档：
#   1) 闭合式（标准）：/.../ 内可含空格、分号、括号、斜杠等任意非中文字符（如 /ˌaɪs ˈkriːm/、/biː ɡʊd fɔː(r)/）
#   2) 无闭合（历史遗留）：red panda /red/panda 小熊猫 —— 斜杠只出现一次、音标到空格/中文为止
# 两档按顺序尝试：先闭合式；若闭合式截断后释义不以非 ASCII（中文/全角）开头，说明音标未完（如 red/panda 被切成 /red/），
# 则回退到无闭合式重新匹配，保证两种格式都能取到完整音标。
_PHONETIC_RE = re.compile(r'/[^\u4e00-\u9fff]+?/')
_PHONETIC_OPEN_RE = re.compile(r'/[^\s\u4e00-\u9fff]+')
# 句子中的「单元分段标题」：Part A / Part B 等（无中文翻译，zh 为空）
_PART_RE = re.compile(r'^Part\s+[A-Za-z0-9]+$', re.I)

# 课文板块小标题（渲染时作为标题显示，不编号、不入四线格）
_SECTION_HEADERS = {
    "Part A", "Part B",
    "Let's talk", "Let's learn", "Listen and do",
    "Listen and chant", "Reading time",
    "Self-check",
    # 各单元 Part A/B 互动板块标题
    "Ask and answer", "Do a survey", "Play with hand shadows",
    "Guess and check", "Colour and say", "Look and talk",
    "Count and say", "Choose and role-play", "Listen, sing and play",
    # 三下板块标题
    "Choose and say", "Look, say and guess", "Think and say",
    "Play a guessing game", "Let's play", "Read and write", "Let's spell",
    # 四上 Read and write 板块
    "Read and compare", "My best friend",
    "Read and tick", "Read and match", "Read and answer",
    # 四下 Read and write 板块 / 短文标题 / 任务指令（居中，与四上一致）
    "Read and number", "Read and circle", "Read and underline",
    "Read, tick and underline",
    "Helping hands in class", "Rules",
    # 五上 Read and write 板块标题
    "Join us for the school talent show!",
    # 五上其他短文标题（Read and write 用）
    "Do you have healthy habits?",
    "The lotus plant",
    "Things you should know before mountain hiking",
    # 五下（2024 新版）Read and write 短文标题
    "Helpful Mr Lu", "The Green Project",
    "Choosing a summer holiday tour",
    # 陕旅版板块标题
    "Let's read", "Let's learn more",
    "Read and think", "Read and discuss", "Read and act",
    "Let's play", "Let's sing", "Let's chant",
}

# 进入这些短文标题后，后续正文首行缩进（与 "Read and X" 等价）
_PARAGRAPH_TITLES = {"My best friend", "Helping hands in class", "Rules",
                     "Join us for the school talent show!",
                     "Do you have healthy habits?",
                     "The lotus plant",
                     "Things you should know before mountain hiking",
                     "Helpful Mr Lu", "The Green Project",
                     "Choosing a summer holiday tour"}

# 组合板块标题：子板块名 + Part 后缀（如 "Let's talk PartA" / "Let's talk Part A" / "Do a survey A" / "Listen and chant B"）
_PART_TITLE_RE = re.compile(
    r"^(Let's talk|Let's learn|Let's sing|Let's chant|Listen and do|Listen and chant|Look and match|Role-play|Ask and answer|Guess and check|Count and say|Do a survey|Play with hand shadows|Look and talk|Colour and say|Choose and role-play|Choose and say|Look, say and guess|Think and say|Play a guessing game|Let's play)\s+(Part\s*[A-Za-z0-9]+|[AB])$",
    re.I)

def _is_part_header(en):
    return bool(_PART_RE.match(en or ""))

def _is_section_header(en):
    # 归一化弯/直引号，兼容数据里混用两种 Let's 写法（否则板块标题会被误判为普通句子）
    en = (en or "").strip()
    norm = en.replace("'", "’")
    if en in _SECTION_HEADERS or norm in _SECTION_HEADERS:
        return True
    # 组合标题（"Let's talk PartA" 等）：直/弯引号都试
    if _PART_TITLE_RE.match(en) or _PART_TITLE_RE.match(norm):
        return True
    return False

def _parse_words(s):
    out = []
    for line in (s or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = _PHONETIC_RE.search(line)
        if m:
            word = line[:m.start()].strip()
            phonetic = m.group(0)
            meaning = line[m.end():].strip()
            # 若闭合式音标截断后剩余释义以 ASCII 开头（如 red panda /red/panda 被切成 /red/ + "panda 小熊猫"），
            # 说明音标实际无闭合斜杠，回退到「音标到空格/中文为止」的无闭合式重新匹配。
            if meaning and re.match(r'[\x00-\x7f]', meaning):
                m2 = _PHONETIC_OPEN_RE.search(line)
                if m2:
                    word = line[:m2.start()].strip()
                    phonetic = m2.group(0)
                    meaning = line[m2.end():].strip()
        else:
            # 无音标：单词 = 首个非 ASCII 字符之前的部分（可含空格、连字符、缩写点等；
            # 中文/全角标点均归为释义，避免把「（」等全角符号并入侵单词）
            m2 = re.search(r'[^\x00-\x7f]', line)
            if m2:
                word = line[:m2.start()].strip()
                meaning = line[m2.start():].strip()
            else:
                word, meaning = line, ""
            phonetic = ""
        out.append({"word": word.lstrip('*').strip(), "phonetic": phonetic, "meaning": meaning})
    return out

def _parse_sentences(s):
    out = []
    for line in (s or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # 按 "||" 切分（不要求两侧空格），兼容 "Part A ||" 这类尾随写法
        if "||" in line:
            en, zh = line.split("||", 1)
        else:
            en, zh = line, ""
        out.append({"en": en.strip(), "zh": zh.strip()})
    return out

def _fmt_word(w):
    return f"{w.get('word','')} {w.get('phonetic','')} {w.get('meaning','')}".strip()

def _fmt_sent(s):
    return f"{s.get('en','')} || {s.get('zh','')}"

def _unit_list(semester_dict):
    """学期字典 → 按序的单元 dict 列表（单元数随数据动态，不再写死 6）。

    数据层存的是原始行列表，这里适配成上层一直使用的
    {"words": 多行字符串, "课文": ..., "表达句": ...} 契约。
    """
    def _num(k):
        try:
            return int(k.split()[1])
        except Exception:
            return 999
    units = []
    for k in sorted(semester_dict.keys(), key=_num):
        if not k.startswith("Unit"):
            continue
        units.append(_store.unit_to_legacy(semester_dict[k]))
    return units

def get_versions():
    return list(_get_data().keys())

def get_grades(version):
    return list(_get_data().get(version, {}).keys())

def get_semesters(version, grade):
    return list(_get_data().get(version, {}).get(grade, {}).keys())

def get_units(version=None, grade=None, semester=None, fallback=6):
    """返回单元下拉项：Unit 1 ~ Unit N + "全部单元"，N 取该版本/年级/学期实际单元数。"""
    n = fallback
    if version and grade and semester:
        try:
            n = len(get_units_data(version, grade, semester))
        except Exception:
            n = fallback
    if n < fallback:
        n = fallback  # 单元数不足常规 6 个时补足（新增版本后还没填内容也能正常选单元）
    names = [f"Unit {i+1}" for i in range(n)]
    names.append("全部单元")
    return names

def get_units_data(version, grade, semester):
    vd = _get_data().get(version, {})
    sd = vd.get(grade, {})
    return _unit_list(sd.get(semester, {}))

def get_unit_words(version, grade, semester, unit_index):
    units = get_units_data(version, grade, semester)
    if not units or unit_index < 0:
        return []
    if unit_index < len(units):
        return _parse_words(units[unit_index]["words"])
    return [w for u in units for w in _parse_words(u["words"])]

def get_unit_sentences(version, grade, semester, unit_index):
    units = get_units_data(version, grade, semester)
    if not units or unit_index < 0:
        return []
    if unit_index < len(units):
        return _parse_sentences(units[unit_index]["课文"])
    return [s for u in units for s in _parse_sentences(u["课文"])]

def get_unit_expressions(version, grade, semester, unit_index):
    """表达句（日常用语）取数，结构与课文一致（en/zh）。"""
    units = get_units_data(version, grade, semester)
    if not units or unit_index < 0:
        return []
    if unit_index < len(units):
        return _parse_sentences(units[unit_index]["表达句"])
    return [s for u in units for s in _parse_sentences(u["表达句"])]

# ── 常用词句（分类词表，独立于 版本/年级/学期/单元） ──
# 数据放在 yingyu_common.py（同款扁平格式），本文件负责加载与解析。
# 独立文件存放：常用词表是固定资源，不与课内数据（yingyu/data/yingyu_data.txt）混在一起，
# 这样编辑课内数据时不会碰到它。
_COMMON_PATH = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "yingyu_common.py")
_COMMON_CACHE = {}

def _get_common():
    if "common" not in _COMMON_CACHE:
        ns = {}
        try:
            exec(compile(open(_COMMON_PATH, encoding="utf-8").read(), _COMMON_PATH, "exec"), ns)
        except Exception:
            ns = {}
        _COMMON_CACHE["common"] = ns.get("COMMON_WORDS", {})
    return _COMMON_CACHE["common"]

def get_common_categories():
    """返回常用词句分类名列表（按 yingyu_common.py 中书写顺序）。"""
    return list(_get_common().keys())

def get_common_words(category):
    """返回某分类下的单词列表（已解析为 dict 列表）。"""
    return _parse_words(_get_common().get(category, ""))

# ── 国际音标表（内容→音标选项） ──
# 数据放在 yingyu_phonetic.py（分组键：元音 / 辅音），行格式：
#   音标 读法 中文读法 | 例词1 意思1；例词2 意思2；例词3 意思3
_PHONETIC_PATH = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "yingyu_phonetic.py")
_PHONETIC_CACHE = {}

def _get_phonetic():
    if "phonetic" not in _PHONETIC_CACHE:
        ns = {}
        try:
            exec(compile(open(_PHONETIC_PATH, encoding="utf-8").read(), _PHONETIC_PATH, "exec"), ns)
        except Exception:
            ns = {}
        _PHONETIC_CACHE["phonetic"] = ns.get("PHONETIC_GROUPS", {})
    return _PHONETIC_CACHE["phonetic"]

def get_phonetic_groups():
    """返回音标一级分组名列表（元音 / 辅音，按书写顺序）。"""
    return list(_get_phonetic().keys())

def get_phonetic_subgroups(group):
    """返回某一级分组下的二级分组名列表。"""
    data = _get_phonetic().get(group, {})
    if isinstance(data, dict):
        return list(data.keys())
    return []

def _parse_phonetic_items(group_text):
    out = []
    for line in (group_text or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # 格式：符号... | 记忆口诀 | 例词...
        # 兼容旧格式（无口诀）：符号... | 例词...
        mnemonic = ""
        if "|" in line:
            segs = [s.strip() for s in line.split("|")]
            symbol_part = segs[0]
            if len(segs) >= 3:
                mnemonic = segs[1]
                examples = segs[2]
            else:
                examples = segs[1]
        else:
            symbol_part, examples = line, ""
        parts = symbol_part.split()
        out.append({
            "symbol": parts[0] if parts else "",
            "read": parts[1] if len(parts) > 1 else "",
            "zh": parts[2] if len(parts) > 2 else "",
            "examples": examples,
            "mnemonic": mnemonic,
        })
    return out

def _parse_examples(examples_str):
    """把例词字符串解析为 (word, ph, meaning) 列表。
    支持两种格式：
      旧：  car 汽车；heart 心
      新：  car /kɑː/ 汽车；heart /hɑːt/ 心
    其中 /.../ 为英文音标（用 _PHONETIC_RE 提取）。"""
    res = []
    for part in (examples_str or "").split("；"):
        part = part.strip()
        if not part:
            continue
        m = _PHONETIC_RE.search(part)
        if m:
            ph = m.group(0)
            word = part[:m.start()].strip()
            meaning = part[m.end():].strip()
        else:
            ph = ""
            sp = part.split(None, 1)
            word = sp[0] if sp else ""
            meaning = sp[1].strip() if len(sp) > 1 else ""
        res.append((word, ph, meaning))
    return res

def _draw_info_line(c, x, y, item, sim_font, ipa_font, size, max_n=1):
    """混排绘制例词信息行：中文读音(zh) + 例词(单词 /音标/ 中文意思)。
    例词音标必须用 ipa_font（Times，IPA 字形完整），中文/单词用 sim_font（SimSun），
    因为 SimSun 缺 ˈ ɜː ɪŋ 等 IPA 字形，直接用会显示成方框。
    max_n：显示前几个例词（默认 1）。返回绘制结束的 x 坐标。"""
    from reportlab.lib import colors
    from reportlab.pdfbase.pdfmetrics import stringWidth
    c.setFillColor(colors.black)
    cur = x
    zh = item.get("zh", "")
    if zh:
        c.setFont(sim_font, size)
        c.drawString(cur, y, zh)
        cur += stringWidth(zh, sim_font, size)
        c.setFont(sim_font, size)
        c.drawString(cur, y, " ")
        cur += stringWidth(" ", sim_font, size)
    for i, (word, ph, meaning) in enumerate(_parse_examples(item.get("examples", ""))[:max_n]):
        if i > 0:
            c.setFont(sim_font, size)
            c.drawString(cur, y, "；")
            cur += stringWidth("；", sim_font, size)
        if word:
            c.setFont(sim_font, size)
            c.drawString(cur, y, word)
            cur += stringWidth(word, sim_font, size)
            c.setFont(sim_font, size)
            c.drawString(cur, y, " ")
            cur += stringWidth(" ", sim_font, size)
        if ph:
            c.setFont(ipa_font, size)
            c.drawString(cur, y, ph)
            cur += stringWidth(ph, ipa_font, size)
            c.setFont(sim_font, size)
            c.drawString(cur, y, " ")
            cur += stringWidth(" ", sim_font, size)
        if meaning:
            c.setFont(sim_font, size)
            c.drawString(cur, y, meaning)
            cur += stringWidth(meaning, sim_font, size)
    # 记忆口诀（比主文小 1 号，置于例词之后）
    mn = item.get("mnemonic", "")
    if mn:
        mnem_size = size - 1
        c.setFont(sim_font, mnem_size)
        c.drawString(cur, y, " ")
        cur += stringWidth(" ", sim_font, mnem_size)
        c.drawString(cur, y, mn)
        cur += stringWidth(mn, sim_font, mnem_size)
    # 描红练习：重复 3 次音标（去掉括号），10pt
    practice = (item.get("symbol", "") or "").strip("[]")
    if practice:
        psize = 11
        c.setFont(ipa_font, psize)
        for _ in range(3):
            c.drawString(cur, y, " ")
            cur += stringWidth(" ", ipa_font, psize)
            c.drawString(cur, y, practice)
            cur += stringWidth(practice, ipa_font, psize)
    return cur

def get_phonetic_items():
    """返回全部音标条目（dict 列表），每条含 group（级）和 sub（二级）字段。"""
    out = []
    data = _get_phonetic()
    for group, subs in data.items():
        if isinstance(subs, dict):
            # 二级分组结构（元音下长元音/短元音/双元音，辅音下爆破音/摩擦音/...）
            for sub, text in subs.items():
                for it in _parse_phonetic_items(text):
                    it["group"] = group
                    it["sub"] = sub
                    out.append(it)
        else:
            # 兼容旧扁平结构
            for it in _parse_phonetic_items(subs):
                it["group"] = group
                out.append(it)
    return out

def add_version(name):
    """新增版本：建一个只含占位单元的版本，原子写回数据文件。

    会在 yingyu/data/<版本>/ 下建好各年级文件（三年级先建），占位单元在文件里
    留下一行分节标题，用户照着补内容即可。
    """
    name = (name or "").strip()
    if not name:
        return False, "版本名不能为空。"
    if "[" in name or "]" in name:
        return False, "版本名里不能包含 [ 或 ]（会与分节标题冲突）。"
    if any(c in name for c in '\\/:*?"<>|'):
        return False, '版本名里不能包含 \\ / : * ? " < > | （要用作文件夹名）。'
    data = _get_data()
    if name in data:
        return False, f"版本「{name}」已存在，请勿重复添加。"
    data[name] = {"三年级": {"上学期": {"Unit 1": _store.empty_unit()}}}
    try:
        paths = _store.save(data)
    except Exception as e:
        return False, f"写回数据文件失败：{e}"
    path = paths[0] if paths else _store.data_file(name, "三年级")
    return True, (
        f"已新增版本「{name}」，数据文件已建好：\n{path}\n\n"
        f"打开它，找到这一节补充内容：\n"
        f"    [上学期] Unit 1\n\n"
        f"    .单词\n    team /tiːm/ 队；组\n\n"
        f"    .课文\n    Hello! || 你好！\n\n"
        f"其它年级（四年级~六年级）在同一个文件夹里，需要时新建同名 txt 即可。"
    )

def add_entry(version, grade, semester, unit_index, entry_type, **fields):
    """新增一条单词或句子：只向目标内容块**追加一行**，然后原子写回。

    与旧实现的关键区别：不再把整块「解析成结构 → 重新格式化」，所以同单元里
    其它行的 * 三会词标记、无 || 的纯英文行、行内空格都原样保留。
    """
    if unit_index < 0:
        return False, "请选择一个单元。"
    data = _get_data()
    if version not in data:
        return False, f"版本「{version}」不存在。"
    uname = f"Unit {unit_index + 1}"
    unit = (data.setdefault(version, {})
                .setdefault(grade, {})
                .setdefault(semester, {})
                .setdefault(uname, _store.empty_unit()))
    for _k in _store.BLOCKS:
        unit.setdefault(_k, [])

    if entry_type == "word":
        w = (fields.get("word") or "").strip()
        if not w:
            return False, "单词不能为空。"
        existing = _parse_words("\n".join(unit[_store.BLOCK_WORDS]))
        if any(x["word"] == w for x in existing):
            return False, f"单词「{w}」在本单元已存在，无需重复添加。"
        unit[_store.BLOCK_WORDS].append(_fmt_word({
            "word": w,
            "phonetic": (fields.get("phonetic") or "").strip(),
            "meaning": (fields.get("meaning") or "").strip(),
        }))
        label = w
    elif entry_type in ("sentence", "expression"):
        en = (fields.get("en") or "").strip()
        if not en:
            return False, "英文句子不能为空。"
        key = _store.BLOCK_TEXT if entry_type == "sentence" else _store.BLOCK_EXPR
        existing = _parse_sentences("\n".join(unit[key]))
        if any(x["en"] == en for x in existing):
            return False, f"句子「{en}」在本单元已存在，无需重复添加。"
        zh = (fields.get("zh") or "").strip()
        unit[key].append(_fmt_sent({"en": en, "zh": zh}) if zh else en)
        label = en
    else:
        return False, "未知的条目类型。"

    try:
        _store.save(data)
    except Exception as e:
        return False, f"写回数据文件失败：{e}"
    return True, f"已添加「{label}」→ {version} · {grade}{semester} · {uname}"

# 导出可用英文字体（用于四线三格上的英文书写）
FONT_OPTIONS = ["舒窈衡水体", "手写体", "Helvetica", "Courier", "Times-Roman"]

def _resolve_en_font(name):
    """将下拉选项解析为 reportlab 可用的字体名。

    内置三种直接用标准字体；自定义两项（舒窈衡水体/手写体）映射到
    用户提供的正式字体文件（assets/fonts 下）。
    """
    if name in ("Helvetica", "Courier", "Times-Roman"):
        return name
    import os.path as _osp
    from constants import FONTS_DIR
    cand = {
        "舒窈衡水体": ("舒窈衡水体.ttf",),
        "手写体": ("舒窈意大利斜体.ttf",),
    }.get(name, ())
    for fn in cand:
        p = _osp.join(FONTS_DIR, fn)
        if _osp.exists(p):
            key = "FNT_" + name
            try:
                from reportlab.pdfbase import pdfmetrics
                from reportlab.pdfbase.ttfonts import TTFont
                pdfmetrics.registerFont(TTFont(key, p))
                return key
            except Exception:
                pass
    return "Helvetica"

# ── 单词字号：让单词大致填满四线三格，但留些余量不顶满 ──
# 基线落在第 3 线（top - 2/3·GRID_H）。各字体在 1em 内的 cap 高度比例不同，
# 据此反推点阵大小。默认 cap 目标 5.0mm（手写体已调好）；衡水体单独调小一点。
_WORD_CAP_TARGET_MM = 5.0
_MM_PER_PT = 25.4 / 72  # 1pt = 0.3528mm
# 个别字体直接给定点阵大小（绕过 cap 比例换算），用于手动微调字号
_WORD_SIZE_BY_FONT = {
    "舒窈衡水体": 17,   # 用户手动指定
    "Helvetica": 15,
    "Courier": 17,
    "Times-Roman": 17,
}

def _word_size_for(font_option):
    if font_option in _WORD_SIZE_BY_FONT:
        return _WORD_SIZE_BY_FONT[font_option]
    # 各字体 cap 高度占 em 的比例（fontTools bbox 实测）
    cap_frac = {
        "舒窈衡水体": 0.646,   # 舒窈衡水体.ttf
        "手写体": 0.820,       # 舒窈意大利斜体.ttf（斜体字形更高）
        "Helvetica": 0.716,
        "Courier": 0.583,
        "Times-Roman": 0.662,
    }.get(font_option, 0.70)
    return int(round(_WORD_CAP_TARGET_MM / (cap_frac * _MM_PER_PT)))

class YingyuGenerator:
    """英语练习生成器：支持 单词记忆 / 课文（课本句子）/ 表达句（日常用语）。"""

    def get_versions(self):
        return get_versions()

    def get_grades(self, version):
        return get_grades(version)

    def get_semesters(self, version, grade):
        return get_semesters(version, grade)

    def get_units(self, version=None, grade=None, semester=None):
        return get_units(version, grade, semester)

    def add_version(self, name):
        return add_version(name)

    def get_unit_words(self, version, grade, semester, unit_index):
        return get_unit_words(version, grade, semester, unit_index)

    def get_unit_sentences(self, version, grade, semester, unit_index):
        return get_unit_sentences(version, grade, semester, unit_index)

    def get_unit_expressions(self, version, grade, semester, unit_index):
        return get_unit_expressions(version, grade, semester, unit_index)

    def get_common_categories(self):
        return get_common_categories()

    def get_common_words(self, category):
        return get_common_words(category)

    def get_phonetic_items(self):
        return get_phonetic_items()

    def sample(self, items, n):
        """从列表中随机抽取 n 个（n<=0 或超出则返回全部）。"""
        if not items:
            return []
        if n <= 0 or n >= len(items):
            return list(items)
        return random.sample(items, n)

    # ───────── 文本渲染（用于界面预览） ─────────
    def render_text(self, content, style, version, grade, semester, items, unit_name="", direction="汉译英"):
        if not items:
            return "（当前选区的词/句数据为空，请点「打开数据」补充。）"
        lines = []
        _last_phon_key = ("", "")
        if content == "单词":
            for w in items:
                if style == "字帖（描红）":
                    lines.append(f"   {w['word']:<14} {w.get('phonetic',''):<12} {w['meaning']}")
                else:
                    # 出题（默写）：按方向显示题干、隐藏答案
                    #   汉译英：显示汉语（题干），英语隐藏留给学生作答
                    #   英译汉：显示英语（题干），汉语隐藏
                    if direction == "汉译英":
                        lines.append(f"   {w['meaning']}")
                    elif direction == "英译汉":
                        lines.append(f"   {w['word']}")
                    else:  # 随机出题：每题按 _dir
                        d = w.get('_dir') or random.choice(("汉译英", "英译汉"))
                        lines.append(f"   {w['meaning'] if d == '汉译英' else w['word']}")
            lines.append("")
        elif content in ("课文", "表达句"):
            for s in items:
                en = s.get('en', '').strip()
                zh = s.get('zh', '').strip()
                # 板块标题（Part A/B 或 Let's talk 等）：作为标题行，不编号
                if _is_section_header(en):
                    title = f"{unit_name} {en}" if (_is_part_header(en) and unit_name.startswith("Unit ")) else en
                    lines.append("")
                    lines.append(title)
                    lines.append("")
                    continue
                if style == "字帖（描红）":
                    lines.append(f"   {en}")
                    if zh:
                        lines.append(f"     {zh}")
                else:
                    # 出题（默写）：按方向显示题干、隐藏答案
                    if direction == "汉译英":
                        prompt = zh if zh else en
                    elif direction == "英译汉":
                        prompt = en
                    else:  # 随机出题
                        d = s.get('_dir') or random.choice(("汉译英", "英译汉"))
                        prompt = (zh if zh else en) if d == "汉译英" else en
                    lines.append(f"   {prompt}")
                lines.append("")
        elif content == "音标":
            # 音标表：按一级分组 + 二级分组逐行显示「音标 读法 中文读法 例词3个」，不区分字帖/出题方式
            for it in items:
                key = (it.get("group", ""), it.get("sub", ""))
                if key != _last_phon_key:
                    title = f"{key[0]} · {key[1]}" if key[1] else key[0]
                    lines.append(f"── {title} ──")
                    _last_phon_key = key
                _mn = it.get("mnemonic", "")
                _prac = (it.get("symbol", "") or "").strip("[]")
                _tail = ""
                if _mn:
                    _tail += f"   {_mn}"
                if _prac:
                    _tail += f"   {_prac} {_prac} {_prac}"
                lines.append(f"   {it['symbol']:<10}{it.get('read',''):<12}{it.get('zh',''):<6}{it.get('examples','')}{_tail}")
            lines.append("")
        else:
            return "不支持的内容"
        lines.append("")
        return "\n".join(lines)

    # ───────── 文件名规则 ─────────
    def make_pdf_path(self, version, grade, semester, unit_name, content):
        """项目目录下生成唯一文件名：
        版本前2字_年级学期(上/下)_单元(全部单元→"全部")+内容_时间，同分钟多份加 _1/_2/_3。
        例：人教_三年级上_Unit 1单词_20260811-0144.pdf / 陕旅_四年级下_全部单词_20260811-0144.pdf"""
        if content == "音标":
            # 音标表与版本/年级/单元无关，用固定前缀名
            now = datetime.datetime.now()
            stamp = now.strftime("%Y%m%d-%H%M")
            base = os.path.join(BASE_DIR, f"音标表_{stamp}")
            path = base + ".pdf"
            i = 1
            while os.path.exists(path):
                path = f"{base}_{i}.pdf"
                i += 1
            return path
        ver2 = version[:2] if version else "英语"
        # 常用词句模式下 grade 为空，则不拼 上/下（避免出现「下」字样）
        gs = (f"{grade}{'上' if '上' in semester else '下'}" if grade else "")
        unit = "全部" if "全部" in unit_name else (unit_name or "全部")
        now = datetime.datetime.now()
        stamp = now.strftime("%Y%m%d-%H%M")
        # 用非空部件拼接文件名，避免连续多余下划线
        parts = [ver2, gs, f"{unit}{content}"]
        name = "_".join(p for p in parts if p)
        base = os.path.join(BASE_DIR, f"{name}_{stamp}")
        path = base + ".pdf"
        i = 1
        while os.path.exists(path):
            path = f"{base}_{i}.pdf"
            i += 1
        return path

    # ───────── PDF 导出 ─────────
    def export_pdf(self, content, style, version, grade, semester, items, unit_name="", font="Helvetica", direction="汉译英", gray=False):
        """导出练习 PDF 到项目目录（文件名自动唯一化）。
        返回 (True, 路径) 或 (False, 错误说明)。"""
        if not items:
            return False, "没有可导出的内容，请先生成。"
        path = self.make_pdf_path(version, grade, semester, unit_name, content)
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import mm
            from reportlab.pdfgen import canvas as _canvas
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from reportlab.pdfbase.pdfmetrics import stringWidth
            from reportlab.lib import colors
        except Exception as e:
            return False, f"缺少 reportlab 库：{e}"

        # 注册字体（与字帖模块一致的回退策略）
        cn_font = "Helvetica"
        en_font = _resolve_en_font(font)
        try:
            from constants import FONTS_DIR
            import os.path as _osp
            for _f in ("kaiti_gb2312.ttf", "simhei.ttf", "simsun.ttc", "msyh.ttc"):
                _p = _osp.join(FONTS_DIR, _f)
                if _osp.exists(_p):
                    pdfmetrics.registerFont(TTFont("CN", _p))
                    cn_font = "CN"
                    break
            else:
                for _p in (r"C:\Windows\Fonts\simkai.ttf",
                           r"C:\Windows\Fonts\simhei.ttf",
                           r"C:\Windows\Fonts\simsun.ttc",
                           r"C:\Windows\Fonts\msyh.ttc"):
                    if _osp.exists(_p):
                        pdfmetrics.registerFont(TTFont("CN", _p))
                        cn_font = "CN"
                        break
        except Exception:
            pass

        # 注册「宋体」(SimSun) 用于「中文意思」；
        # 注册 Windows「Times New Roman」用于「音标/IPA」，
        # 因为标准 Arial/Helvetica/微软雅黑/宋体均缺失部分 IPA 字形（ˈ ɜː ɪŋ 等），
        # 会导致音标显示成「/ˌhɑːd w k /」这种缺字效果；
        # Times New Roman 的 Latin/IPA 字形完整，可正确显示音标。
        simsun_font = "Helvetica"
        ipa_font = "Helvetica"
        try:
            _simsun_path = r"C:\Windows\Fonts\simsun.ttc"
            if _os.path.exists(_simsun_path):
                pdfmetrics.registerFont(TTFont("SIMSUN", _simsun_path, subfontIndex=0))
                simsun_font = "SIMSUN"
        except Exception:
            pass
        try:
            _times_path = r"C:\Windows\Fonts\times.ttf"
            if _os.path.exists(_times_path):
                pdfmetrics.registerFont(TTFont("TIMES_TTF", _times_path))
                ipa_font = "TIMES_TTF"
        except Exception:
            pass

        # 音标表：独立简单版式（逐行「音标 读法 中文读法 例词3个」，不画四线三格）
        if content == "音标":
            return self._export_phonetic(path, items, cn_font, simsun_font, ipa_font)

        # ── 版面参数：严格复刻字帖「四线三格」模板导出规则 ──
        # 来源 zitie_core.generate_blank_template(grid_type="四线三格")：
        #   cell_size_mm=10  base_cell_width_mm=14  row_spacing_mm=5  min_margin=20
        #   margin_x = (210 - cols*14)/2 ；margin_y = max((297 - (rows*(10+5)-5))/2, 20)
        #   _draw_sixiansange：顶线1.0 / 距顶1/3细0.3 / 距顶2/3细0.3 / 底线1.0
        #   _draw_page_header：SimSun 10pt 左上「日期:_____年_____月____日」
        #   _draw_page_number：SimSun 9pt 右下「当前/总」
        page_w, page_h = A4
        GRID_H = 8.5 * mm            # 四线三格总高：3 个格子各减 0.5mm → 10-1.5=8.5
        ROW_GAP = 5 * mm             # 行间距（复刻 row_spacing_mm=5）
        ROWS_PER_PAGE = 18          # 每页四线三格数量（复刻字帖四线三格 rows=17）
        min_margin = 20 * mm        # 复刻 四线三格 min_margin
        CAP_GAP = 3 * mm             # 四线块底到释义基线的距离
        PAD = 2 * mm                 # 文字距左边距的内缩

        # 边距计算（复刻字帖公式）
        margin_x = 14 * mm           # 复刻 (210 - 13*14)/2 = 14mm
        content_left = margin_x
        content_right = page_w - margin_x
        content_width = content_right - content_left

        total_rows_mm = ROWS_PER_PAGE * (GRID_H + ROW_GAP) - ROW_GAP
        margin_y = max((page_h - total_rows_mm) / 2, min_margin)
        start_y = page_h - margin_y  # 网格顶部（复刻 start_y = A4[1] - margin_y）

        SENT_SIZE = 15

        def wrap_text(text, size):
            max_w = content_width - 4 * mm
            parts = text.split()
            if not parts:
                return [text]
            lines, cur = [], ""
            for w in parts:
                test = (cur + " " + w).strip()
                if not cur or stringWidth(test, en_font, size) <= max_w:
                    cur = test
                else:
                    lines.append(cur)
                    cur = w
            if cur:
                lines.append(cur)
            return lines

        # 预先计算分页，得到总页数用于右下页码（复刻字帖的「当前/总」）
        def blocks_of(it):
            if content == "单词":
                return 1
            lines = wrap_text(it.get("en", ""), SENT_SIZE)
            return max(1, len(lines))
        total_blocks = sum(blocks_of(it) for it in items)
        total_pages = max(1, (total_blocks + ROWS_PER_PAGE - 1) // ROWS_PER_PAGE)

        c = _canvas.Canvas(path, pagesize=A4)

        def draw_sixian(y_top):
            # 复刻字帖 _draw_sixiansange：上下粗线 + 中间两条细线
            for ly, lw in ((y_top, 1.0),
                           (y_top - GRID_H / 3, 0.3),
                           (y_top - 2 * GRID_H / 3, 0.3),
                           (y_top - GRID_H, 1.0)):
                c.setLineWidth(lw)
                c.setStrokeColor(colors.black)
                c.line(content_left, ly, content_right, ly)

        def draw_header():
            # 复刻字帖 _draw_page_header：左上角日期填空（SimSun 宋体 10pt，与其他模块一致）
            c.setFillColor(colors.black)
            c.setFont(simsun_font, 10)
            c.drawString(margin_x + 5 * mm, page_h - margin_y + 5 * mm,
                         "日期:_____年_____月____日")

        def page_footer(pno):
            # 复刻字帖 _draw_page_number：右下角「当前/总」
            c.setFont(cn_font, 9)
            c.drawRightString(page_w - margin_x - 5 * mm, margin_y - 6 * mm,
                              f"{pno}/{total_pages}")

        draw_header()
        slot = 0
        page_no = 1

        def new_page():
            nonlocal slot, page_no
            page_footer(page_no)
            c.showPage()
            page_no += 1
            draw_header()
            slot = 0

        def fill_remaining():
            # 将当前页剩余空位全部补画为空白四线三格，保证每一页都画满
            nonlocal slot
            while slot < ROWS_PER_PAGE:
                top = start_y - slot * (GRID_H + ROW_GAP)
                draw_sixian(top)
                slot += 1

        WORD_SIZE = _word_size_for(font)

        # 「灰字」勾选：格内单词/句子范字用灰色（供描红临摹），未勾选则黑色
        text_color = colors.Color(0.62, 0.62, 0.62) if gray else colors.black

        if style == "字帖（描红）":
            # 范字（浅灰）写在四线三格上，下方标音标/翻译，供临摹
            # 短文段落标志：Read and xxx / My best friend 板块下的内容首行缩进（不受 len(grid_lines)>1 限制）
            in_paragraph = False
            for i, it in enumerate(items, 1):
                if content == "单词":
                    word = it.get("word", "")
                    phonetic = it.get("phonetic", "")
                    meaning = it.get("meaning", "")
                    grid_lines = [word]
                    n = 1
                    caption = f"{phonetic}   {meaning}".strip()
                else:
                    en = it.get("en", "").strip()
                    zh = it.get("zh", "").strip()
                    # 板块标题（Part A/B 或 Let's talk 等）：作为标题行，不入四线格
                    if _is_section_header(en):
                        title = f"{unit_name} {en}" if (_is_part_header(en) and unit_name.startswith("Unit ")) else en
                        if slot + 1 > ROWS_PER_PAGE:
                            fill_remaining()
                            new_page()
                        top = start_y - slot * (GRID_H + ROW_GAP)
                        draw_sixian(top)
                        c.setFillColor(colors.black)
                        c.setFont(en_font, SENT_SIZE)
                        # 板块标题居中显示
                        c.drawCentredString(content_left + content_width / 2, top - GRID_H / 3 - 2.5 * mm, title)
                        # 短文段落标志：进入 Read and write 板块或短文小标题
                        in_paragraph = en.startswith("Read and ") or en in _PARAGRAPH_TITLES
                        slot += 1
                        continue
                    # 单元分段标题（Part A/Part B）：单单元视图下前缀单元名
                    if _PART_RE.match(en) and unit_name.startswith("Unit "):
                        en_show = f"{unit_name} {en}"
                    else:
                        en_show = en
                    grid_lines = wrap_text(en_show, SENT_SIZE)
                    n = max(1, len(grid_lines))
                    caption = f"{zh}".strip()
                if slot >= ROWS_PER_PAGE:
                    fill_remaining()
                    new_page()
                c.setFillColor(text_color)   # 默认黑色；勾选「灰字」时为灰色
                # 首行缩进：短文段落（Read and xxx 板块）第一行缩进 5 字符（国际惯例），单词/单行不受影响
                first_indent = stringWidth("     ", en_font, SENT_SIZE) if (content != "单词" and in_paragraph) else 0
                # 书信落款/签名（Love, / Dad）：单行右对齐到横线最右端
                right_align = (content != "单词" and len(grid_lines) == 1 and en.strip() in ("Love,", "Dad", "Mum", "Yours, Jim", "Li Xia", "Eric"))
                # 多行条目跨页自动分割：当前页能装几行装几行，剩余行移到下一页（不整条跳页造成空行）
                last_top = None
                for li, gtxt in enumerate(grid_lines):
                    if slot >= ROWS_PER_PAGE:
                        fill_remaining()
                        new_page()
                    top = start_y - slot * (GRID_H + ROW_GAP)
                    draw_sixian(top)
                    baseline = top - 2 * GRID_H / 3 + 0.6 * mm - 0.5 * mm   # 单词基线（舒窈衡水体/意大利斜体通用）
                    c.setFont(en_font, WORD_SIZE if content == "单词" else SENT_SIZE)
                    if right_align:
                        c.drawRightString(content_left + content_width - 21 * mm, baseline, gtxt)
                    else:
                        c.drawString(content_left + PAD - 1 * mm + (first_indent if li == 0 else 0), baseline, gtxt)   # 单词整体左移 1mm
                    slot += 1
                    last_top = top
                n = len(grid_lines)
                # 音标用 Times New Roman（含完整 IPA 字形，修复缺字）；意思用宋体
                y_cap = last_top - GRID_H - CAP_GAP - 1.45 * mm  # 音标+释义较原版下移 0.95mm（净上移 0.05mm）
                c.setFillColor(colors.black)
                if content == "单词":
                    if phonetic:
                        c.setFont(ipa_font, 9)
                        c.drawString(content_left, y_cap, phonetic)
                    if meaning:
                        w = stringWidth((phonetic or "") + "   ", ipa_font, 9) if phonetic else 0
                        c.setFont(simsun_font, 10)
                        c.drawString(content_left + w, y_cap, meaning)
                else:
                    c.setFont(simsun_font, 10)
                    c.drawString(content_left, y_cap, caption)
        elif style == "出题（默写）":
            # 出题（默写）：版式与字帖完全一致——英语在四线三格、汉语在 caption 区域（不画线）
            # 按方向隐藏答案：汉译英时四线三格留白、caption 写汉语题干；英译汉时四线三格写英语题干、caption 留空
            in_paragraph = False
            for it in items:
                # 每题方向
                if direction == "汉译英":
                    d = "汉译英"
                elif direction == "英译汉":
                    d = "英译汉"
                else:
                    d = it.get('_dir') or random.choice(("汉译英", "英译汉"))
                if content == "单词":
                    word = it.get("word", "")
                    meaning = it.get("meaning", "")
                    grid_lines = [word]
                    n = 1
                else:
                    en = it.get("en", "").strip()
                    zh = it.get("zh", "").strip()
                    # 板块标题（Part A/B 或 Let's talk 等）：作为标题行
                    if _is_section_header(en):
                        title = f"{unit_name} {en}" if (_is_part_header(en) and unit_name.startswith("Unit ")) else en
                        if slot + 1 > ROWS_PER_PAGE:
                            fill_remaining()
                            new_page()
                        top = start_y - slot * (GRID_H + ROW_GAP)
                        draw_sixian(top)
                        c.setFillColor(colors.black)   # 标题恒黑（防止继承灰字填色）
                        c.setFont(cn_font, 11)
                        # 板块标题居中显示
                        c.drawCentredString(content_left + content_width / 2, top - GRID_H / 3 - 2.5 * mm, title)
                        in_paragraph = en.startswith("Read and ") or en in _PARAGRAPH_TITLES
                        slot += 1
                        continue
                    grid_lines = wrap_text(en, SENT_SIZE)
                    n = max(1, len(grid_lines))
                if slot >= ROWS_PER_PAGE:
                    fill_remaining()
                    new_page()
                # 画四线三格（与字帖模式完全一致）；多行条目跨页自动分割
                if d == "英译汉":
                    # 英语题干写在四线三格中
                    c.setFillColor(text_color)
                    first_indent = stringWidth("     ", en_font, SENT_SIZE) if (content != "单词" and in_paragraph) else 0
                    right_align = (content != "单词" and len(grid_lines) == 1 and en.strip() in ("Love,", "Dad", "Mum", "Yours, Jim", "Li Xia", "Eric"))
                    last_top = None
                    for li, gtxt in enumerate(grid_lines):
                        if slot >= ROWS_PER_PAGE:
                            fill_remaining()
                            new_page()
                        top = start_y - slot * (GRID_H + ROW_GAP)
                        draw_sixian(top)
                        baseline = top - 2 * GRID_H / 3 + 0.6 * mm - 0.5 * mm
                        c.setFont(en_font, WORD_SIZE if content == "单词" else SENT_SIZE)
                        if right_align:
                            c.drawRightString(content_left + content_width - 21 * mm, baseline, gtxt)
                        else:
                            c.drawString(content_left + PAD - 1 * mm + (first_indent if li == 0 else 0), baseline, gtxt)
                        slot += 1
                        last_top = top
                    n = len(grid_lines)
                else:
                    # 汉译英：四线三格留白（学生写英语），只画线不写字
                    last_top = None
                    for _ in range(n):
                        if slot >= ROWS_PER_PAGE:
                            fill_remaining()
                            new_page()
                        top = start_y - slot * (GRID_H + ROW_GAP)
                        draw_sixian(top)
                        slot += 1
                        last_top = top
                # caption 区域（与字帖模式位置一致，不画线）
                y_cap = last_top - GRID_H - CAP_GAP - 1.45 * mm
                if d == "汉译英":
                    caption_text = meaning if content == "单词" else zh
                    if caption_text:
                        c.setFillColor(colors.black)
                        c.setFont(simsun_font, 10)
                        c.drawString(content_left, y_cap, caption_text)
                # 英译汉：caption 留空（学生写汉语）
        else:
            return False, "不支持的方式"

        # 最后一页补满空白四线三格
        fill_remaining()
        page_footer(page_no)
        c.showPage()
        c.save()
        return True, path
    def _export_phonetic(self, path, items, cn_font, simsun_font, ipa_font):
        # 音标表导出：教案格类型。先精确预算总行数，再遍历块绘制：
        # 每页满纸 + 横线等高（9mm）+ 在配对标题行画竖线 + 清浊对调（浊在左、清在右）。
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import mm
            from reportlab.pdfgen import canvas as _canvas
            from reportlab.lib import colors
        except Exception as e:
            return False, f"缺少 reportlab 库：{e}"
        hei_font = cn_font
        try:
            from reportlab.pdfbase import pdfmetrics as _pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont as _TTFont
            import os.path as _osp
            from constants import FONTS_DIR
            for _fp in (_osp.join(FONTS_DIR, "simhei.ttf"), _osp.join(FONTS_DIR, "simhei.ttc"), r"C:/Windows/Fonts//simhei.ttf"):
                if _osp.exists(_fp):
                    _pdfmetrics.registerFont(_TTFont("HEI", _fp))
                    hei_font = "HEI"
                    break
        except Exception:
            pass
        page_w, page_h = A4
        cell_width = 140 * mm
        cell_height = 9 * mm
        row_spacing = 0 * mm
        header_h = 12 * mm
        margin_x = (page_w - cell_width) / 2              # 35mm
        margin_y = 20 * mm
        start_y = page_h - margin_y + 5 * mm             # 整体上移 5mm
        rows_per_page = max(1, int((start_y - margin_y) // cell_height))  # 总可用 284-20=262 / 9 = 29
        start_x = margin_x
        vline_x = start_x + cell_width / 2               # 105mm
        left_x = start_x - 15 * mm
        right_x = vline_x + 1 * mm

        # 按 (group, sub) 分块
        blocks = []
        for it in items:
            key = (it.get("group", ""), it.get("sub", ""))
            if not blocks or blocks[-1]["key"] != key:
                blocks.append({"key": key, "items": [it]})
            else:
                blocks[-1]["items"].append(it)

        # 精确预算总行数（按实际循环邀ྈ：调、清浊对调、鼻音+半元音/舌侧音合并）
        def _calc_actual_rows():
            rows = 0
            i = 0
            has_vowel = any(k == ("元音", "长元音") for k, _ in blocks)
            has_consonant = any(k[0] == "辅音" for k, _ in blocks)
            if has_vowel: rows += 1
            if has_consonant: rows += 1
            while i < len(blocks):
                key, blk = blocks[i]["key"], blocks[i]["items"]
                if key == ("元音", "长元音") and i + 1 < len(blocks) and blocks[i + 1]["key"] == ("元音", "短元音"):
                    rows += 1 + max(len(blk), len(blocks[i + 1]["items"]))
                    i += 2
                    if i < len(blocks) and blocks[i]["key"] == ("元音", "双元音"):
                        rows += 1 + (len(blocks[i]["items"]) + 1) // 2        # 双元音：half 行音标 + 1 标题
                        i += 1
                elif key[0] == "辅音":
                    if key[1].endswith("·清") and i + 1 < len(blocks) and blocks[i + 1]["key"] == (key[0], key[1].replace("·清", "·浊")):
                        rows += 1 + max(len(blk), len(blocks[i + 1]["items"]))
                        i += 2
                    elif key[1] == "鼻音" and i + 2 < len(blocks) and blocks[i + 1]["key"] == ("辅音", "半元音") and blocks[i + 2]["key"] == ("辅音", "舌侧音"):
                        rows += 1 + max(len(blk), len(blocks[i + 1]["items"]) + len(blocks[i + 2]["items"]))
                        i += 3
                    else:
                        rows += 1 + len(blk)
                        i += 1
                else:
                    rows += 1 + len(blk)
                    i += 1
            return rows
            return rows

        total_rows = _calc_actual_rows()
        total_pages = max(1, (total_rows + rows_per_page - 1) // rows_per_page)

        c = _canvas.Canvas(path, pagesize=A4)

        def header(pno):
            # 音标表：不显示日期，仅保留右下页码
            c.setFillColor(colors.black)
            c.setFont(cn_font, 9)
            c.drawRightString(page_w - 20 * mm, margin_y - 6 * mm, f"{pno}/{total_pages}")

        header(1)
        page_no = 1
        row_in_page = 0

        def fill_remaining():
            # 当前页剩余行全部画刷空白横线（0.3 细线）
            nonlocal row_in_page
            while row_in_page < rows_per_page:
                y = start_y - row_in_page * (cell_height + row_spacing)
                draw_hline(y - cell_height, 0.3)
                row_in_page += 1

        def new_page():
            nonlocal page_no, row_in_page
            fill_remaining()                                  # 补满当前页
            draw_hline(start_y - row_in_page * (cell_height + row_spacing), 1.0)  # 底部粗线
            page_no += 1
            c.showPage()
            header(page_no)
            row_in_page = 0

        def draw_hline(y_top, width):
            c.setLineWidth(width)
            c.setStrokeColor(colors.black)
            c.line(start_x - 15 * mm, y_top, start_x + cell_width + 15 * mm, y_top)
            c.setStrokeColor(colors.black)

        def draw_row_hline(y_top):
            draw_hline(y_top - cell_height, 0.3)

        def draw_cell_text(y, x, text, font_name, size, bold=False):
            c.setFillColor(colors.black)
            c.setFont(hei_font if bold else font_name, size)
            c.drawCentredString(x, y - cell_height * 0.62 - 3 * mm, text)

        def ensure_line_row():
            nonlocal row_in_page
            if row_in_page + 1 > rows_per_page:
                new_page()
                draw_hline(start_y, 1.0)

        def draw_pair(title_left, title_right, left_items, right_items, draw_vline_pair=True):
            # 左右分区：标题行℉动竖线）+ 成对音标（左 left_x / 右 right_x）
            nonlocal row_in_page
            ensure_line_row()
            y = start_y - row_in_page * (cell_height + row_spacing)
            draw_row_hline(y)
            if draw_vline_pair:
                c.setLineWidth(0.3)
                c.setStrokeColor(colors.black)
                c.line(vline_x, y, vline_x, y - cell_height)
                c.setStrokeColor(colors.black)
            c.setFillColor(colors.black)
            c.setFont(simsun_font, 12)
            c.drawString(left_x, y - cell_height * 0.62 - 3 * mm, title_left)
            c.drawString(right_x, y - cell_height * 0.62 - 3 * mm, title_right)
            row_in_page += 1
            n = max(len(left_items), len(right_items))
            for r in range(n):
                ensure_line_row()
                y = start_y - row_in_page * (cell_height + row_spacing)
                draw_row_hline(y)
                if draw_vline_pair:
                    # 音标行也画竖线（与标题行一致）
                    c.setLineWidth(0.3)
                    c.setStrokeColor(colors.black)
                    c.line(vline_x, y, vline_x, y - cell_height)
                    c.setStrokeColor(colors.black)
                c.setFillColor(colors.black)
                if r < len(left_items):
                    _it = left_items[r]
                    c.setFont(ipa_font, 18)
                    c.drawString(left_x, y - cell_height * 0.62 - 2 * mm, _it["symbol"])
                    _w = c.stringWidth(_it["symbol"], ipa_font, 18)
                    _draw_info_line(c, left_x + _w + 2 * mm, y - cell_height * 0.62 - 3 * mm, _it, simsun_font, ipa_font, 11, 1)
                if r < len(right_items):
                    _it = right_items[r]
                    c.setFont(ipa_font, 18)
                    c.drawString(right_x, y - cell_height * 0.62 - 2 * mm, _it["symbol"])
                    _w = c.stringWidth(_it["symbol"], ipa_font, 18)
                    _draw_info_line(c, right_x + _w + 2 * mm, y - cell_height * 0.62 - 3 * mm, _it, simsun_font, ipa_font, 11, 1)
                row_in_page += 1
                if row_in_page >= rows_per_page:
                    draw_hline(y - cell_height, 1.0)

        def draw_single(title, items):
            nonlocal row_in_page
            ensure_line_row()
            y = start_y - row_in_page * (cell_height + row_spacing)
            draw_row_hline(y)
            c.setFillColor(colors.black)
            c.setFont(simsun_font, 12)
            c.drawString(left_x, y - cell_height * 0.62 - 3 * mm, title)
            row_in_page += 1
            for it in items:
                ensure_line_row()
                y = start_y - row_in_page * (cell_height + row_spacing)
                draw_row_hline(y)
                c.setFillColor(colors.black)
                c.setFont(ipa_font, 18)
                c.drawString(left_x, y - cell_height * 0.62 - 2 * mm, it["symbol"])
                _w = c.stringWidth(it["symbol"], ipa_font, 18)
                _draw_info_line(c, left_x + _w + 2 * mm, y - cell_height * 0.62 - 3 * mm, it, simsun_font, ipa_font, 11, 1)
                row_in_page += 1
                if row_in_page >= rows_per_page:
                    draw_hline(y - cell_height, 1.0)

        draw_hline(start_y, 1.0)
        drawn_consonant_title = False
        bi = 0
        while bi < len(blocks):
            key, blk = blocks[bi]["key"], blocks[bi]["items"]
            # ── 元音区 ──
            if key == ("元音", "长元音") and bi + 1 < len(blocks) and blocks[bi + 1]["key"] == ("元音", "短元音"):
                short_items = blocks[bi + 1]["items"]
                # 一级标题「元音」（黑体，居中）
                ensure_line_row()
                y = start_y - row_in_page * (cell_height + row_spacing)
                draw_row_hline(y)
                draw_cell_text(y, start_x + cell_width / 2, "元音", simsun_font, 13, bold=True)
                row_in_page += 1
                # 长元音 | 短元音 左右分区（画竖线）
                draw_pair("长元音", "短元音", blk, short_items, draw_vline_pair=True)
                bi += 2
                # 双元音：标题左对齐，音标左4右4（画竖线）
                if bi < len(blocks) and blocks[bi]["key"] == ("元音", "双元音"):
                    diph = blocks[bi]["items"]
                    half = (len(diph) + 1) // 2
                    ensure_line_row()
                    y = start_y - row_in_page * (cell_height + row_spacing)
                    draw_row_hline(y)
                    # 双元音标题行画竖线
                    c.setLineWidth(0.3)
                    c.setStrokeColor(colors.black)
                    c.line(vline_x, y, vline_x, y - cell_height)
                    c.setStrokeColor(colors.black)
                    c.setFillColor(colors.black)
                    c.setFont(simsun_font, 12)
                    c.drawString(left_x, y - cell_height * 0.62 - 3 * mm, "双元音")
                    row_in_page += 1
                    n2 = max(half, len(diph) - half)
                    for r in range(n2):
                        ensure_line_row()
                        y = start_y - row_in_page * (cell_height + row_spacing)
                        draw_row_hline(y)
                        # 双元音音标行画竖线
                        c.setLineWidth(0.3)
                        c.setStrokeColor(colors.black)
                        c.line(vline_x, y, vline_x, y - cell_height)
                        c.setStrokeColor(colors.black)
                        c.setFillColor(colors.black)
                        if r < half:
                            _it = diph[r]
                            c.setFont(ipa_font, 18)
                            c.drawString(left_x, y - cell_height * 0.62 - 2 * mm, _it["symbol"])
                            _w = c.stringWidth(_it["symbol"], ipa_font, 18)
                            _draw_info_line(c, left_x + _w + 2 * mm, y - cell_height * 0.62 - 3 * mm, _it, simsun_font, ipa_font, 11, 1)
                        if r < len(diph) - half:
                            _it = diph[half + r]
                            c.setFont(ipa_font, 18)
                            c.drawString(right_x, y - cell_height * 0.62 - 2 * mm, _it["symbol"])
                            _w = c.stringWidth(_it["symbol"], ipa_font, 18)
                            _draw_info_line(c, right_x + _w + 2 * mm, y - cell_height * 0.62 - 3 * mm, _it, simsun_font, ipa_font, 11, 1)
                        row_in_page += 1
                        if row_in_page >= rows_per_page:
                            draw_hline(y - cell_height, 1.0)
                    bi += 1
                continue
            # ── 辅音区 ──
            if key[0] == "辅音":
                if not drawn_consonant_title:
                    ensure_line_row()
                    y = start_y - row_in_page * (cell_height + row_spacing)
                    draw_row_hline(y)
                    draw_cell_text(y, start_x + cell_width / 2, "辅音", simsun_font, 13, bold=True)
                    row_in_page += 1
                    drawn_consonant_title = True
                # 清/浊成对：浊在左、清在右（对调后）
                if (key[1].endswith("·清")
                        and bi + 1 < len(blocks)
                        and blocks[bi + 1]["key"] == (key[0], key[1].replace("·清", "·浊"))):
                    draw_pair(key[1].replace("·清", "·浊"), key[1], blocks[bi + 1]["items"], blk, draw_vline_pair=True)
                    bi += 2
                    continue
                # 鼻音 + 半元音 + 舌侧音 合并
                if key[1] == "鼻音" and bi + 2 < len(blocks) \
                        and blocks[bi + 1]["key"] == ("辅音", "半元音") \
                        and blocks[bi + 2]["key"] == ("辅音", "舌侧音"):
                    draw_pair("鼻音", "半元/舌侧音", blk, blocks[bi + 1]["items"] + blocks[bi + 2]["items"], draw_vline_pair=True)
                    bi += 3
                    continue
                if key[1] == "半元音" and bi + 1 < len(blocks) and blocks[bi + 1]["key"] == ("辅音", "舌侧音"):
                    draw_pair("半元音/舌侧音", "", blk + blocks[bi + 1]["items"], [], draw_vline_pair=False)
                    bi += 2
                    continue
                draw_single(key[1], blk)
                bi += 1
                continue
            draw_single(key[1] if key[1] else key[0], blk)
            bi += 1

        # 循环结束：补满最后一页空白 + 底部粗线 + 页码 + 保存
        fill_remaining()
        draw_hline(start_y - row_in_page * (cell_height + row_spacing), 1.0)
        c.setFont(cn_font, 9)
        c.drawRightString(page_w - 20 * mm, margin_y - 6 * mm, f"{page_no}/{total_pages}")
        c.showPage()
        c.save()
        return True, path
