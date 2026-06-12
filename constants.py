# constants.py — 公共常量定义
# 所有模块共享的常量集中管理

import sys
import os

# ══════════════════════════════════════════════════════════
#  路径常量
# ══════════════════════════════════════════════════════════

# 项目根目录（兼容 PyInstaller 编译：exe 所在目录即为项目根）
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 字体目录
FONTS_DIR = os.path.join(BASE_DIR, 'assets', 'fonts')

# 数据文件
STROKE_DATA_FILE = os.path.join(BASE_DIR, 'assets', 'stroke_data.json')

# 真题下载目录（保存到项目根目录）
ZHENTI_DIR = BASE_DIR

# ══════════════════════════════════════════════════════════
#  UI 常量
# ══════════════════════════════════════════════════════════

# 背景色
BG_COLOR = "#f0f0f0"

# 主题色
PRIMARY_COLOR = "#2563eb"
PRIMARY_HOVER = "#1d4ed8"

# 字体
DEFAULT_FONT = ("Microsoft YaHei", 10)
DEFAULT_FONT_BOLD = ("Microsoft YaHei", 10, "bold")
TITLE_FONT = ("Microsoft YaHei", 12, "bold")

# 按钮样式
BUTTON_WIDTH = 100
BUTTON_HEIGHT = 32

# ══════════════════════════════════════════════════════════
#  年级映射
# ══════════════════════════════════════════════════════════

# 年级名称列表
GRADES = ["一年级", "二年级", "三年级", "四年级", "五年级", "六年级",
          "七年级", "八年级", "九年级", "高一", "高二", "高三"]

# 年级名称 -> 数字
GRADE_MAP = {
    "一年级": "1", "二年级": "2", "三年级": "3",
    "四年级": "4", "五年级": "5", "六年级": "6",
    "七年级": "7", "八年级": "8", "九年级": "9",
    "高一": "10", "高二": "11", "高三": "12",
}

# 数字 -> 年级名称
GRADE_MAP_REVERSE = {v: k for k, v in GRADE_MAP.items()}

# 年级关键词映射（用于搜索解析）
GRADE_KEYWORDS = {
    "一年级": "1", "二年级": "2", "三年级": "3",
    "四年级": "4", "五年级": "5", "六年级": "6",
    "七年级": "7", "八年级": "8", "九年级": "9",
    "高一": "10", "高二": "11", "高三": "12",
    "一年": "1", "二年": "2", "三年": "3",
    "四年": "4", "五年": "5", "六年": "6",
    "七年": "7", "八年": "8", "九年": "9",
}

# 学科关键词映射（用于搜索解析）
SUBJECT_KEYWORDS = {
    "语文": "语文", "数学": "数学", "英语": "英语",
    "物理": "物理", "化学": "化学", "生物": "生物",
    "历史": "历史", "地理": "地理", "政治": "政治",
    "道德与法治": "道德与法治", "道法": "道德与法治",
    "科学": "科学",
}

# ══════════════════════════════════════════════════════════
#  字体路径
# ══════════════════════════════════════════════════════════

# Windows 字体路径
WINDOWS_FONTS = [
    r'C:\Windows\Fonts\simkai.ttf',
    r'C:\Windows\Fonts\simsun.ttc',
    r'C:\Windows\Fonts\simhei.ttf',
    r'C:\Windows\Fonts\msyh.ttc',
    r'C:\Windows\Fonts\simfang.ttf',
    r'C:\Windows\Fonts\arial.ttf',
]

# 项目内置字体
BUILTIN_FONTS = [
    os.path.join(FONTS_DIR, 'kaiti_gb2312.ttf'),
    os.path.join(FONTS_DIR, 'simkai.ttf'),
]

# ══════════════════════════════════════════════════════════
#  爬虫常量
# ══════════════════════════════════════════════════════════

# 爬虫平台 URL
CRAWLER_URLS = {
    "shijuan1": "https://www.shijuan1.com",
    "szxuexiao": "https://appsj.szxuexiao.com",
    "yishijuan": "https://www.yishijuan.com",
    "shijuan_net": "https://www.shijuan.net",
    "xbjy": "https://www.xbjy.com",
}

# 请求头
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# 请求超时（秒）
REQUEST_TIMEOUT = 15

# ══════════════════════════════════════════════════════════
#  文件名常量
# ══════════════════════════════════════════════════════════

# 收藏夹文件
FAVORITES_FILE = os.path.join(BASE_DIR, "zhenti", ".zhenti_favorites.json")

# 搜索历史文件
HISTORY_FILE = os.path.join(BASE_DIR, "zhenti", ".zhenti_history.json")

# 题目缓存文件
QUESTION_CACHE_FILE = os.path.join(BASE_DIR, "shuxue", ".question_cache.json")
