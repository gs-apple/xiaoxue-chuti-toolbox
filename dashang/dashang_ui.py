# dashang/dashang_ui.py — 打赏标签页：右上角收款码 + 分组栏（打赏支持/软件功能/安全提醒）
import tkinter as tk
from tkinter import ttk

from constants import BG_COLOR
from dashang.dashang_core import DEFAULT_THANKS, load_qr_image

TITLE_FONT = ("Microsoft YaHei", 13, "bold")
THANKS_FONT = ("Microsoft YaHei", 11)
THANKS_COLOR = "#333333"
SPECIAL_FONT = ("Microsoft YaHei", 11, "bold")
SPECIAL_COLOR = "#7c3aed"            # 特别感谢：紫色
FEATURE_FONT = ("Microsoft YaHei", 10)
FEATURE_NAME_FONT = ("Microsoft YaHei", 10, "bold")
FEATURE_NAME_COLOR = "#1d4ed8"
SAFE_FONT = ("Microsoft YaHei", 15, "bold")
SAFE_COLOR = "#dc2626"               # 安全提醒：红色大字
CAPTION_FONT = ("宋体", 11)           # 二维码下方说明：淡灰色宋体
CAPTION_COLOR = "#999999"            # 淡灰色
QR_SIZE = 112                        # 约 3cm 见方

# 软件功能一览（左列=标签页名，右列=功能说明；中文里不要夹空格，避免换行断点）
FEATURES = (
    ("数 学", "口算/竖式练习卷一键生成：加减法、乘法、除法、四则混合四种模式，"
              "覆盖计算、应用、几何、数论、逻辑五大题型，可调题量难度，"
              "自动生成答案页，A4直接打印"),
    ("字 帖", "汉字笔顺字帖生成：多种字体与格子样式可选，支持自定义生字、"
              "词语内容，逐笔演示笔顺，打印后照帖练字"),
    ("作 文", "同步课本的作文题目库与范文例文：按年级/学期/单元选择题目，"
              "附字数要求与写作提示，可参考例文学布局"),
    ("真 题", "五大试卷网站真题一站搜索：按年级、学科、年份筛选，"
              "结果可直接打开页面下载试卷与答案"),
    ("英 语", "英语单词/课文练习生成：人教版(PEP)与陕旅版课本同步，"
              "单词按四线三格排版，支持音标默写、课文抄写"),
    ("趣 味", "四种益智游戏：简笔画分步临摹、迷宫运笔、数独、幻方，"
              "随机出题，可打印成纸质练习"),
)


class DashangTabWidget:
    """打赏标签页：右上角小收款码 + 三个分组栏（打赏支持/软件功能/安全提醒）。"""

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
        qr.place(relx=1.0, rely=0.0, x=-14, y=10, anchor="ne")
        tk.Label(self.frame, text="微信赞赏码", bg=BG_COLOR,
                 font=CAPTION_FONT, fg=CAPTION_COLOR,
                 ).place(relx=1.0, rely=0.0,
                         x=-14 - QR_SIZE // 2, y=10 + QR_SIZE + 4,
                         anchor="n", width=QR_SIZE + 8)

        # 首个分组让出右上角二维码的位置（右侧留 ~150px）
        top_padx = (16, 156)

        # ── 分组栏一：打赏支持 ─────────────────────────────────
        g1 = tk.LabelFrame(self.frame, text=" 💝 打赏支持 ",
                           font=TITLE_FONT, bg=BG_COLOR, fg="#e11d48")
        g1.pack(fill="x", padx=top_padx, pady=(8, 4))
        tk.Label(g1, text=DEFAULT_THANKS, font=THANKS_FONT,
                 bg=BG_COLOR, fg=THANKS_COLOR, justify="left", anchor="w",
                 wraplength=410).pack(anchor="w", padx=10, pady=(4, 2))
        tk.Label(g1, text="⭐ 特别感谢：52pojie 的 王丶 先生",
                 font=SPECIAL_FONT, bg=BG_COLOR, fg=SPECIAL_COLOR,
                 anchor="w").pack(anchor="w", padx=10)
        tk.Label(g1, text="趣味模块基本复刻了他的思路，向大神致敬！",
                 font=THANKS_FONT, bg=BG_COLOR, fg=SPECIAL_COLOR,
                 anchor="w").pack(anchor="w", padx=10, pady=(1, 6))

        # ── 分组栏二：软件功能 ─────────────────────────────────
        g2 = tk.LabelFrame(self.frame, text=" 📋 软件功能 ",
                           font=TITLE_FONT, bg=BG_COLOR, fg="#1d4ed8")
        g2.pack(fill="x", padx=16, pady=4)
        for name, desc in FEATURES:
            row = tk.Frame(g2, bg=BG_COLOR)
            row.pack(anchor="w", padx=10, pady=2)
            tk.Label(row, text=name, font=FEATURE_NAME_FONT,
                     bg=BG_COLOR, fg=FEATURE_NAME_COLOR,
                     width=5, anchor="w").pack(side="left")
            tk.Label(row, text=desc, font=FEATURE_FONT,
                     bg=BG_COLOR, fg="#444444", justify="left", anchor="w",
                     wraplength=475).pack(side="left", padx=(2, 0))

        # ── 分组栏三：安全提醒 ─────────────────────────────────
        g3 = tk.LabelFrame(self.frame, text=" ⚠️ 安全提醒 ",
                           font=TITLE_FONT, bg=BG_COLOR, fg=SAFE_COLOR)
        g3.pack(fill="x", padx=16, pady=(4, 8))
        tk.Label(g3, text="本软件纯免费，不收任何费用！",
                 font=SAFE_FONT, bg=BG_COLOR, fg=SAFE_COLOR,
                 ).pack(pady=(2, 6))
