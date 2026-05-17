# shuxue_drawings.py — 几何题图形绘制模块
# 从题目文本中提取尺寸参数，使用 ReportLab 矢量原语绘制图形

import re
import math
from dataclasses import dataclass
from typing import Optional

mm = 1  # this module works in PDF points; callers convert mm to points


@dataclass
class DrawingSpec:
    shape_type: str
    params: dict
    figure_height_mm: float


GEOMETRY_QUESTION_TYPES = {
    "cb_perimeter", "cb_3d_graph", "cb_equal_area",
    "cb_graph_count", "cb_graph_split",
}

FIGURE_HEIGHTS = {
    "rectangle": 16, "square": 16, "triangle": 16, "circle": 16,
    "cube": 18, "prism": 18,
    "eq_tri_para": 17, "eq_tri_trap": 17, "eq_para_rect": 17,
    "points_circle": 18, "line_grid": 16, "rect_grid": 16,
    "line_segment": 12, "circle_lines": 17, "cell_grid": 16,
}


# ══════════════════════════════════════════════════════════
#  参数提取
# ══════════════════════════════════════════════════════════

def _extract_perimeter(text: str) -> Optional[DrawingSpec]:
    m = re.search(r'长方形长(\d+)厘米宽(\d+)厘米', text)
    if m:
        return DrawingSpec("rectangle", {"l": int(m.group(1)), "w": int(m.group(2))}, 25)
    m = re.search(r'正方形边长(\d+)厘米', text)
    if m:
        return DrawingSpec("square", {"s": int(m.group(1))}, 25)
    m = re.search(r'三角形底(\d+)厘米[，,]高(\d+)厘米', text)
    if m:
        return DrawingSpec("triangle", {"b": int(m.group(1)), "h": int(m.group(2))}, 25)
    m = re.search(r'圆的半径是(\d+)厘米', text)
    if m:
        return DrawingSpec("circle", {"r": int(m.group(1))}, 25)
    return None


def _extract_3d(text: str) -> Optional[DrawingSpec]:
    m = re.search(r'棱长(\d+)厘米的正方体', text)
    if m:
        return DrawingSpec("cube", {"a": int(m.group(1))}, 30)
    m = re.search(r'长方体长(\d+)厘米[、,]宽(\d+)厘米[、,]高(\d+)厘米', text)
    if m:
        return DrawingSpec("prism", {"l": int(m.group(1)), "w": int(m.group(2)), "h": int(m.group(3))}, 30)
    return None


def _extract_equal_area(text: str) -> Optional[DrawingSpec]:
    if '三角形' in text and '平行四边形' in text:
        return DrawingSpec("eq_tri_para", {"text": text}, 28)
    if '三角形' in text and '梯形' in text:
        return DrawingSpec("eq_tri_trap", {"text": text}, 28)
    if '平行四边形' in text and '长方形' in text:
        return DrawingSpec("eq_para_rect", {"text": text}, 28)
    return None


def _extract_graph_count(text: str) -> Optional[DrawingSpec]:
    m = re.search(r'(\d+)个点两两连线', text)
    if m:
        return DrawingSpec("points_circle", {"n": int(m.group(1))}, 30)
    m = re.search(r'(\d+)条横线和(\d+)条竖线', text)
    if m:
        return DrawingSpec("line_grid", {"h": int(m.group(1)), "v": int(m.group(2))}, 25)
    m = re.search(r'(\d+)行(\d+)列的方格网', text)
    if m:
        return DrawingSpec("rect_grid", {"rows": int(m.group(1)), "cols": int(m.group(2))}, 25)
    return None


def _extract_graph_split(text: str) -> Optional[DrawingSpec]:
    m = re.search(r'一条线段[，,](\d+)个点', text)
    if m:
        return DrawingSpec("line_segment", {"n": int(m.group(1))}, 18)
    m = re.search(r'圆内画(\d+)条直线', text)
    if m:
        return DrawingSpec("circle_lines", {"n": int(m.group(1))}, 28)
    m = re.search(r'(\d+)行(\d+)列的方格图', text)
    if m:
        return DrawingSpec("cell_grid", {"rows": int(m.group(1)), "cols": int(m.group(2))}, 25)
    return None


_EXTRACTORS = {
    "cb_perimeter": _extract_perimeter,
    "cb_3d_graph": _extract_3d,
    "cb_equal_area": _extract_equal_area,
    "cb_graph_count": _extract_graph_count,
    "cb_graph_split": _extract_graph_split,
}


def extract_drawing_spec(q_type: str, question_text: str) -> Optional[DrawingSpec]:
    extractor = _EXTRACTORS.get(q_type)
    if extractor:
        return extractor(question_text)
    return None


# ══════════════════════════════════════════════════════════
#  绘图辅助
# ══════════════════════════════════════════════════════════

def _dim_label(c, x, y, text, font, size=8):
    c.setFont(font, size)
    c.drawCentredString(x, y, text)


def _dashed_line(c, x1, y1, x2, y2):
    c.saveState()
    c.setDash([2, 2])
    c.setLineWidth(0.3)
    c.line(x1, y1, x2, y2)
    c.restoreState()


# ══════════════════════════════════════════════════════════
#  绘图函数
# ══════════════════════════════════════════════════════════

def draw_rectangle(c, x, y, w, h, params):
    l, wd = params["l"], params["w"]
    fn = c._fontname if hasattr(c, '_fontname') else 'SimSun'
    # Reserve space for bottom label (10pt) and side label, then scale shape to fill
    avail_w = w - 4
    avail_h = h - 14
    scale = min(avail_w / l, avail_h / wd)
    rw, rh = l * scale, wd * scale
    rx = x + (w - rw) / 2
    ry = y + 8
    c.setLineWidth(0.6)
    c.rect(rx, ry, rw, rh)
    _dim_label(c, rx + rw / 2, ry - 10, f"{l}cm", fn, 8)
    c.saveState()
    c.translate(rx - 4, ry + rh / 2)
    c.rotate(90)
    _dim_label(c, 0, 0, f"{wd}cm", fn, 8)
    c.restoreState()


def draw_square(c, x, y, w, h, params):
    s = params["s"]
    fn = c._fontname if hasattr(c, '_fontname') else 'SimSun'
    avail = min(w - 4, h - 14)
    ss = min(avail, s * (avail / max(s, 1)))
    rx = x + (w - ss) / 2
    ry = y + 8
    c.setLineWidth(0.6)
    c.rect(rx, ry, ss, ss)
    _dim_label(c, rx + ss / 2, ry - 10, f"{s}cm", fn, 8)


def draw_triangle(c, x, y, w, h, params):
    b, ht = params["b"], params["h"]
    fn = c._fontname if hasattr(c, '_fontname') else 'SimSun'
    avail_w = w - 4
    avail_h = h - 14
    scale = min(avail_w / b, avail_h / ht)
    sb, sh = b * scale, ht * scale
    cx = x + w / 2
    by = y + 8
    pts = [(cx - sb / 2, by), (cx + sb / 2, by), (cx, by + sh)]
    p = c.beginPath()
    p.moveTo(*pts[0])
    p.lineTo(*pts[1])
    p.lineTo(*pts[2])
    p.close()
    c.drawPath(p, stroke=1, fill=0)
    _dashed_line(c, cx, by + sh, cx, by)
    _dim_label(c, cx, by - 10, f"{b}cm", fn, 8)
    c.saveState()
    c.translate(cx + 3, by + sh / 2)
    c.rotate(90)
    _dim_label(c, 0, 0, f"{ht}cm", fn, 8)
    c.restoreState()


def draw_circle(c, x, y, w, h, params):
    r = params["r"]
    fn = c._fontname if hasattr(c, '_fontname') else 'SimSun'
    avail = min(w - 4, h - 16) / 2
    sr = min(avail, r * (avail / max(r, 1)))
    cx = x + w / 2
    cy = y + 8 + sr
    c.setLineWidth(0.6)
    c.circle(cx, cy, sr)
    c.line(cx, cy, cx + sr, cy)
    _dim_label(c, cx + sr / 2, cy + 4, f"r={r}cm", fn, 8)


def draw_cube(c, x, y, w, h, params):
    a = params["a"]
    fn = c._fontname if hasattr(c, '_fontname') else 'SimSun'
    avail_w = w - 6
    avail_h = h - 14
    # oblique projection: total width = sa + ox = sa * 1.35
    max_a = min(avail_w / 1.35, avail_h)
    sa = min(max_a, a * (max_a / max(a, 1)))
    ox = sa * 0.35
    oy = sa * 0.35
    bx = x + (w - sa - ox) / 2
    by = y + 8
    c.setLineWidth(0.6)
    c.rect(bx, by, sa, sa)
    c.rect(bx + ox, by + oy, sa, sa)
    c.line(bx, by, bx + ox, by + oy)
    c.line(bx + sa, by, bx + sa + ox, by + oy)
    c.line(bx, by + sa, bx + ox, by + sa + oy)
    c.line(bx + sa, by + sa, bx + sa + ox, by + sa + oy)
    _dim_label(c, bx + sa / 2, by - 10, f"{a}cm", fn, 8)


def draw_prism(c, x, y, w, h, params):
    l, wd, ht = params["l"], params["w"], params["h"]
    fn = c._fontname if hasattr(c, '_fontname') else 'SimSun'
    avail_w = w - 6
    avail_h = h - 14
    # oblique projection: total width = sl + ox = sl + sw*0.4
    max_dim = min(avail_w / 1.4, avail_h)
    scale = max_dim / max(l, wd, ht, 1)
    sl, sw, sh = l * scale, wd * scale, ht * scale
    ox, oy = sw * 0.4, sw * 0.3
    bx = x + (w - sl - ox) / 2
    by = y + 8
    c.setLineWidth(0.6)
    c.rect(bx, by, sl, sh)
    c.rect(bx + ox, by + oy, sl, sh)
    c.line(bx, by, bx + ox, by + oy)
    c.line(bx + sl, by, bx + sl + ox, by + oy)
    c.line(bx, by + sh, bx + ox, by + sh + oy)
    c.line(bx + sl, by + sh, bx + sl + ox, by + sh + oy)
    _dim_label(c, bx + sl / 2, by - 10, f"{l}cm", fn, 8)


def draw_eq_tri_para(c, x, y, w, h, params):
    fn = c._fontname if hasattr(c, '_fontname') else 'SimSun'
    c.setLineWidth(0.6)
    half_w = w / 2 - 2
    # triangle on left
    tx = x + 1
    ty = y + 6
    tw, th = half_w - 2, h - 14
    p = c.beginPath()
    p.moveTo(tx, ty)
    p.lineTo(tx + tw, ty)
    p.lineTo(tx + tw / 2, ty + th)
    p.close()
    c.drawPath(p, stroke=1, fill=0)
    _dim_label(c, tx + tw / 2, ty + th + 4, "S", fn, 9)
    # parallelogram on right
    px = x + half_w + 4
    pw, ph = half_w - 2, th * 0.65
    skew = tw * 0.2
    p2 = c.beginPath()
    p2.moveTo(px + skew, ty + ph)
    p2.lineTo(px + skew + pw, ty + ph)
    p2.lineTo(px + pw, ty)
    p2.lineTo(px, ty)
    p2.close()
    c.drawPath(p2, stroke=1, fill=0)
    _dim_label(c, px + pw / 2 + skew / 2, ty + ph + 4, "S", fn, 9)
    c.saveState()
    c.setDash([2, 2])
    c.line(x + w / 2 - 2, ty + th + 10, x + w / 2 - 2, ty - 2)
    c.restoreState()


def draw_eq_tri_trap(c, x, y, w, h, params):
    fn = c._fontname if hasattr(c, '_fontname') else 'SimSun'
    c.setLineWidth(0.6)
    half_w = w / 2 - 2
    tx, ty = x + 1, y + 6
    tw, th = half_w - 2, h - 14
    p = c.beginPath()
    p.moveTo(tx, ty)
    p.lineTo(tx + tw, ty)
    p.lineTo(tx + tw / 2, ty + th)
    p.close()
    c.drawPath(p, stroke=1, fill=0)
    _dim_label(c, tx + tw / 2, ty + th + 4, "S", fn, 9)
    px = x + half_w + 4
    pw, ph = half_w - 2, th * 0.7
    p2 = c.beginPath()
    p2.moveTo(px, ty)
    p2.lineTo(px + pw, ty)
    p2.lineTo(px + pw * 0.7, ty + ph)
    p2.lineTo(px + pw * 0.3, ty + ph)
    p2.close()
    c.drawPath(p2, stroke=1, fill=0)
    _dim_label(c, px + pw / 2, ty + ph + 4, "S", fn, 9)


def draw_eq_para_rect(c, x, y, w, h, params):
    fn = c._fontname if hasattr(c, '_fontname') else 'SimSun'
    c.setLineWidth(0.6)
    half_w = w / 2 - 2
    tx, ty = x + 1, y + 6
    tw, th = half_w - 2, h - 14
    skew = tw * 0.2
    p = c.beginPath()
    p.moveTo(tx + skew, ty + th)
    p.lineTo(tx + skew + tw, ty + th)
    p.lineTo(tx + tw, ty)
    p.lineTo(tx, ty)
    p.close()
    c.drawPath(p, stroke=1, fill=0)
    _dim_label(c, tx + tw / 2 + skew / 2, ty + th + 4, "S", fn, 9)
    px = x + half_w + 4
    pw, ph = half_w - 2, th
    c.rect(px, ty, pw, ph)
    _dim_label(c, px + pw / 2, ty + ph + 4, "S", fn, 9)


def draw_points_circle(c, x, y, w, h, params):
    n = min(params["n"], 8)
    cx = x + w / 2
    cy = y + h / 2
    r = min(w - 8, h - 16) / 2
    c.setLineWidth(0.3)
    for i in range(n):
        a1 = 2 * math.pi * i / n
        for j in range(i + 1, n):
            a2 = 2 * math.pi * j / n
            c.line(cx + r * math.cos(a1), cy + r * math.sin(a1),
                   cx + r * math.cos(a2), cy + r * math.sin(a2))
    c.setLineWidth(0.6)
    for i in range(n):
        a = 2 * math.pi * i / n
        c.circle(cx + r * math.cos(a), cy + r * math.sin(a), 2, stroke=1, fill=1)


def draw_line_grid(c, x, y, w, h, params):
    hv, vv = params["h"], params["v"]
    pad = 4
    gw, gh = w - 2 * pad, h - 2 * pad - 6
    c.setLineWidth(0.5)
    for i in range(hv):
        yy = y + pad + gh * i / max(hv - 1, 1)
        c.line(x + pad, yy, x + pad + gw, yy)
    for j in range(vv):
        xx = x + pad + gw * j / max(vv - 1, 1)
        c.line(xx, y + pad, xx, y + pad + gh)


def draw_rect_grid(c, x, y, w, h, params):
    rows, cols = params["rows"], params["cols"]
    pad = 4
    gw, gh = w - 2 * pad, h - 2 * pad - 6
    cw, ch = gw / cols, gh / rows
    c.setLineWidth(0.5)
    for i in range(rows + 1):
        c.line(x + pad, y + pad + ch * i, x + pad + gw, y + pad + ch * i)
    for j in range(cols + 1):
        c.line(x + pad + cw * j, y + pad, x + pad + cw * j, y + pad + gh)


def draw_line_segment(c, x, y, w, h, params):
    n = params["n"]
    pad = 6
    sx, ex = x + pad, x + w - pad
    sy = y + h / 2
    c.setLineWidth(0.6)
    c.line(sx, sy, ex, sy)
    c.circle(sx, sy, 2.5, stroke=1, fill=1)
    c.circle(ex, sy, 2.5, stroke=1, fill=1)
    c.setLineWidth(0.5)
    for i in range(1, n + 1):
        px = sx + (ex - sx) * i / (n + 1)
        c.circle(px, sy, 2, stroke=1, fill=1)


def draw_circle_lines(c, x, y, w, h, params):
    n = min(params["n"], 6)
    cx = x + w / 2
    cy = y + h / 2
    r = min(w - 8, h - 16) / 2
    c.setLineWidth(0.5)
    c.circle(cx, cy, r)
    for i in range(n):
        angle = math.pi * i / n + 0.1
        dx = r * math.cos(angle)
        dy = r * math.sin(angle)
        c.line(cx - dx, cy - dy, cx + dx, cy + dy)


def draw_cell_grid(c, x, y, w, h, params):
    draw_rect_grid(c, x, y, w, h, params)


_DRAW_FUNCS = {
    "rectangle": draw_rectangle,
    "square": draw_square,
    "triangle": draw_triangle,
    "circle": draw_circle,
    "cube": draw_cube,
    "prism": draw_prism,
    "eq_tri_para": draw_eq_tri_para,
    "eq_tri_trap": draw_eq_tri_trap,
    "eq_para_rect": draw_eq_para_rect,
    "points_circle": draw_points_circle,
    "line_grid": draw_line_grid,
    "rect_grid": draw_rect_grid,
    "line_segment": draw_line_segment,
    "circle_lines": draw_circle_lines,
    "cell_grid": draw_cell_grid,
}


def draw_figure(c, x, y, width, height, spec: DrawingSpec):
    c.saveState()
    c._fontname = 'SimSun'
    func = _DRAW_FUNCS.get(spec.shape_type)
    if func:
        func(c, x, y, width, height, spec.params)
    c.restoreState()
