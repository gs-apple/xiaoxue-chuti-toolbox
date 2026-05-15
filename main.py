# main.py — 小学出题工具箱 (tkinter 版)
import tkinter as tk
from tkinter import ttk
import sys

from widgets import GradientButton
from shuxue_ui import ShuxueTabWidget
from zi_tie_ui import ZiTieTabWidget
from zuowen_ui import ZuowenTabWidget
from zhenti_ui import ZhentiTabWidget


class MathGeneratorApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("小学出题工具箱")
        self.root.geometry("700x700")
        self.root.resizable(False, False)
        self._center()
        self._init_ui()

    def _center(self):
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"700x700+{x}+{y}")

    def _init_ui(self):
        style = ttk.Style()
        style.theme_use("default")
        BG = "#f0f0f0"
        self.root.configure(bg=BG)
        style.configure("TFrame", background=BG)
        style.configure("TLabelframe", background=BG)
        style.configure("TLabelframe.Label", background=BG, font=("Microsoft YaHei", 10, "bold"))
        style.configure("TNotebook", borderwidth=0, background=BG)
        # 现代风选项卡
        style.configure("TNotebook.Tab",
                         font=("Microsoft YaHei", 11, "bold"),
                         padding=[16, 6],
                         background="#e2e8f0", foreground="#475569")
        style.map("TNotebook.Tab",
                   background=[("selected", "#2563eb"), ("active", "#cbd5e1")],
                   foreground=[("selected", "#ffffff"), ("active", "#1e293b")])

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # 数学标签页
        self.math_tab = ShuxueTabWidget(notebook)
        notebook.add(self.math_tab.frame, text="  数学  ")

        # 字帖标签页
        self.zitie_tab = ZiTieTabWidget(notebook)
        notebook.add(self.zitie_tab.frame, text="  字帖  ")

        # 作文标签页
        self.zuowen_tab = ZuowenTabWidget(notebook)
        notebook.add(self.zuowen_tab.frame, text="  作文  ")

        # 真题下载标签页
        self.zhenti_tab = ZhentiTabWidget(notebook)
        notebook.add(self.zhenti_tab.frame, text="  真题下载  ")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = MathGeneratorApp()
    app.run()
