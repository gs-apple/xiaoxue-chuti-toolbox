# dashang/dashang_ui.py — 打赏标签页：右上角收款码 + 软件功能介绍
import tkinter as tk
from tkinter import ttk

from constants import BG_COLOR
from dashang.dashang_core import DEFAULT_THANKS, load_qr_image

TITLE_FONT = ("Microsoft YaHei", 18, "bold")
THANKS_FONT = ("Microsoft YaHei", 13)
FEATURE_TITLE_FONT = ("Microsoft YaHei", 14, "bold")
FEATURE_FONT = ("Microsoft YaHei", 12)
CAPTION_FONT = ("宋体", 11)           # 二维码下方说明：淡灰色宋体
CAPTION_COLOR = "#999999"            # 淡灰色
QR_SIZE = 112                        # 约 3cm 见方

# 软件功能一览（左列=标签页名，右列=功能说明）
FEATURES = (
    ("数 学", "口算练习卷生成：加减法 / 乘法 / 除法 / 四则混合，"
              "涵盖计算、应用、几何、数论、逻辑各类题型，附答案页"),
    ("字 帖", "汉字笔顺字帖：多种字体与样式，支持自定义生字内容"),
    ("作 文", "各年级作文题目与例文库，按单元 / 学期选择"),
    ("真 题", "五大试卷网站真题搜索与下载"),
    ("英 语", "英语单词 / 课文字帖（四线三格），人教版与陕旅版"),
    ("趣 味", "简笔画 / 迷宫运笔 / 数独 / 幻方"),
)


class DashangTabWidget:
    """打赏支持标签页：右上角小收款码，其余区域展示软件功能。"""

    def __init__(self, parent):
        self.frame = ttk.Frame(parent)
        self._wechat_img = None   # 保留 PhotoImage 引用，避免被 GC
        self._init_ui()

    def _init_ui(self):
        # ── 右上角：收款码（内嵌在软件里，约 3cm 见方）────────────
        img = load_qr_image(QR_SIZE)
        if img:
            self._wechat_img = img
            qr = tk.Label(self.frame, image=img, bg="#ffffff",
                          relief="groove", bd=2)
        else:
            qr = tk.Label(self.frame, text="收款码加载失败\n请重新安装或反馈",
                          bg="#ffffff", relief="groove", bd=2,
                          justify="center", font=("Microsoft YaHei", 10),
                          width=12, height=6)
        qr.place(relx=1.0, rely=0.0, x=-14, y=14, anchor="ne")
        tk.Label(self.frame, text="微信赞赏码", bg=BG_COLOR,
                 font=CAPTION_FONT, fg=CAPTION_COLOR,
                 ).place(relx=1.0, rely=0.0,
                         x=-14 - QR_SIZE // 2, y=14 + QR_SIZE + 6,
                         anchor="n", width=QR_SIZE + 8)

        # ── 左上：标题 + 致谢语 ────────────────────────────────
        tk.Label(self.frame, text="💝 打赏支持", font=TITLE_FONT,
                 bg=BG_COLOR, fg="#e11d48", anchor="w",
                 ).pack(anchor="w", padx=18, pady=(20, 4))
        tk.Label(self.frame, text=DEFAULT_THANKS, font=THANKS_FONT,
                 bg=BG_COLOR, fg="#333333", justify="left", anchor="w",
                 wraplength=430).pack(anchor="w", padx=18, pady=(0, 14))

        # ── 中部：软件功能介绍 ─────────────────────────────────
        tk.Label(self.frame, text="软件功能", font=FEATURE_TITLE_FONT,
                 bg=BG_COLOR, fg="#1d4ed8", anchor="w",
                 ).pack(anchor="w", padx=18, pady=(2, 4))
        for name, desc in FEATURES:
            row = tk.Frame(self.frame, bg=BG_COLOR)
            row.pack(anchor="w", padx=18, pady=2)
            tk.Label(row, text=name, font=("Microsoft YaHei", 12, "bold"),
                     bg=BG_COLOR, fg="#000000", width=5, anchor="w").pack(side="left")
            tk.Label(row, text=desc, font=FEATURE_FONT,
                     bg=BG_COLOR, fg="#444444", justify="left", anchor="w",
                     wraplength=460).pack(side="left", padx=(2, 0))
