# shuxue_export.py — 数学题目PDF导出（排版优化版）
import os
import re
from datetime import datetime
from fractions import Fraction

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

def export_pdf(questions_data, use_vertical=False, use_answer=False):
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

    regular = []
    for i, item in enumerate(basic_qs):
        if len(item) >= 2:
            regular.append((i, item[1]))
    advanced = []
    for i, item in enumerate(advance_qs):
        if len(item) >= 2:
            advanced.append((i + len(basic_qs), item[1]))

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
        col_w = uw / 4
        for idx, (orig_i, question) in enumerate(regular):
            col = idx % 4
            if col == 0 and idx > 0:
                cur_y -= reg_row_h
                if cur_y < bm + reg_row_h:
                    cur_y = new_page()
            x = lm + col * col_w
            label = f"{orig_i + 1:>3}. "
            # 紧凑运算符间距
            question = question.replace(" + ", "+").replace(" - ", "-").replace(" × ", "×").replace(" ÷ ", "÷")
            parts = _split_frac_parts(question)
            c.setFont(fn_sun, 11)
            lw = c.stringWidth(label, fn_sun, 11)
            c.drawString(x, cur_y, label)
            _draw_mixed(c, x + lw, cur_y, parts, fn_sun, 11)

    # 绘制提升题
    if advanced:
        adv_font_size = 10
        adv_line_gap = 5.5 * mm
        adv_item_gap = 8 * mm

        def wrap_text(text, max_w, fn, fs):
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
            # 有基础题时，从基础题下方开始
            cur_y -= reg_row_h + 4 * mm
            if cur_y < bm + adv_line_gap * 2 + adv_item_gap:
                cur_y = new_page()
        else:
            # 单独出提升题时，使用首页起始位置（避免距离横线太远）
            cur_y = first_page_start_y

        sep_gap = 0.5 * mm
        mid_x = pw / 2
        left_x = lm
        right_x = mid_x + sep_gap / 2 + 2 * mm
        col_w_l = mid_x - sep_gap / 2 - 2 * mm - left_x
        col_w_r = pw - rm - right_x

        pairs = []
        for i in range(0, len(advanced), 2):
            left_item = advanced[i]
            right_item = advanced[i + 1] if i + 1 < len(advanced) else None
            pairs.append((left_item, right_item))

        def draw_sep(y_top, y_bot):
            c.setLineWidth(0.283)
            # 实线（不再设置虚线）
            c.line(mid_x - sep_gap / 2, y_top, mid_x - sep_gap / 2, y_bot)
            c.line(mid_x + sep_gap / 2, y_top, mid_x + sep_gap / 2, y_bot)
            c.setLineWidth(0.3)

        draw_sep(cur_y + 2 * mm, bm)

        for left_item, right_item in pairs:
            def calc_lines(item, col_x, col_w):
                orig_i, question = item
                label = f"{orig_i + 1}. "
                plain = _frac_to_text(question)
                full = label + plain
                c.setFont(fn_sun, adv_font_size)
                return wrap_text(full, col_w, fn_sun, adv_font_size)

            left_lines = calc_lines(left_item, left_x, col_w_l)
            right_lines = calc_lines(right_item, right_x, col_w_r) if right_item else []
            max_lines = max(len(left_lines), len(right_lines))
            pair_height = max_lines * adv_line_gap + adv_item_gap

            if cur_y - pair_height < bm:
                cur_y = new_page()
                draw_sep(cur_y + 2 * mm, bm)

            c.setFont(fn_sun, adv_font_size)
            for li, line_txt in enumerate(left_lines):
                c.drawString(left_x, cur_y - li * adv_line_gap, line_txt)
            if right_item:
                c.setFont(fn_sun, adv_font_size)
                for li, line_txt in enumerate(right_lines):
                    c.drawString(right_x, cur_y - li * adv_line_gap, line_txt)
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
        per_line = 8   # 每行9个答案

        ans_texts = []
        for i, ans in enumerate(all_answers):
            ans_str = _safe_fmt_answer(ans)
            ans_texts.append(f"{i + 1}. {ans_str}")

        for i in range(0, len(ans_texts), per_line):
            group = ans_texts[i:i + per_line]
            line = "    ".join(group)
            if cur_y < bm + ans_line_h:
                cur_y = new_page()
                c.setFont(fn_sun, 9)
            c.drawString(lm, cur_y, line)
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
            col_w = uw / 4
            for idx, (orig_i, question) in enumerate(regular):
                col = idx % 4
                if col == 0 and idx > 0:
                    cur_y -= reg_row_h
                    if cur_y < bm + reg_row_h:
                        c.showPage()
                        current_page[0] += 1
                        draw_header()
                        cur_y = other_page_start_y
                x = lm + col * col_w
                label = f"{orig_i + 1:>3}. "
                question = question.replace(" + ", "+").replace(" - ", "-").replace(" × ", "×").replace(" ÷ ", "÷")
                parts = _split_frac_parts(question)
                c.setFont(fn_sun, 11)
                lw = c.stringWidth(label, fn_sun, 11)
                c.drawString(x, cur_y, label)
                _draw_mixed(c, x + lw, cur_y, parts, fn_sun, 11)
        
        # 重新绘制提升题
        if advanced:
            adv_font_size = 10
            adv_line_gap = 5.5 * mm
            adv_item_gap = 8 * mm
            
            if regular:
                cur_y -= reg_row_h + 4 * mm
                if cur_y < bm + adv_line_gap * 2 + adv_item_gap:
                    c.showPage()
                    current_page[0] += 1
                    draw_header()
                    cur_y = other_page_start_y
            else:
                cur_y = first_page_start_y
            
            sep_gap = 3 * mm  # 两线间距1cm
            mid_x = pw / 2
            left_x = lm
            right_x = mid_x + sep_gap / 2 + 2 * mm
            col_w_l = mid_x - sep_gap / 2 - 2 * mm - left_x
            col_w_r = pw - rm - right_x
            
            pairs = []
            for i in range(0, len(advanced), 2):
                left_item = advanced[i]
                right_item = advanced[i + 1] if i + 1 < len(advanced) else None
                pairs.append((left_item, right_item))
            
            def draw_sep2(y_top, y_bot):
                c.setLineWidth(0.283)
                # 实线（不再设置虚线）
                c.line(mid_x - sep_gap / 2, y_top, mid_x - sep_gap / 2, y_bot)
                c.line(mid_x + sep_gap / 2, y_top, mid_x + sep_gap / 2, y_bot)
                c.setLineWidth(0.3)
            
            draw_sep2(cur_y + 2 * mm, bm)
            
            for left_item, right_item in pairs:
                def calc_lines2(item, col_x, col_w):
                    orig_i, question = item
                    label = f"{orig_i + 1}. "
                    plain = _frac_to_text(question)
                    full = label + plain
                    c.setFont(fn_sun, adv_font_size)
                    lines_out = []
                    cur_line = label  # 从label开始
                    for ch in list(plain):
                        test = cur_line + ch
                        if c.stringWidth(test, fn_sun, adv_font_size) <= col_w:
                            cur_line = test
                        else:
                            if cur_line:
                                lines_out.append(cur_line)
                            cur_line = ch
                    if cur_line:
                        lines_out.append(cur_line)
                    return lines_out if lines_out else [""]
                
                left_lines = calc_lines2(left_item, left_x, col_w_l)
                right_lines = calc_lines2(right_item, right_x, col_w_r) if right_item else []
                max_lines = max(len(left_lines), len(right_lines))
                pair_height = max_lines * adv_line_gap + adv_item_gap
                
                if cur_y - pair_height < bm:
                    c.showPage()
                    current_page[0] += 1
                    draw_header()
                    cur_y = other_page_start_y
                    draw_sep2(cur_y + 2 * mm, bm)
                
                c.setFont(fn_sun, adv_font_size)
                for li, line_txt in enumerate(left_lines):
                    c.drawString(left_x, cur_y - li * adv_line_gap, line_txt)
                if right_item:
                    c.setFont(fn_sun, adv_font_size)
                    for li, line_txt in enumerate(right_lines):
                        c.drawString(right_x, cur_y - li * adv_line_gap, line_txt)
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
            per_line = 8
            
            ans_texts = []
            for i, ans in enumerate(all_answers):
                ans_str = _safe_fmt_answer(ans)
                ans_texts.append(f"{i + 1}. {ans_str}")
            
            for i in range(0, len(ans_texts), per_line):
                group = ans_texts[i:i + per_line]
                line = "    ".join(group)
                if cur_y < bm + ans_line_h:
                    c.showPage()
                    current_page[0] += 1
                    draw_header()
                    c.setFont(fn_sun, 9)
                c.drawString(lm, cur_y, line)
                cur_y -= ans_line_h
        
        c.save()
    
    return filepath