# dashang/dashang_ui.py — 打赏标签页 UI（纯展示，无交互按钮）
import os
import tkinter as tk
from tkinter import ttk

from constants import BG_COLOR
from dashang.dashang_core import WECHAT_QR_PATH, DEFAULT_THANKS, load_qr_image

TITLE_FONT = ("Microsoft YaHei", 18, "bold")
THANKS_FONT = ("Microsoft YaHei", 15, "bold")
CAPTION_FONT = ("宋体", 13)           # 图片下方说明：淡灰色宋体
CAPTION_COLOR = "#999999"            # 淡灰色


class DashangTabWidget:
    """打赏支持标签页：大字体致谢语 + 微信收款码展示（展示型，无按钮）。"""

    def __init__(self, parent):
        self.frame = ttk.Frame(parent)
        self._wechat_img = None   # 保留 PhotoImage 引用，避免被 GC
        self._init_ui()

    def _init_ui(self):
        # 标题
        tk.Label(self.frame, text="💝 打赏支持", font=TITLE_FONT,
                 bg=BG_COLOR, fg="#e11d48").pack(pady=(24, 10))

        # 致谢语（大字体标签，居中）
        tk.Label(self.frame, text=DEFAULT_THANKS, font=THANKS_FONT,
                 bg=BG_COLOR, fg="#333333", justify="center",
                 wraplength=460).pack(pady=(0, 18))

        # 微信收款码
        img = load_qr_image(WECHAT_QR_PATH)
        if img:
            self._wechat_img = img
            qr_label = tk.Label(self.frame, image=img, bg="#ffffff",
                                relief="groove", bd=2)
        else:
            if os.path.exists(WECHAT_QR_PATH):
                # 文件存在但加载失败：多半是 JPG 且未安装 Pillow
                reason = ("无法显示该 JPG 收款码\n请先安装 Pillow：\n"
                          "pip install pillow")
            else:
                reason = "未找到收款码图片：\n" + WECHAT_QR_PATH
            qr_label = tk.Label(self.frame, text=reason, bg="#ffffff",
                                relief="groove", bd=2, justify="center",
                                font=("Microsoft YaHei", 11),
                                width=26, height=14)
        qr_label.pack(pady=(0, 6))
        tk.Label(self.frame, text="微信赞赏码", bg=BG_COLOR,
                 font=CAPTION_FONT, fg=CAPTION_COLOR).pack(pady=(4, 0))
