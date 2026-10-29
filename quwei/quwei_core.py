# quwei/quwei_core.py — 趣味模块核心：简笔画 / 迷宫运笔 / 数独 / 幻方
# 统一输出黑白可打印 A4 PDF（题目页 + 答案页），文件保存到项目根目录，命名唯一化。
import os
import random
import datetime

from constants import BASE_DIR

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm, cm
except Exception:  # 缺 reportlab 时延迟报错，不阻塞 import
    A4 = mm = cm = None


# ══════════════════════════════════════════════════════════
#  公共工具
# ══════════════════════════════════════════════════════════

def _unique_path(prefix):
    """项目目录下生成唯一 PDF 路径：前缀_时间戳.pdf，同分钟多份加 _1/_2。"""
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    base = os.path.join(BASE_DIR, f"{prefix}_{stamp}")
    path = base + ".pdf"
    i = 1
    while os.path.exists(path):
        path = f"{base}_{i}.pdf"
        i += 1
    return path


def _register_cn(pdfmetrics, TTFont):
    """注册中文字体（与英语模块一致的回退策略），返回字体名。"""
    try:
        from constants import FONTS_DIR
        for f in ("kaiti_gb2312.ttf", "simhei.ttf", "simsun.ttc", "msyh.ttc"):
            p = os.path.join(FONTS_DIR, f)
            if os.path.exists(p):
                pdfmetrics.registerFont(TTFont("CN", p))
                return "CN"
    except Exception:
        pass
    for p in (r"C:\Windows\Fonts\simkai.ttf", r"C:\Windows\Fonts\simhei.ttf",
              r"C:\Windows\Fonts\simsun.ttc", r"C:\Windows\Fonts\msyh.ttc"):
        if os.path.exists(p):
            pdfmetrics.registerFont(TTFont("CN", p))
            return "CN"
    return "Helvetica"


def _import_reportlab():
    try:
        from reportlab.pdfgen import canvas as _canvas_mod
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        return _canvas_mod.Canvas, pdfmetrics, TTFont, None
    except Exception as e:
        return None, None, None, f"缺少 reportlab 库：{e}"


def _draw_page_footer(c, page_w, page_h, idx, total, cn="CN"):
    """参照字帖模块规则：页眉左上日期栏（SimSun 风格 10 号）+ 右下页码 N/M（9 号）。"""
    c.setFont(cn, 10)
    c.drawString(15 * mm, page_h - 13 * mm, "日期:_____年_____月____日")
    c.setFont(cn, 9)
    c.drawRightString(page_w - 17 * mm, 8 * mm, f"{idx}/{total}")


# ── A4 四宫格版式：整页按纵横对称四等分，虚线框显示，内容居中 ──
PAGE_MARGIN_MM = 12  # 统一页边距，保证四宫格对页心对称


def _quadrant_boxes(page_w, page_h, margin=None):
    """整页按纵横对称四等分，返回 4 个方框 [(x, y, w, h)]，
    顺序为 左上、右上、左下、右下（即导出内容的填充顺序）。"""
    m = (PAGE_MARGIN_MM * mm) if margin is None else margin
    bw = (page_w - 2 * m) / 2.0
    bh = (page_h - 2 * m) / 2.0
    boxes = []
    for row in (0, 1):
        for col in (0, 1):
            boxes.append((m + col * bw, page_h - m - (row + 1) * bh, bw, bh))
    return boxes


# ══════════════════════════════════════════════════════════
#  一、简笔画（图片驱动：quwei/images/ 目录，文件名即图案名）
# ══════════════════════════════════════════════════════════

IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")


def _scan_images():
    """扫描 images/ 目录，返回 {图案名: 路径}。"""
    images = {}
    if not os.path.isdir(IMAGES_DIR):
        return images
    for f in os.listdir(IMAGES_DIR):
        name, ext = os.path.splitext(f)
        if ext.lower() not in (".png", ".jpg", ".jpeg"):
            continue
        images[name] = os.path.join(IMAGES_DIR, f)
    return images


_APP_DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_data.json")


def _load_app_data():
    """加载原版分类/难度映射（quwei/app_data.json，提取自快乐神器）。"""
    try:
        import json
        with open(_APP_DATA_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"drawing_category_map": {}, "drawing_difficulty_map": {}}


def get_jianbihua_categories():
    """分类单选框选项（全部/基础图形/动物/食物/交通建筑/花草物品）。"""
    return list(_load_app_data()["drawing_category_map"].keys())


# ───── 参考实现移植（来源：小学生快乐神器9.7 pdf_generator 反编译还原） ─────
_image_cache = {}


def load_pil_font(size):
    """加载 PIL 中文字体（水印用），失败返回 None。"""
    try:
        from PIL import ImageFont
    except Exception:
        return None
    candidates = []
    try:
        from constants import FONTS_DIR
        for f in ("kaiti_gb2312.ttf", "simhei.ttf", "simsun.ttc", "msyh.ttc"):
            candidates.append(os.path.join(FONTS_DIR, f))
    except Exception:
        pass
    candidates += [r"C:\Windows\Fonts\simkai.ttf", r"C:\Windows\Fonts\simhei.ttf",
                   r"C:\Windows\Fonts\simsun.ttc", r"C:\Windows\Fonts\msyh.ttc"]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return None


def register_pdf_fonts():
    """注册 reportlab 中文字体，返回字体名。"""
    _, pdfmetrics, TTFont, err = _import_reportlab()
    if err:
        raise RuntimeError(err)
    return _register_cn(pdfmetrics, TTFont)


def load_original_image(img_path, target_size=400):
    """加载原图：白底化 → 按内容裁边 → 等比缩放到 target_size 内（带缓存）。"""
    from PIL import Image, ImageOps
    cache_key = (img_path, target_size)
    if cache_key in _image_cache:
        return _image_cache[cache_key].copy()
    img = Image.open(img_path).convert('RGBA')
    white_bg = Image.new('RGBA', img.size, (255, 255, 255, 255))
    white_bg.paste(img, mask=img.split()[3])
    img = white_bg.convert('RGB')
    bbox = ImageOps.invert(img.convert('L')).getbbox()
    if bbox:
        padding = 10
        bbox = (max(0, bbox[0] - padding), max(0, bbox[1] - padding),
                min(img.size[0], bbox[2] + padding), min(img.size[1], bbox[3] + padding))
        img = img.crop(bbox)
    max_dim = max(img.size)
    if max_dim > target_size:
        ratio = target_size / max_dim
        new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
        img = img.resize(new_size, Image.LANCZOS)
    _image_cache[cache_key] = img.copy()
    return img


def create_tracing_image(original_img, canvas_size=600):
    """生成描红图：固定方形白底画布 + 图案淡化 35% 居中（不再画虚线边框）。
    所有图案的画布都是同样大小的正方形（与原版软件一致）。"""
    from PIL import Image
    # 淡化到 35%
    img = original_img.convert('RGBA')
    faint = img.copy()
    alpha = faint.split()[3]
    new_alpha = alpha.point(lambda a: int(a * 0.35))
    faint.putalpha(new_alpha)
    # 贴到固定方形画布：图片等比缩放到画布内并居中
    inner = canvas_size - 12  # 四周各留 6px，让图案尽量占满画布
    fw, fh = faint.size
    m = max(fw, fh)
    if m != inner:
        ratio = inner / m
        faint = faint.resize((max(1, int(fw * ratio)), max(1, int(fh * ratio))),
                             Image.LANCZOS)
    canvas = Image.new('RGBA', (canvas_size, canvas_size), (255, 255, 255, 255))
    px = (canvas_size - faint.size[0]) // 2
    py = (canvas_size - faint.size[1]) // 2
    canvas.paste(faint, (px, py), faint)
    return canvas.convert('RGB')


def generate_pdf_tracing(images_data, output_path):
    """生成描红 PDF：A4 竖版按纵横对称分 4 个方框（虚线），每框一张淡化描红图，
    物品名 + 图片整体居中于方框内。
    images_data: [[{image, name, sub_label}, ...], ...]  外层=页，内层=格"""
    import io
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.pdfgen import canvas as pdf_canvas
    from reportlab.lib.utils import ImageReader
    font_name = register_pdf_fonts()
    c = pdf_canvas.Canvas(output_path, pagesize=A4)
    page_w, page_h = A4
    boxes = _quadrant_boxes(page_w, page_h)
    label_h = 7 * cm * 0.1
    idx = 0
    for page_data in images_data:
        for i, item in enumerate(page_data):
            img_pil = item['image']
            name = item['name']
            sub_label = item.get('sub_label', '')
            bx, by, bw, bh = boxes[i % 4]
            img_w_px, img_h_px = img_pil.size
            aspect = img_w_px / img_h_px if img_h_px > 0 else 1
            pad = 4 * cm * 0.1
            avail_w = bw - 2 * pad
            avail_h = bh - 2 * pad - label_h
            if avail_w / avail_h > aspect:
                draw_h = avail_h
                draw_w = draw_h * aspect
            else:
                draw_w = avail_w
                draw_h = draw_w / aspect if aspect > 0 else avail_h
            # 物品名 + 图片作为整体，居中于方框中间
            top = by + (bh - (draw_h + label_h)) / 2
            img_x = bx + (bw - draw_w) / 2
            img_y = top
            c.setFont(font_name, 11)
            # 物品名在图片上方 7mm（原 2mm，上移 5mm）
            c.drawCentredString(bx + bw / 2, img_y + draw_h + 7 * cm * 0.1,
                                f'{name} {sub_label}'.strip())
            c.setStrokeColorRGB(0.82, 0.82, 0.82)
            c.setLineWidth(0.5)
            c.rect(img_x - 2 * cm * 0.1, img_y - 2 * cm * 0.1,
                   draw_w + 4 * cm * 0.1, draw_h + 4 * cm * 0.1)
            buf = io.BytesIO()
            img_pil.convert('RGB').save(buf, format='PNG')
            buf.seek(0)
            c.drawImage(ImageReader(buf), img_x, img_y, draw_w, draw_h,
                        preserveAspectRatio=True, mask='auto')
        _draw_page_footer(c, page_w, page_h, idx + 1, len(images_data),
                          font_name)
        idx += 1
        if idx < len(images_data):
            c.showPage()
    c.save()


def generate_pdf_compare(images_data, output_path):
    """生成对比临摹 PDF：A4 横版左右两栏，左边参考图，右边空白格。
    images_data: [[{image, name, sub_label}, ...], ...]  每页 [参考图, 自己画]"""
    import io
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import cm
    from reportlab.pdfgen import canvas as pdf_canvas
    from reportlab.lib.utils import ImageReader
    font_name = register_pdf_fonts()
    page_size = landscape(A4)
    c = pdf_canvas.Canvas(output_path, pagesize=page_size)
    page_w, page_h = page_size
    margin_x = 15 * cm * 0.1
    margin_top = 15 * cm * 0.1  # 顶部下移给页眉日期让位
    margin_bot = 10 * cm * 0.1
    gap = 10 * cm * 0.1
    label_h = 8 * cm * 0.1
    usable_w = page_w - 2 * margin_x - gap
    usable_h = page_h - margin_top - margin_bot - label_h
    cell_w = usable_w / 2
    cell_h = usable_h
    idx = 0
    for page_data in images_data:
        c.setFont(font_name, 10)
        left_item = page_data[0] if len(page_data) > 0 else None
        right_item = page_data[1] if len(page_data) > 1 else None
        for col_idx, item in enumerate([left_item, right_item]):
            if not item:
                continue
            img_pil = item['image']
            sub_label = item.get('sub_label', '')
            cx = margin_x + col_idx * (cell_w + gap)
            cy = margin_bot
            img_w_px, img_h_px = img_pil.size
            aspect = img_w_px / img_h_px if img_h_px > 0 else 1
            pad = 4 * cm * 0.1
            avail_w = cell_w - 2 * pad
            avail_h = cell_h - 2 * pad - label_h
            if avail_w / avail_h > aspect:
                draw_h = avail_h
                draw_w = draw_h * aspect
            else:
                draw_w = avail_w
                draw_h = draw_w / aspect if aspect > 0 else avail_h
            img_x = cx + (cell_w - draw_w) / 2
            img_y = cy + pad + label_h + (avail_h - draw_h) / 2
            # 物品名在方框上方 9mm（原 4mm，上移 5mm）
            c.setFont(font_name, 11)
            c.drawCentredString(cx + cell_w / 2,
                                img_y + draw_h + 9 * cm * 0.1,
                                sub_label)
            c.setStrokeColorRGB(0.8, 0.8, 0.8)
            c.setLineWidth(0.8)
            c.rect(img_x - 2 * cm * 0.1, img_y - 2 * cm * 0.1,
                   draw_w + 4 * cm * 0.1, draw_h + 4 * cm * 0.1)
            buf = io.BytesIO()
            img_pil.convert('RGB').save(buf, format='PNG')
            buf.seek(0)
            c.drawImage(ImageReader(buf), img_x, img_y, draw_w, draw_h,
                        preserveAspectRatio=True, mask='auto')
        _draw_page_footer(c, page_w, page_h, idx + 1, len(images_data),
                          font_name)
        idx += 1
        if idx < len(images_data):
            c.showPage()
    c.save()


def get_jianbihua_filtered(category, item="全部"):
    """UI 预览与导出共用：按 分类（可再指定单幅/多幅图案）过滤。
    分类严格隔离：勾选具体分类时绝不混入其他分类的图。"""
    available = _scan_images()
    data = _load_app_data()
    cat_map = data["drawing_category_map"]
    avail_set = set(available.keys())
    if category in ("随机", "全部", ""):
        pool = set(avail_set)
    else:
        pool = avail_set & set(cat_map.get(category, []))
    # 指定了具体图案（单个名称或多选列表，且属于当前池）→ 只出选中的
    if item and item != "全部":
        sel = {item} if isinstance(item, str) else set(item)
        sel &= pool
        if sel:
            pool = sel
    return sorted(pool)


def export_jianbihua(mode, category, count, item="全部", selected=None,
                     random_pick=True):
    """简笔画练习（参考小学生快乐神器实现）。
    mode: 描红练习 | 对比临摹；category: 全部 或 分类名；
    count: 1-20 页；item: 「全部」或图案名/图案名列表（兼容旧调用）；
    selected: 预览框中左键选中的图案名列表（非空时优先导出这些图）；
    random_pick: True 随机抽取，False 按分类顺序取前 N 张。
    返回 (True, 路径) 或 (False, 错误)。"""
    try:
        from PIL import Image  # noqa: F401
    except Exception:
        return False, "缺少 Pillow 库，请先安装：pip install pillow"
    available = _scan_images()
    if not available:
        return False, f"没有可用图片，请把 PNG/JPG 放入：{IMAGES_DIR}"
    count = max(1, min(int(count), 20))
    per_page = 2 if mode == "对比临摹" else 4
    sel = [n for n in (selected or []) if n in available]
    if sel:
        # 选中的图案优先：按选择顺序各出一次（描红按 4 幅/页排版）
        names = sel
    else:
        # 分类（可指定单幅/多幅图案）过滤
        pool_names = get_jianbihua_filtered(category, item)
        if not pool_names:
            return False, "当前分类下没有可用图片"
        if random_pick:
            # 随机选取，不够则循环补充（复刻原版 _select_images）
            pool = pool_names[:]
            random.shuffle(pool)
            names = []
            for _ in range(count * per_page):
                if not pool:
                    pool = pool_names[:]
                    random.shuffle(pool)
                names.append(pool.pop(0))
        else:
            # 不随机：按分类顺序取前 count 页
            pool = pool_names[:]
            names = []
            for _ in range(count * per_page):
                if not pool:
                    pool = pool_names[:]
                names.append(pool.pop(0))
    items = []
    for name in names:
        try:
            original = load_original_image(available[name])
            if mode == "描红练习":
                items.append({"image": create_tracing_image(original),
                              "name": name, "sub_label": "描红"})
            else:
                w, h = original.size
                empty = Image.new('RGB', (w, h), (255, 255, 255))
                items.append({"image": original, "name": name, "sub_label": "参考图"})
                items.append({"image": empty, "name": name, "sub_label": "自己画"})
        except Exception:
            continue
    if not items:
        return False, "图片处理失败！"
    pages = [items[i:i + per_page] for i in range(0, len(items), per_page)]
    tag = "描红" if mode == "描红练习" else "对比"
    suffix = f"{len(pages)}页" if sel else f"{count}张"
    path = _unique_path(f"简笔画练习_{tag}_{suffix}")
    try:
        if mode == "描红练习":
            generate_pdf_tracing(pages, path)
        else:
            generate_pdf_compare(pages, path)
        return True, path
    except Exception as e:
        return False, f"生成失败：{e}"


# ══════════════════════════════════════════════════════════
#  二、迷宫运笔（算法与版式移植自原版 core_maze_pdf.py）
# ══════════════════════════════════════════════════════════

# 难度 → 迷宫逻辑尺寸候选（原版：简单/中等/困难；史诗为扩展档）
_MAZE_DIFF_SIZES = {
    "简单": [(3, 3), (3, 4), (4, 4)],
    "中等": [(5, 5), (5, 6), (6, 6)],
    "困难": [(6, 6), (7, 7), (8, 8)],
    "史诗": [(9, 9), (10, 10), (12, 12)],
}


def _generate_maze(rows, cols, rng):
    """生成 (2*rows+1)×(2*cols+1) 迷宫网格，1=墙，0=通道。
    递归回溯 DFS：逻辑格中心置通道，随机打通相邻墙；最后开入口/出口。"""
    grid = [[1] * (2 * cols + 1) for _ in range(2 * rows + 1)]
    for r in range(rows):
        for c in range(cols):
            grid[2 * r + 1][2 * c + 1] = 0
    visited = [[False] * cols for _ in range(rows)]

    def dfs(r, c):
        visited[r][c] = True
        dirs = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        rng.shuffle(dirs)
        for dr, dc in dirs:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and not visited[nr][nc]:
                grid[2 * r + 1 + dr][2 * c + 1 + dc] = 0  # 打通两格之间的墙
                dfs(nr, nc)

    dfs(0, 0)
    grid[1][0] = 0                      # 入口（左侧，S）
    grid[2 * rows - 1][2 * cols] = 0    # 出口（右侧，E）
    return grid


def _maze_solution_path(grid, rows, cols):
    """BFS 求逻辑格 (0,0)→(rows-1,cols-1) 路径，返回 [(r,c), ...]。"""
    from collections import deque
    prev = {(0, 0): None}
    q = deque([(0, 0)])
    while q:
        r, c = q.popleft()
        if (r, c) == (rows - 1, cols - 1):
            break
        for dr, dc in ((0, 1), (1, 0), (0, -1), (-1, 0)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and (nr, nc) not in prev \
                    and grid[2 * r + 1 + dr][2 * c + 1 + dc] == 0:
                prev[(nr, nc)] = (r, c)
                q.append((nr, nc))
    path, cur = [], (rows - 1, cols - 1)
    while cur is not None:
        path.append(cur)
        cur = prev.get(cur)
    path.reverse()
    return path if path and path[0] == (0, 0) else []


def _draw_arrow_head(c, px, py, dx, dy, size):
    """在 (px, py) 处按方向 (dx, dy) 画一个实心箭头（三角形）。"""
    import math
    ln = math.hypot(dx, dy)
    if ln < 1e-6:
        return
    ux, uy = dx / ln, dy / ln
    nx, ny = -uy, ux
    tip = (px + ux * size, py + uy * size)
    b1 = (px - ux * size * 0.55 + nx * size * 0.6,
          py - uy * size * 0.55 + ny * size * 0.6)
    b2 = (px - ux * size * 0.55 - nx * size * 0.6,
          py - uy * size * 0.55 - ny * size * 0.6)
    p = c.beginPath()
    p.moveTo(*tip)
    p.lineTo(*b1)
    p.lineTo(*b2)
    p.close()
    c.setFillColorRGB(0.8, 0.1, 0.1)
    c.drawPath(p, stroke=0, fill=1)


def _draw_maze_pdf(c, x, y, cell_size, grid, cn, solution=None):
    """原版画法：只画与通道相邻的墙面（粗线 0.15 格宽）；
    入口/出口用中文标在迷宫左右两侧；solution 传入时叠加红色箭头路线。"""
    c.setStrokeColorRGB(0.2, 0.2, 0.2)
    c.setLineWidth(cell_size * 0.15)
    rows = len(grid)
    cols = len(grid[0])
    for r in range(rows):
        for c2 in range(cols):
            if grid[r][c2] != 1:
                continue
            px = x + c2 * cell_size
            py = y + r * cell_size
            if r > 0 and grid[r - 1][c2] == 0:
                c.line(px, py, px + cell_size, py)
            if r < rows - 1 and grid[r + 1][c2] == 0:
                c.line(px, py + cell_size, px + cell_size, py + cell_size)
            if c2 > 0 and grid[r][c2 - 1] == 0:
                c.line(px, py, px, py + cell_size)
            if c2 < cols - 1 and grid[r][c2 + 1] == 0:
                c.line(px + cell_size, py, px + cell_size, py + cell_size)
    # 入口（左侧，物理格第 1 行）/ 出口（右侧，倒数第 2 行）文字标注
    c.setFillColorRGB(0.2, 0.2, 0.2)
    fs = max(6.5, min(9, cell_size * 0.85))
    c.setFont(cn, fs)
    c.drawRightString(x - 3, y + cell_size * 1.15, '入口')
    c.drawString(x + cols * cell_size + 3,
                 y + cell_size * (rows - 1.35), '出口')
    if solution:
        c.saveState()
        c.setStrokeColorRGB(0.8, 0.1, 0.1)
        c.setLineWidth(cell_size * 0.16)
        c.setLineCap(1)
        c.setLineJoin(1)
        pts = [(x + (2 * cc + 1.5) * cell_size,
                y + (2 * r + 1.5) * cell_size) for r, cc in solution]
        p = c.beginPath()
        for i, (px_, py_) in enumerate(pts):
            if i == 0:
                p.moveTo(px_, py_)
            else:
                p.lineTo(px_, py_)
        c.drawPath(p, stroke=1, fill=0)
        # 沿线每隔一格画箭头，指示行进方向（红线→红色箭头线）
        for i in range(len(pts) - 1):
            if i % 2 and i != len(pts) - 2:
                continue
            (x1, y1), (x2, y2) = pts[i], pts[i + 1]
            _draw_arrow_head(c, (x1 + x2) / 2, (y1 + y2) / 2,
                             x2 - x1, y2 - y1, cell_size * 0.40)
        c.restoreState()
        c.setFillColorRGB(0.2, 0.2, 0.2)


def _maze_render(c, mazes, title, cn, with_path=False):
    """A4 四宫格版式：每页按纵横对称分 4 个方框（虚线），每框 1 个迷宫并居中，
    迷宫左下角标 R×C；右下角页码。"""
    page_w, page_h = A4
    boxes = _quadrant_boxes(page_w, page_h)
    per_page = len(boxes)
    total_pages = (len(mazes) + per_page - 1) // per_page
    page_no = 0
    for idx, (grid, label, path) in enumerate(mazes):
        if idx % per_page == 0:
            if idx:
                c.showPage()
            page_no += 1
            _draw_page_footer(c, page_w, page_h, page_no, total_pages, cn)
        bx, by, bw, bh = boxes[idx % per_page]
        rows_grid, cols_grid = len(grid), len(grid[0])
        pad_x, pad_y = 11 * mm, 9 * mm  # 方框内留白（左右留给「入口/出口」）
        cell = min((bw - 2 * pad_x) / cols_grid, (bh - 2 * pad_y) / rows_grid)
        maze_w, maze_h = cols_grid * cell, rows_grid * cell
        mx = bx + (bw - maze_w) / 2.0
        my = by + (bh - maze_h) / 2.0
        _draw_maze_pdf(c, mx, my, cell, grid, cn,
                       solution=path if with_path else None)
        c.setFont(cn, 8)
        c.setFillColorRGB(0.3, 0.3, 0.3)
        c.drawString(mx, my - 10, label)
        c.setFillColorRGB(0, 0, 0)


def export_migong(difficulty, pages, with_answer=False):
    """迷宫运笔（原版版式）：每页 2×2 共 4 个迷宫；答案为独立 PDF（红色箭头路线）。
    with_answer=False（默认）时只出练习册。"""
    if difficulty not in _MAZE_DIFF_SIZES:
        return False, f"未知难度：{difficulty}"
    pages = max(1, min(int(pages), 5))
    count = pages * 4
    rng = random.Random()
    mazes = []
    for _ in range(count):
        r, cc = rng.choice(_MAZE_DIFF_SIZES[difficulty])
        grid = _generate_maze(r, cc, rng)
        mazes.append((grid, f'{r}×{cc}', _maze_solution_path(grid, r, cc)))
    Canvas, pdfmetrics, TTFont, err = _import_reportlab()
    if err:
        return False, err
    cn = _register_cn(pdfmetrics, TTFont)
    path = _unique_path(f"迷宫练习_{difficulty}_{pages}页")
    try:
        c = Canvas(path, pagesize=A4)
        _maze_render(c, mazes, "迷宫练习", cn, with_path=False)
        c.save()
    except Exception as e:
        return False, f"生成失败：{e}"
    if with_answer:
        apath = _unique_path(f"迷宫答案_{difficulty}")
        try:
            c = Canvas(apath, pagesize=A4)
            _maze_render(c, mazes, "迷宫答案", cn, with_path=True)
            c.save()
        except Exception as e:
            return False, f"答案生成失败：{e}"
        return True, path + "\n" + apath
    return True, path


def _render_maze_tile(grid, cell_px=110):
    """把一道迷宫渲染成紧贴内容的 PIL 黑白图：入口/出口中文标在左右两侧，
    迷宫左下角标 R×C（与导出版式一致）。返回 PIL 图。"""
    from PIL import Image, ImageDraw
    rows, cols = len(grid), len(grid[0])
    cell = float(cell_px)
    pad_x = int(cell * 1.5)  # 左右留白给「入口/出口」
    pad_top = max(6, int(cell * 0.15))
    label_h = max(14, int(cell * 0.32))  # 下方留给 R×C 标签
    px_w = int(cols * cell + 2 * pad_x)
    px_h = int(rows * cell + pad_top + label_h)
    img = Image.new('RGB', (px_w, px_h), 'white')
    d = ImageDraw.Draw(img)
    ox, oy = pad_x, pad_top
    maze_w = cols * cell
    lw = max(2, int(cell * 0.15))
    for rr in range(rows):
        for c2 in range(cols):
            if grid[rr][c2] != 1:
                continue
            x0, y0 = ox + c2 * cell, oy + rr * cell
            if rr > 0 and grid[rr - 1][c2] == 0:
                d.line([(x0, y0), (x0 + cell, y0)], fill='black', width=lw)
            if rr < rows - 1 and grid[rr + 1][c2] == 0:
                d.line([(x0, y0 + cell), (x0 + cell, y0 + cell)],
                       fill='black', width=lw)
            if c2 > 0 and grid[rr][c2 - 1] == 0:
                d.line([(x0, y0), (x0, y0 + cell)], fill='black', width=lw)
            if c2 < cols - 1 and grid[rr][c2 + 1] == 0:
                d.line([(x0 + cell, y0), (x0 + cell, y0 + cell)],
                       fill='black', width=lw)
    font = load_pil_font(max(12, int(cell * 0.42)))
    if font:
        d.text((ox - 8, oy + cell * 1.15), '入口', fill='black',
               font=font, anchor='rm')
        d.text((ox + maze_w + 8, oy + cell * (rows - 1.35)), '出口',
               fill='black', font=font, anchor='lm')
    lfont = load_pil_font(max(11, int(cell * 0.30)))
    if lfont:
        d.text((ox, oy + rows * cell + pad_top * 0.5),
               f'{rows // 2}×{cols // 2}', fill=(90, 90, 90),
               font=lfont, anchor='la')
    return img


def render_maze_preview(difficulty, cell_px=140):
    """UI 预览用：一次生成 4 道迷宫（= 导出每页 4 道），按导出页的
    2×2 上下左右排布返回 4 张图，由界面铺满预览框显示。点击可换一组。
    返回 ([PIL图×4], 说明文字)。"""
    rng = random.Random()
    if difficulty not in _MAZE_DIFF_SIZES:
        difficulty = "简单"
    tiles = []
    for _ in range(4):
        r, cc = rng.choice(_MAZE_DIFF_SIZES[difficulty])
        grid = _generate_maze(r, cc, rng)
        # 大迷宫降采样点数，控制合成耗时与内存
        span = max(len(grid), len(grid[0]))
        px = max(48, min(cell_px, int(2400 / max(1, span))))
        tiles.append(_render_maze_tile(grid, px))
    return tiles, f'{difficulty} · 4 道（同导出每页）'

# ══════════════════════════════════════════════════════════
#  三、数独（生成引擎与版式移植自原版 core_sudoku.py / core_sudoku_pdf.py）
# ══════════════════════════════════════════════════════════

_SUDOKU_SHAPE = {"4×4": (4, 2, 2), "6×6": (6, 2, 3), "9×9": (9, 3, 3)}
# 各规格难度对应提示数（原版 初级/中级/高级/专家 → 简单/中等/困难/专家）
_SUDOKU_CLUES = {
    "4×4": {"简单": 10, "中等": 8, "困难": 6, "专家": 5},
    "6×6": {"简单": 22, "中等": 18, "困难": 15, "专家": 12},
    "9×9": {"简单": 40, "中等": 34, "困难": 30, "专家": 26},
}


def _sudoku_is_safe(grid, r, c, val, N, box_h, box_w):
    for i in range(N):
        if grid[r][i] == val or grid[i][c] == val:
            return False
    br, bc = (r // box_h) * box_h, (c // box_w) * box_w
    for i in range(br, br + box_h):
        for j in range(bc, bc + box_w):
            if grid[i][j] == val:
                return False
    return True


def _sudoku_fill(grid, N, box_h, box_w, rng):
    """随机回溯填满整个盘面（行优先）。"""
    for r in range(N):
        for c in range(N):
            if grid[r][c] != 0:
                continue
            nums = list(range(1, N + 1))
            rng.shuffle(nums)
            for val in nums:
                if _sudoku_is_safe(grid, r, c, val, N, box_h, box_w):
                    grid[r][c] = val
                    if _sudoku_fill(grid, N, box_h, box_w, rng):
                        return True
                    grid[r][c] = 0
            return False
    return True


def _sudoku_count_solutions(grid, limit, N, box_h, box_w):
    """统计解的数量，达到 limit 提前停止（唯一解校验）。
    原版快速版：行/列/宫位掩码 + MRV（最少候选优先）剪枝。"""
    ALL = (1 << N) - 1
    rows = [0] * N
    cols = [0] * N
    boxes = [0] * N
    cells = [[0] * N for _ in range(N)]
    empties = []
    nbox_w = N // box_w
    for r in range(N):
        for c in range(N):
            v = grid[r][c]
            cells[r][c] = v
            if v:
                bit = 1 << (v - 1)
                rows[r] |= bit
                cols[c] |= bit
                boxes[(r // box_h) * nbox_w + c // box_w] |= bit
            else:
                empties.append((r, c))
    counter = [0]

    def bt():
        if counter[0] >= limit:
            return
        best_r = best_c = -1
        best_avail = ALL
        best_nb = 99
        for r, c in empties:
            if cells[r][c]:
                continue
            bidx = (r // box_h) * nbox_w + c // box_w
            avail = ALL & ~(rows[r] | cols[c] | boxes[bidx])
            nb = bin(avail).count('1')
            if nb == 0:
                return
            if nb < best_nb:
                best_nb, best_r, best_c, best_avail = nb, r, c, avail
                if nb == 1:
                    break
        if best_r == -1:
            counter[0] += 1
            return
        r, c = best_r, best_c
        bidx = (r // box_h) * nbox_w + c // box_w
        avail = best_avail
        while avail:
            lsb = avail & -avail
            avail ^= lsb
            v = lsb.bit_length()
            cells[r][c] = v
            rows[r] |= lsb
            cols[c] |= lsb
            boxes[bidx] |= lsb
            bt()
            cells[r][c] = 0
            rows[r] ^= lsb
            cols[c] ^= lsb
            boxes[bidx] ^= lsb
            if counter[0] >= limit:
                return

    bt()
    return counter[0]


def _sudoku_dig_holes(full, target_clues, N, box_h, box_w, rng):
    """从完整解挖洞至约 target_clues 个提示数，保持唯一解；
    对称挖洞（镜像格）让卷面更好看（原版逻辑）。"""
    puzzle = [row[:] for row in full]
    cells = [(r, c) for r in range(N) for c in range(N)]
    rng.shuffle(cells)
    clues = N * N
    for r, c in cells:
        if clues <= target_clues:
            return puzzle
        backup = puzzle[r][c]
        if backup == 0:
            continue
        mr, mc = N - 1 - r, N - 1 - c
        puzzle[r][c] = 0
        removed_pair = False
        if (mr, mc) != (r, c) and puzzle[mr][mc] != 0:
            backup2 = puzzle[mr][mc]
            puzzle[mr][mc] = 0
            removed_pair = True
        if _sudoku_count_solutions(puzzle, limit=2, N=N,
                                   box_h=box_h, box_w=box_w) != 1:
            puzzle[r][c] = backup
            if removed_pair:
                puzzle[mr][mc] = backup2
            continue
        clues -= 2 if removed_pair else 1
    return puzzle


def _sudoku_generate_puzzle(spec, difficulty, rng):
    """生成 (题面, 完整解)，N×N 嵌套列表，0=空格。"""
    N, box_h, box_w = _SUDOKU_SHAPE[spec]
    target = _SUDOKU_CLUES[spec][difficulty]
    grid = [[0] * N for _ in range(N)]
    _sudoku_fill(grid, N, box_h, box_w, rng)
    puzzle = _sudoku_dig_holes(grid, target, N, box_h, box_w, rng)
    return puzzle, grid


def _draw_sudoku_grid(c, x, y, size, grid, N, box_h, box_w):
    """原版版式：细线灰 0.5、宫界/外框粗线 1.8、Helvetica-Bold 数字。"""
    cell = size / N
    c.setStrokeColorRGB(0.55, 0.5, 0.48)
    c.setLineWidth(0.5)
    for i in range(N + 1):
        c.line(x, y + i * cell, x + size, y + i * cell)
        c.line(x + i * cell, y, x + i * cell, y + size)
    c.setStrokeColorRGB(0.25, 0.22, 0.2)
    c.setLineWidth(1.8)
    for i in range(0, N + 1):
        if i % box_h == 0:
            c.line(x, y + i * cell, x + size, y + i * cell)
        if i % box_w == 0:
            c.line(x + i * cell, y, x + i * cell, y + size)
    c.setFillColorRGB(0.15, 0.13, 0.12)
    fs = cell * 0.62
    c.setFont('Helvetica-Bold', fs)
    for r in range(N):
        for col in range(N):
            val = grid[r][col]
            if val:
                c.drawCentredString(x + col * cell + cell / 2,
                                    y + r * cell + cell * 0.3, str(val))


def _sudoku_render(c, puzzles, spec, title, fill_all, cn):
    """A4 四宫格版式：每页按纵横对称分 4 个方框（虚线），每框 1 题并居中。"""
    N, box_h, box_w = _SUDOKU_SHAPE[spec]
    page_w, page_h = A4
    boxes = _quadrant_boxes(page_w, page_h)
    per_page = len(boxes)
    total_pages = (len(puzzles) + per_page - 1) // per_page
    page_no = 0
    for idx, item in enumerate(puzzles):
        if idx % per_page == 0:
            if idx:
                c.showPage()
            page_no += 1
            _draw_page_footer(c, page_w, page_h, page_no, total_pages, cn)
        bx, by, bw, bh = boxes[idx % per_page]
        grid_size = min(bw, bh) - 18 * mm  # 方框内四周留白
        sx = bx + (bw - grid_size) / 2.0
        gy = by + (bh - grid_size) / 2.0
        grid = item[1] if fill_all else item[0]
        _draw_sudoku_grid(c, sx, gy, grid_size, grid, N, box_h, box_w)


def export_shudu(spec, difficulty, pages, with_answer=True):
    """数独（A4 四宫格）：每页 4 题 + 可选独立答案 PDF。
    with_answer=False 时只出练习册。"""
    if spec not in _SUDOKU_SHAPE or difficulty not in _SUDOKU_CLUES[spec]:
        return False, f"未知规格/难度：{spec}/{difficulty}"
    pages = max(1, min(int(pages), 4))
    count = pages * 4
    rng = random.Random()
    puzzles = [_sudoku_generate_puzzle(spec, difficulty, rng)
               for _ in range(count)]
    Canvas, pdfmetrics, TTFont, err = _import_reportlab()
    if err:
        return False, err
    cn = _register_cn(pdfmetrics, TTFont)
    label = f"{spec} {difficulty}"
    path = _unique_path(f"数独练习_{spec.replace('×', 'x')}_{difficulty}_{pages}页")
    try:
        c = Canvas(path, pagesize=A4)
        _sudoku_render(c, puzzles, spec, f"数独练习（{label}）", False, cn)
        c.save()
    except Exception as e:
        return False, f"生成失败：{e}"
    if with_answer:
        apath = _unique_path(f"数独答案_{spec.replace('×', 'x')}_{difficulty}")
        try:
            c = Canvas(apath, pagesize=A4)
            _sudoku_render(c, puzzles, spec, f"数独答案（{label}）", True, cn)
            c.save()
        except Exception as e:
            return False, f"答案生成失败：{e}"
        return True, path + "\n" + apath
    return True, path


def _render_sudoku_tile(puzzle, spec, px=440):
    """单张数独盘渲染成 PIL 黑白图（细线格 + 粗线宫）。"""
    from PIL import Image, ImageDraw, ImageFont
    N, box_h, box_w = _SUDOKU_SHAPE[spec]
    img = Image.new('RGB', (px, px), 'white')
    d = ImageDraw.Draw(img)
    pad = 8  # 四周留白，保证外框粗线完整显示
    cell = (px - 2 * pad) / N
    for i in range(N + 1):
        wdt = 2 if (i % box_h == 0 or i % box_w == 0) else 1
        d.line([(pad, pad + i * cell), (px - pad, pad + i * cell)],
               fill='black', width=wdt)
        d.line([(pad + i * cell, pad), (pad + i * cell, px - pad)],
               fill='black', width=wdt)
    fs = max(8, int(cell * 0.62))
    try:
        f = ImageFont.truetype('arialbd.ttf', fs)
    except Exception:
        try:
            f = ImageFont.load_default(size=fs)
        except TypeError:
            f = ImageFont.load_default()
    for r in range(N):
        for c2 in range(N):
            v = puzzle[r][c2]
            if v:
                d.text((pad + (c2 + 0.5) * cell, pad + (r + 0.5) * cell),
                       str(v), fill='black', font=f, anchor='mm')
    return img


def render_sudoku_preview(spec, difficulty, px=800):
    """UI 预览用：一次生成导出每页的 4 题，排进 A4 四宫格（虚线方框）
    并居中，与导出版式一致。返回 (PIL图, 题数说明)。"""
    rng = random.Random()
    tiles = []
    for _ in range(4):
        puzzle, _sol = _sudoku_generate_puzzle(spec, difficulty, rng)
        tiles.append(_render_sudoku_tile(puzzle, spec, 440))
    return tiles, f'{spec} · 4 题'


# ══════════════════════════════════════════════════════════
#  四、幻方（生成引擎与版式移植自原版 core_magic_square.py / core_magic_square_pdf.py）
# ══════════════════════════════════════════════════════════

_HUANFANG_ORDER = {"3阶": 3, "4阶": 4, "5阶": 5}

# 原版基准幻方（3/4 阶固定解，随机旋转/翻转得到变体）
_MS_BASE = {
    3: [[8, 1, 6],
        [3, 5, 7],
        [4, 9, 2]],
    4: [[16, 3, 2, 13],
        [5, 10, 11, 8],
        [9, 6, 7, 12],
        [4, 15, 14, 1]],
}


def _ms_rotate90(m):
    N = len(m)
    return [[m[N - 1 - j][i] for j in range(N)] for i in range(N)]


def _ms_reflect_v(m):
    N = len(m)
    return [[m[N - 1 - i][j] for j in range(N)] for i in range(N)]


def _ms_reflect_h(m):
    N = len(m)
    return [[m[i][N - 1 - j] for j in range(N)] for i in range(N)]


def _ms_transform(sq, rng):
    """随机旋转/翻转得到等价幻方（保持魔性，原版逻辑）。"""
    sq = [row[:] for row in sq]
    for _ in range(rng.randint(0, 3)):
        sq = _ms_rotate90(sq)
    if rng.random() < 0.5:
        sq = _ms_reflect_v(sq)
    if rng.random() < 0.5:
        sq = _ms_reflect_h(sq)
    return sq


def _ms_siamese(n):
    """奇数阶幻方（罗伯法），用于 5 阶。"""
    sq = [[0] * n for _ in range(n)]
    i, j = 0, n // 2
    for v in range(1, n * n + 1):
        sq[i][j] = v
        ni, nj = (i - 1) % n, (j + 1) % n
        if sq[ni][nj]:
            i = (i + 1) % n
        else:
            i, j = ni, nj
    return sq


def _huanfang_generate_puzzle(n, rng):
    """返回 (题面, 完整解, 幻和)。3/4 阶用原版基准解+变换，5 阶罗伯法+变换。
    挖空数沿用原版：3阶 2~3，4阶 4~6；5阶 6~9。"""
    if n in _MS_BASE:
        solution = _ms_transform(_MS_BASE[n], rng)
    else:
        solution = _ms_transform(_ms_siamese(n), rng)
    msum = n * (n * n + 1) // 2
    if n == 3:
        blanks = rng.randint(2, 3)
    elif n == 4:
        blanks = rng.randint(4, 6)
    else:
        blanks = rng.randint(6, 9)
    puzzle = [row[:] for row in solution]
    positions = [(r, c) for r in range(n) for c in range(n)]
    rng.shuffle(positions)
    for r, c in positions[:blanks]:
        puzzle[r][c] = 0
    return puzzle, solution, msum


def _draw_huanfang_grid(c, x, y, size, grid, N):
    """原版版式：细线灰 0.5、外框粗线 2.2、Helvetica-Bold 数字。"""
    cell = size / N
    c.setStrokeColorRGB(0.55, 0.5, 0.48)
    c.setLineWidth(0.5)
    for i in range(N + 1):
        c.line(x, y + i * cell, x + size, y + i * cell)
        c.line(x + i * cell, y, x + i * cell, y + size)
    c.setStrokeColorRGB(0.2, 0.18, 0.16)
    c.setLineWidth(2.2)
    c.rect(x, y, size, size)
    c.setFillColorRGB(0.15, 0.13, 0.12)
    fs = cell * 0.6
    c.setFont('Helvetica-Bold', fs)
    for r in range(N):
        for col in range(N):
            v = grid[r][col]
            if v:
                c.drawCentredString(x + col * cell + cell / 2,
                                    y + r * cell + cell * 0.3, str(v))


def _huanfang_render(c, puzzles, title, msum, fill_all, cn):
    """A4 四宫格版式：每页按纵横对称分 4 个方框（虚线），每框 1 题并居中。"""
    N = len(puzzles[0][0])
    page_w, page_h = A4
    boxes = _quadrant_boxes(page_w, page_h)
    per_page = len(boxes)
    total_pages = (len(puzzles) + per_page - 1) // per_page
    page_no = 0
    for idx, item in enumerate(puzzles):
        if idx % per_page == 0:
            if idx:
                c.showPage()
            page_no += 1
            _draw_page_footer(c, page_w, page_h, page_no, total_pages, cn)
        bx, by, bw, bh = boxes[idx % per_page]
        grid_size = min(bw, bh) - 20 * mm  # 方框内四周留白
        sx = bx + (bw - grid_size) / 2.0
        gy = by + (bh - grid_size) / 2.0
        grid = item[1] if fill_all else item[0]
        _draw_huanfang_grid(c, sx, gy, grid_size, grid, N)


def export_huanfang(order_name, pages, with_answer=True):
    """幻方（A4 四宫格）：每页 4 题 + 可选独立答案 PDF。
    挖空数自动随机（3阶 2~3 / 4阶 4~6 / 5阶 6~9）。"""
    if order_name not in _HUANFANG_ORDER:
        return False, f"未知阶数：{order_name}"
    pages = max(1, min(int(pages), 4))
    n = _HUANFANG_ORDER[order_name]
    count = pages * 4
    rng = random.Random()
    puzzles = [_huanfang_generate_puzzle(n, rng) for _ in range(count)]
    msum = puzzles[0][2]
    Canvas, pdfmetrics, TTFont, err = _import_reportlab()
    if err:
        return False, err
    cn = _register_cn(pdfmetrics, TTFont)
    path = _unique_path(f"幻方练习_{order_name}_{pages}页")
    try:
        c = Canvas(path, pagesize=A4)
        _huanfang_render(c, puzzles, f"幻方练习（{order_name}）", msum, False, cn)
        c.save()
    except Exception as e:
        return False, f"生成失败：{e}"
    if with_answer:
        apath = _unique_path(f"幻方答案_{order_name}")
        try:
            c = Canvas(apath, pagesize=A4)
            _huanfang_render(c, puzzles, f"幻方答案（{order_name}）", msum, True, cn)
            c.save()
        except Exception as e:
            return False, f"答案生成失败：{e}"
        return True, path + "\n" + apath
    return True, path


def _render_huanfang_tile(puzzle, px=520):
    """单张幻方盘渲染成 PIL 黑白图。"""
    from PIL import Image, ImageDraw, ImageFont
    N = len(puzzle)
    img = Image.new('RGB', (px, px), 'white')
    d = ImageDraw.Draw(img)
    pad = 8  # 四周留白，保证外框粗线完整显示
    cell = (px - 2 * pad) / N
    for i in range(N + 1):
        wdt = 2 if i in (0, N) else 1
        d.line([(pad, pad + i * cell), (px - pad, pad + i * cell)],
               fill='black', width=wdt)
        d.line([(pad + i * cell, pad), (pad + i * cell, px - pad)],
               fill='black', width=wdt)
    fs = max(10, int(cell * 0.6))
    try:
        f = ImageFont.truetype('arialbd.ttf', fs)
    except Exception:
        try:
            f = ImageFont.load_default(size=fs)
        except TypeError:
            f = ImageFont.load_default()
    for r in range(N):
        for c2 in range(N):
            v = puzzle[r][c2]
            if v:
                d.text((pad + (c2 + 0.5) * cell, pad + (r + 0.5) * cell),
                       str(v), fill='black', font=f, anchor='mm')
    return img


def render_huanfang_preview(order_name, px=800):
    """UI 预览用：一次生成导出每页的 4 道幻方，排进 A4 四宫格
    （虚线方框）并居中，与导出版式一致。返回 (PIL图, 题数说明)。"""
    rng = random.Random()
    n = _HUANFANG_ORDER[order_name]
    tiles = []
    for _ in range(4):
        puzzle, _sol, _msum = _huanfang_generate_puzzle(n, rng)
        tiles.append(_render_huanfang_tile(puzzle, 460))
    return tiles, f'{order_name} · 4 题'
