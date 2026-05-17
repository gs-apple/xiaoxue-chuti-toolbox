# shuxue_export.py — 数学题目PDF导出（排版优化版）
import os
import re
from datetime import datetime
from fractions import Fraction
from shuxue_drawings import GEOMETRY_QUESTION_TYPES, extract_drawing_spec, draw_figure

def _get_export_dir():
    return os.path.dirname(os.path.abspath(__file__))

def _build_filename(questions_data):
    from shuxue_core import CATEGORY_NAMES
    cat_names = []
    seen = set()
    for item in questions_data.get("basic", []):
        if len(item) >= 1:
            cat = item[0]
            name = CATEGORY_NAMES.get(cat, cat)
            if name not in seen:
                seen.add(name)
                cat_names.append(name)
    for item in questions_data.get("advance", []):
        if len(item) >= 1:
            cat = item[0]
            name = CATEGORY_NAMES.get(cat, cat)
            if name not in seen:
                seen.add(name)
                cat_names.append(name)
    date_str = datetime.now().strftime("%Y%m%d")
    # 清理文件名中的非法字符 (Windows: \ / : * ? " < > |)
    import re
    safe_names = []
    for name in cat_names[:3]:
        # 替换非法字符为下划线
        safe_name = re.sub(r'[\\/:*?"<>|]', '_', name)
        safe_names.append(safe_name)
    names_part = "_".join(safe_names)
    if not names_part:
        names_part = "练习"
    return f"数学_{names_part}_{date_str}.pdf"

FRAC_RE = re.compile(r'FRAC\[(\d+),(\d+)\]')

def _frac_to_text(s):
    return FRAC_RE.sub(lambda m: f"{m.group(1)}/{m.group(2)}", s)

def _split_frac_parts(s):
    parts = []
    last = 0
    for m in FRAC_RE.finditer(s):
        if m.start() > last:
            parts.append(('text', s[last:m.start()]))
        parts.append(('frac', m.group(1), m.group(2)))
        last = m.end()
    if last < len(s):
        parts.append(('text', s[last:]))
    return parts

def _draw_mixed(c, x, y, parts, font_name, font_size, frac_font_size=None):
    if frac_font_size is None:
        frac_font_size = font_size
    cur_x = x
    line_y_offset = frac_font_size * 0.28
    for p in parts:
        if p[0] == 'text':
            c.setFont(font_name, font_size)
            c.drawString(cur_x, y, p[1])
            cur_x += c.stringWidth(p[1], font_name, font_size)
        else:
            num_str, den_str = p[1], p[2]
            nw = c.stringWidth(num_str, font_name, frac_font_size)
            dw = c.stringWidth(den_str, font_name, frac_font_size)
            box_w = max(nw, dw) + 4
            c.setFont(font_name, frac_font_size)
            c.drawCentredString(cur_x + box_w / 2,
                                y + line_y_offset + frac_font_size * 0.15,
                                num_str)
            c.setLineWidth(0.6)
            c.line(cur_x, y + line_y_offset, cur_x + box_w, y + line_y_offset)
            c.drawCentredString(cur_x + box_w / 2,
                                y + line_y_offset - frac_font_size * 1.0,
                                den_str)
            cur_x += box_w + 2
    c.setFont(font_name, font_size)
    return cur_x

def _safe_fmt_answer(ans):
    if ans is None:
        return "略"
    if isinstance(ans, tuple):
        if len(ans) == 2:
            return f"{ans[0]}余{ans[1]}"
        else:
            return str(ans)
    elif isinstance(ans, Fraction):
        if ans.denominator == 1:
            return str(ans.numerator)
        return f"{ans.numerator}/{ans.denominator}"
    elif isinstance(ans, float):
        ans = round(ans, 4)
        if ans.is_integer():
            return str(int(ans))
        return f"{ans:g}"
    else:
        return str(ans)

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

_font_cache = None
def _get_font():
    global _font_cache
    if _font_cache:
        return _font_cache
    try:
        from reportlab.pdfbase import pdfmetrics
        pdfmetrics.getFont('SimSun')
        _font_cache = 'SimSun'
    except Exception:
        _font_cache = 'Helvetica'
    return _font_cache

def _draw_bold(c, x, y, text, font_name, font_size):
    """模拟加粗：偏移0.3pt重绘一次"""
    c.drawString(x, y, text)
    c.drawString(x + 0.3, y, text)

def export_pdf(questions_data, use_vertical=False, use_answer=False, show_titles=False):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors

    _register_fonts()
    fn_sun = _get_font()

    basic_qs = questions_data.get("basic", [])
    advance_qs = questions_data.get("advance", [])
    total_count = len(basic_qs) + len(advance_qs)

    basic_answers = []
    for item in basic_qs:
        if len(item) >= 3:
            basic_answers.append(item[2])
        else:
            basic_answers.append("略")
    advance_answers = []
    for item in advance_qs:
        if len(item) >= 3:
            advance_answers.append(item[2])
        else:
            advance_answers.append("略")
    all_answers = basic_answers + advance_answers

    export_dir = _get_export_dir()
    filename = _build_filename(questions_data)
    filepath = os.path.join(export_dir, filename)

    pw, ph = A4
    lm = 15 * mm
    rm = 15 * mm
    tm = 28 * mm
    bm = 18 * mm
    uw = pw - lm - rm

    reg_row_h = 8 * mm if not use_vertical else 32 * mm
    adv_row_h = 35 * mm

    MIXED_TYPES = {"cb_mix_addsub", "cb_mix_addmul", "cb_mix_addmulsub", "cb_mix_dec", "cb_mix_frac"}

    regular = []
    for i, item in enumerate(basic_qs):
        if len(item) >= 2:
            regular.append((i, item[0], item[1]))
    advanced = []
    for i, item in enumerate(advance_qs):
        if len(item) >= 2:
            advanced.append((i + len(basic_qs), item[1], item[0]))

    # 使用临时总页数（先设为1，最后会修正）
    total_pages = [1]  # 用列表实现nonlocal修改

    c = canvas.Canvas(filepath, pagesize=A4)
    c.setTitle("数学练习题")

    header_y = ph - tm + 12 * mm
    header_line_y = header_y - 2 * mm
    # 首页内容起始 Y
    first_page_start_y = header_line_y - 6 * mm
    # 后续页内容起始 Y（避免压线）
    other_page_start_y = header_line_y - 6 * mm

    current_page = [1]
    cur_y = first_page_start_y

    def draw_header():
        c.setFont(fn_sun, 10)
        c.drawString(lm, header_y, "日期:_____年_____月_____日")
        c.drawRightString(pw - rm, header_y, f"共{total_count}题")
        c.setLineWidth(0.3)
        c.line(lm, header_line_y, pw - rm, header_line_y)
        c.setFont(fn_sun, 9)
        c.drawRightString(pw - rm, bm * 0.5, f"{current_page[0]}/{total_pages[0]}")
        c.setFont(fn_sun, 10)

    def new_page():
        c.showPage()
        current_page[0] += 1
        draw_header()
        return other_page_start_y

    draw_header()
    page_started = True

    # 绘制基础题
    if regular:
        # 统一重新编号（1开始），避免 normal/mixed 分组后序号错乱
        renumbered = [(seq, q, t) for seq, (i, t, q) in enumerate(regular, 1)]
        regular_normal = [(seq, q, t) for seq, q, t in renumbered if t not in MIXED_TYPES]
        regular_mixed = [(seq, q, t) for seq, q, t in renumbered if t in MIXED_TYPES]

        # 基础题标题（仅一键出题显示）
        if show_titles:
            c.setFont(fn_sun, 12)
            _draw_bold(c, lm, cur_y, f"基础计算（{len(regular)}题）", fn_sun, 12)
            cur_y -= reg_row_h

        # 先绘制普通基础题（4列）
        col_w = uw / 4
        for idx, (seq, question, _qtype) in enumerate(regular_normal):
            col = idx % 4
            if col == 0 and idx > 0:
                cur_y -= reg_row_h
                if cur_y < bm + reg_row_h:
                    cur_y = new_page()
            x = lm + col * col_w
            label = f"{seq:>3}. "
            question = question.replace(" + ", "+").replace(" - ", "-").replace(" × ", "×").replace(" ÷ ", "÷")
            parts = _split_frac_parts(question)
            c.setFont(fn_sun, 11.5)
            lw = c.stringWidth(label, fn_sun, 11)
            c.drawString(x, cur_y, label)
            _draw_mixed(c, x + lw, cur_y, parts, fn_sun, 11)

        # 基础题结束后换行，避免与混合题重叠
        if regular_normal:
            last_col = len(regular_normal) % 4
            if last_col != 0:  # 不是整行结束
                cur_y -= reg_row_h

        # 再绘制四则混合（3列，保留空格）
        if regular_mixed:
            col_w_m = uw / 3
            for idx, (seq, question, _qtype) in enumerate(regular_mixed):
                col = idx % 3
                if col == 0 and idx > 0:
                    cur_y -= reg_row_h
                    if cur_y < bm + reg_row_h:
                        cur_y = new_page()
                x = lm + col * col_w_m
                label = f"{seq:>3}. "
                parts = _split_frac_parts(question)
                c.setFont(fn_sun, 11.5)
                lw = c.stringWidth(label, fn_sun, 11)
                c.drawString(x, cur_y, label)
                _draw_mixed(c, x + lw, cur_y, parts, fn_sun, 11)

    # 绘制提升题（一行两题，无竖线分隔，留做题空间）
    if advanced:
        adv_font_size = 10.5
        adv_line_gap = 5.5 * mm
        adv_work_gap = 20 * mm  # 做题空间（缩短）

        def wrap_text_adv(text, max_w, fn, fs):
            lines_out = []
            cur_line = ""
            plain = _frac_to_text(text)
            for ch in list(plain):
                test = cur_line + ch
                if c.stringWidth(test, fn, fs) <= max_w:
                    cur_line = test
                else:
                    if cur_line:
                        lines_out.append(cur_line)
                    cur_line = ch
            if cur_line:
                lines_out.append(cur_line)
            return lines_out if lines_out else [""]

        # 根据是否有基础题决定起始位置
        if regular:
            cur_y -= reg_row_h + 4 * mm  # 基础题与提升题间距
            if cur_y < bm + adv_line_gap + adv_work_gap:
                cur_y = new_page()
        else:
            cur_y = first_page_start_y

        # 提升题标题（仅一键出题显示）
        if show_titles:
            c.setFont(fn_sun, 12)
            _draw_bold(c, lm, cur_y, f"运用题（{len(advanced)}题）", fn_sun, 12)
            cur_y -= reg_row_h

        FIGURE_SIZE_MM = 30

        def is_geometry(item):
            if not item or len(item) < 3:
                return False
            return item[2] in GEOMETRY_QUESTION_TYPES

        def draw_fig_right(item, col_x, col_w, top_y):
            if not is_geometry(item):
                return 0
            spec = extract_drawing_spec(item[2], item[1])
            if not spec:
                return 0
            fig_size_pt = FIGURE_SIZE_MM * mm
            fig_x = col_x + col_w - fig_size_pt
            fig_y = top_y - fig_size_pt
            draw_figure(c, fig_x, fig_y, fig_size_pt, fig_size_pt, spec)
            return fig_size_pt

        # 两列布局参数
        col_gap = 6 * mm
        col_w_adv = (uw - col_gap) / 2
        left_x = lm
        right_x = lm + col_w_adv + col_gap
        text_w_adv = col_w_adv - FIGURE_SIZE_MM * mm - 2 * mm

        # 配对渲染（左右各一题）
        pairs = []
        for i in range(0, len(advanced), 2):
            left_item = advanced[i]
            right_item = advanced[i + 1] if i + 1 < len(advanced) else None
            pairs.append((left_item, right_item))

        for left_item, right_item in pairs:
            left_label = f"{left_item[0] + 1}. "
            left_qtext = _frac_to_text(left_item[1])
            left_geo = is_geometry(left_item)
            left_w = text_w_adv if left_geo else col_w_adv

            right_label = f"{right_item[0] + 1}. " if right_item else ""
            right_qtext = _frac_to_text(right_item[1]) if right_item else ""
            right_geo = is_geometry(right_item) if right_item else False
            right_w = text_w_adv if right_geo else col_w_adv

            c.setFont(fn_sun, adv_font_size)
            left_lines = wrap_text_adv(left_label + left_qtext, left_w, fn_sun, adv_font_size) if left_qtext else []
            right_lines = wrap_text_adv(right_label + right_qtext, right_w, fn_sun, adv_font_size) if right_qtext else []
            max_lines = max(len(left_lines), len(right_lines))
            pair_height = max_lines * adv_line_gap + adv_work_gap

            if cur_y - pair_height < bm:
                cur_y = new_page()

            # 左列文字
            c.setFont(fn_sun, adv_font_size)
            for li, line_txt in enumerate(left_lines):
                c.drawString(left_x, cur_y - li * adv_line_gap, line_txt)
            # 左列图形
            draw_fig_right(left_item, left_x, col_w_adv, cur_y)

            # 右列文字
            if right_item:
                c.setFont(fn_sun, adv_font_size)
                for li, line_txt in enumerate(right_lines):
                    c.drawString(right_x, cur_y - li * adv_line_gap, line_txt)
                draw_fig_right(right_item, right_x, col_w_adv, cur_y)

            cur_y -= pair_height

    # 答案页
    if use_answer and all_answers:
        c.showPage()
        current_page[0] += 1
        draw_header()
        cur_y = other_page_start_y

        c.setFont(fn_sun, 14)
        c.drawCentredString(pw / 2, cur_y - 3 * mm, "参 考 答 案")
        cur_y -= 10 * mm + 3 * mm

        c.setFont(fn_sun, 9)
        ans_line_h = 6 * mm
        ans_sep = "    "
        ans_texts = []
        for i, ans in enumerate(all_answers):
            ans_str = _safe_fmt_answer(ans)
            ans_texts.append(f"{i + 1}. {ans_str}")

        cur_line = ""
        for txt in ans_texts:
            test = cur_line + (ans_sep + txt if cur_line else txt)
            if c.stringWidth(test, fn_sun, 9) <= uw:
                cur_line = test
            else:
                if cur_line:
                    if cur_y < bm + ans_line_h:
                        cur_y = new_page()
                        c.setFont(fn_sun, 9)
                    c.drawString(lm, cur_y, cur_line)
                    cur_y -= ans_line_h
                cur_line = txt
        if cur_line:
            if cur_y < bm + ans_line_h:
                cur_y = new_page()
                c.setFont(fn_sun, 9)
            c.drawString(lm, cur_y, cur_line)
            cur_y -= ans_line_h

    c.save()
    
    # 第二遍：重新生成PDF，使用正确的总页数
    if current_page[0] != total_pages[0]:
        total_pages[0] = current_page[0]
        current_page[0] = 1
        
        # 重新创建canvas
        c = canvas.Canvas(filepath, pagesize=A4)
        c.setTitle("数学练习题")
        cur_y = first_page_start_y
        page_started = True
        
        draw_header()
        
        # 重新绘制基础题
        if regular:
            renumbered2 = [(seq, q, t) for seq, (i, t, q) in enumerate(regular, 1)]
            regular_normal = [(seq, q, t) for seq, q, t in renumbered2 if t not in MIXED_TYPES]
            regular_mixed = [(seq, q, t) for seq, q, t in renumbered2 if t in MIXED_TYPES]

            # 基础题标题（仅一键出题显示）
            if show_titles:
                c.setFont(fn_sun, 12)
                _draw_bold(c, lm, cur_y, f"基础计算（{len(regular)}题）", fn_sun, 12)
                cur_y -= reg_row_h

            col_w = uw / 4
            for idx, (seq, question, _qtype) in enumerate(regular_normal):
                col = idx % 4
                if col == 0 and idx > 0:
                    cur_y -= reg_row_h
                    if cur_y < bm + reg_row_h:
                        c.showPage()
                        current_page[0] += 1
                        draw_header()
                        cur_y = other_page_start_y
                x = lm + col * col_w
                label = f"{seq:>3}. "
                question = question.replace(" + ", "+").replace(" - ", "-").replace(" × ", "×").replace(" ÷ ", "÷")
                parts = _split_frac_parts(question)
                c.setFont(fn_sun, 11.5)
                lw = c.stringWidth(label, fn_sun, 11)
                c.drawString(x, cur_y, label)
                _draw_mixed(c, x + lw, cur_y, parts, fn_sun, 11)

            # 基础题结束后换行，避免与混合题重叠
            if regular_normal:
                last_col = len(regular_normal) % 4
                if last_col != 0:
                    cur_y -= reg_row_h

            if regular_mixed:
                col_w_m = uw / 3
                for idx, (seq, question, _qtype) in enumerate(regular_mixed):
                    col = idx % 3
                    if col == 0 and idx > 0:
                        cur_y -= reg_row_h
                        if cur_y < bm + reg_row_h:
                            c.showPage()
                            current_page[0] += 1
                            draw_header()
                            cur_y = other_page_start_y
                    x = lm + col * col_w_m
                    label = f"{seq:>3}. "
                    parts = _split_frac_parts(question)
                    c.setFont(fn_sun, 11.5)
                    lw = c.stringWidth(label, fn_sun, 11)
                    c.drawString(x, cur_y, label)
                    _draw_mixed(c, x + lw, cur_y, parts, fn_sun, 11)
        
        # 重新绘制提升题（一行两题，无竖线分隔，留做题空间）
        if advanced:
            adv_font_size = 10.5
            adv_line_gap = 5.5 * mm
            adv_work_gap = 20 * mm  # 做题空间（缩短）

            if regular:
                cur_y -= reg_row_h + 4 * mm  # 基础题与提升题间距
                if cur_y < bm + adv_line_gap + adv_work_gap:
                    c.showPage()
                    current_page[0] += 1
                    draw_header()
                    cur_y = other_page_start_y
            else:
                cur_y = first_page_start_y

            # 提升题标题（仅一键出题显示）
            if show_titles:
                c.setFont(fn_sun, 12)
                _draw_bold(c, lm, cur_y, f"运用题（{len(advanced)}题）", fn_sun, 12)
                cur_y -= reg_row_h

            # 两列布局参数
            col_gap = 6 * mm
            col_w_adv = (uw - col_gap) / 2
            left_x = lm
            right_x = lm + col_w_adv + col_gap
            text_w_adv = col_w_adv - FIGURE_SIZE_MM * mm - 2 * mm

            pairs = []
            for i in range(0, len(advanced), 2):
                left_item = advanced[i]
                right_item = advanced[i + 1] if i + 1 < len(advanced) else None
                pairs.append((left_item, right_item))

            for left_item, right_item in pairs:
                left_label = f"{left_item[0] + 1}. "
                left_qtext = _frac_to_text(left_item[1])
                left_geo = is_geometry(left_item)
                left_w = text_w_adv if left_geo else col_w_adv

                right_label = f"{right_item[0] + 1}. " if right_item else ""
                right_qtext = _frac_to_text(right_item[1]) if right_item else ""
                right_geo = is_geometry(right_item) if right_item else False
                right_w = text_w_adv if right_geo else col_w_adv

                c.setFont(fn_sun, adv_font_size)
                left_lines = wrap_text_adv(left_label + left_qtext, left_w, fn_sun, adv_font_size) if left_qtext else []
                right_lines = wrap_text_adv(right_label + right_qtext, right_w, fn_sun, adv_font_size) if right_qtext else []
                max_lines = max(len(left_lines), len(right_lines))
                pair_height = max_lines * adv_line_gap + adv_work_gap

                if cur_y - pair_height < bm:
                    c.showPage()
                    current_page[0] += 1
                    draw_header()
                    cur_y = other_page_start_y

                c.setFont(fn_sun, adv_font_size)
                for li, line_txt in enumerate(left_lines):
                    c.drawString(left_x, cur_y - li * adv_line_gap, line_txt)
                draw_fig_right(left_item, left_x, col_w_adv, cur_y)

                if right_item:
                    c.setFont(fn_sun, adv_font_size)
                    for li, line_txt in enumerate(right_lines):
                        c.drawString(right_x, cur_y - li * adv_line_gap, line_txt)
                    draw_fig_right(right_item, right_x, col_w_adv, cur_y)

                cur_y -= pair_height
        
        # 重新绘制答案页
        if use_answer and all_answers:
            c.showPage()
            current_page[0] += 1
            draw_header()
            cur_y = other_page_start_y
            
            c.setFont(fn_sun, 14)
            c.drawCentredString(pw / 2, cur_y - 3 * mm, "参 考 答 案")
            cur_y -= 10 * mm + 3 * mm
            
            c.setFont(fn_sun, 9)
            ans_line_h = 6 * mm
            ans_sep = "    "

            ans_texts = []
            for i, ans in enumerate(all_answers):
                ans_str = _safe_fmt_answer(ans)
                ans_texts.append(f"{i + 1}. {ans_str}")

            cur_line = ""
            for txt in ans_texts:
                test = cur_line + (ans_sep + txt if cur_line else txt)
                if c.stringWidth(test, fn_sun, 9) <= uw:
                    cur_line = test
                else:
                    if cur_line:
                        if cur_y < bm + ans_line_h:
                            c.showPage()
                            current_page[0] += 1
                            draw_header()
                            c.setFont(fn_sun, 9)
                        c.drawString(lm, cur_y, cur_line)
                        cur_y -= ans_line_h
                    cur_line = txt
            if cur_line:
                if cur_y < bm + ans_line_h:
                    c.showPage()
                    current_page[0] += 1
                    draw_header()
                    c.setFont(fn_sun, 9)
                c.drawString(lm, cur_y, cur_line)
                cur_y -= ans_line_h
        
        c.save()
    
    return filepath