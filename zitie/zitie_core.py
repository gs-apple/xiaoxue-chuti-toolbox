# zitie_core.py - 字帖生成核心模块
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import black, gray, HexColor
from reportlab import rl_config
import os
import re
import math
import io
import json
from PIL import Image, ImageDraw, ImageFont

# 设置 reportlab 配置，允许自动生成缺少的 PostScript 名称
rl_config.autoGenerateMissingTTFName = 1


# ══════════════════════════════════════════════════════════
#  笔顺渲染器 (原 stroke_renderer.py)
# ══════════════════════════════════════════════════════════

class StrokeRenderer:
    """汉字笔顺渲染器 - 从 stroke_data.json 加载笔画路径"""

    def __init__(self, data_path=None):
        if data_path is None:
            data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'stroke_data.json')
        self._data_path = data_path
        self._data = None
        self._cache = {}
        self._font_cache = {}

    def _ensure_loaded(self):
        if self._data is not None:
            return
        try:
            with open(self._data_path, 'r', encoding='utf-8') as f:
                self._data = json.load(f)
        except Exception:
            self._data = {}

    def has_stroke_data(self, char):
        self._ensure_loaded()
        return str(ord(char)) in self._data

    def get_stroke_count(self, char):
        self._ensure_loaded()
        paths = self._data.get(str(ord(char)))
        return len(paths) if paths else -1

    def _get_stroke_paths(self, char):
        self._ensure_loaded()
        return self._data.get(str(ord(char)), [])

    @staticmethod
    def _parse_svg_path_d(path_str):
        commands = []
        tokens = re.findall(r'([MLHVCSQTZmlhvcsqtz])\s*|([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)', path_str)
        current_cmd = None
        numbers = []
        for cmd_token, num_token in tokens:
            if cmd_token:
                if current_cmd is not None and numbers:
                    coords = [(float(numbers[i]), float(numbers[i+1]))
                              for i in range(0, len(numbers)-1, 2)]
                    commands.append((current_cmd.upper(), coords))
                current_cmd = cmd_token
                numbers = []
            elif num_token != '':
                numbers.append(float(num_token))
        if current_cmd is not None and numbers:
            coords = [(float(numbers[i]), float(numbers[i+1]))
                      for i in range(0, len(numbers)-1, 2)]
            commands.append((current_cmd.upper(), coords))
        return commands

    def _flatten_path_to_points(self, commands, steps_per_segment=8):
        points = []
        current_x, current_y = 0.0, 0.0
        last_ctrl_x, last_ctrl_y = 0.0, 0.0
        first_x, first_y = 0.0, 0.0

        for cmd, coords in commands:
            if cmd == 'M':
                for (x, y) in coords:
                    current_x, current_y = x, y
                    first_x, first_y = x, y
                    points.append((x, y))
            elif cmd == 'L':
                for (x, y) in coords:
                    dx, dy = x - current_x, y - current_y
                    dist = math.sqrt(dx*dx + dy*dy)
                    steps = max(3, int(dist / 15 * steps_per_segment))
                    for s in range(1, steps + 1):
                        t = s / steps
                        px = current_x + dx * t
                        py = current_y + dy * t
                        points.append((px, py))
                    current_x, current_y = x, y
            elif cmd == 'H':
                for (x,) in coords:
                    dx = x - current_x
                    dist = abs(dx)
                    steps = max(3, int(dist / 15 * steps_per_segment))
                    for s in range(1, steps + 1):
                        t = s / steps
                        points.append((current_x + dx * t, current_y))
                    current_x = x
            elif cmd == 'V':
                for (y,) in coords:
                    dy = y - current_y
                    dist = abs(dy)
                    steps = max(3, int(dist / 15 * steps_per_segment))
                    for s in range(1, steps + 1):
                        t = s / steps
                        points.append((current_x, current_y + dy * t))
                    current_y = y
            elif cmd == 'Q':
                for i in range(0, len(coords), 2):
                    cx1, cy1 = coords[i]
                    ex, ey = coords[i+1]
                    steps = steps_per_segment * 4
                    for s in range(1, steps + 1):
                        t = s / steps
                        u = 1 - t
                        px = u*u*current_x + 2*u*t*cx1 + t*t*ex
                        py = u*u*current_y + 2*u*t*cy1 + t*t*ey
                        points.append((px, py))
                    last_ctrl_x, last_ctrl_y = cx1, cy1
                    current_x, current_y = ex, ey
            elif cmd == 'T':
                for (ex, ey) in coords:
                    cx1 = 2 * current_x - last_ctrl_x
                    cy1 = 2 * current_y - last_ctrl_y
                    steps = steps_per_segment * 4
                    for s in range(1, steps + 1):
                        t = s / steps
                        u = 1 - t
                        px = u*u*current_x + 2*u*t*cx1 + t*t*ex
                        py = u*u*current_y + 2*u*t*cy1 + t*t*ey
                        points.append((px, py))
                    last_ctrl_x, last_ctrl_y = cx1, cy1
                    current_x, current_y = ex, ey
            elif cmd == 'C':
                for i in range(0, len(coords), 3):
                    c1x, c1y = coords[i]
                    c2x, c2y = coords[i+1]
                    ex, ey = coords[i+2]
                    steps = steps_per_segment * 6
                    for s in range(1, steps + 1):
                        t = s / steps
                        u = 1 - t
                        uu, tt = u*u, t*t
                        uuu, ttt = uu*u, tt*t
                        px = uuu*current_x + 3*uu*t*c1x + 3*u*tt*c2x + ttt*ex
                        py = uuu*current_y + 3*uu*t*c1y + 3*u*tt*c2y + ttt*ey
                        points.append((px, py))
                    last_ctrl_x, last_ctrl_y = c2x, c2y
                    current_x, current_y = ex, ey
            elif cmd == 'S':
                for i in range(0, len(coords), 2):
                    c2x, c2y = coords[i]
                    if i + 1 < len(coords):
                        ex, ey = coords[i+1]
                    else:
                        ex, ey = c2x, c2y
                    c1x = 2 * current_x - last_ctrl_x
                    c1y = 2 * current_y - last_ctrl_y
                    steps = steps_per_segment * 6
                    for s in range(1, steps + 1):
                        t = s / steps
                        u = 1 - t
                        uu, tt = u*u, t*t
                        uuu, ttt = uu*u, tt*t
                        px = uuu*current_x + 3*uu*t*c1x + 3*u*tt*c2x + ttt*ex
                        py = uuu*current_y + 3*uu*t*c1y + 3*u*tt*c2y + ttt*ey
                        points.append((px, py))
                    last_ctrl_x, last_ctrl_y = c2x, c2y
                    current_x, current_y = ex, ey
            elif cmd == 'Z':
                if (abs(current_x - first_x) > 0.1 or abs(current_y - first_y) > 0.1):
                    points.append((first_x, first_y))
                current_x, current_y = first_x, first_y
        return points

    def _get_stroke_bbox(self, char):
        cache_key = f'_bbox_{char}'
        if cache_key in self._cache:
            return self._cache[cache_key]
        all_paths = self._get_stroke_paths(char)
        if not all_paths:
            return None
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')
        for path_str in all_paths:
            commands = self._parse_svg_path_d(path_str)
            points = self._flatten_path_to_points(commands, steps_per_segment=6)
            for x, y in points:
                if x < min_x: min_x = x
                if x > max_x: max_x = x
                ty = 900 - y
                if ty < min_y: min_y = ty
                if ty > max_y: max_y = ty
        bbox = (min_x, min_y, max_x, max_y)
        self._cache[cache_key] = bbox
        return bbox

    def _transform_points(self, points, grid_size, padding_ratio=0.05, bbox=None):
        if not points:
            return []
        usable = grid_size * (1 - 2 * padding_ratio)
        offset = grid_size * padding_ratio
        if bbox:
            min_x, min_y, max_x, max_y = bbox
            bw = max_x - min_x
            bh = max_y - min_y
            if bw < 1: bw = 1
            if bh < 1: bh = 1
            scale = min(usable / bw, usable / bh)
            cx = (min_x + max_x) / 2
            cy = (min_y + max_y) / 2
            center = grid_size / 2
            result = []
            for (x, y) in points:
                ty = 900 - y
                sx = (x - cx) * scale + center
                sy = (ty - cy) * scale + center
                result.append((sx, sy))
        else:
            scale = usable / 1024.0
            result = []
            for (x, y) in points:
                sx = x * scale + offset
                sy = (900 - y) * scale + offset
                result.append((sx, sy))
        return result

    def _get_kaiti_font(self, size):
        cache_key = f"kaiti_{size}"
        if cache_key in self._font_cache:
            return self._font_cache[cache_key]
        font_candidates = [
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'fonts', 'kaiti_gb2312.ttf'),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'fonts', 'simkai.ttf'),
            'C:/Windows/Fonts/simkai.ttf',
            'C:/Windows/Fonts/simhei.ttf',
            'C:/Windows/Fonts/msyh.ttc',
        ]
        font = None
        for fp in font_candidates:
            if os.path.exists(fp):
                try:
                    font = ImageFont.truetype(fp, size)
                    break
                except Exception:
                    continue
        if font is None:
            font = ImageFont.load_default()
        self._font_cache[cache_key] = font
        return font

    def render_font_char(self, char, grid_size, color=(0, 0, 0), alpha=255):
        font_size = int(grid_size * 0.75)
        font = self._get_kaiti_font(font_size)
        img = Image.new('RGBA', (grid_size, grid_size), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        bbox = draw.textbbox((0, 0), char, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (grid_size - tw) / 2 - bbox[0]
        y = (grid_size - th) / 2 - bbox[1] + grid_size * 0.02
        color_rgba = (*color, alpha)
        draw.text((x, y), char, font=font, fill=color_rgba)
        return img

    def render_strokes_to_image(self, char, grid_size=200, up_to_stroke=-1,
                                 stroke_color=(45, 50, 55), stroke_width_ratio=0.038, mode='svg'):
        all_paths = self._get_stroke_paths(char)
        if not all_paths or mode == 'font':
            return self._render_font_mode(char, grid_size, up_to_stroke, stroke_color)
        if up_to_stroke < 0:
            up_to_stroke = len(all_paths)
        cache_key = (char, grid_size, up_to_stroke, stroke_color)
        if cache_key in self._cache:
            return self._cache[cache_key].copy()
        img = Image.new('RGBA', (grid_size, grid_size), (255, 255, 255, 0))
        color_with_alpha = (*stroke_color, 235)
        bbox = self._get_stroke_bbox(char)
        for idx in range(min(up_to_stroke, len(all_paths))):
            path_str = all_paths[idx]
            commands = self._parse_svg_path_d(path_str)
            raw_points = self._flatten_path_to_points(commands, steps_per_segment=6)
            if raw_points:
                points = self._transform_points(raw_points, grid_size, bbox=bbox)
                if len(points) >= 3:
                    draw = ImageDraw.Draw(img)
                    draw.polygon(points, fill=color_with_alpha)
        self._cache[cache_key] = img.copy()
        return img

    def render_all_steps(self, char, grid_size, stroke_color=(180, 180, 180), ref_bbox=None):
        all_paths = self._get_stroke_paths(char)
        if not all_paths:
            return []
        cache_key = ('all_steps', char, grid_size, stroke_color, ref_bbox is not None)
        if cache_key in self._cache:
            return self._cache[cache_key]
        bbox = ref_bbox if ref_bbox else self._get_stroke_bbox(char)
        color_with_alpha = (*stroke_color, 235)
        all_polygons = []
        for path_str in all_paths:
            commands = self._parse_svg_path_d(path_str)
            raw_points = self._flatten_path_to_points(commands, steps_per_segment=6)
            if raw_points:
                points = self._transform_points(raw_points, grid_size, bbox=bbox)
                if len(points) >= 3:
                    all_polygons.append(points)
                else:
                    all_polygons.append(None)
            else:
                all_polygons.append(None)
        images = []
        img = Image.new('RGBA', (grid_size, grid_size), (255, 255, 255, 0))
        for poly in all_polygons:
            if poly:
                draw = ImageDraw.Draw(img)
                draw.polygon(poly, fill=color_with_alpha)
            images.append(img.copy())
        self._cache[cache_key] = images
        return images

    def _render_font_mode(self, char, grid_size, up_to_stroke, stroke_color):
        alpha = 200
        return self.render_font_char(char, grid_size, color=stroke_color, alpha=alpha)

    def render_full_sequence_for_pdf(self, char, grid_size=200, cols=6,
                                      first_char_color=(20, 20, 20),
                                      stroke_color=(45, 50, 55),
                                      stroke_width_ratio=0.035):
        all_paths = self._get_stroke_paths(char)
        if not all_paths:
            images = []
            ref = self.render_font_char(char, grid_size, color=first_char_color, alpha=255)
            images.append(ref)
            for _ in range(1, cols):
                light = self.render_font_char(char, grid_size, color=(180, 180, 185), alpha=160)
                images.append(light)
            return images[:cols]
        total_strokes = len(all_paths)
        images = []
        ref_img = self.render_font_char(char, grid_size, color=first_char_color, alpha=255)
        images.append(ref_img)
        max_steps = cols - 2
        for step in range(1, min(max_steps, total_strokes) + 1):
            step_img = self.render_strokes_to_image(
                char, grid_size, up_to_stroke=step,
                stroke_color=stroke_color, stroke_width_ratio=stroke_width_ratio
            )
            images.append(step_img)
        full_img = self.render_strokes_to_image(
            char, grid_size, up_to_stroke=-1,
            stroke_color=stroke_color, stroke_width_ratio=stroke_width_ratio
        )
        images.append(full_img)
        while len(images) < cols:
            empty = Image.new('RGBA', (grid_size, grid_size), (255, 255, 255, 0))
            images.append(empty)
        return images[:cols]

    def image_to_bytes(self, img, format='PNG'):
        buf = io.BytesIO()
        img.save(buf, format=format)
        buf.seek(0)
        return buf


def create_stroke_renderer(data_path=None):
    return StrokeRenderer(data_path=data_path)


STROKE_RENDERER_AVAILABLE = True


# ================= 汉字笔顺数据 =================
STROKE_DATA = {
    '一': ['一'],
    '二': ['一', '一'],
    '三': ['一', '一', '一'],
    '十': ['一', '丨'],
    '人': ['丿', '㇏'],
    '大': ['一', '丿', '㇏'],
    '小': ['亅', '丶', '丶'],
    '口': ['丨', '𠃍', '一'],
    '日': ['丨', '𠃍', '一', '一'],
    '月': ['丿', '𠃍', '一', '一', '一'],
    '水': ['亅', '㇡', '丿', '㇏'],
    '火': ['丶', '丿', '丿', '㇏'],
    '山': ['丨', '𠃊', '丨'],
    '木': ['一', '丨', '丿', '㇏'],
    '土': ['一', '丨', '一'],
    '王': ['一', '一', '丨', '一'],
    '天': ['一', '一', '丿', '㇏'],
    '中': ['丨', '𠃍', '一', '丨'],
    '国': ['丨', '𠃍', '一', '一', '丨', '一', '一'],
    '上': ['丨', '一', '一'],
    '下': ['一', '丨', '丶'],
    '左': ['一', '丿', '一', '𠃌'],
    '右': ['一', '丿', '𠃌', '一'],
    '前': ['丶', '丿', '一', '一', '丨', '𠃍', '一'],
    '后': ['丿', '一', '𠃍', '一', '一'],
    '东': ['一', '𠃋', '丨', '丶'],
    '西': ['一', '丨', '𠃍', '一', '丿', '乚'],
    '南': ['一', '丨', '𠃍', '一', '丨', '一', '丶'],
    '北': ['丨', '𠃍', '一', '一', '丿', '乚'],
    '手': ['丿', '一', '一', '亅'],
    '足': ['丨', '𠃍', '一', '丨', '一', '丿', '㇏'],
    '耳': ['一', '丨', '丨', '一', '一', '一'],
    '目': ['丨', '𠃍', '一', '一', '一'],
    '牙': ['一', '丨', '丿', '乚'],
    '心': ['丶', '㇃', '丶'],
    '面': ['一', '丿', '丨', '𠃍', '一', '一', '一'],
    '发': ['𠄌', '丿', '㇏'],
    '毛': ['丿', '一', '乚'],
    '皮': ['𠃇', '丿', '㇏'],
    '肉': ['丨', '𠃍', '一', '丿', '㇏'],
    '骨': ['丨', '𠃍', '一', '丨', '一', '丿', '乚'],
    '血': ['丿', '丨', '𠃍', '一', '一'],
    '风': ['丿', '㇐', '丶', '㇏'],
    '雨': ['一', '丨', '𠃍', '一', '丶', '丶', '丶', '丶'],
    '雪': ['一', '丨', '𠃍', '一', '丶', '丶', '一', '一'],
    '电': ['丨', '𠃍', '一', '乚'],
    '云': ['一', '一', '𠃍', '一'],
    '瓜': ['丿', '𠃍', '丶', '㇏'],
    '豆': ['一', '丨', '𠃍', '一', '丶'],
    '米': ['丶', '丿', '一', '丨', '丶', '丿'],
    '麦': ['一', '丨', '丿', '㇏', '丶', '丶'],
    '石': ['一', '丿', '一', '𠃍', '一'],
    '田': ['丨', '𠃍', '一', '丨', '一'],
    '金': ['丿', '一', '一', '一', '丨'],
    '玉': ['一', '一', '丨', '丶'],
    '立': ['丶', '一', '丶', '丶', '丶'],
    '世': ['一', '𠃌', '丨', '一', '一'],
    '本': ['一', '丨', '丿', '㇏', '一'],
    '末': ['一', '一', '丨', '丿', '㇏'],
    '未': ['一', '一', '丨', '丿', '㇏'],
    '牛': ['丿', '一', '一', '丨'],
    '羊': ['丶', '丿', '一', '一', '丨'],
    '马': ['㇉', '一', '㇏'],
    '鸟': ['丿', '㇉', '丶', '一', '㇏'],
    '鱼': ['丿', '𠃍', '一', '一', '一', '一'],
    '虫': ['丨', '𠃍', '一', '丶', '㇏'],
    '贝': ['丨', '𠃍', '一', '丶'],
    '见': ['丨', '𠃍', '一', '丿', '乚'],
    '角': ['丿', '乚', '丿', '一', '𠃌'],
    '力': ['𠄌', '丿'],
    '刀': ['𠃌', '丿'],
    '又': ['㇏', '丿'],
    '女': ['𡿨', '丿', '一'],
    '儿': ['丿', '乚'],
    '曰': ['丨', '𠃍', '一', '一'],
    '白': ['丿', '丨', '𠃍', '一', '一'],
    '由': ['丨', '𠃍', '一', '丨', '一'],
    '甲': ['丨', '𠃍', '一', '一', '丨'],
    '申': ['丨', '𠃍', '一', '丨', '一'],
    '自': ['丿', '丨', '𠃍', '一', '一', '一'],
    '舌': ['丿', '一', '丨', '一', '一'],
    '身': ['丿', '一', '丨', '𠃍', '一', '一', '㇏'],
    '衣': ['丶', '一', '一', '丿', '𠃍', '一', '丿', '㇏'],
    '示': ['丶', '一', '一', '丿', '丶'],
    '糸': ['𠃌', '𠃌', '𠃌', '丶'],
    '辛': ['丶', '一', '丨', '一', '一', '一'],
    '青': ['一', '一', '丨', '𠃍', '一', '一', '一'],
    '黑': ['丨', '𠃍', '一', '一', '一', '丶', '丶', '丿', '乚'],
    '黄': ['一', '丨', '𠃍', '一', '一', '丨', '一', '丶', '㇏'],
    '赤': ['一', '丨', '一', '丿', '㇏', '丶'],
    '我': ['丿', '一', '亅', '㇂', '丿', '㇏'],
    '你': ['丿', '丨', '丿', '丶', '亅', '丶'],
    '他': ['丿', '丨', '乚'],
    '个': ['丿', '㇏'],
    '出': ['𠃊', '𠃊', '丨'],
    '入': ['丿', '㇏'],
    '升': ['丿', '一', '丿', '一'],
    '开': ['一', '一', '丿', '一'],
    '井': ['一', '一', '丿', '丨'],
    '夫': ['一', '一', '丿', '㇏'],
    '元': ['一', '一', '丿', '乚'],
    '专': ['一', '𠃍', '丶', '㇔'],
    '内': ['𠃍', '丿', '丶'],
    '长': ['丿', '一', '𠃍', '㇏'],
    '来': ['一', '丶', '丿', '一', '丨', '丿', '㇏'],
    '不': ['一', '丿', '丶'],
    '工': ['一', '丨', '一'],
    '业': ['一', '一', '一', '亅'],
    '生': ['丿', '一', '一', '一', '丨'],
    '飞': ['乙', '丶', '丶'],
    '竹': ['丿', '一', '丿', '一'],
    '犬': ['一', '丿', '丶'],
    '豕': ['一', '丿', '𠃍', '一', '一'],
    '兔': ['𠃍', '一', '丿', '㇏'],
    '龙': ['一', '丿', '乚', '丶', '丿', '丶'],
    '龟': ['𠃍', '一', '一', '乚']}

# ================= 初始化中文字体 =================
def _register_fonts():
    fonts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'fonts')
    os.makedirs(fonts_dir, exist_ok=True)

    for path in ['simkai.ttf', r'C:\Windows\Fonts\simkai.ttf']:
        try:
            pdfmetrics.registerFont(TTFont('KaiTi', path))
            break
        except Exception:
            pass

    for path in ['simsun.ttc', r'C:\Windows\Fonts\simsun.ttc']:
        try:
            pdfmetrics.registerFont(TTFont('SimSun', path))
            break
        except Exception:
            pass

    # 注册仿宋字体
    for path in ['simfang.ttf', r'C:\Windows\Fonts\simfang.ttf']:
        try:
            pdfmetrics.registerFont(TTFont('仿宋', path))
            break
        except Exception:
            pass

    # 注册 Arial（支持Ü/ü等带变音符号的字符）
    for path in [r'C:\Windows\Fonts\arial.ttf']:
        try:
            pdfmetrics.registerFont(TTFont('Arial', path))
            break
        except Exception:
            pass

    # 显式注册拼音自定义字体
    for pn in ['pinyin-me']:
        pn_path = os.path.join(fonts_dir, pn + '.ttf')
        if os.path.exists(pn_path):
            try:
                pdfmetrics.registerFont(TTFont(pn, pn_path))
            except Exception:
                pass

    for filename in os.listdir(fonts_dir):
        if filename.lower().endswith('.ttf') or filename.lower().endswith('.ttc') or filename.lower().endswith('.otf'):
            font_path = os.path.join(fonts_dir, filename)
            font_name = os.path.splitext(filename)[0]
            try:
                if filename.lower().endswith('.ttc'):
                    pdfmetrics.registerFont(TTFont(font_name, font_path, subfontIndex=0))
                else:
                    pdfmetrics.registerFont(TTFont(font_name, font_path))
            except Exception:
                pass

_register_fonts()

def get_registered_fonts():
    return list(pdfmetrics.getRegisteredFontNames())

def get_fonts_in_fonts_folder():
    """获取fonts文件夹中的所有字体文件"""
    fonts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'fonts')
    os.makedirs(fonts_dir, exist_ok=True)
    
    fonts = []
    for filename in os.listdir(fonts_dir):
        if filename.lower().endswith(('.ttf', '.ttc', '.otf')):
            font_name = os.path.splitext(filename)[0]
            font_path = os.path.join(fonts_dir, filename)
            fonts.append({'name': font_name, 'path': font_path})
    
    return fonts

def load_fonts_from_folder():
    """重新加载fonts文件夹中的所有字体"""
    fonts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'fonts')
    os.makedirs(fonts_dir, exist_ok=True)
    
    loaded_fonts = []
    failed_fonts = []
    
    for filename in os.listdir(fonts_dir):
        if filename.lower().endswith(('.ttf', '.ttc', '.otf')):
            font_path = os.path.join(fonts_dir, filename)
            font_name = os.path.splitext(filename)[0]
            
            if font_name in pdfmetrics.getRegisteredFontNames():
                loaded_fonts.append(font_name)
                continue
            
            try:
                pdfmetrics.registerFont(TTFont(font_name, font_path))
                loaded_fonts.append(font_name)
            except Exception as e:
                error_msg = str(e)
                if "Can't open" in error_msg:
                    error_msg = "无法打开文件"
                elif "Not a TrueType" in error_msg or "not a valid" in error_msg.lower():
                    error_msg = "不是有效的字体格式"
                elif "Permission" in error_msg:
                    error_msg = "权限不足"
                else:
                    error_msg = "加载失败"
                failed_fonts.append({'name': font_name, 'error': error_msg})
    
    return {'loaded': loaded_fonts, 'failed': failed_fonts}

def register_builtin_fonts():
    """注册内置字体（jingxiaopeng-行书、tianyingzhang-行楷、ouyangxun-大楷）"""
    fonts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'fonts')
    builtin = [
        ("jingxiaopeng", "jingxiaopeng.ttf"),
        ("tianyingzhang", "tianyingzhang.ttf"),
        ("ouyangxun", "ouyangxun.ttf"),
    ]
    registered = []
    for font_name, filename in builtin:
        font_path = os.path.join(fonts_dir, filename)
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont(font_name, font_path))
                registered.append(font_name)
            except Exception as e:
                print(f"注册内置字体 '{font_name}' 失败: {e}")
        else:
            print(f"内置字体文件不存在: {font_path}")
    return registered

def add_custom_font(font_path):
    fonts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'fonts')
    os.makedirs(fonts_dir, exist_ok=True)
    
    if not os.path.exists(font_path):
        print(f"字体文件不存在: {font_path}")
        return None
    
    filename = os.path.basename(font_path)
    dest_path = os.path.join(fonts_dir, filename)
    font_name = os.path.splitext(filename)[0]
    
    print(f"字体文件名: {filename}")
    print(f"字体名称: {font_name}")
    print(f"目标路径: {dest_path}")
    
    if font_name in pdfmetrics.getRegisteredFontNames():
        print(f"字体 '{font_name}' 已注册，跳过重复注册")
        return font_name
    
    if not os.path.exists(dest_path):
        import shutil
        try:
            shutil.copy(font_path, dest_path)
            print(f"字体文件已复制到: {dest_path}")
        except Exception as e:
            print(f"复制字体文件失败: {str(e)}")
            return None
    
    try:
        pdfmetrics.registerFont(TTFont(font_name, dest_path))
        print(f"字体 '{font_name}' 注册成功")
        return font_name
    except Exception as e:
        print(f"字体注册失败 ({type(e).__name__}): {str(e)}")
        return None

def _build_poem_rows(processed_words, cols):
    """Build rows from poem items, wrapping body lines that exceed cols."""
    rows = []
    last_poem = -1
    first_body_seen = set()  # track which poems have had their first body row
    for item in processed_words:
        pi = item['poem']
        if pi != last_poem:
            last_poem = pi
        if not rows or rows[-1][0]['poem'] != pi or rows[-1][0]['line'] != item['line']:
            rows.append([item])
        else:
            rows[-1].append(item)
    # Wrap body rows that exceed cols, mark first body row per poem
    wrapped = []
    for row in rows:
        if row is None:
            continue  # skip blank line separators between poems
        pi = row[0]['poem']
        is_first_body = row[0]['type'] == 'body' and pi not in first_body_seen
        # 当 cols <= indent(2) 时，body首行无法缩进，强制 indent=0
        effective_indent = 2 if (is_first_body and cols > 2) else 0
        if row[0]['type'] != 'body' or len(row) <= cols:
            if is_first_body:
                first_body_seen.add(pi)
                for item in row:
                    item['first_body'] = True
            wrapped.append(row)
        else:
            # First body line: first chunk has indent, so fewer chars fit
            first_limit = max(1, cols - effective_indent)
            chunks = []
            pos = 0
            while pos < len(row):
                limit = first_limit if pos == 0 and effective_indent else cols
                limit = max(1, limit)
                chunks.append(row[pos:pos + limit])
                pos += limit
            for ci, chunk in enumerate(chunks):
                if ci == 0 and is_first_body:
                    first_body_seen.add(pi)
                    for item in chunk:
                        item['first_body'] = True
                wrapped.append(chunk)
    return wrapped


class ZitieConfig:
    def __init__(self):
        self.mode = "blank"
        self.chars = ""
        self.char_type = "单字"
        self.grid_type = "田字格"
        self.font_name = "kaiti_gb2312"
        self.font_size = 30
        self.cols = 13
        self.rows = 17
        self.page_count = 1
        self.content_type = "生字"

class ZitieGenerator:
    def __init__(self):
        self.config = ZitieConfig()
    
    def set_config(self, config):
        self.config = config
    
    def generate_blank_template(self, filename):
        grid_type = self.config.grid_type
        page_count = self.config.page_count

        # 根据 grid_type 设置默认的 cols 和 rows
        grid_defaults = {
            "田字格": {"cols": 13, "rows": 17},
            "米字格": {"cols": 13, "rows": 17},
            "方格": {"cols": 13, "rows": 17},
            "四线三格": {"cols": 13, "rows": 17},
            "生字格": {"cols": 13, "rows": 11},
            "数学格": {"cols": 13, "rows": 17},
            "作文本": {"cols": 21, "rows": 25},
            "教案格": {"cols": 1, "rows": 25},
            "大楷本": {"cols": 7, "rows": 4},
            "竖行": {"cols": 20, "rows": 12}
        }

        defaults = grid_defaults.get(grid_type, {"cols": 13, "rows": 17})
        cols = defaults["cols"]
        rows = defaults["rows"]
        
        if grid_type == "大楷本" or grid_type == "竖行":
            c = canvas.Canvas(filename, pagesize=landscape(A4))
        else:
            c = canvas.Canvas(filename, pagesize=A4)
        
        cell_size_mm = 14
        base_cell_width_mm = 14
        row_spacing_mm = 1.5
        min_margin = 10
        
        if grid_type == "四线三格":
            cell_size_mm = 10
            base_cell_width_mm = 14
            row_spacing_mm = 5
            min_margin = 20
        elif grid_type == "生字格":
            cell_size_mm = 23
            rows = 11
            row_spacing_mm = 1
            min_margin = 15
        elif grid_type == "米字格":
            cell_size_mm = 13
            min_margin = 12
        elif grid_type == "方格":
            cell_size_mm = 13
            min_margin = 8
        elif grid_type == "数学格":
            cell_size_mm = 14
            min_margin = 10
        elif grid_type == "作文本":
            cell_size_mm = 8
            base_cell_width_mm = 8
            cols = 21
            rows = 25
            row_spacing_mm = 0
            min_margin = 8
        elif grid_type == "教案格":
            cell_size_mm = 18
            base_cell_width_mm = 60
            rows = 10
            row_spacing_mm = 2
            min_margin = 15
        elif grid_type == "大楷本":
            cell_size_mm = 40
            base_cell_width_mm = 40
            rows = 4
            cols = 7
            row_spacing_mm = 0
            min_margin = 10
        elif grid_type == "竖行":
            cell_size_mm = 10
            base_cell_width_mm = 10
            rows = 12
            cols = 20
            row_spacing_mm = 10
            min_margin = 20
        else:
            cell_size_mm = 13
            min_margin = 8
        
        if grid_type == "大楷本" or grid_type == "竖行":
            page_width_mm = 297
            page_height_mm = 210
        else:
            page_width_mm = 210
            page_height_mm = 297
        
        margin_x_mm = (page_width_mm - cols * base_cell_width_mm) / 2
        total_vertical_mm = rows * (cell_size_mm + row_spacing_mm) - row_spacing_mm
        margin_y_calculated = (page_height_mm - total_vertical_mm) / 2
        margin_y_mm = max(margin_y_calculated, min_margin)
        
        margin_x = margin_x_mm * mm
        margin_y = margin_y_mm * mm
        cell_width = base_cell_width_mm * mm
        cell_size = cell_size_mm * mm
        row_spacing = row_spacing_mm * mm
        
        start_x = margin_x
        if grid_type == "大楷本" or grid_type == "竖行":
            start_y = landscape(A4)[1] - margin_y
        else:
            start_y = A4[1] - margin_y
        
        for page in range(page_count):
            if grid_type == "数学格":
                c.setLineWidth(1.0)
                c.setStrokeColor(black)
                
                page_top = A4[1] - margin_y
                page_bottom = margin_y
                page_left = margin_x
                page_right = A4[0] - margin_x
                
                row_height = 10 * mm
                current_y = page_top - row_height
                last_row_y = page_top - row_height
                while current_y > page_bottom:
                    last_row_y = current_y
                    current_y -= row_height
                
                c.line(page_left, page_top, page_right, page_top)
                c.line(page_left, last_row_y, page_right, last_row_y)
                
                c.line(page_left, page_top, page_left, last_row_y)
                c.line(page_right, page_top, page_right, last_row_y)
                
                center_x = (page_left + page_right) / 2
                gap = 5 * mm
                left_center_x = center_x - gap / 2
                right_center_x = center_x + gap / 2
                c.line(left_center_x, page_top, left_center_x, last_row_y)
                c.line(right_center_x, page_top, right_center_x, last_row_y)
                
                c.setLineWidth(0.5)
                current_y = page_top - row_height
                while current_y > last_row_y:
                    c.line(page_left, current_y, left_center_x, current_y)
                    c.line(right_center_x, current_y, page_right, current_y)
                    current_y -= row_height
                c.setLineWidth(1.0)
                
                c.setFont("SimSun", 10)
                c.drawString(margin_x + 5 * mm, A4[1] - margin_y + 4 * mm, "日期:_____年_____月____日")
                
                c.setFont("SimSun", 9)
                c.drawRightString(A4[0] - margin_x - 5 * mm, margin_y - 6 * mm, f"{page + 1}/{page_count}")
            elif grid_type == "教案格":
                c.setFont("SimSun", 10)
                c.drawString(25 * mm, A4[1] - 20 * mm, "日期:_____年_____月____日")
                
                c.setFont("SimSun", 9)
                c.drawRightString(A4[0] - 25 * mm, 15 * mm, f"{page + 1}/{page_count}")
                
                page_top = A4[1] - 25 * mm
                line_left = 20 * mm
                line_right = A4[0] - 20 * mm
                
                row_height = 10 * mm
                
                c.setLineWidth(1.0)
                c.setStrokeColor(black)
                c.line(line_left, page_top + 2 * mm, line_right, page_top + 2 * mm)
                
                c.setLineWidth(0.5)
                current_y = page_top
                for _ in range(26):
                    c.line(line_left, current_y, line_right, current_y)
                    current_y -= row_height
                
                c.setLineWidth(1.0)
                c.line(line_left, current_y + row_height - 2 * mm, line_right, current_y + row_height - 2 * mm)
            else:
                if grid_type == "作文本":
                    top_margin_2cm = 20 * mm
                    top_start_y = A4[1] - top_margin_2cm
                    
                    c.setFont("SimSun", 10)
                    c.drawString(margin_x + 5 * mm, top_start_y + 5 * mm, "日期:_____年_____月____日")
                    
                    total_width = cols * cell_width
                    total_height = 2 * cell_size + row_spacing
                    
                    c.setLineWidth(1.0)
                    c.rect(start_x, top_start_y - total_height, total_width, total_height)
                    
                    c.setLineWidth(0.3)
                    for col in range(1, cols):
                        x = start_x + col * cell_width
                        c.line(x, top_start_y, x, top_start_y - total_height)
                    c.line(start_x, top_start_y - cell_size, start_x + total_width, top_start_y - cell_size)
                    
                    c.setFont("SimSun", 12)
                    c.setFillColor(black)
                    c.drawCentredString(start_x + cell_width / 2, top_start_y - cell_size / 2 - 4, "正")
                    c.drawCentredString(start_x + cell_width / 2, top_start_y - cell_size - cell_size / 2 - 4, "误")
                    
                    c.setLineWidth(0.3)
                    for col in range(cols):
                        x = start_x + col * cell_width
                        c.rect(x, top_start_y - cell_size, cell_width, cell_size)
                        c.rect(x, top_start_y - 2 * cell_size - row_spacing, cell_width, cell_size)
                    
                    row_gap = 5 * mm
                    remaining_start_y = top_start_y - 2 * (cell_size + row_spacing) - 5 * mm
                    remaining_rows = rows - 7
                    remaining_height = remaining_rows * (cell_size + row_gap)
                    
                    c.setLineWidth(1.0)
                    c.rect(start_x, remaining_start_y - remaining_height, total_width, remaining_height)
                    
                    c.setLineWidth(0.3)
                    for row in range(remaining_rows):
                        current_y = remaining_start_y - row * (cell_size + row_gap)
                        for col in range(cols - 3):
                            x = start_x + col * cell_width
                            c.rect(x, current_y - cell_size, cell_width, cell_size)
                        
                        if row == 0:
                            c.line(start_x, current_y - cell_size, start_x + total_width, current_y - cell_size)
                            
                            c.setFont("SimSun", 12)
                            c.setFillColor(black)
                            pi_x = start_x + (cols - 3) * cell_width + cell_width / 2 + cell_width * 0.5
                            c.drawCentredString(pi_x, current_y - cell_size / 2 - 4, "批")
                            yu_x = start_x + (cols - 3) * cell_width + cell_width / 2 + cell_width * 1.5
                            c.drawCentredString(yu_x, current_y - cell_size / 2 - 4, "语")
                    
                    c.setLineWidth(0.3)
                    right_start_x = start_x + (cols - 3) * cell_width
                    c.line(right_start_x, remaining_start_y, right_start_x, remaining_start_y - remaining_height)
                    
                    c.setFont("SimSun", 9)
                    c.drawRightString(A4[0] - margin_x - 2 * mm, remaining_start_y - remaining_height - 6 * mm, f"{page + 1}/{page_count}")
                elif grid_type == "竖行":
                    # 竖行模板：A4纸横向，绘制竖向的行，古代书籍样式
                    # 页边距固定为2cm（20mm）
                    margin_x = 20 * mm
                    margin_y = 20 * mm

                    # 重新计算起始位置
                    start_x = margin_x
                    start_y = landscape(A4)[1] - margin_y

                    # 计算底部位置（留出下边距）
                    bottom_y = margin_y

                    # 计算每列宽度（让21列正好填满可用宽度）
                    page_width = landscape(A4)[0]
                    available_width = page_width - 2 * margin_x
                    col_width = available_width / cols

                    c.setLineWidth(1.0)
                    c.setStrokeColor(black)

                    # 计算竖行的位置（需要 cols+1 条竖线，包括左右边界）
                    for col in range(cols + 1):
                        x = start_x + col * col_width
                        c.line(x, start_y, x, bottom_y)

                    # 绘制顶部和底部边界线（上下封边）
                    c.line(start_x, start_y, start_x + cols * col_width, start_y)
                    c.line(start_x, bottom_y, start_x + cols * col_width, bottom_y)
                else:
                    for row in range(rows):
                        for col in range(cols):
                            x = start_x + col * cell_width
                            y = start_y - row * (cell_size + row_spacing)
                            self._draw_grid(c, grid_type, x, y, cell_width, cell_size)

                    if grid_type == "生字格":
                        for row in range(rows - 1):
                            dashed_y = start_y - (row + 1) * (cell_size + row_spacing) + row_spacing / 2
                            c.setLineWidth(0.3)
                            c.setStrokeColor(gray)
                            c.setDash([2, 2])
                            c.line(margin_x, dashed_y, A4[0] - margin_x, dashed_y)
                            c.setDash([])
                            c.setLineWidth(1.0)
            
            if grid_type != "作文本" and grid_type != "大楷本" and grid_type != "数学格" and grid_type != "竖行":
                self._draw_page_header(c, margin_x, margin_y)
                self._draw_page_number(c, page + 1, page_count, margin_x, margin_y)
            
            if page < page_count - 1:
                c.showPage()
        
        c.save()
        return True
    
    def generate_zitie(self, filename):
        grid_type = self.config.grid_type
        words = self.config.chars
        font_name = self.config.font_name
        pinyin_font = "pinyin-me"
        hanzi_type = self.config.char_type
        content_type = self.config.content_type

        try:
            if grid_type == "大楷本" or grid_type == "竖行":
                c = canvas.Canvas(filename, pagesize=landscape(A4))
            else:
                c = canvas.Canvas(filename, pagesize=A4)
            
            grid_config = {
                "田字格": {"cols": 13, "rows": 17, "cell_width": 14, "cell_height": 14, "row_spacing": 1, "font_size": 30, "dx": 0, "dy": 0},
                "米字格": {"cols": 13, "rows": 17, "cell_width": 13, "cell_height": 13, "row_spacing": 1, "font_size": 30, "dx": 0, "dy": 0},
                "方格": {"cols": 13, "rows": 17, "cell_width": 13, "cell_height": 13, "row_spacing": 1, "font_size": 30, "dx": 0, "dy": 0},
                "四线三格": {"cols": 13, "rows": 17, "cell_width": 14, "cell_height": 10, "row_spacing": 5, "font_size": 20, "dx": 0, "dy": 6},
                "生字格": {"cols": 13, "rows": 11, "cell_width": 14, "cell_height": 23, "row_spacing": 0, "font_size": 30, "dx": 0, "dy": -14},
                "数学格": {"cols": 13, "rows": 17, "cell_width": 14, "cell_height": 14, "row_spacing": 1, "font_size": 30, "dx": 0, "dy": 0},
                "作文本": {"cols": 21, "rows": 25, "cell_width": 8, "cell_height": 8, "row_spacing": 0, "font_size": 12, "dx": 0, "dy": 0},
                "教案格": {"cols": 1, "rows": 25, "cell_width": 140, "cell_height": 10, "row_spacing": 0, "font_size": 19, "dx": 0, "dy": 0},
                "大楷本": {"cols": 7, "rows": 4, "cell_width": 40, "cell_height": 40, "row_spacing": 0, "font_size": 110, "dx": -3, "dy": -30},
                "竖行": {"cols": 20, "rows": 12, "cell_width": 10, "cell_height": 10, "row_spacing": 10, "font_size": 20, "dx": 0, "dy": 0}
            }
            
            config = grid_config.get(grid_type, grid_config["田字格"])
            cols = config["cols"]
            rows_per_page = config["rows"]
            base_cell_width_mm = config["cell_width"]
            cell_height_mm = config["cell_height"]
            row_spacing_mm = config["row_spacing"]
            font_size = config["font_size"]
            offset = {"dx": config["dx"], "dy": config["dy"]}
            
            is_dakai_mode = grid_type == "大楷本"
            # 大楷模式下，如果用户没有选择自定义字体，则使用默认的ouyangxun字体
            # 如果用户选择了自定义字体，则使用用户选择的字体
            if is_dakai_mode and font_name == "kaiti_gb2312":
                font_name = "ouyangxun"

            enable_empty_line = "+1行" in hanzi_type
            is_huizi_mode = hanzi_type.startswith("灰字") or hanzi_type.startswith("描红")
            is_single_char_mode = content_type == "生字"
            
            def draw_char(c, x, y, char, font_name, font_size, is_huizi):
                if is_huizi:
                    c.saveState()
                    c.setFillColor(HexColor("#CCCCCC"))
                    c.setDash([2, 2])
                    c.setFont(font_name, font_size)
                    c.drawCentredString(x, y, char)
                    c.restoreState()
                else:
                    c.setFont(font_name, font_size)
                    c.setFillColor(black)
                    c.drawCentredString(x, y, char)

            def draw_pinyin_char(c, x, y, char, font_name, font_size, is_huizi):
                """拼音左对齐绘制函数"""
                x_adjusted = x + 1 * mm  # 向右移动1mm
                y_adjusted = y - 0.26 * mm  # 向下移动0.26mm (原来是0.21mm，现在增加0.05mm)
                if is_huizi:
                    c.saveState()
                    c.setFillColor(HexColor("#CCCCCC"))
                    c.setDash([2, 2])
                    c.setFont(font_name, font_size)
                    c.drawString(x_adjusted, y_adjusted, char)
                    c.restoreState()
                else:
                    c.setFont(font_name, font_size)
                    c.setFillColor(black)
                    c.drawString(x_adjusted, y_adjusted, char)
            # Strip "灰字" or "描红" prefix to get base type for mode detection
            base_type = hanzi_type
            if base_type.startswith("灰字"):
                base_type = base_type[2:]
            elif base_type.startswith("描红"):
                base_type = base_type[2:]

            is_stroke_mode = base_type.startswith("笔顺") and not is_dakai_mode
            is_multi_char_mode = base_type.startswith("单字") and not is_dakai_mode
            is_whole_line_mode = base_type.startswith("整行") and not is_dakai_mode
            is_multi_word_mode = base_type.startswith("多词") and not is_dakai_mode
            is_multi_sentence_mode = (base_type.startswith("词语") or content_type == "词语") and not is_dakai_mode
            is_article_mode = (base_type == "文章" or base_type.startswith("文章")) and not is_dakai_mode
            is_poem_mode = content_type in ("诗词", "文言文") and not is_dakai_mode
            is_wenyan_mode = content_type == "文言文"
            is_guoxue_mode = content_type in ("千字文", "道德经", "三字经", "弟子规", "百家姓", "阴符经", "金刚经", "心经")
            is_shuzi_mode = content_type == "数字" and not is_dakai_mode
            is_pinyin_mode = content_type == "拼音" and not is_dakai_mode
            is_dai_pinyin_mode = base_type.startswith("带拼音") and not is_dakai_mode
            
            if is_dakai_mode:
                if is_wenyan_mode:
                    raw_lines = words.replace('\r\n', '\n').split('\n')
                    wenyan_articles = []
                    current_article = []
                    for line in raw_lines:
                        stripped = line.strip()
                        if stripped:
                            current_article.append(stripped)
                        elif current_article:
                            wenyan_articles.append(current_article)
                            current_article = []
                    if current_article:
                        wenyan_articles.append(current_article)

                    processed_words = []
                    for article in wenyan_articles:
                        title = article[0] if len(article) >= 1 else ""
                        author = article[1] if len(article) >= 2 else ""
                        content = '\n'.join(article[2:]) if len(article) >= 3 else ""
                        text = title + ' ' + author + ' ' + content
                        text = text.replace('\n', '').replace('\u3000', '')
                        processed_words.append(text)
                elif base_type.startswith("\u5355\u5b57"):
                    # \u5355\u5b57\u6a21\u5f0f\uff1a\u63d0\u53d6\u6bcf\u4e2a\u5b57\u7b26\uff0c\u4e00\u4e2a\u5b57\u5360\u4e00\u6574\u884c
                    raw = words.replace('\r\n', '\n').replace(' ', '')
                    processed_words = [ch for ch in raw if ch.strip() and ch != '\n']
                elif base_type.startswith("\u6574\u884c"):
                    # \u6574\u884c\u6a21\u5f0f\uff1a\u63d0\u53d6\u6bcf\u4e2a\u5b57\u7b26\uff0c\u4e00\u4e2a\u5b57\u5360\u4e00\u884c\uff08\u53ea\u653e\u7b2c\u4e00\u5217\uff09
                    raw = words.replace('\r\n', '\n').replace(' ', '')
                    processed_words = [ch for ch in raw if ch.strip() and ch != '\n']
                else:
                    # \u6587\u7ae0\u6a21\u5f0f\uff1a\u62fc\u63a5\u6240\u6709\u884c\uff0c\u9010\u5b57\u9010\u683c\u586b\u6ee1
                    raw = words.replace('\r\n', '\n').replace('\n', '').replace(' ', '')
                    processed_words = [ch for ch in raw if ch.strip()]
            elif is_article_mode:
                if is_multi_sentence_mode:
                    # 词语文章模式：按词语分组，然后展平为字符列表
                    lines = words.replace('\r\n', '\n').split('\n')
                    all_chars = []
                    for line in lines:
                        line = line.strip()
                        if line:
                            if '|' in line:
                                word_list = [w.strip() for w in line.split('|') if w.strip()]
                            elif ' ' in line:
                                word_list = [w.strip() for w in line.split(' ') if w.strip()]
                            else:
                                word_list = [line]
                            for word in word_list:
                                for char in word:
                                    if char.strip():
                                        all_chars.append(char)
                    processed_words = all_chars
                elif is_poem_mode:
                    # 诗词文章模式：按空行分隔多首诗，保留行结构（题目/朝代作者/正文）
                    raw_lines = words.replace('\r\n', '\n').split('\n')
                    poems = []
                    current_poem = []
                    for line in raw_lines:
                        stripped = line.strip()
                        if stripped:
                            current_poem.append(stripped)
                        elif current_poem:
                            poems.append(current_poem)
                            current_poem = []
                    if current_poem:
                        poems.append(current_poem)

                    article_items = []
                    for pi, poem_lines in enumerate(poems):
                        for li, line in enumerate(poem_lines):
                            if li == 0:
                                line_type = 'title'
                            elif li == 1:
                                line_type = 'author'
                            else:
                                line_type = 'body'
                            for ch in line:
                                if ch.strip():
                                    article_items.append({
                                        'char': ch, 'poem': pi,
                                        'line': li, 'type': line_type
                                    })
                    processed_words = article_items
                elif is_shuzi_mode:
                    # 数字文章模式：按空格分割，保持数字完整性
                    numbers = words.replace('\r\n', '\n').replace('\n', ' ').split(' ')
                    processed_words = [num.strip() for num in numbers if num.strip()]
                elif is_pinyin_mode:
                    # 拼音文章模式：按空格分割，保持拼音完整性
                    pinyins = words.replace('\r\n', '\n').replace('\n', ' ').split(' ')
                    processed_words = []
                    for p in pinyins:
                        p = p.strip()
                        if p:
                            p = p.replace('v', 'ü').replace('V', 'Ü')
                            processed_words.append(p)
                else:
                    processed_words = list(words.replace('\r\n', '\n').replace('\n', '').replace(' ', ''))
            elif is_stroke_mode:
                stroke_items = []
                chars = words.replace('\r\n', '\n').replace('\n', '').replace(' ', '')

                # 创建笔顺渲染器（统一使用同一个实例）
                stroke_renderer = None
                if STROKE_RENDERER_AVAILABLE:
                    try:
                        stroke_renderer = create_stroke_renderer()
                    except Exception:
                        pass

                for char in chars:
                    if char.strip():
                        # 优先使用 SVG 笔顺渲染器获取笔画数
                        if stroke_renderer and stroke_renderer.has_stroke_data(char):
                            stroke_count = stroke_renderer.get_stroke_count(char)
                            stroke_items.append({
                                'char': char,
                                'strokes': ['svg'] * stroke_count,
                                'use_svg': True,
                                'stroke_count': stroke_count
                            })
                        else:
                            # 回退到旧的笔画部首数据
                            strokes = STROKE_DATA.get(char, [char])
                            stroke_items.append({
                                'char': char,
                                'strokes': strokes,
                                'use_svg': False,
                                'stroke_count': len(strokes)
                            })
                processed_words = stroke_items

                # 统一参考边界框（保持所有字大小一致）
                ref_bbox = None
                if stroke_renderer:
                    all_min_x = all_min_y = float('inf')
                    all_max_x = all_max_y = float('-inf')
                    for item in processed_words:
                        ch = item['char']
                        if item.get('use_svg') and stroke_renderer.has_stroke_data(ch):
                            bb = stroke_renderer._get_stroke_bbox(ch)
                            if bb:
                                min_x, min_y, max_x, max_y = bb
                                if min_x < all_min_x: all_min_x = min_x
                                if min_y < all_min_y: all_min_y = min_y
                                if max_x > all_max_x: all_max_x = max_x
                                if max_y > all_max_y: all_max_y = max_y
                    if all_min_x != float('inf'):
                        ref_bbox = (all_min_x, all_min_y, all_max_x, all_max_y)

                # 展开笔顺溢出的字符: 一个字占多行时拆分成多行
                max_stroke_cols = cols - 1
                expanded_words = []
                for item in processed_words:
                    ch = item['char']
                    use_svg = item.get('use_svg', False)
                    if use_svg and stroke_renderer and stroke_renderer.has_stroke_data(ch):
                        stroke_count = stroke_renderer.get_stroke_count(ch)
                        if stroke_count <= max_stroke_cols:
                            expanded_words.append(item)
                        else:
                            expanded_words.append({**item, '_stroke_start': 0, '_stroke_end': max_stroke_cols})
                            remaining = stroke_count - max_stroke_cols
                            offset_val = max_stroke_cols
                            while remaining > 0:
                                take = min(remaining, max_stroke_cols)
                                expanded_words.append({**item, '_stroke_start': offset_val, '_stroke_end': offset_val + take, '_continuation': True})
                                offset_val += take
                                remaining -= take
                    else:
                        expanded_words.append(item)

            elif is_dai_pinyin_mode:
                from pypinyin import pinyin, Style
                lines = words.replace('\r\n', '\n').split('\n')
                processed_words = []
                if is_poem_mode:
                    # 诗词带拼音：按空行分隔多首诗，保留行结构+拼音
                    raw_lines = words.replace('\r\n', '\n').split('\n')
                    poems = []
                    current_poem = []
                    for line in raw_lines:
                        stripped = line.strip()
                        if stripped:
                            current_poem.append(stripped)
                        elif current_poem:
                            poems.append(current_poem)
                            current_poem = []
                    if current_poem:
                        poems.append(current_poem)
                    for pi, poem_lines in enumerate(poems):
                        for li, line in enumerate(poem_lines):
                            if li == 0:
                                line_type = 'title'
                            elif li == 1:
                                line_type = 'author'
                            else:
                                line_type = 'body'
                            for ch in line:
                                if ch.strip():
                                    py = pinyin(ch, style=Style.TONE)
                                    syllable = py[0][0] if py and py[0] else ''
                                    processed_words.append({
                                        'char': ch, 'poem': pi,
                                        'line': li, 'type': line_type,
                                        'pinyin': syllable
                                    })
                elif is_multi_sentence_mode:
                    # 词语带拼音模式：按词语分组
                    for line in lines:
                        line = line.strip()
                        if line:
                            if '|' in line:
                                word_list = [w.strip() for w in line.split('|') if w.strip()]
                            elif ' ' in line:
                                word_list = [w.strip() for w in line.split(' ') if w.strip()]
                            else:
                                word_list = [line]
                            for word in word_list:
                                word_data = []
                                for char in word:
                                    if char.strip():
                                        py = pinyin(char, style=Style.TONE)
                                        syllable = py[0][0] if py and py[0] else ''
                                        word_data.append({'char': char, 'pinyin': syllable})
                                processed_words.append(word_data)
                else:
                    # 单字带拼音模式：逐字处理
                    for line in lines:
                        line = line.strip()
                        if line:
                            for char in line:
                                if char.strip():
                                    py = pinyin(char, style=Style.TONE)
                                    syllable = py[0][0] if py and py[0] else ''
                                    processed_words.append({'char': char, 'pinyin': syllable})
            elif is_multi_char_mode and is_single_char_mode:
                lines = words.replace('\r\n', '\n').split('\n')
                chars_list = []
                for line in lines:
                    line = line.strip()
                    if line:
                        for char in line:
                            if char.strip():
                                chars_list.append(char)
                processed_words = chars_list
            elif is_multi_word_mode:
                lines = words.replace('\r\n', '\n').split('\n')
                word_list = []
                for line in lines:
                    line = line.strip()
                    if line:
                        if ' ' in line:
                            word_list.extend([w.strip() for w in line.split(' ') if w.strip()])
                        elif '|' in line:
                            word_list.extend([w.strip() for w in line.split('|') if w.strip()])
                        elif '，' in line:
                            word_list.extend([w.strip() for w in line.split('，') if w.strip()])
                        else:
                            word_list.append(line)
                processed_words = word_list
            elif is_multi_sentence_mode:
                lines = words.replace('\r\n', '\n').split('\n')
                sentence_list = []
                for line in lines:
                    line = line.strip()
                    if line:
                        if '|' in line:
                            sentence_list.extend([s.strip() for s in line.split('|') if s.strip()])
                        elif ' ' in line:
                            sentence_list.extend([w.strip() for w in line.split(' ') if w.strip()])
                        else:
                            sentence_list.append(line)
                processed_words = sentence_list
            elif is_poem_mode:
                lines = words.replace('\r\n', '\n').split('\n')
                processed_words = [line.strip() for line in lines if line.strip()]
            elif is_wenyan_mode or is_guoxue_mode or (content_type == "古书"):
                # 保持编辑框中的原始格式，按空行分隔多个文言文/国学内容/古书内容
                raw_lines = words.replace('\r\n', '\n').split('\n')
                # 将多个文章分割开
                articles = []
                current_article = []
                for line in raw_lines:
                    stripped = line.strip()
                    if stripped:
                        current_article.append(stripped)
                    elif current_article:
                        # 遇到空行，且当前文章有内容，则保存并开始新文章
                        articles.append(current_article)
                        current_article = []
                # 处理最后一个文章（如果最后没有空行分隔）
                if current_article:
                    articles.append(current_article)

                # processed_words用于后续处理，将每个文章格式化为：标题|作者|内容
                processed_words = []
                for article in articles:
                    if len(article) >= 1:
                        title = article[0]  # 第一行：标题
                    else:
                        title = ""
                    if len(article) >= 2:
                        author = article[1]  # 第二行：作者
                    else:
                        author = ""
                    if len(article) >= 3:
                        content = '\n'.join(article[2:])  # 第三行开始：内容
                    else:
                        content = ""
                    # 使用|分隔符来标识一个文章的结束，新的|标识下一个文章开始
                    processed_words.append({'title': title, 'author': author, 'content': content})
            elif is_shuzi_mode:
                # 数字：以空格分割，每行一个数字
                numbers = words.replace('\r\n', '\n').replace('\n', ' ').split(' ')
                processed_words = [num.strip() for num in numbers if num.strip()]
            elif is_pinyin_mode:
                # 拼音：以空格分割，每行一个拼音，v替换为ü
                pinyins = words.replace('\r\n', '\n').replace('\n', ' ').split(' ')
                processed_words = []
                for p in pinyins:
                    p = p.strip()
                    if p:
                        # v -> ü, V -> Ü
                        p = p.replace('v', 'ü').replace('V', 'Ü')
                        processed_words.append(p)
            else:
                lines = words.replace('\r\n', '\n').split('\n')
                processed_words = [line.strip() for line in lines if line.strip()]

            if is_whole_line_mode and not is_multi_sentence_mode and not is_shuzi_mode and not is_pinyin_mode:
                char_list = []
                for line in processed_words:
                    for ch in line:
                        if ch.strip():
                            char_list.append(ch)
                processed_words = char_list
            
            if is_article_mode:
                if is_poem_mode and processed_words and isinstance(processed_words[0], dict):
                    if grid_type == "教案格":
                        # 教案格+诗词：按行渲染文本，与文言文教案格相同的分页逻辑
                        chars_per_line_for_poem = 25
                        total_lines = 0
                        poem_lines = {}
                        for item in processed_words:
                            key = (item['poem'], item['line'])
                            if key not in poem_lines:
                                poem_lines[key] = []
                            poem_lines[key].append(item['char'])
                        for key in sorted(poem_lines.keys()):
                            line_text = ''.join(poem_lines[key])
                            li = key[1]
                            if li >= 2:
                                line_text = '\u3000\u3000' + line_text
                            total_lines += (len(line_text) + chars_per_line_for_poem - 1) // chars_per_line_for_poem
                        if enable_empty_line:
                            total_pages = max(1, (total_lines + rows_per_page // 2 - 1) // (rows_per_page // 2))
                        else:
                            total_pages = max(1, (total_lines + rows_per_page - 1) // rows_per_page)
                    else:
                        # 诗词文章：按行逐项分页，题目/作者不分离
                        rows = _build_poem_rows(processed_words, cols)

                        total_pages = 1
                        current_row = 0
                        i = 0
                        while i < len(rows):
                            row = rows[i]
                            if row is None:
                                current_row += 1
                                i += 1
                                continue
                            is_title = row[0]['type'] == 'title'
                            is_author = row[0]['type'] == 'author'
                            if is_title and current_row + 1 >= rows_per_page:
                                total_pages += 1
                                current_row = 0
                            elif is_author and current_row >= rows_per_page:
                                total_pages += 1
                                current_row = 0
                            current_row += 1
                            i += 1
                else:
                    chars_per_page = cols * rows_per_page
                    total_chars = len(processed_words)
                    if enable_empty_line:
                        total_pages = (total_chars * 2 + rows_per_page - 1) // rows_per_page
                    else:
                        total_pages = (total_chars + chars_per_page - 1) // chars_per_page
            elif is_dai_pinyin_mode:
                if is_poem_mode and processed_words and isinstance(processed_words[0], dict) and 'poem' in processed_words[0]:
                    if grid_type == "教案格":
                        # 教案格+诗词带拼音：与教案格+诗词文章相同的分页逻辑
                        chars_per_line_for_poem = 25
                        total_lines = 0
                        poem_lines = {}
                        for item in processed_words:
                            key = (item.get('poem', 0), item.get('line', 0))
                            if key not in poem_lines:
                                poem_lines[key] = []
                            poem_lines[key].append(item.get('char', ''))
                        for key in sorted(poem_lines.keys()):
                            line_text = ''.join(poem_lines[key])
                            li = key[1]
                            if li >= 2:
                                line_text = '\u3000\u3000' + line_text
                            total_lines += (len(line_text) + chars_per_line_for_poem - 1) // chars_per_line_for_poem
                        if enable_empty_line:
                            total_pages = max(1, (total_lines + rows_per_page // 2 - 1) // (rows_per_page // 2))
                        else:
                            total_pages = max(1, (total_lines + rows_per_page - 1) // rows_per_page)
                    else:
                        # 诗词带拼音：按行分页，与诗词文章相同的分页逻辑
                        rows = _build_poem_rows(processed_words, cols)
                        total_pages = 1
                        current_row = 0
                        i = 0
                        while i < len(rows):
                            row = rows[i]
                            if row is None:
                                current_row += 1
                                i += 1
                                continue
                            is_title = row[0]['type'] == 'title'
                            is_author = row[0]['type'] == 'author'
                            if is_title and current_row + 1 >= rows_per_page:
                                total_pages += 1
                                current_row = 0
                            elif is_author and current_row >= rows_per_page:
                                total_pages += 1
                                current_row = 0
                            current_row += 1
                            i += 1
                else:
                    total_chars = len(processed_words)
                    if enable_empty_line:
                        total_pages = (total_chars * 2 + rows_per_page - 1) // rows_per_page
                    else:
                        total_pages = (total_chars + rows_per_page - 1) // rows_per_page
            elif is_multi_char_mode and is_single_char_mode:
                if enable_empty_line:
                    total_pages = (len(processed_words) * 2 + rows_per_page - 1) // rows_per_page
                else:
                    total_pages = (len(processed_words) + rows_per_page - 1) // rows_per_page
            elif is_whole_line_mode:
                if enable_empty_line:
                    total_pages = (len(processed_words) * 2 + rows_per_page - 1) // rows_per_page
                else:
                    total_pages = (len(processed_words) + rows_per_page - 1) // rows_per_page
            elif is_stroke_mode:
                # 新版SVG笔顺模式: 每个字占1行(一行内cols个格子展示笔顺步骤)
                # 使用 expanded_words 计算，因为溢出字符会拆成多行
                total_rows = len(expanded_words)
                if enable_empty_line:
                    total_rows *= 2  # 每字后面空一行
                total_pages = max(1, (total_rows + rows_per_page - 1) // rows_per_page)
            elif is_wenyan_mode or is_guoxue_mode:
                if is_dakai_mode:
                    total_chars = 0
                    for item in processed_words:
                        total_chars += len(item)
                    total_pages = max(1, (total_chars + cols * rows_per_page - 1) // (cols * rows_per_page))
                else:
                    total_lines = 0
                    chars_per_line_for_wenyan = 25 if grid_type == "教案格" else cols
                    for article in processed_words:
                        if isinstance(article, dict):
                            if article.get('title'):
                                title = article['title']
                                total_lines += (len(title) + chars_per_line_for_wenyan - 1) // chars_per_line_for_wenyan
                            if article.get('author'):
                                author = article['author']
                                total_lines += (len(author) + chars_per_line_for_wenyan - 1) // chars_per_line_for_wenyan
                            if article.get('content'):
                                content = article['content']
                                content_lines = content.split('\n') if '\n' in content else [content]
                                for line in content_lines:
                                    total_lines += (len(line) + chars_per_line_for_wenyan - 1) // chars_per_line_for_wenyan
                        else:
                            text = article
                            total_lines += (len(text) + chars_per_line_for_wenyan - 1) // chars_per_line_for_wenyan
                    if enable_empty_line:
                        total_pages = max(1, (total_lines + rows_per_page // 2 - 1) // (rows_per_page // 2))
                    else:
                        total_pages = max(1, (total_lines + rows_per_page - 1) // rows_per_page)
            elif is_dakai_mode and base_type.startswith("单字"):
                # 单字模式：一个字占一行（+1行时每字后空一行）
                total_chars = len(processed_words)
                total_rows = total_chars * 2 if enable_empty_line else total_chars
                total_pages = max(1, (total_rows + rows_per_page - 1) // rows_per_page)
            elif is_dakai_mode and base_type.startswith("整行"):
                # 整行模式：一个字占一行（+1行时每字后空一行）
                total_chars = len(processed_words)
                total_rows = total_chars * 2 if enable_empty_line else total_chars
                total_pages = max(1, (total_rows + rows_per_page - 1) // rows_per_page)
            elif is_dakai_mode:
                # 文章模式：逐字填满格子
                total_chars = len(processed_words)
                total_pages = max(1, (total_chars + cols * rows_per_page - 1) // (cols * rows_per_page))
            else:
                content_lines = len(processed_words)
                total_lines = content_lines * 2 if enable_empty_line else content_lines
                total_pages = (total_lines + rows_per_page - 1) // rows_per_page
            
            if grid_type == "大楷本" or grid_type == "竖行":
                page_width_mm = 297
                page_height_mm = 210
            else:
                page_width_mm = 210
                page_height_mm = 297
            
            total_vertical_mm = rows_per_page * (cell_height_mm + row_spacing_mm) - row_spacing_mm
            margin_x_mm = (page_width_mm - cols * base_cell_width_mm) / 2
            margin_y_mm = (page_height_mm - total_vertical_mm) / 2
            
            margin_x = margin_x_mm * mm
            margin_y = margin_y_mm * mm
            cell_width = base_cell_width_mm * mm
            cell_height = cell_height_mm * mm
            row_spacing = row_spacing_mm * mm
            start_x = margin_x
            
            if grid_type == "大楷本" or grid_type == "竖行":
                start_y = landscape(A4)[1] - margin_y
            else:
                start_y = A4[1] - margin_y
            
            page_top = start_y
            page_bottom = margin_y
            page_left = margin_x
            
            if grid_type == "大楷本" or grid_type == "竖行":
                page_right = landscape(A4)[0] - margin_x
            else:
                page_right = A4[0] - margin_x

            for current_page in range(1, total_pages + 1):
                if grid_type != "作文本" and grid_type != "大楷本" and grid_type != "数学格" and grid_type != "教案格":
                    self._draw_page_header(c, margin_x, margin_y)
                
                if grid_type == "数学格":
                    c.setLineWidth(1.0)
                    c.setStrokeColor(black)
                    
                    row_height = 10 * mm
                    current_y = page_top - row_height
                    last_row_y = page_top - row_height
                    while current_y > page_bottom:
                        last_row_y = current_y
                        current_y -= row_height
                    
                    c.line(page_left, page_top, page_right, page_top)
                    c.line(page_left, last_row_y, page_right, last_row_y)
                    
                    c.line(page_left, page_top, page_left, last_row_y)
                    c.line(page_right, page_top, page_right, last_row_y)
                    
                    center_x = (page_left + page_right) / 2
                    gap = 5 * mm
                    left_center_x = center_x - gap / 2
                    right_center_x = center_x + gap / 2
                    c.line(left_center_x, page_top, left_center_x, last_row_y)
                    c.line(right_center_x, page_top, right_center_x, last_row_y)
                    
                    c.setLineWidth(0.5)
                    current_y = page_top - row_height
                    while current_y > last_row_y:
                        c.line(page_left, current_y, left_center_x, current_y)
                        c.line(right_center_x, current_y, page_right, current_y)
                        current_y -= row_height
                    c.setLineWidth(1.0)
                elif grid_type == "作文本":
                    top_margin_2cm = 20 * mm
                    top_start_y = A4[1] - top_margin_2cm
                    
                    c.setFont("SimSun", 10)
                    c.drawString(margin_x + 5 * mm, top_start_y + 5 * mm, "日期:_____年_____月____日")
                    
                    total_width = cols * cell_width
                    total_height = 2 * cell_height + row_spacing
                    
                    c.setLineWidth(1.0)
                    c.rect(start_x, top_start_y - total_height, total_width, total_height)
                    
                    c.setLineWidth(0.3)
                    for col in range(1, cols):
                        x = start_x + col * cell_width
                        c.line(x, top_start_y, x, top_start_y - total_height)
                    c.line(start_x, top_start_y - cell_height, start_x + total_width, top_start_y - cell_height)
                    
                    c.setFont("SimSun", 12)
                    c.setFillColor(black)
                    c.drawCentredString(start_x + cell_width / 2, top_start_y - cell_height / 2 - 4, "正")
                    c.drawCentredString(start_x + cell_width / 2, top_start_y - cell_height - cell_height / 2 - 4, "误")
                    
                    c.setLineWidth(0.3)
                    for col in range(cols):
                        x = start_x + col * cell_width
                        c.rect(x, top_start_y - cell_height, cell_width, cell_height)
                        c.rect(x, top_start_y - 2 * cell_height - row_spacing, cell_width, cell_height)
                    
                    row_gap = 5 * mm
                    remaining_start_y = top_start_y - 2 * (cell_height + row_spacing) - 5 * mm
                    remaining_rows = rows_per_page - 7
                    remaining_height = remaining_rows * (cell_height + row_gap)
                    
                    c.setLineWidth(1.0)
                    c.rect(start_x, remaining_start_y - remaining_height, total_width, remaining_height)
                    
                    c.setLineWidth(0.3)
                    for row in range(remaining_rows):
                        current_y = remaining_start_y - row * (cell_height + row_gap)
                        for col in range(cols - 3):
                            x = start_x + col * cell_width
                            c.rect(x, current_y - cell_height, cell_width, cell_height)
                        
                        if row == 0:
                            c.line(start_x, current_y - cell_height, start_x + total_width, current_y - cell_height)
                            
                            c.setFont("SimSun", 12)
                            c.setFillColor(black)
                            pi_x = start_x + (cols - 3) * cell_width + cell_width / 2 + cell_width * 0.5
                            c.drawCentredString(pi_x, current_y - cell_height / 2 - 4, "批")
                            yu_x = start_x + (cols - 3) * cell_width + cell_width / 2 + cell_width * 1.5
                            c.drawCentredString(yu_x, current_y - cell_height / 2 - 4, "语")
                    
                    c.setLineWidth(0.3)
                    right_start_x = start_x + (cols - 3) * cell_width
                    c.line(right_start_x, remaining_start_y, right_start_x, remaining_start_y - remaining_height)
                elif grid_type == "教案格":
                    c.setFont("SimSun", 10)
                    c.drawString(25 * mm, A4[1] - 20 * mm, "日期:_____年_____月____日")
                    
                    page_top = A4[1] - 25 * mm
                    line_left = 20 * mm
                    line_right = A4[0] - 20 * mm
                    
                    row_height = 10 * mm
                    lines_per_page = 24  # 每页24行内容
                    
                    c.setLineWidth(1.0)
                    c.setStrokeColor(black)
                    c.line(line_left, page_top + 2 * mm, line_right, page_top + 2 * mm)
                    
                    c.setLineWidth(0.5)
                    current_y = page_top
                    
                    expanded_lines = []
                    chars_per_line = 25
                    text_width = (line_right - line_left)
                    
                    for item in processed_words:
                        if isinstance(item, dict):
                            if item.get('title'):
                                title = item['title']
                                while len(title) > chars_per_line:
                                    expanded_lines.append({'text': title[:chars_per_line], 'align': 'center'})
                                    title = title[chars_per_line:]
                                if title:
                                    expanded_lines.append({'text': title, 'align': 'center'})
                            if item.get('author'):
                                author = item['author']
                                while len(author) > chars_per_line:
                                    expanded_lines.append({'text': author[:chars_per_line], 'align': 'center'})
                                    author = author[chars_per_line:]
                                if author:
                                    expanded_lines.append({'text': author, 'align': 'center'})
                            if item.get('content'):
                                content = item['content']
                                content_lines = content.split('\n') if '\n' in content else [content]
                                for line in content_lines:
                                    if content_type == '\u9053\u5fb7\u7ecf':
                                        is_chapter_title = line.startswith('\u7b2c') and '\u7ae0' in line[:6]
                                        if is_chapter_title:
                                            while len(line) > chars_per_line:
                                                expanded_lines.append({'text': line[:chars_per_line], 'align': 'left'})
                                                line = line[chars_per_line:]
                                            if line:
                                                expanded_lines.append({'text': line, 'align': 'left'})
                                        else:
                                            line = '\u3000\u3000' + line
                                            while len(line) > chars_per_line:
                                                expanded_lines.append({'text': line[:chars_per_line], 'align': 'left'})
                                                line = line[chars_per_line:]
                                            if line:
                                                expanded_lines.append({'text': line, 'align': 'left'})
                                    elif is_guoxue_mode:
                                        while len(line) > chars_per_line:
                                            expanded_lines.append({'text': line[:chars_per_line], 'align': 'center'})
                                            line = line[chars_per_line:]
                                        if line:
                                            expanded_lines.append({'text': line, 'align': 'center'})
                                    else:
                                        line = '\u3000\u3000' + line
                                        while len(line) > chars_per_line:
                                            expanded_lines.append({'text': line[:chars_per_line], 'align': 'left'})
                                            line = line[chars_per_line:]
                                        if line:
                                            expanded_lines.append({'text': line, 'align': 'left'})
                            # 诗词/文言文文章模式：processed_words 是 {'char':..., 'poem':..., 'line':..., 'type':...} 格式
                            if 'char' in item and 'poem' in item and 'line' in item and 'type' in item:
                                # 先跳过，下面统一处理
                                pass
                        else:
                            text = item
                            while len(text) > chars_per_line:
                                expanded_lines.append({'text': text[:chars_per_line], 'align': 'left'})
                                text = text[chars_per_line:]
                            if text:
                                expanded_lines.append({'text': text, 'align': 'left'})
                    
                    # 诗词/文言文文章模式：将逐字 dict 按诗/行分组拼接为文本行
                    if processed_words and isinstance(processed_words[0], dict) and 'char' in processed_words[0] and 'poem' in processed_words[0] and 'type' in processed_words[0] and not processed_words[0].get('title'):
                        expanded_lines = []  # 重新构建
                        poem_lines = {}  # (poem_idx, line_idx) -> list of chars
                        for item in processed_words:
                            key = (item['poem'], item['line'])
                            if key not in poem_lines:
                                poem_lines[key] = []
                            poem_lines[key].append(item['char'])
                        # 按 poem_idx, line_idx 排序
                        for key in sorted(poem_lines.keys()):
                            line_text = ''.join(poem_lines[key])
                            pi, li = key
                            # 所有行都左对齐：题目、朝代作者、正文（无缩进）
                            align = 'left'
                            while len(line_text) > chars_per_line:
                                expanded_lines.append({'text': line_text[:chars_per_line], 'align': align})
                                line_text = line_text[chars_per_line:]
                            if line_text:
                                expanded_lines.append({'text': line_text, 'align': align})
                    
                    for row_idx in range(rows_per_page):
                        c.line(line_left, current_y, line_right, current_y)
                        
                        if enable_empty_line:
                            content_lines_per_page = lines_per_page // 2
                            page_start_idx = (current_page - 1) * content_lines_per_page
                            is_content_line = (row_idx % 2) == 0
                            content_row_idx = row_idx // 2
                            actual_idx = page_start_idx + content_row_idx
                        else:
                            page_start_idx = (current_page - 1) * lines_per_page
                            is_content_line = True
                            actual_idx = page_start_idx + row_idx
                        
                        if is_content_line and actual_idx < len(expanded_lines) and row_idx < lines_per_page:
                            current_item = expanded_lines[actual_idx]
                            text = current_item['text']
                            align = current_item['align']
                            y_pos = current_y - row_height / 2 - 4.0 * mm

                            if align == 'center':
                                text_width_actual = c.stringWidth(text, font_name, font_size)
                                x_pos = line_left + (text_width - text_width_actual) / 2 + 5 * mm
                            else:
                                x_pos = line_left + 1 * mm

                            # 灰字模式：使用灰色字体
                            if is_huizi_mode:
                                c.saveState()
                                c.setFillColor(HexColor("#CCCCCC"))
                                c.setDash([2, 2])
                                c.setFont(font_name, font_size)
                                c.drawString(x_pos, y_pos, text)
                                c.restoreState()
                            else:
                                # 正常模式：使用黑色字体
                                c.setFont(font_name, font_size)
                                c.setFillColor(black)
                                c.drawString(x_pos, y_pos, text)
                        
                        current_y -= row_height
                    
                    c.setLineWidth(1.0)
                    c.line(line_left, current_y + row_height - 2 * mm, line_right, current_y + row_height - 2 * mm)
                elif (hanzi_type == "文章" or hanzi_type == "灰字文章") and not is_dakai_mode:
                    # 古书+竖行+文章模式：从右上到下的古籍排版（完全独立的渲染逻辑）
                    # 检查是否为古书模式（content_type 可能是 "古书" 或具体的著作名称）
                    is_gushu_content = content_type in ["古书", "千字文", "道德经", "三字经", "弟子规", "百家姓", "阴符经", "金刚经", "心经"]
                    if grid_type == "竖行" and is_gushu_content:
                        # ========== 古书+竖行+文章专用配置 ==========
                        total_pages_from_config = total_pages  # 保存原始页数
                        # 页边距：左右2cm，上下1.5cm
                        gushu_margin_x = 20 * mm
                        gushu_margin_y = 15 * mm  # 上下边距1.5cm

                        # 计算起始位置
                        gushu_start_x = gushu_margin_x
                        gushu_start_y = landscape(A4)[1] - gushu_margin_y

                        # 计算底部位置（留出下边距）
                        gushu_bottom_y = gushu_margin_y

                        # 计算每列宽度（让20列正好填满可用宽度）
                        gushu_page_width = landscape(A4)[0]
                        gushu_available_width = gushu_page_width - 2 * gushu_margin_x
                        gushu_col_width = gushu_available_width / cols

                        # 古书专用字体大小和位置调整
                        gushu_font_size = 33  # 古书专用字体大小
                        gushu_dx = 0  # 古书专用水平偏移
                        gushu_dy = -18  # 古书专用垂直偏移（向上移动2mm）

                        c.setLineWidth(1.0)
                        c.setStrokeColor(black)

                        # 绘制竖线（从右到左，共21条竖线）
                        for col in range(cols + 1):
                            x = gushu_start_x + col * gushu_col_width
                            c.line(x, gushu_start_y, x, gushu_bottom_y)

                        # 绘制顶部和底部边界线（上下封边）
                        c.line(gushu_start_x, gushu_start_y, gushu_start_x + cols * gushu_col_width, gushu_start_y)
                        c.line(gushu_start_x, gushu_bottom_y, gushu_start_x + cols * gushu_col_width, gushu_bottom_y)

                        # 渲染内容（从右上到下）
                        # 古书专用行高（字高 + 字间距）
                        gushu_cell_height = 10 * mm  # 字高
                        gushu_row_spacing = 1 * mm   # 字间距（1mm）
                        gushu_rows_per_page = 16  # 每列16个字

                        # 处理古书内容（直接按照编辑框中的换行来处理）
                        # 按照编辑框中的原始换行来处理，换行会导致换列
                        raw_lines = words.replace('\r\n', '\n').split('\n')

                        # 去掉标点符号
                        punctuation_pattern = r'[，。！？、；：""''（）《》【】　、。「」『』【】〔〕〖〗〘〙〚〛〜〝〞〟〠〡〢〣〤〥〦〧〨〩〪〭〮〯〫〬〰〱〲〳〴〵〶〷〸〹〺〻〼〽〾〿぀ぁあぃいぅうぇえぉおかがきぎくぐけげこごさざしじすずせぜそぞただちぢっつづてでとどなにぬねのはばぱひびぴふぶぷへべぺほぼぽまみむめもゃやゅゆょよらりるれろゎわゐゑをんゔゕゖ゗゘゙゚゛゜ゝゞゟ゠ァアィイゥウェエォオカガキギクグケゲコゴサザシジスズセゼソゾタダチヂッツヅテデトドナニヌネノハバパヒビピフブプヘベペホボポマミムメモャヤュユョヨラリルレロヮワヰヱヲンヴヵヶヷヸヹヺ・ーヽヾヿ]'

                        # 构建内容结构：每行是一个独立的单元，换行会导致换列
                        gushu_content_lines = []
                        for line in raw_lines:
                            if line.strip():
                                # 每行内容作为一个独立的单元，去掉标点符号
                                line_chars = []
                                for ch in line:
                                    if ch.strip() and not re.match(punctuation_pattern, ch):
                                        line_chars.append(ch)
                                # 如果一行超过16个字，按16个字拆分
                                if line_chars:
                                    if len(line_chars) <= 16:
                                        gushu_content_lines.append(line_chars)
                                    else:
                                        # 按16个字拆分
                                        for i in range(0, len(line_chars), 16):
                                            gushu_content_lines.append(line_chars[i:i+16])

                        # 计算每页可以显示的内容
                        # 每列显示一行内容，如果一行超过16个字，则换列继续
                        gushu_display_chars = []
                        for line_chars in gushu_content_lines:
                            # 每行内容独立显示，如果超过16个字，则换列继续
                            for i, ch in enumerate(line_chars):
                                gushu_display_chars.append(ch)
                            # 每行结束后，换列（添加一个换行标记）
                            gushu_display_chars.append('\n')  # 换行标记

                        # 计算实际字符数量（不包含换行标记）
                        gushu_real_chars_count = len([ch for ch in gushu_display_chars if ch != '\n'])

                        # 计算每页可以显示的字符数
                        gushu_chars_per_page = cols * gushu_rows_per_page

                        # 重新计算古书模式的总页数
                        total_pages = max(1, (gushu_real_chars_count + gushu_chars_per_page - 1) // gushu_chars_per_page)

                        # 如果当前页超出总页数，跳过
                        if current_page > total_pages:
                            if current_page < total_pages_from_config:
                                c.showPage()
                            continue

                        gushu_start_char = (current_page - 1) * gushu_chars_per_page
                        gushu_end_char = min(current_page * gushu_chars_per_page, gushu_real_chars_count)

                        # 渲染内容
                        current_col = cols - 1  # 从最右边开始
                        current_row = 0  # 从上到下
                        rendered_chars = 0  # 已渲染的字符数（不含换行标记）
                        skipped_chars = 0  # 已跳过的字符数（用于分页）

                        for current_char in gushu_display_chars:
                            # 如果已经渲染了足够的字符，则停止
                            if rendered_chars >= gushu_end_char:
                                break

                            # 如果遇到换行标记
                            if current_char == '\n':
                                if skipped_chars >= gushu_start_char:
                                    # 已经在当前页范围内，执行换列
                                    current_col -= 1
                                    current_row = 0
                                continue

                            # 如果当前列已满，则换列
                            if skipped_chars >= gushu_start_char and current_row >= gushu_rows_per_page:
                                current_col -= 1
                                current_row = 0

                            # 如果已经超出页面，则停止
                            if skipped_chars >= gushu_start_char and current_col < 0:
                                break

                            # 跳过不属于当前页的字符
                            if skipped_chars < gushu_start_char:
                                skipped_chars += 1
                                continue

                            # 渲染当前页的字符
                            # 计算位置
                            x_pos = gushu_start_x + current_col * gushu_col_width + gushu_col_width / 2 + gushu_dx
                            y_pos = gushu_start_y - current_row * (gushu_cell_height + gushu_row_spacing) - gushu_cell_height / 2 + gushu_dy

                            # 绘制字符
                            if current_char.strip():
                                if is_huizi_mode:
                                    # 灰字模式：使用灰色字体
                                    c.saveState()
                                    c.setFillColor(HexColor("#CCCCCC"))
                                    c.setDash([2, 2])
                                    c.setFont(font_name, gushu_font_size)
                                    c.drawCentredString(x_pos, y_pos, current_char)
                                    c.restoreState()
                                else:
                                    # 正常模式：使用黑色字体
                                    c.setFont(font_name, gushu_font_size)
                                    c.setFillColor(black)
                                    c.drawCentredString(x_pos, y_pos, current_char)

                            rendered_chars += 1
                            skipped_chars += 1
                            current_row += 1
                    elif is_poem_mode and processed_words and isinstance(processed_words[0], dict):
                        # 诗词文章模式：按行分页，正文逐字填格
                        rows = _build_poem_rows(processed_words, cols)

                        # 计算当前页的行范围
                        page_start = 0
                        pg = 1
                        cur_row = 0
                        i = 0
                        while i < len(rows):
                            row = rows[i]
                            if row is None:
                                cur_row += 1
                                i += 1
                                continue
                            is_title = row[0]['type'] == 'title'
                            is_author = row[0]['type'] == 'author'
                            if is_title and cur_row + 1 >= rows_per_page and pg < current_page:
                                pg += 1
                                cur_row = 0
                                page_start = i
                            elif is_author and cur_row >= rows_per_page and pg < current_page:
                                pg += 1
                                cur_row = 0
                                page_start = i
                            elif cur_row >= rows_per_page and pg < current_page:
                                pg += 1
                                cur_row = 0
                                page_start = i
                            cur_row += 1
                            i += 1

                        # 绘制格子
                        for row in range(rows_per_page):
                            for col in range(cols):
                                x = start_x + col * cell_width
                                y = start_y - row * (cell_height + row_spacing)
                                self._draw_grid(c, grid_type, x, y, cell_width, cell_height)

                        # 渲染当前页内容
                        display_row = 0
                        for i in range(page_start, len(rows)):
                            if display_row >= rows_per_page:
                                break
                            row = rows[i]
                            if row is None:
                                display_row += 1
                                continue
                            # 文言文：标题/朝代作者居中，正文首行缩进2字；诗词：左对齐
                            if is_wenyan_mode:
                                row_type = row[0]['type'] if row else 'body'
                                if row_type in ('title', 'author'):
                                    start_col = (cols - len(row)) // 2
                                elif row[0].get('first_body', False):
                                    start_col = 2
                                else:
                                    start_col = 0
                            else:
                                start_col = 0
                            for col, item in enumerate(row):
                                x_pos = start_x + (start_col + col) * cell_width + cell_width / 2 + offset["dx"]
                                y_pos = start_y - display_row * (cell_height + row_spacing) - cell_height / 2 - 11 + offset["dy"]
                                draw_char(c, x_pos, y_pos, item['char'], font_name, font_size, is_huizi_mode)
                            display_row += 1
                    elif grid_type == "教案格":
                        for row in range(rows_per_page):
                            for col in range(cols):
                                x = start_x + col * cell_width
                                y = start_y - row * (cell_height + row_spacing)
                                self._draw_grid(c, grid_type, x, y, cell_width, cell_height)

                        chars_per_page = cols * rows_per_page
                        start_char = (current_page - 1) * chars_per_page
                        end_char = min(current_page * chars_per_page, len(processed_words))
                        for idx in range(start_char, end_char):
                            page_row = (idx - start_char) // cols
                            page_col = (idx - start_char) % cols
                            x = start_x + page_col * cell_width
                            y = start_y - page_row * (cell_height + row_spacing)

                            current_char = processed_words[idx]
                            if current_char != " ":
                                c.saveState()
                                c.setFillColor(HexColor("#CCCCCC"))
                                c.setDash([2, 2])
                                c.setFont(font_name, font_size)
                                c.drawCentredString(
                                    x + cell_width / 2 + offset["dx"],
                                    y - cell_height / 2 - 11 + offset["dy"],
                                    current_char
                                )
                                c.restoreState()
                    else:
                        for row in range(rows_per_page):
                            for col in range(cols):
                                x = start_x + col * cell_width
                                y = start_y - row * (cell_height + row_spacing)
                                self._draw_grid(c, grid_type, x, y, cell_width, cell_height)

                        chars_per_page = cols * rows_per_page
                        start_char = (current_page - 1) * chars_per_page
                        end_char = min(current_page * chars_per_page, len(processed_words))
                        for idx in range(start_char, end_char):
                            page_row = (idx - start_char) // cols
                            page_col = (idx - start_char) % cols
                            x_pos = start_x + page_col * cell_width + cell_width / 2 + offset["dx"]
                            y_pos = start_y - page_row * (cell_height + row_spacing) - cell_height / 2 - 11 + offset["dy"]
                            if is_pinyin_mode:
                                y_pos += 1 * mm
                                # 让拼音首字母对齐到格子左边
                                x_pos = start_x + page_col * cell_width + offset["dx"]

                            current_char = processed_words[idx]
                            if current_char.strip():
                                if is_pinyin_mode:
                                    draw_pinyin_char(c, x_pos, y_pos, current_char, pinyin_font, font_size * 0.68, is_huizi_mode)
                                else:
                                    draw_char(c, x_pos, y_pos, current_char, font_name, font_size, is_huizi_mode)
                else:
                    # 预绘制所有田字格背景（笔顺模式除外，它在自己循环里画）
                    if not is_stroke_mode:
                        for row in range(rows_per_page):
                            for col in range(cols):
                                x = start_x + col * cell_width
                                y = start_y - row * (cell_height + row_spacing)
                                self._draw_grid(c, grid_type, x, y, cell_width, cell_height)
                    
                    # 笔顺模式仅支持田字格/方格/米字格
                    if is_stroke_mode and grid_type in ("田字格", "方格", "米字格"):
                        # ========== 新版笔顺模式: 逐步叠加式 SVG 渲染 ==========
                        page_start_row = (current_page - 1) * rows_per_page
                        page_end_row = page_start_row + rows_per_page  # 始终取整页行数，确保空白行也画格子

                        # ========== 笔顺模式微调配置（直接改数值即可） ==========
                        # 每种格子可独立调整: 字大小缩放、上下左右偏移、渲染分辨率
                        STROKE_TUNE = {
                            "田字格": {
                                "grid_scale":     3.0,    # 笔顺图片分辨率倍数 (越大越清晰)
                                "row_offset_mm":   16.0,   # 整体上下偏移(mm), 正=下移 负=上移
                                "inner_margin_mm": 1.0,    # 格子内边距(mm), 字与格线间距
                                "offset_x_mm":     0.0,    # 字水平额外偏移(mm)
                                "offset_y_mm":     -14.0,  # 字垂直额外偏移(mm), 正=下移 负=上移
                            },
                            "方格": {
                                "grid_scale":     3.0,
                                "row_offset_mm":   10.0,
                                "inner_margin_mm": 1.0,
                                "offset_x_mm":     0.0,
                                "offset_y_mm":     -10.0,
                            },
                            "米字格": {
                                "grid_scale":     3.0,
                                "row_offset_mm":   10.0,
                                "inner_margin_mm": 1.0,
                                "offset_x_mm":     0.0,
                                "offset_y_mm":     -10.0,
                            },
                        }
                        tune = STROKE_TUNE.get(grid_type, STROKE_TUNE["田字格"])

                        # 遍历当前页的所有行（包括空白行），确保填满
                        page_row_count = page_end_row - page_start_row
                        for page_row in range(page_row_count):
                            row_idx = page_start_row + page_row

                            current_row = page_row
                            y_pos_base = start_y - current_row * (cell_height + row_spacing) + tune["row_offset_mm"] * mm
                            y_center = y_pos_base - cell_height / 2 + offset["dy"]

                            # 先绘制该行的所有田字格（每行都有 cols 个格子）
                            for col_idx in range(cols):
                                x_cell = start_x + col_idx * cell_width
                                y_cell = y_pos_base - cell_height
                                self._draw_grid(c, grid_type, x_cell, y_cell, cell_width, cell_height)

                            # 如果该行有字，嵌入内容（处理 enable_empty_line 间隔）
                            actual_item_idx = row_idx
                            is_content_row = True
                            if enable_empty_line:
                                is_content_row = (row_idx % 2) == 0
                                actual_item_idx = row_idx // 2

                            if is_content_row and actual_item_idx < len(expanded_words):
                                item = expanded_words[actual_item_idx]
                                char = item['char']
                                use_svg = item.get('use_svg', False)
                                is_continuation = item.get('_continuation', False)

                                if use_svg and stroke_renderer and stroke_renderer.has_stroke_data(char):
                                    # === SVG笔顺模式 ===
                                    if not is_continuation:
                                        # 第一行: 参考字
                                        x_pos = start_x + 0 * cell_width + cell_width / 2 + offset["dx"]
                                        y_ref = y_center - (cell_height + row_spacing) - 3 * mm
                                        c.setFont(font_name, font_size)
                                        c.setFillColor(black)
                                        c.drawCentredString(x_pos, y_ref, char)

                                    # 笔顺步骤图
                                    grid_px = int(cell_width * tune["grid_scale"])
                                    all_step_images = stroke_renderer.render_all_steps(
                                        char, grid_px, stroke_color=(180, 180, 180), ref_bbox=ref_bbox)

                                    stroke_start = item.get('_stroke_start', 0)
                                    stroke_end = item.get('_stroke_end', len(all_step_images))
                                    start_col = 0 if is_continuation else 1

                                    for step in range(stroke_start, min(stroke_end, len(all_step_images))):
                                        col_idx = start_col + (step - stroke_start)
                                        if col_idx >= cols:
                                            break
                                        step_img = all_step_images[step]

                                        x_cell = start_x + col_idx * cell_width
                                        y_cell = y_pos_base - cell_height

                                        try:
                                            img_bytes = stroke_renderer.image_to_bytes(step_img, 'PNG')
                                            from reportlab.lib.utils import ImageReader
                                            img_reader = ImageReader(img_bytes)

                                            img_w, img_h = step_img.size
                                            aspect = img_w / img_h if img_h > 0 else 1

                                            inner_margin = tune["inner_margin_mm"] * mm
                                            avail_w = cell_width - inner_margin * 2
                                            avail_h = cell_height - inner_margin * 2

                                            stroke_scale = 1.0

                                            if avail_w / avail_h > aspect:
                                                draw_h = avail_h * stroke_scale
                                                draw_w = draw_h * aspect
                                            else:
                                                draw_w = avail_w * stroke_scale
                                                draw_h = draw_w / aspect

                                            draw_x = x_cell + (cell_width - draw_w) / 2 + tune["offset_x_mm"] * mm
                                            draw_y = y_cell + (cell_height - draw_h) / 2 + tune["offset_y_mm"] * mm

                                            c.drawImage(img_reader, draw_x, draw_y,
                                                       width=draw_w, height=draw_h,
                                                       mask='auto')
                                        except Exception:
                                            pass
                                else:
                                    # === 回退模式: 旧式的笔画部首字符绘制 ===
                                    strokes = item.get('strokes', [])
                                    stroke_count = item.get('stroke_count', len(strokes))

                                    # 第一格: 完整汉字 (参考字)
                                    x_pos = start_x + 0 * cell_width + cell_width / 2 + offset["dx"]
                                    c.setFont(font_name, font_size)
                                    c.setFillColor(black)
                                    c.drawCentredString(x_pos, y_center, char)

                                    # 后续格: 每个笔画部首字符 (旧方式回退)
                                    for col_idx in range(stroke_count):
                                        if col_idx + 1 >= cols:
                                            break
                                        x_pos = start_x + (col_idx + 1) * cell_width + cell_width / 2 + offset["dx"]
                                        c.setFont(font_name, font_size)
                                        c.setFillColor(HexColor("#888888"))
                                        stroke_char = strokes[col_idx] if col_idx < len(strokes) else ''
                                        c.drawCentredString(x_pos, y_center, stroke_char)
                    elif is_article_mode:
                        if is_poem_mode and processed_words and isinstance(processed_words[0], dict):
                            # 诗词文章模式：按行分页，正文逐字填格
                            rows = _build_poem_rows(processed_words, cols)

                            page_start = 0
                            pg = 1
                            cur_row = 0
                            i = 0
                            while i < len(rows):
                                row = rows[i]
                                if row is None:
                                    cur_row += 1
                                    i += 1
                                    continue
                                is_title = row[0]['type'] == 'title'
                                is_author = row[0]['type'] == 'author'
                                if is_title and cur_row + 1 >= rows_per_page and pg < current_page:
                                    pg += 1
                                    cur_row = 0
                                    page_start = i
                                elif is_author and cur_row >= rows_per_page and pg < current_page:
                                    pg += 1
                                    cur_row = 0
                                    page_start = i
                                elif cur_row >= rows_per_page and pg < current_page:
                                    pg += 1
                                    cur_row = 0
                                    page_start = i
                                cur_row += 1
                                i += 1

                            display_row = 0
                            for i in range(page_start, len(rows)):
                                if display_row >= rows_per_page:
                                    break
                                row = rows[i]
                                if row is None:
                                    display_row += 1
                                    continue
                                # 文言文：标题/朝代作者居中，正文首行缩进2字；诗词：左对齐
                                if is_wenyan_mode:
                                    row_type = row[0]['type'] if row else 'body'
                                    if row_type in ('title', 'author'):
                                        start_col = (cols - len(row)) // 2
                                    elif row[0].get('first_body', False):
                                        start_col = 2
                                    else:
                                        start_col = 0
                                else:
                                    start_col = 0
                                for col, item in enumerate(row):
                                    x_pos = start_x + (start_col + col) * cell_width + cell_width / 2 + offset["dx"]
                                    y_pos = start_y - display_row * (cell_height + row_spacing) - cell_height / 2 - 11 + offset["dy"]
                                    draw_char(c, x_pos, y_pos, item['char'], font_name, font_size, is_huizi_mode)
                                display_row += 1
                        else:
                            chars_per_page = cols * rows_per_page
                            page_start_char = (current_page - 1) * chars_per_page

                            for idx in range(len(processed_words)):
                                if idx >= page_start_char + chars_per_page:
                                    break
                                if idx < page_start_char:
                                    continue

                                relative_idx = idx - page_start_char
                                row = relative_idx // cols
                                col = relative_idx % cols

                                x_pos = start_x + col * cell_width + cell_width / 2 + offset["dx"]
                                y_pos = start_y - row * (cell_height + row_spacing) - cell_height / 2 - 11 + offset["dy"]
                                if is_pinyin_mode:
                                    # 让拼音首字母对齐到格子左边
                                    x_pos = start_x + col * cell_width + offset["dx"]

                                current_item = processed_words[idx]
                                if is_pinyin_mode:
                                    draw_pinyin_char(c, x_pos, y_pos, current_item, pinyin_font, font_size * 0.68, is_huizi_mode)
                                else:
                                    draw_char(c, x_pos, y_pos, current_item, font_name, font_size, is_huizi_mode)
                    elif is_poem_mode and is_dai_pinyin_mode and processed_words and isinstance(processed_words[0], dict) and 'pinyin' in processed_words[0]:
                        # 诗词带拼音：生字格格式，拼音在上汉字在下
                        from pypinyin import pinyin as _py
                        from reportlab.pdfbase.pdfmetrics import stringWidth

                        four_line_h = 10 * mm
                        pinyin_font_size = font_size * 0.45

                        rows = _build_poem_rows(processed_words, cols)

                        page_start = 0
                        pg = 1
                        cur_row = 0
                        i = 0
                        while i < len(rows):
                            row = rows[i]
                            if row is None:
                                cur_row += 1
                                i += 1
                                continue
                            is_title = row[0]['type'] == 'title'
                            is_author = row[0]['type'] == 'author'
                            if is_title and cur_row + 1 >= rows_per_page and pg < current_page:
                                pg += 1
                                cur_row = 0
                                page_start = i
                            elif is_author and cur_row >= rows_per_page and pg < current_page:
                                pg += 1
                                cur_row = 0
                                page_start = i
                            elif cur_row >= rows_per_page and pg < current_page:
                                pg += 1
                                cur_row = 0
                                page_start = i
                            cur_row += 1
                            i += 1

                        for row in range(rows_per_page):
                            for col in range(cols):
                                x = start_x + col * cell_width
                                y = start_y - row * (cell_height + row_spacing)
                                self._draw_shengzige(c, x, y, cell_width, cell_height)

                        tone_map = {0x0304: '1', 0x0301: '2', 0x030C: '3', 0x0300: '4'}
                        pinyin_font = "pinyin-me"

                        display_row = 0
                        for i in range(page_start, len(rows)):
                            if display_row >= rows_per_page:
                                break
                            row_items = rows[i]
                            if row_items is None:
                                display_row += 1
                                continue
                            # 文言文：标题/朝代作者居中，正文首行缩进2字；诗词：左对齐
                            if is_wenyan_mode:
                                row_type = row_items[0]['type'] if row_items else 'body'
                                if row_type in ('title', 'author'):
                                    start_col = (cols - len(row_items)) // 2
                                elif row_items[0].get('first_body', False):
                                    start_col = 2
                                else:
                                    start_col = 0
                            else:
                                start_col = 0
                            for col, item in enumerate(row_items):
                                x_pos = start_x + (start_col + col) * cell_width + cell_width / 2 + offset["dx"]
                                y_hanzi = start_y - display_row * (cell_height + row_spacing) - cell_height / 2 - 11 + offset["dy"]
                                y_pinyin = start_y - display_row * (cell_height + row_spacing) - four_line_h * 2 / 3 + 0.6 * mm
                                y_tone = y_pinyin + 0.6 * mm
                                draw_char(c, x_pos, y_hanzi, item['char'], font_name, font_size, is_huizi_mode)
                                py_text = item.get('pinyin', '')
                                if py_text:
                                    base_py = ''
                                    tone_char = ''
                                    for ch in py_text:
                                        cp = ord(ch)
                                        if cp in tone_map:
                                            tone_char = ch
                                        else:
                                            base_py += ch
                                    if is_huizi_mode:
                                        c.saveState()
                                        c.setFillColor(HexColor("#CCCCCC"))
                                        c.setDash([2, 2])
                                        c.setFont(pinyin_font, pinyin_font_size)
                                        c.setFillColor(HexColor("#CCCCCC"))
                                        c.drawCentredString(x_pos, y_pinyin, base_py)
                                        if tone_char:
                                            c.drawCentredString(x_pos, y_tone, tone_char)
                                        c.restoreState()
                                    else:
                                        c.setFont(pinyin_font, pinyin_font_size)
                                        c.setFillColor(black)
                                        c.drawCentredString(x_pos, y_pinyin, base_py)
                                        if tone_char:
                                            c.setFont(pinyin_font, pinyin_font_size)
                                            c.setFillColor(black)
                                            c.drawCentredString(x_pos, y_tone, tone_char)
                            display_row += 1
                    elif is_dai_pinyin_mode:
                        page_start_line = (current_page - 1) * rows_per_page
                        page_end_line = min(page_start_line + rows_per_page,
                                         len(processed_words) * 2 if enable_empty_line else len(processed_words))
                        four_line_h = 10 * mm
                        pinyin_font_size = font_size * 0.45
                        from reportlab.pdfbase.pdfmetrics import stringWidth

                        def _draw_pinyin_text(c, text, x_center, y, font, size, color):
                            c.setFont(font, size)
                            c.setFillColor(color)
                            c.drawCentredString(x_center, y, text)
                            if 't' not in text:
                                return
                            parts = text.split('t', 1)
                            w_left = stringWidth(parts[0], font, size) if parts[0] else 0
                            w_t = stringWidth('t', font, size)
                            total_w = stringWidth(text, font, size)
                            x0 = x_center - total_w / 2
                            tx = x0 + w_left + w_t / 2
                            c.saveState()
                            c.transform(1, 0, 0, 1.3, tx, y * (1 - 1.3))
                            c.setFont(font, size)
                            c.setFillColor(color)
                            c.drawCentredString(0, 0, 't')
                            c.restoreState()

                        if is_multi_sentence_mode:
                            # 词语带拼音模式：每个词语的字占一行
                            for page_line in range(page_start_line, page_end_line):
                                is_content_line = True
                                item_index = page_line
                                if enable_empty_line:
                                    is_content_line = (page_line % 2) == 0
                                    item_index = page_line // 2
                                if item_index >= len(processed_words):
                                    continue
                                if not is_content_line:
                                    continue
                                row = page_line % rows_per_page
                                word_data = processed_words[item_index]
                                y_hanzi = start_y - row * (cell_height + row_spacing) - cell_height / 2 - 11 + offset["dy"]
                                y_pinyin = start_y - row * (cell_height + row_spacing) - four_line_h * 2 / 3 + 0.6 * mm
                                y_tone = y_pinyin + 0.6 * mm
                                for ci, item in enumerate(word_data):
                                    x_pos = start_x + ci * cell_width + cell_width / 2 + offset["dx"]
                                    draw_char(c, x_pos, y_hanzi, item['char'], font_name, font_size, is_huizi_mode)
                                    tone_map = {0x0304: '1', 0x0301: '2', 0x030C: '3', 0x0300: '4'}
                                    py_text = item['pinyin']
                                    base_py = ''
                                    tone_char = ''
                                    for ch in py_text:
                                        cp = ord(ch)
                                        if cp in tone_map:
                                            tone_char = ch
                                        else:
                                            base_py += ch
                                    if is_huizi_mode:
                                        c.saveState()
                                        c.setFillColor(HexColor("#CCCCCC"))
                                        c.setDash([2, 2])
                                        _draw_pinyin_text(c, base_py, x_pos, y_pinyin, pinyin_font, pinyin_font_size, HexColor("#CCCCCC"))
                                        if tone_char:
                                            c.drawCentredString(x_pos, y_tone, tone_char)
                                        c.restoreState()
                                    else:
                                        _draw_pinyin_text(c, base_py, x_pos, y_pinyin, pinyin_font, pinyin_font_size, black)
                                        if tone_char:
                                            c.setFont(pinyin_font, pinyin_font_size)
                                            c.setFillColor(black)
                                            c.drawCentredString(x_pos, y_tone, tone_char)
                        else:
                            # 单字带拼音模式
                            for page_line in range(page_start_line, page_end_line):
                                is_content_line = True
                                item_index = page_line
                                if enable_empty_line:
                                    is_content_line = (page_line % 2) == 0
                                    item_index = page_line // 2
                                if item_index >= len(processed_words):
                                    continue
                                if not is_content_line:
                                    continue
                                row = page_line % rows_per_page
                                item = processed_words[item_index]
                                x_pos = start_x + 0 * cell_width + cell_width / 2 + offset["dx"]
                                y_hanzi = start_y - row * (cell_height + row_spacing) - cell_height / 2 - 11 + offset["dy"]
                                draw_char(c, x_pos, y_hanzi, item['char'], font_name, font_size, is_huizi_mode)
                                y_pinyin = start_y - row * (cell_height + row_spacing) - four_line_h * 2 / 3 + 0.6 * mm
                                tone_map = {0x0304: '1', 0x0301: '2', 0x030C: '3', 0x0300: '4'}
                                py_text = item['pinyin']
                                base_py = ''
                                tone_char = ''
                                for ch in py_text:
                                    cp = ord(ch)
                                    if cp in tone_map:
                                        tone_char = ch
                                    else:
                                        base_py += ch
                                y_tone = y_pinyin + 0.6 * mm
                                if is_huizi_mode:
                                    c.saveState()
                                    c.setFillColor(HexColor("#CCCCCC"))
                                    c.setDash([2, 2])
                                    _draw_pinyin_text(c, base_py, x_pos, y_pinyin, pinyin_font, pinyin_font_size, HexColor("#CCCCCC"))
                                    if tone_char:
                                        c.drawCentredString(x_pos, y_tone, tone_char)
                                    c.restoreState()
                                else:
                                    _draw_pinyin_text(c, base_py, x_pos, y_pinyin, pinyin_font, pinyin_font_size, black)
                                    if tone_char:
                                        c.setFont(pinyin_font, pinyin_font_size)
                                        c.setFillColor(black)
                                        c.drawCentredString(x_pos, y_tone, tone_char)
                    elif is_multi_char_mode and is_single_char_mode:
                        page_start_line = (current_page - 1) * rows_per_page
                        page_end_line = min(page_start_line + rows_per_page,
                                         len(processed_words) * 2 if enable_empty_line else len(processed_words))

                        for page_line in range(page_start_line, page_end_line):
                            is_content_line = True
                            item_index = page_line

                            if enable_empty_line:
                                is_content_line = (page_line % 2) == 0
                                item_index = page_line // 2

                            if item_index >= len(processed_words):
                                continue

                            if not is_content_line:
                                continue

                            row = page_line % rows_per_page
                            y_pos = start_y - row * (cell_height + row_spacing) - cell_height / 2 - 11 + offset["dy"]

                            current_item = processed_words[item_index]
                            chars = list(current_item)
                            num_chars = len(chars)
                            # 诗词：逐字从第一格开始排列
                            for ci, ch in enumerate(chars):
                                x_pos = start_x + ci * cell_width + cell_width / 2 + offset["dx"]
                                draw_char(c, x_pos, y_pos, ch, font_name, font_size, is_huizi_mode)
                    elif is_whole_line_mode:
                        page_start_line = (current_page - 1) * rows_per_page
                        page_end_line = min(page_start_line + rows_per_page,
                                         len(processed_words) * 2 if enable_empty_line else len(processed_words))
                        for page_line in range(page_start_line, page_end_line):
                            is_content_line = True
                            item_index = page_line
                            if enable_empty_line:
                                is_content_line = (page_line % 2) == 0
                                item_index = page_line // 2
                            if item_index >= len(processed_words):
                                continue
                            if not is_content_line:
                                continue
                            row = page_line % rows_per_page
                            y_pos = start_y - row * (cell_height + row_spacing) - cell_height / 2 - 11 + offset["dy"]
                            if is_pinyin_mode:
                                y_pos += 1 * mm
                            current_item = processed_words[item_index]
                            if is_multi_sentence_mode:
                                # 词语整行模式：将词语重复填满一行
                                chars = list(current_item)
                                repeat_chars = []
                                while len(repeat_chars) < cols:
                                    repeat_chars.extend(chars)
                                for col in range(cols):
                                    x_pos = start_x + col * cell_width + cell_width / 2 + offset["dx"]
                                    if is_pinyin_mode:
                                        # 让拼音首字母对齐到格子左边
                                        x_pos = start_x + col * cell_width + offset["dx"]
                                        draw_pinyin_char(c, x_pos, y_pos, repeat_chars[col], pinyin_font, font_size * 0.68, is_huizi_mode)
                                    else:
                                        draw_char(c, x_pos, y_pos, repeat_chars[col], font_name, font_size, is_huizi_mode)
                            elif is_shuzi_mode:
                                # 数字整行模式：将数字作为一个整体重复填满一行
                                for col in range(cols):
                                    x_pos = start_x + col * cell_width + cell_width / 2 + offset["dx"]
                                    draw_char(c, x_pos, y_pos, current_item, font_name, font_size, is_huizi_mode)
                            elif is_pinyin_mode:
                                # 拼音整行模式：将拼音作为一个整体重复填满一行
                                for col in range(cols):
                                    # 让拼音首字母对齐到格子左边
                                    x_pos = start_x + col * cell_width + offset["dx"]
                                    draw_pinyin_char(c, x_pos, y_pos, current_item, pinyin_font, font_size * 0.68, is_huizi_mode)
                            else:
                                first_char = current_item[0] if current_item else ''
                                for col in range(cols):
                                    x_pos = start_x + col * cell_width + cell_width / 2 + offset["dx"]
                                    draw_char(c, x_pos, y_pos, first_char, font_name, font_size, is_huizi_mode)
                    elif is_wenyan_mode:
                        all_lines = []
                        for article_idx, article in enumerate(processed_words):
                            if article_idx > 0:
                                all_lines.append('')
                            if isinstance(article, dict):
                                all_lines.append(article['title'])
                                all_lines.append(article['author'])
                                if article['content']:
                                    content_lines = article['content'].split('\n')
                                    all_lines.extend(content_lines)
                            else:
                                all_lines.append(article)

                        # 将长行拆分为多个短行（每行最多cols个字符）
                        display_lines = []
                        for line in all_lines:
                            if line == '':
                                display_lines.append('')
                            else:
                                chars = list(line)
                                while len(chars) > cols:
                                    display_lines.append(''.join(chars[:cols]))
                                    chars = chars[cols:]
                                if chars:
                                    display_lines.append(''.join(chars))

                        lines_per_page = rows_per_page
                        page_start_line = (current_page - 1) * lines_per_page
                        page_end_line = min(page_start_line + lines_per_page, len(display_lines))

                        for line_idx in range(page_start_line, page_end_line):
                            row = line_idx - page_start_line
                            line = display_lines[line_idx]
                            if line == '':
                                continue
                            y_pos = start_y - row * (cell_height + row_spacing) - cell_height / 2 - 11 + offset["dy"]
                            for col_idx, ch in enumerate(line):
                                x_pos = start_x + col_idx * cell_width + cell_width / 2 + offset["dx"] + 0.5 * mm
                                c.setFont(font_name, font_size)
                                c.setFillColor(black)
                                c.drawCentredString(x_pos, y_pos, ch)

                    elif is_guoxue_mode:
                        # 国学模式: 标题和作者居中，教案格下正文也居中
                        display_lines = []  # (text, line_type): line_type='title'/'author'/'body'/''(empty)
                        for article_idx, article in enumerate(processed_words):
                            if article_idx > 0:
                                display_lines.append(('', ''))
                            if isinstance(article, dict):
                                display_lines.append((article['title'], 'title'))
                                display_lines.append((article['author'], 'author'))
                                if article['content']:
                                    content_lines = article['content'].split('\n')
                                    for cl in content_lines:
                                        chars = list(cl)
                                        while len(chars) > cols:
                                            display_lines.append((''.join(chars[:cols]), 'body'))
                                            chars = chars[cols:]
                                        if chars:
                                            display_lines.append((''.join(chars), 'body'))
                            else:
                                display_lines.append((article, 'body'))

                        lines_per_page = rows_per_page
                        page_start_line = (current_page - 1) * lines_per_page
                        page_end_line = min(page_start_line + lines_per_page, len(display_lines))

                        use_center_all = (grid_type == "教案格")

                        for line_idx in range(page_start_line, page_end_line):
                            row = line_idx - page_start_line
                            line_text, line_type = display_lines[line_idx]
                            if not line_text:
                                continue

                            y_pos = start_y - row * (cell_height + row_spacing) - cell_height / 2 - 11 + offset["dy"]

                            # 标题和作者始终居中，正文仅教案格居中
                            should_center = line_type in ('title', 'author') or (line_type == 'body' and use_center_all)

                            if should_center:
                                if cols == 1:
                                    # 教案格等单列格子: 整体字符串右移1cm
                                    c.setFont(font_name, font_size)
                                    c.setFillColor(black)
                                    c.drawString(start_x + 10 * mm, y_pos, line_text)
                                else:
                                    # 多列格子: 逐字居中
                                    text_width = len(line_text) * cell_width
                                    total_grid = cols * cell_width
                                    start_offset = (total_grid - text_width) / 2
                                    for col_idx, ch in enumerate(line_text):
                                        x_pos = start_x + start_offset + col_idx * cell_width + cell_width / 2
                                        c.setFont(font_name, font_size)
                                        c.setFillColor(black)
                                        c.drawCentredString(x_pos, y_pos, ch)
                            else:
                                for col_idx, ch in enumerate(line_text):
                                    x_pos = start_x + col_idx * cell_width + cell_width / 2
                                    c.setFont(font_name, font_size)
                                    c.setFillColor(black)
                                    c.drawCentredString(x_pos, y_pos, ch)
                    else:
                        if is_dakai_mode and base_type.startswith("单字"):
                            # 单字模式：一个字占一行，只在第一列显示（+1行时每字后空一行）
                            content_rows = rows_per_page // 2 if enable_empty_line else rows_per_page
                            char_start = (current_page - 1) * content_rows
                            for row in range(rows_per_page):
                                if enable_empty_line and row % 2 == 1:
                                    continue  # 跳过空行
                                idx = char_start + (row // 2 if enable_empty_line else row)
                                if idx >= len(processed_words):
                                    break
                                ch = processed_words[idx]
                                x_pos = start_x + cell_width / 2 + offset["dx"]
                                y_pos = start_y - row * (cell_height + row_spacing) - cell_height / 2 - 11 + offset["dy"]
                                c.setFont(font_name, font_size)
                                c.setFillColor(HexColor("#CCCCCC") if is_huizi_mode else black)
                                c.drawCentredString(x_pos, y_pos, ch)
                        elif is_dakai_mode and base_type.startswith("整行"):
                            # 整行模式：一个字占一整行，所有格子都是同一个字（+1行时每字后空一行）
                            content_rows = rows_per_page // 2 if enable_empty_line else rows_per_page
                            char_start = (current_page - 1) * content_rows
                            for row in range(rows_per_page):
                                if enable_empty_line and row % 2 == 1:
                                    continue  # 跳过空行
                                idx = char_start + (row // 2 if enable_empty_line else row)
                                if idx >= len(processed_words):
                                    break
                                ch = processed_words[idx]
                                for col in range(cols):
                                    x_pos = start_x + col * cell_width + cell_width / 2 + offset["dx"]
                                    y_pos = start_y - row * (cell_height + row_spacing) - cell_height / 2 - 11 + offset["dy"]
                                    c.setFont(font_name, font_size)
                                    c.setFillColor(HexColor("#CCCCCC") if is_huizi_mode else black)
                                    c.drawCentredString(x_pos, y_pos, ch)
                        elif is_dakai_mode:
                            # 文章模式：逐字逐格填满
                            char_start = (current_page - 1) * cols * rows_per_page
                            for row in range(rows_per_page):
                                for col in range(cols):
                                    idx = char_start + row * cols + col
                                    if idx >= len(processed_words):
                                        break
                                    ch = processed_words[idx]
                                    x_pos = start_x + col * cell_width + cell_width / 2 + offset["dx"]
                                    y_pos = start_y - row * (cell_height + row_spacing) - cell_height / 2 - 11 + offset["dy"]
                                    c.setFont(font_name, font_size)
                                    c.setFillColor(HexColor("#CCCCCC") if is_huizi_mode else black)
                                    c.drawCentredString(x_pos, y_pos, ch)
                        else:
                            page_start_line = (current_page - 1) * rows_per_page
                            page_end_line = min(page_start_line + rows_per_page,
                                             len(processed_words) * 2 if enable_empty_line else len(processed_words))

                            for page_line in range(page_start_line, page_end_line):
                                is_content_line = True
                                item_index = page_line

                                if enable_empty_line:
                                    is_content_line = (page_line % 2) == 0
                                    item_index = page_line // 2

                                if item_index >= len(processed_words):
                                    continue

                                row = page_line % rows_per_page

                                if is_content_line:
                                    current_item = processed_words[item_index]
                                    # 笔顺模式下 processed_words 是 dict 列表，需提取 char 字段
                                    if isinstance(current_item, dict):
                                        current_item = current_item.get('char', '')
                                    if is_dakai_mode:
                                        # 整行/文言文模式：每个item是一行文本，逐字填入
                                        chars = list(current_item)
                                        for ci, ch in enumerate(chars):
                                            if is_wenyan_mode:
                                                x_pos = start_x + ci * cell_width + cell_width / 2 + offset["dx"] + 5 * mm
                                            else:
                                                x_pos = start_x + ci * cell_width + cell_width / 2 + offset["dx"]
                                            y_pos = start_y - row * (cell_height + row_spacing) - cell_height / 2 - 11 + offset["dy"]
                                            c.setFont(font_name, font_size)
                                            c.setFillColor(black)
                                            c.drawCentredString(x_pos, y_pos, ch)
                                    elif is_multi_sentence_mode:
                                        # 词语单字模式：每个词语逐字填入一行
                                        chars = list(current_item)
                                        for ci, ch in enumerate(chars):
                                            x_pos = start_x + ci * cell_width + cell_width / 2 + offset["dx"]
                                            y_pos = start_y - row * (cell_height + row_spacing) - cell_height / 2 - 11 + offset["dy"]
                                            draw_char(c, x_pos, y_pos, ch, font_name, font_size, is_huizi_mode)
                                    elif is_shuzi_mode:
                                        # 数字单字模式：每个数字占一格（左半格绘制）
                                        # 单数字(0-9)绘制在左半格中心，多位数从左半格开始向右延伸+2mm
                                        if len(current_item) == 1:
                                            # 一位数（0-9）：左半格中心+1mm
                                            x_pos = start_x + cell_width / 4 + offset["dx"] + 1 * mm
                                        else:
                                            # 两位数及以上（10、11等）：左半格中心+3mm
                                            x_pos = start_x + cell_width / 4 + offset["dx"] + 3 * mm
                                        y_pos = start_y - row * (cell_height + row_spacing) - cell_height / 2 - 11 + offset["dy"]
                                        draw_char(c, x_pos, y_pos, current_item, font_name, font_size, is_huizi_mode)
                                    elif is_pinyin_mode:
                                        # 拼音单字模式：每个拼音占一格（左对齐，用拼音字体）
                                        x_pos = start_x + offset["dx"]  # 让拼音首字母对齐到格子左边
                                        y_pos = start_y - row * (cell_height + row_spacing) - cell_height / 2 - 11 + offset["dy"] + 1 * mm
                                        draw_pinyin_char(c, x_pos, y_pos, current_item, pinyin_font, font_size * 0.68, is_huizi_mode)
                                    else:
                                        # 其他单字/通用模式：每个item占一格
                                        x_pos = start_x + cell_width / 2 + offset["dx"]
                                        y_pos = start_y - row * (cell_height + row_spacing) - cell_height / 2 - 11 + offset["dy"]
                                        draw_char(c, x_pos, y_pos, current_item, font_name, font_size, is_huizi_mode)
                                else:
                                    # 空行（+1行模式的间隔行），留白不画字
                                    pass
                    
                    if grid_type == "生字格":
                        for row in range(rows_per_page - 1):
                            dashed_y = start_y - (row + 1) * (cell_height + row_spacing) + row_spacing / 2
                            c.setLineWidth(0.3)
                            c.setStrokeColor(gray)
                            c.setDash([2, 2])
                            c.line(margin_x, dashed_y, A4[0] - margin_x, dashed_y)
                            c.setDash([])
                            c.setLineWidth(1.0)
                
                if grid_type == "作文本":
                    c.setFont("SimSun", 9)
                    c.drawRightString(A4[0] - margin_x - 2 * mm, margin_y - 6 * mm, f"{current_page}/{total_pages}")
                elif grid_type == "教案格":
                    c.setFont("SimSun", 9)
                    c.drawRightString(A4[0] - 25 * mm, 25 * mm, f"{current_page}/{total_pages}")
                elif grid_type == "大楷本":
                    pass  # 大楷本不显示页码
                else:
                    self._draw_page_number(c, current_page, total_pages, margin_x, margin_y)
                
                if current_page < total_pages:
                    c.showPage()
            
            c.save()
            return filename
        except Exception as e:
            raise RuntimeError(f"生成失败: {str(e)}")
    
    def generate(self):
        grid_name = self.config.grid_type
        date_str = datetime.now().strftime("%Y%m%d_%H%M")

        if self.config.mode == "blank":
            filename = f"{grid_name}_{self.config.page_count}页.pdf"
            self.generate_blank_template(filename)
            return filename
        else:
            filename = f"{grid_name}字帖_{date_str}.pdf"
            return self.generate_zitie(filename)
    
    def save_pdf(self, filename=None):
        if not filename:
            grid_name = self.config.grid_type
            date_str = datetime.now().strftime("%Y%m%d_%H%M")
            if self.config.mode == "blank":
                filename = f"{grid_name}_{self.config.page_count}页.pdf"
            else:
                filename = f"{grid_name}字帖_{date_str}.pdf"
        
        try:
            if self.config.mode == "blank":
                self.generate_blank_template(filename)
            else:
                self.generate_zitie(filename)
            return filename
        except Exception as e:
            print(f"保存PDF失败: {e}")
            return None
    
    def _draw_grid(self, c, grid_type, x, y, width, height):
        if grid_type == "田字格":
            self._draw_tianzige(c, x, y, width, height)
        elif grid_type == "米字格":
            self._draw_mizige(c, x, y, width, height)
        elif grid_type == "四线三格":
            self._draw_sixiansange(c, x, y, width, height)
        elif grid_type == "生字格":
            self._draw_shengzige(c, x, y, width, height)
        elif grid_type == "数学格":
            self._draw_maths_grid(c, x, y, width, height)
        elif grid_type == "教案格":
            self._draw_jiaoange(c, x, y, width, height)
        elif grid_type == "大楷本":
            self._draw_dakaige(c, x, y, width, height)
        else:
            self._draw_fangge(c, x, y, width, height)
    
    def _draw_tianzige(self, c, x, y, width, height):
        c.setLineWidth(1.0)
        c.setStrokeColor(black)
        c.rect(x, y - height, width, height)
        c.setLineWidth(0.2)
        c.setStrokeColor(gray)
        c.setDash([2, 2])
        c.line(x, y - height / 2, x + width, y - height / 2)
        c.line(x + width / 2, y - height, x + width / 2, y)
        c.setDash([])
    
    def _draw_mizige(self, c, x, y, width, height):
        self._draw_tianzige(c, x, y, width, height)
        c.setLineWidth(0.2)
        c.line(x, y - height, x + width, y)
        c.line(x, y, x + width, y - height)
    
    def _draw_sixiansange(self, c, x, y, width, height):
        line_config = [
            (y, 1.0),
            (y - height / 3, 0.3),
            (y - 2 * height / 3, 0.3),
            (y - height, 1.0)
        ]
        for line_y, line_width in line_config:
            c.setLineWidth(line_width)
            c.line(x, line_y, x + width, line_y)
    
    def _draw_shengzige(self, c, x, y, width, height):
        four_line_height = 10 * mm
        tianzige_height = 13 * mm
        interval_mm = 13

        c.setStrokeColor(black)

        line_config = [
            (y, 1.0, False),
            (y - four_line_height / 3, 0.3, True),
            (y - 2 * four_line_height / 3, 0.3, True),
            (y - four_line_height, 1.0, False)
        ]
        for line_y, line_width, is_dashed in line_config:
            c.setLineWidth(line_width)
            c.setDash([2, 2] if is_dashed else [])
            c.line(x, line_y, x + width, line_y)

        interval_pt = interval_mm * mm

        c.saveState()
        c.setLineWidth(1.0)
        c.setDash([])
        c.line(x, y, x, y - four_line_height)
        c.restoreState()

        current_x = x + interval_pt
        while current_x <= x + width - interval_pt:
            c.saveState()
            c.setLineWidth(1.0)
            c.setDash([2, 2])
            c.line(current_x, y, current_x, y - four_line_height)
            c.restoreState()
            current_x += interval_pt

        c.saveState()
        c.setLineWidth(1.0)
        c.setDash([])
        c.line(x + width, y, x + width, y - four_line_height)
        c.restoreState()

        c.setLineWidth(1.0)
        c.setDash([])
        c.line(x, y - four_line_height, x, y - four_line_height - tianzige_height)
        c.line(x + width, y - four_line_height, x + width, y - four_line_height - tianzige_height)
        c.line(x, y - four_line_height - tianzige_height, x + width, y - four_line_height - tianzige_height)

        c.setLineWidth(0.3)
        c.setDash([2, 2])
        c.line(x, y - four_line_height - tianzige_height / 2, x + width, y - four_line_height - tianzige_height / 2)
        c.line(x + width / 2, y - four_line_height, x + width / 2, y - four_line_height - tianzige_height)
        c.setDash([])
    
    def _draw_fangge(self, c, x, y, width, height):
        c.rect(x, y - height, width, height)
    
    def _draw_jiaoange(self, c, x, y, width, height):
        c.setLineWidth(1.0)
        c.setStrokeColor(black)
        c.rect(x, y - height, width, height)
        
        col_widths = [width * 0.15, width * 0.2, width * 0.25, width * 0.4]
        current_x = x
        for w in col_widths[:-1]:
            current_x += w
            c.line(current_x, y, current_x, y - height)
        
        c.setLineWidth(0.3)
        c.setStrokeColor(gray)
        c.line(x, y - height / 3, x + width, y - height / 3)
        c.line(x, y - 2 * height / 3, x + width, y - 2 * height / 3)
        c.setDash([])
    
    def _draw_dakaige(self, c, x, y, width, height):
        c.setLineWidth(1.0)
        c.setStrokeColor(black)
        c.rect(x, y - height, width, height)
        c.setLineWidth(0.2)
        c.setStrokeColor(gray)
        c.setDash([2, 2])
        c.line(x, y - height / 2, x + width, y - height / 2)
        c.line(x + width / 2, y - height, x + width / 2, y)
        c.line(x, y - height, x + width, y)
        c.line(x, y, x + width, y - height)
        c.setDash([])
    
    def _draw_maths_grid(self, c, x, y, width, height):
        c.setLineWidth(1.0)
        c.setStrokeColor(black)
        
        c.line(x, y, x + width, y)
        c.line(x, y - height, x + width, y - height)
        
        center_x = x + width / 2
        gap = 5 * mm
        c.line(center_x - gap / 2, y, center_x - gap / 2, y - height)
        c.line(center_x + gap / 2, y, center_x + gap / 2, y - height)
    
    def _draw_page_header(self, c, margin_x, margin_y):
        c.setFont("SimSun", 10)
        c.drawString(margin_x + 5 * mm, A4[1] - margin_y + 5 * mm, "日期:_____年_____月____日")
    
    def _draw_page_number(self, c, current_page, total_pages, margin_x, margin_y):
        c.setFont("SimSun", 9)
        text = f"{current_page}/{total_pages}"
        c.drawRightString(A4[0] - margin_x - 5 * mm, margin_y - 6 * mm, text)