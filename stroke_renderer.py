# -*- coding: utf-8 -*-
"""
笔顺渲染核心模块 v2 - 基于本地 SVG 文件
直接使用 makemeahanzi 的 SVG 笔顺文件进行高质量渲染

数据源: makemeahanzi-master/svgs/*.svg (每个汉字一个SVG，含逐笔路径)
渲染引擎: Pillow + SVG path 解析 (纯 Python，无外部依赖)
"""

import os
import re
import math
import io
from PIL import Image, ImageDraw, ImageFont, ImageFilter


class StrokeRenderer:
    """汉字笔顺渲染器 - 从本地 SVG 文件生成逐步叠加式笔顺图片"""

    def __init__(self, svg_dir=None):
        """
        Args:
            svg_dir: SVG文件目录路径 (默认: ./makemeahanzi-master/svgs/)
        """
        if svg_dir is None:
            base = os.path.dirname(os.path.abspath(__file__))
            svg_dir = os.path.join(base, 'makemeahanzi-master', 'svgs')

        self._svg_dir = svg_dir
        self._cache = {}  # 缓存解析后的笔画路径
        self._font_cache = {}

    def has_stroke_data(self, char):
        """检查是否有该字的SVG笔顺数据"""
        code = ord(char)
        return os.path.exists(os.path.join(self._svg_dir, f'{code}.svg'))

    def get_stroke_count(self, char):
        """获取笔画数（返回 -1 表示无数据）"""
        paths = self._get_stroke_paths(char)
        return len(paths) if paths else -1

    def _parse_svg_paths(self, svg_text):
        """
        解析 SVG 文本，提取所有笔画的矢量路径
        
        返回: list of str, 每个元素是一笔的 SVG path d= 属性值
              只返回实际的笔画路径（以 M 开头的坐标序列）
        """
        # 提取所有 d="..." 属性值
        all_paths = re.findall(r'd="([^"]+)"', svg_text)

        # 过滤 + 去重: 只保留包含贝塞尔曲线(Q/C)的真实笔画轮廓路径
        # (SVG中每笔出现2次: 轮廓+动画; 纯L的是辅助线; clip/animation是引用)
        stroke_paths = []
        seen_fingerprints = set()

        for p in all_paths:
            stripped = p.strip()
            if not re.match(r'^M\s*[\d]', stripped):
                continue
            # 必须含曲线命令 Q 或 C（笔画轮廓特征）
            if 'Q' not in stripped and 'C' not in stripped:
                continue
            if len(stripped) < 30:
                continue
            # 指纹去重: 每笔只保留一条
            fp = stripped[:60]
            if fp in seen_fingerprints:
                continue
            seen_fingerprints.add(fp)
            stroke_paths.append(stripped)

        return stroke_paths

    def _get_stroke_paths(self, char):
        """获取汉字的所有笔画路径（带缓存）"""
        if char in self._cache:
            return self._cache[char]

        code = ord(char)
        filepath = os.path.join(self._svg_dir, f'{code}.svg')

        if not os.path.exists(filepath):
            return []

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read()

            paths = self._parse_svg_paths(text)
            self._cache[char] = paths
            return paths
        except Exception:
            return []

    @staticmethod
    def _parse_svg_path_d(path_str):
        """
        解析 SVG path 的 d 属性字符串为命令列表。
        
        支持的命令: M (moveto), L (lineto), Q (二次贝塞尔), T (平滑二次贝塞尔),
                    C (三次贝塞尔), S (平滑三次贝塞尔), Z (闭合)
        
        返回: list of tuples, 每个元素是 (cmd, [(x,y), ...])
               例如 [('M', [(100,200)]), ('L', [(300,400)]), ('Q', [(100,200), (300,400)])]
        """
        commands = []
        
        # 匹配命令字母和后续数字参数
        tokens = re.findall(r'([MLHVCSQTZmlhvcsqtz])\s*|([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)', path_str)
        
        current_cmd = None
        numbers = []

        for cmd_token, num_token in tokens:
            if cmd_token:
                # 遇到新命令时，保存之前的命令
                if current_cmd is not None and numbers:
                    coords = [(float(numbers[i]), float(numbers[i+1])) 
                              for i in range(0, len(numbers)-1, 2)]
                    commands.append((current_cmd.upper(), coords))
                
                current_cmd = cmd_token
                numbers = []
            elif num_token != '':
                numbers.append(float(num_token))

        # 最后一个命令
        if current_cmd is not None and numbers:
            coords = [(float(numbers[i]), float(numbers[i+1])) 
                      for i in range(0, len(numbers)-1, 2)]
            commands.append((current_cmd.upper(), coords))

        return commands

    def _flatten_path_to_points(self, commands, steps_per_segment=8):
        """
        将 SVG path 命令展平为一系列采样点坐标。
        
        Args:
            commands: _parse_svg_path_d 返回的命令列表
            steps_per_segment: 每段曲线的采样步数
        
        Returns:
            list of (x, y) 坐标点
        """
        points = []
        current_x, current_y = 0.0, 0.0
        last_ctrl_x, last_ctrl_y = 0.0, 0.0
        first_x, first_y = 0.0, 0.0

        for cmd, coords in commands:
            if cmd == 'M':  # Moveto
                if points and coords:
                    # 如果之前有点，说明是新子路径的开始
                    pass
                for (x, y) in coords:
                    current_x, current_y = x, y
                    first_x, first_y = x, y
                    points.append((x, y))

            elif cmd == 'L':  # Lineto
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

            elif cmd == 'H':  # Horizontal lineto
                for (x,) in coords:
                    dx = x - current_x
                    dist = abs(dx)
                    steps = max(3, int(dist / 15 * steps_per_segment))
                    for s in range(1, steps + 1):
                        t = s / steps
                        points.append((current_x + dx * t, current_y))
                    current_x = x

            elif cmd == 'V':  # Vertical lineto
                for (y,) in coords:
                    dy = y - current_y
                    dist = abs(dy)
                    steps = max(3, int(dist / 15 * steps_per_segment))
                    for s in range(1, steps + 1):
                        t = s / steps
                        points.append((current_x, current_y + dy * t))
                    current_y = y

            elif cmd == 'Q':  # Quadratic bezier
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

            elif cmd == 'T':  # Smooth quadratic
                for (ex, ey) in coords:
                    # 推算控制点：反射上一个控制点
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

            elif cmd == 'C':  # Cubic bezier
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

            elif cmd == 'S':  # Smooth cubic
                for i in range(0, len(coords), 2):
                    ex, ey = coords[i]
                    if i + 1 < len(coords):
                        c2x, c2y = coords[i+1]
                    else:
                        c2x, c2y = ex, ey
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

            elif cmd == 'Z':  # Close path
                if (abs(current_x - first_x) > 0.1 or abs(current_y - first_y) > 0.1):
                    points.append((first_x, first_y))
                current_x, current_y = first_x, first_y

        return points

    def _transform_points(self, points, grid_size, padding_ratio=0.08):
        """
        将 SVG 坐标系 (1024x1024) 变换到输出图像坐标系。
        
        makemeahanzi SVG: viewBox="0 0 1024 1024"
        笔画组使用: transform="scale(1, -1) translate(0, -900)"
        即 Y轴翻转 + 向上平移 900 单位。
        """
        if not points:
            return []

        usable = grid_size * (1 - 2 * padding_ratio)
        offset = grid_size * padding_ratio
        scale = usable / 1024.0

        result = []
        for (x, y) in points:
            # 应用与 SVG 相同的变换: Y翻转 + 平移
            # new_y = 900 - y
            sx = x * scale + offset
            sy = (900 - y) * scale + offset
            result.append((sx, sy))

        return result

    def _get_kaiti_font(self, size):
        """获取指定大小的楷体字体（带缓存）"""
        cache_key = f"kaiti_{size}"
        if cache_key in self._font_cache:
            return self._font_cache[cache_key]
        
        font_candidates = [
            os.path.join(os.path.dirname(__file__), 'fonts', '楷体_GB2312.ttf'),
            os.path.join(os.path.dirname(__file__), 'fonts', 'simkai.ttf'),
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
        """
        使用楷体字体渲染单个汉字。
        返回居中的 RGBA 图像。
        """
        font_size = int(grid_size * 0.75)
        font = self._get_kaiti_font(font_size)
        
        img = Image.new('RGBA', (grid_size, grid_size), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        
        # 计算文字居中位置（粗略估算）
        bbox = draw.textbbox((0, 0), char, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (grid_size - tw) / 2 - bbox[0]
        y = (grid_size - th) / 2 - bbox[1] + grid_size * 0.02
        
        color_rgba = (*color, alpha)
        draw.text((x, y), char, font=font, fill=color_rgba)
        
        return img

    def render_strokes_to_image(self, char, grid_size=200,
                                 up_to_stroke=-1,
                                 stroke_color=(45, 50, 55),
                                 stroke_width_ratio=0.038,
                                 mode='svg'):
        """
        渲染单个汉字的笔顺到 PIL Image（逐步叠加模式）。

        使用 SVG 封闭轮廓填充方式渲染，每笔都是有粗细的实心形状，
        而非单线条描边，从而呈现毛笔/钢笔书写质感。

        Args:
            char: 汉字
            grid_size: 输出图片边长(px)
            up_to_stroke: 渲染到第几笔 (-1=全部笔画)
            stroke_color: 笔画颜色 (R,G,B)
            stroke_width_ratio: (保留参数，polygon模式下自动计算)
            mode: 'svg'=矢量路径渲染, 'font'=字体渲染

        Returns:
            PIL.Image (RGBA), 无数据则返回 None
        """
        all_paths = self._get_stroke_paths(char)

        # 如果没有 SVG 数据，自动回退到字体模式
        if not all_paths or mode == 'font':
            return self._render_font_mode(char, grid_size, up_to_stroke, stroke_color)

        if up_to_stroke < 0:
            up_to_stroke = len(all_paths)

        img = Image.new('RGBA', (grid_size, grid_size), (255, 255, 255, 0))

        color_with_alpha = (*stroke_color, 235)  # 高不透明度，接近实心

        for idx in range(min(up_to_stroke, len(all_paths))):
            path_str = all_paths[idx]
            commands = self._parse_svg_path_d(path_str)
            raw_points = self._flatten_path_to_points(commands, steps_per_segment=6)

            if raw_points:
                points = self._transform_points(raw_points, grid_size)
                if len(points) >= 3:
                    # 使用 polygon 填充封闭轮廓 — 这是有宽度的实心笔画！
                    draw = ImageDraw.Draw(img)
                    draw.polygon(points, fill=color_with_alpha)

        return img

    def _render_font_mode(self, char, grid_size, up_to_stroke, stroke_color):
        """
        字体回退模式: 用楷体渲染汉字，通过透明度变化模拟笔顺效果。
        
        策略:
          - 参考字(完整): 黑色实心
          - 过程字: 浅灰色半透明描摹字
          - 每一步都显示完整的浅色字（因为无法真正拆分笔画）
          
        注意: 此模式下无法显示真正的逐步叠加笔顺，
              但视觉效果接近参考项目 charprac 的描摹模式。
        """
        alpha = 200  # 半透明
        return self.render_font_char(char, grid_size, 
                                      color=stroke_color, alpha=alpha)

    def render_full_sequence_for_pdf(self, char, grid_size=200, cols=6,
                                      first_char_color=(20, 20, 20),
                                      stroke_color=(45, 50, 55),
                                      stroke_width_ratio=0.035):
        """
        渲染完整一行笔顺序列用于嵌入 PDF 田字格。

        格式: [参考字(黑)] [第1笔] [第1+2笔] [第1+2+3笔] ... [空白格]

        混合渲染策略:
          - 第一格(参考字): 楷体字体渲染，黑色实心
          - 后续格(笔顺步骤): SVG矢量轮廓填充逐步叠加（有粗细的实心笔画）

        Args:
            char: 汉字
            grid_size: 每个格子的像素尺寸
            cols: 总列数
            first_char_color: 参考字颜色 (深黑)
            stroke_color: 过程字的笔画颜色 (深灰近墨)

        Returns:
            list of PIL.Image, 长度为 cols; 无数据返回 None
        """
        all_paths = self._get_stroke_paths(char)
        
        if not all_paths:
            # 无 SVG 数据时全部使用字体模式
            images = []
            ref = self.render_font_char(char, grid_size, color=first_char_color, alpha=255)
            images.append(ref)
            for _ in range(1, cols):
                light = self.render_font_char(char, grid_size, color=(180, 180, 185), alpha=160)
                images.append(light)
            return images[:cols]

        total_strokes = len(all_paths)
        images = []

        # 第一格: 楷体字体渲染的完整参考字（黑色实心）
        ref_img = self.render_font_char(char, grid_size, color=first_char_color, alpha=255)
        images.append(ref_img)

        # 后续格: SVG矢量路径逐步叠加（最多 cols-1 个步骤格 + 1个完整字格）
        max_steps = cols - 2  # 留一格给最终完整字
        for step in range(1, min(max_steps, total_strokes) + 1):
            step_img = self.render_strokes_to_image(
                char, grid_size,
                up_to_stroke=step,
                stroke_color=stroke_color,
                stroke_width_ratio=stroke_width_ratio
            )
            images.append(step_img)

        # 最后一格(或步骤不够时的填充): 全部笔画的完整字
        full_img = self.render_strokes_to_image(
            char, grid_size,
            up_to_stroke=-1,  # 所有笔画
            stroke_color=stroke_color,
            stroke_width_ratio=stroke_width_ratio
        )
        images.append(full_img)

        # 补充空白格，确保始终返回正好 cols 个 Image
        while len(images) < cols:
            empty = Image.new('RGBA', (grid_size, grid_size), (255, 255, 255, 0))
            images.append(empty)

        return images[:cols]

    def image_to_bytes(self, img, format='PNG'):
        """将 PIL Image 转为字节流（用于 reportlab 嵌入）"""
        buf = io.BytesIO()
        img.save(buf, format=format)
        buf.seek(0)
        return buf


def create_stroke_renderer(svg_dir=None):
    """工厂函数: 创建渲染器实例"""
    return StrokeRenderer(svg_dir=svg_dir)
