# quwei/animals.py —— PDF 页角可爱简笔画装饰
# 移植自参考实现 core_animals.py（来源：小学生快乐神器9.7.exe 反编译还原）。
# 原版以 cm 为页面单位；本项目页面用 reportlab points，故坐标统一乘 cm 换算。
from reportlab.lib.units import cm


def draw_cat(c, x, y, s):
    c.setLineWidth(1.5)
    c.setStrokeColorRGB(0.3, 0.3, 0.3)
    c.circle(x, y - s * 0.1, s * 0.35)                                    # 脸
    c.line(x - s * 0.3, y + s * 0.25, x - s * 0.15, y + s * 0.45)         # 左耳
    c.line(x + s * 0.3, y + s * 0.25, x + s * 0.15, y + s * 0.45)         # 右耳
    c.circle(x - s * 0.15, y - s * 0.05, s * 0.06)                        # 左眼
    c.circle(x + s * 0.15, y - s * 0.05, s * 0.06)                        # 右眼
    c.line(x, y - s * 0.15, x, y - s * 0.2)                               # 鼻子
    c.line(x - s * 0.08, y - s * 0.25, x + s * 0.08, y - s * 0.25)        # 嘴


def draw_rabbit(c, x, y, s):
    c.setLineWidth(1.5)
    c.setStrokeColorRGB(0.3, 0.3, 0.3)
    c.ellipse(x - s * 0.2, y + s * 0.2, x + s * 0.2, y + s * 0.6)         # 中耳
    c.ellipse(x - s * 0.35, y + s * 0.2, x - s * 0.1, y + s * 0.7)        # 左耳
    c.ellipse(x + s * 0.1, y + s * 0.2, x + s * 0.35, y + s * 0.7)        # 右耳
    c.circle(x, y - s * 0.1, s * 0.3)                                     # 头
    c.circle(x - s * 0.1, y - s * 0.1, s * 0.05)                          # 左眼
    c.circle(x + s * 0.1, y - s * 0.1, s * 0.05)                          # 右眼
    c.ellipse(x - s * 0.05, y - s * 0.25, x + s * 0.05, y - s * 0.15)     # 鼻子


def draw_bear(c, x, y, s):
    c.setLineWidth(1.5)
    c.setStrokeColorRGB(0.3, 0.3, 0.3)
    c.circle(x, y + s * 0.3, s * 0.2)                                     # 头
    c.circle(x, y - s * 0.1, s * 0.35)                                    # 身体
    c.circle(x - s * 0.15, y - s * 0.05, s * 0.06)                        # 左眼
    c.circle(x + s * 0.15, y - s * 0.05, s * 0.06)                        # 右眼
    c.ellipse(x - s * 0.08, y - s * 0.2, x + s * 0.08, y - s * 0.12)      # 口鼻


def draw_bird(c, x, y, s):
    c.setLineWidth(1.5)
    c.setStrokeColorRGB(0.3, 0.3, 0.3)
    c.ellipse(x - s * 0.2, y - s * 0.1, x + s * 0.3, y + s * 0.15)        # 身体
    c.circle(x + s * 0.25, y + s * 0.05, s * 0.12)                        # 头
    c.line(x + s * 0.35, y + s * 0.05, x + s * 0.45, y + s * 0.05)        # 喙
    c.circle(x + s * 0.28, y + s * 0.08, s * 0.03)                        # 眼
    c.line(x - s * 0.2, y, x - s * 0.4, y + s * 0.1)                      # 尾羽上
    c.line(x - s * 0.2, y, x - s * 0.4, y - s * 0.05)                     # 尾羽下
    c.line(x, y - s * 0.1, x, y - s * 0.35)                               # 左腿
    c.line(x + s * 0.1, y - s * 0.1, x + s * 0.1, y - s * 0.35)           # 右腿


def draw_fish(c, x, y, s):
    c.setLineWidth(1.5)
    c.setStrokeColorRGB(0.3, 0.3, 0.3)
    c.ellipse(x - s * 0.3, y - s * 0.15, x + s * 0.2, y + s * 0.15)       # 身体
    c.line(x + s * 0.2, y, x + s * 0.45, y + s * 0.2)                     # 尾鳍上
    c.line(x + s * 0.2, y, x + s * 0.45, y - s * 0.2)                     # 尾鳍下
    c.line(x + s * 0.45, y + s * 0.2, x + s * 0.45, y - s * 0.2)          # 尾鳍边
    c.circle(x - s * 0.1, y + s * 0.02, s * 0.06)                         # 眼


def draw_butterfly(c, x, y, s):
    c.setLineWidth(1.5)
    c.setStrokeColorRGB(0.3, 0.3, 0.3)
    c.ellipse(x - s * 0.3, y, x, y + s * 0.35)                            # 左上翅
    c.ellipse(x, y, x + s * 0.3, y + s * 0.35)                            # 右上翅
    c.ellipse(x - s * 0.25, y - s * 0.05, x - s * 0.05, y - s * 0.25)     # 左下翅
    c.ellipse(x + s * 0.05, y - s * 0.05, x + s * 0.25, y - s * 0.25)     # 右下翅
    c.line(x, y + s * 0.35, x, y - s * 0.15)                              # 身体
    c.line(x, y + s * 0.35, x - s * 0.1, y + s * 0.45)                    # 左触角
    c.line(x, y + s * 0.35, x + s * 0.1, y + s * 0.45)                    # 右触角


def draw_snail(c, x, y, s):
    c.setLineWidth(1.5)
    c.setStrokeColorRGB(0.3, 0.3, 0.3)
    c.circle(x + s * 0.1, y + s * 0.05, s * 0.25)                         # 壳外圈
    c.circle(x + s * 0.1, y + s * 0.05, s * 0.15)                         # 壳内圈
    c.line(x - s * 0.15, y + s * 0.05, x - s * 0.35, y - s * 0.2)         # 身体
    c.line(x - s * 0.35, y - s * 0.2, x - s * 0.25, y - s * 0.25)         # 尾部
    c.circle(x - s * 0.22, y - s * 0.28, s * 0.05)                        # 触角头


def draw_duck(c, x, y, s):
    c.setLineWidth(1.5)
    c.setStrokeColorRGB(0.3, 0.3, 0.3)
    c.ellipse(x - s * 0.15, y - s * 0.1, x + s * 0.25, y + s * 0.15)      # 身体
    c.circle(x + s * 0.25, y + s * 0.1, s * 0.15)                         # 头
    c.line(x + s * 0.38, y + s * 0.08, x + s * 0.5, y + s * 0.12)         # 嘴上
    c.line(x + s * 0.38, y + s * 0.12, x + s * 0.5, y + s * 0.12)         # 嘴下
    c.circle(x + s * 0.32, y + s * 0.15, s * 0.03)                        # 眼
    c.line(x - s * 0.1, y - s * 0.1, x - s * 0.1, y - s * 0.35)           # 左腿
    c.line(x + s * 0.1, y - s * 0.1, x + s * 0.1, y - s * 0.35)           # 右腿


ANIMAL_DRAWINGS = {
    'cat': draw_cat,
    'rabbit': draw_rabbit,
    'bear': draw_bear,
    'bird': draw_bird,
    'fish': draw_fish,
    'butterfly': draw_butterfly,
    'snail': draw_snail,
    'duck': draw_duck,
}
ANIMAL_KEYS = list(ANIMAL_DRAWINGS.keys())


def draw_cute_animal(c, page_width, page_height, page_num):
    """在 PDF 页面右下角按页码轮换画一只小动物（页角装饰）。"""
    key = ANIMAL_KEYS[page_num % len(ANIMAL_KEYS)]
    x = page_width - 0.529167 * cm      # 距右边约 0.53cm
    y = 0.423334 * cm                   # 距底边约 0.42cm
    size = 0.282222 * cm
    ANIMAL_DRAWINGS[key](c, x, y, size)
