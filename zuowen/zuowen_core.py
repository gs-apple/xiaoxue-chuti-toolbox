# zuowen_core.py — 作文核心逻辑引擎
import os
import re
import webbrowser
import subprocess
import platform
from datetime import datetime
from constants import BASE_DIR
from zuowen.zuowen_data import (
    TEXTBOOK_COMPS, EXAMPLE_ESSAYS, XIAOSHENGCHU, ZHONGKAO, GAOKAO, MANFEN)


class ZuowenEngine:
    """作文核心引擎：管理课本作文、中高考作文、例文"""

    def __init__(self):
        pass

    # ========== 课本作文 ==========

    def get_grades(self):
        """返回所有年级列表"""
        return list(TEXTBOOK_COMPS.keys())

    def get_units(self, grade, semester=None):
        """返回指定年级(可选学期)的单元列表 [{title, type, requires, keywords}]"""
        grade_data = TEXTBOOK_COMPS.get(grade, {})
        if semester and semester in grade_data:
            return grade_data[semester]
        # 无学期参数时返回全部
        all_units = []
        for sem_units in grade_data.values():
            all_units.extend(sem_units)
        return all_units

    # ========== 中考/高考作文 ==========

    def get_exam_topics(self, exam_type, year):
        """获取小升初/中考/高考/满分原文的作文题目列表"""
        if exam_type == "小升初":
            data = XIAOSHENGCHU
        elif exam_type == "中考作文":
            data = ZHONGKAO
        elif exam_type == "满分原文":
            data = MANFEN
        else:
            data = GAOKAO
        return data.get(str(year), [])

    # ========== 例文 ==========

    def get_example_essay(self, title, grade="", semester=""):
        """根据标题获取例文

        部分题目在不同年级/学期重名（如二年级上下册都有「看图写故事」），
        因此优先用「年级/学期/标题」精确匹配，找不到再退回按标题匹配。
        """
        if grade and semester:
            hit = EXAMPLE_ESSAYS.get("%s/%s/%s" % (grade, semester, title))
            if hit:
                return hit
        return EXAMPLE_ESSAYS.get(title)


# ============================================================
# AI写作工具
# ============================================================

# AI网页版地址
AI_WEB_URLS = {
    "豆包": "https://www.doubao.com/chat/",
    "DeepSeek": "https://chat.deepseek.com/",
    "通义千问": "https://tongyi.aliyun.com/qianwen/",
    "智谱清言": "https://chatglm.cn/",
    "Kimi": "https://kimi.moonshot.cn/",
    "文心一言": "https://yiyan.baidu.com/",
}


def _copy_to_clipboard(text):
    """复制文本到剪贴板"""
    system = platform.system()
    if system == "Windows":
        subprocess.run(["clip"], input=text.encode("utf-16le"), check=True, capture_output=True)
    elif system == "Darwin":
        subprocess.run(["pbcopy"], input=text.encode(), check=True, capture_output=True)
    else:
        subprocess.run(["xclip", "-selection", "clipboard"], input=text.encode(), check=True, capture_output=True)


def get_ai_web_urls():
    """返回所有AI网页版地址"""
    return dict(AI_WEB_URLS)


def open_ai_web(topic, service="豆包", tip=None, grade=""):
    """
    打开AI网页版并复制提示词到剪贴板
    返回 (success, message)
    """
    url = AI_WEB_URLS.get(service)
    if not url:
        return False, f"未知的AI服务: {service}"

    # 根据年级调整字数要求
    grade_word_count = {
        "一年级": 60, "二年级": 100, "三年级": 200,
        "四年级": 250, "五年级": 350, "六年级": 400,
    }
    word_count = grade_word_count.get(grade, 300)
    prompt = f'请以"{topic}"为题，写一篇适合小学生的优秀作文范文。'
    if tip:
        prompt += f'\n\n写作思路：\n{tip}'
    prompt += f'\n\n要求：语言通顺，用词恰当，内容真实感人，有具体事例，结构清晰，字数{word_count}字左右。直接输出作文内容，第一行为标题，不要加额外说明。'

    try:
        _copy_to_clipboard(prompt)
    except Exception:
        pass

    try:
        webbrowser.open(url)
        return True, f"已打开{service}，提示词已复制到剪贴板，粘贴即可"
    except Exception as e:
        return False, f"打开浏览器失败: {e}"


# ============================================================
# PDF导出
# ============================================================

_export_font_cache = None


def _register_fonts():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    for fp in ['simsun.ttc', r'C:\Windows\Fonts\simsun.ttc']:
        try:
            pdfmetrics.registerFont(TTFont('SimSun', fp))
            return
        except Exception:
            pass
    for fp in ['msyh.ttf', r'C:\Windows\Fonts\msyh.ttf']:
        try:
            pdfmetrics.registerFont(TTFont('SimSun', fp))
            return
        except Exception:
            pass


def _get_export_font():
    global _export_font_cache
    if _export_font_cache:
        return _export_font_cache
    try:
        from reportlab.pdfbase import pdfmetrics
        pdfmetrics.getFont('SimSun')
        _export_font_cache = 'SimSun'
    except Exception:
        _export_font_cache = 'Helvetica'
    return _export_font_cache


def _calc_pages(char_queue, write_cols, writing_rows):
    """计算内容需要多少页"""
    if not char_queue:
        return 1
    pages = 1
    current_row = 1
    current_col = 0
    for item in char_queue:
        if current_row >= writing_rows:
            pages += 1
            current_row = 0
            current_col = 0
        if item == '__INDENT__':
            if current_col > 0:
                current_row += 1
                current_col = 0
                if current_row >= writing_rows:
                    pages += 1
                    current_row = 0
            current_col += 2
            continue
        current_col += 1
        if current_col >= write_cols:
            current_row += 1
            current_col = 0
    return pages


def _draw_page(c, fn, start_x, top_start_y, cell_size, cell_width,
               cols, write_cols, row_gap, page_num, total_pages=1,
               draw_date=False, title=None, title_chars=None,
               char_queue=None, char_idx=0):
    """绘制一整页作文本（正误行 + 写作格），返回 char_idx"""
    from reportlab.lib.units import mm
    from reportlab.lib.colors import black

    total_width = cols * cell_width

    # 日期行（仅第一页）
    if draw_date:
        c.setFont(fn, 10)
        c.drawString(start_x + 5 * mm, top_start_y + 5 * mm,
                     "日期:_____年_____月____日")

    # 正误区域（2行）
    total_height_2 = 2 * cell_size
    c.setLineWidth(1.0)
    c.rect(start_x, top_start_y - total_height_2, total_width, total_height_2)
    c.setLineWidth(0.3)
    for col in range(1, cols):
        x = start_x + col * cell_width
        c.line(x, top_start_y, x, top_start_y - total_height_2)
    c.line(start_x, top_start_y - cell_size,
           start_x + total_width, top_start_y - cell_size)
    c.setFont(fn, 12)
    c.setFillColor(black)
    c.drawCentredString(start_x + cell_width / 2,
                        top_start_y - cell_size / 2 - 4, "正")
    c.drawCentredString(start_x + cell_width / 2,
                        top_start_y - cell_size - cell_size / 2 - 4, "误")
    c.setLineWidth(0.3)
    for col in range(cols):
        x = start_x + col * cell_width
        c.rect(x, top_start_y - cell_size, cell_width, cell_size)
        c.rect(x, top_start_y - 2 * cell_size, cell_width, cell_size)

    # 写作区域（18行）
    writing_rows = 18
    writing_start_y = top_start_y - 2 * cell_size - 5 * mm
    writing_height = writing_rows * (cell_size + row_gap)

    c.setLineWidth(1.0)
    c.rect(start_x, writing_start_y - writing_height, total_width, writing_height)
    c.setLineWidth(0.3)
    for row in range(writing_rows):
        current_y = writing_start_y - row * (cell_size + row_gap)
        for col in range(write_cols):
            x = start_x + col * cell_width
            c.rect(x, current_y - cell_size, cell_width, cell_size)
        if row == 0:
            c.setLineWidth(0.5)
            c.line(start_x, current_y - cell_size,
                   start_x + total_width, current_y - cell_size)
            c.setLineWidth(0.3)

    # 批语区域
    pici_x = start_x + write_cols * cell_width
    c.setLineWidth(0.3)
    c.line(pici_x, writing_start_y, pici_x, writing_start_y - writing_height)
    c.setFont(fn, 12)
    c.setFillColor(black)
    c.drawCentredString(pici_x + cell_width / 2 + cell_width * 0.5,
                        writing_start_y - cell_size / 2 - 4, "批")
    c.drawCentredString(pici_x + cell_width / 2 + cell_width * 1.5,
                        writing_start_y - cell_size / 2 - 4, "语")

    # 填入题目和内容
    if title_chars:
        title_start_col = (write_cols - len(title_chars)) // 2
        for i, ch in enumerate(title_chars):
            col = title_start_col + i
            if 0 <= col < write_cols:
                x = start_x + col * cell_width + cell_width / 2
                c.drawCentredString(x, writing_start_y - cell_size * 0.7, ch)

    content_start_row = 1 if title_chars else 0
    current_row = content_start_row
    current_col = 0

    if char_queue:
        for item in char_queue[char_idx:]:
            if current_row >= writing_rows:
                break
            if item == '__INDENT__':
                if current_col > 0:
                    current_row += 1
                    current_col = 0
                current_col += 2
                char_idx += 1
                continue
            y = writing_start_y - current_row * (cell_size + row_gap)
            x = start_x + current_col * cell_width + cell_width / 2
            c.setFont(fn, 12)
            c.setFillColor(black)
            c.drawCentredString(x, y - cell_size * 0.7, item)
            current_col += 1
            if current_col >= write_cols:
                current_row += 1
                current_col = 0
            char_idx += 1

    # 页码
    c.setFont(fn, 9)
    c.drawRightString(start_x + total_width + 3 * cell_width - 32 * mm,
                      writing_start_y - writing_height - 6 * mm,
                      f"{page_num}/{total_pages}")

    return char_idx


def export_worksheet(title, content="", grade="", comp_type="", filepath=None):
    """导出作文练习卷 — 字帖作文本模板，题目从内容第一行取，内容从第二行开始"""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    _register_fonts()
    fn = _get_export_font()

    # 从内容第一行提取标题
    lines = content.split('\n') if content else []
    actual_title = title
    actual_content = content

    if lines and lines[0].strip():
        first_line = lines[0].strip()
        # 如果第一行不是以标点结尾，且长度适中，认为是标题
        if len(first_line) <= 30 and not first_line[-1] in '，。！？、；：':
            actual_title = first_line
            actual_content = '\n'.join(lines[1:]).strip()

    if filepath is None:
        date_str = datetime.now().strftime("%Y%m%d")
        # 清理文件名中的特殊字符
        safe_title = actual_title.replace('_', ' ').replace('\n', ' ')
        safe_title = re.sub(r'[\\/:*?"<>|]', '_', safe_title)[:30]
        filepath = os.path.join(BASE_DIR, f"作文_{safe_title}_{date_str}.pdf")

    pw, ph = A4
    cell_size = 8 * mm
    cell_width = 8 * mm
    cols = 21
    row_gap = 5 * mm
    margin_x = (pw - cols * cell_width) / 2
    top_margin_2cm = 20 * mm
    start_x = margin_x
    write_cols = cols - 3

    c = canvas.Canvas(filepath, pagesize=A4)
    c.setTitle(f"作文 - {actual_title}")

    # 准备内容字符队列
    paragraphs = actual_content.split('\n') if actual_content else []
    char_queue = []
    for para in paragraphs:
        para = para.strip()
        if para:
            char_queue.append('__INDENT__')
            for ch in para:
                char_queue.append(ch)

    title_chars = list(actual_title.replace('_', ' '))
    char_idx = 0
    page_num = 1
    has_title = True
    writing_rows = 18
    total_pages = _calc_pages(char_queue, write_cols, writing_rows)

    while True:
        top_start_y = ph - top_margin_2cm
        draw_date = (page_num == 1)
        t_chars = title_chars if has_title else None

        char_idx = _draw_page(c, fn, start_x, top_start_y,
                              cell_size, cell_width, cols, write_cols,
                              row_gap, page_num, total_pages=total_pages,
                              draw_date=draw_date, title=actual_title,
                              title_chars=t_chars, char_queue=char_queue,
                              char_idx=char_idx)

        c.showPage()
        page_num += 1
        has_title = False

        if char_idx >= len(char_queue):
            break
        if page_num > 10:
            break

    c.save()
    return filepath
