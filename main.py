# main.py — 小学出题工具箱 (tkinter 版)
import tkinter as tk
from tkinter import ttk

from shuxue.shuxue_ui import ShuxueTabWidget
from zitie.zi_tie_ui import ZiTieTabWidget
from zuowen.zuowen_ui import ZuowenTabWidget
from zhenti.zhenti_ui import ZhentiTabWidget
from constants import BG_COLOR

# 版本信息（每10位进1，如 V1.0.10 -> V1.1.0）
VERSION = "V1.1.1"
APP_NAME = "小学出题工具箱"


class MathGeneratorApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} {VERSION}")
        self.root.geometry("700x700")
        self.root.resizable(False, False)
        self.root.withdraw()  # 先隐藏，避免窗口从左上角滑入
        self._init_ui()
        self._center()  # UI 构建完成后再居中
        self.root.deiconify()  # 居中后再显示

    def _center(self):
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"+{x}+{y}")

    def _init_ui(self):
        self.root.configure(bg=BG_COLOR)

        # 配置选项卡样式
        style = ttk.Style()
        style.configure("TNotebook",
                        background=BG_COLOR,
                        borderwidth=0)
        style.configure("TNotebook.Tab",
                        font=("Microsoft YaHei", 12),
                        padding=[14, 3],
                        background="#93c5fd",
                        foreground="#000000")
        style.map("TNotebook.Tab",
                  background=[("selected", "#3b82f6"), ("active", "#60a5fa")],
                  foreground=[("selected", "#000000"), ("active", "#000000")])

        # 使用 ttk.Notebook
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # 数学标签页
        self.math_tab = ShuxueTabWidget(notebook)
        notebook.add(self.math_tab.frame, text=" 数 学 ")

        # 字帖标签页
        self.zitie_tab = ZiTieTabWidget(notebook)
        notebook.add(self.zitie_tab.frame, text=" 字 帖 ")

        # 作文标签页
        self.zuowen_tab = ZuowenTabWidget(notebook)
        notebook.add(self.zuowen_tab.frame, text=" 作 文 ")

        # 真题下载标签页
        self.zhenti_tab = ZhentiTabWidget(notebook)
        notebook.add(self.zhenti_tab.frame, text=" 真 题 ")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = MathGeneratorApp()
    app.run()
