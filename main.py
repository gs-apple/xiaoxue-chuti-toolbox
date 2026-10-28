# main.py — 小学出题工具箱 (tkinter 版)
import sys
import ctypes
import tkinter as tk
from tkinter import ttk, messagebox

from shuxue.shuxue_ui import ShuxueTabWidget
from zitie.zi_tie_ui import ZiTieTabWidget
from zuowen.zuowen_ui import ZuowenTabWidget
from zhenti.zhenti_ui import ZhentiTabWidget
from yingyu.yingyu_ui import YingyuTabWidget
from quwei.quwei_ui import QuweiTabWidget
from dashang.dashang_ui import DashangTabWidget
from constants import BG_COLOR

# 版本信息（每10位进1，如 V1.0.10 -> V1.1.0）
VERSION = "V1.2.5"
APP_NAME = "小学出题工具箱"
APP_TITLE = f"{APP_NAME} {VERSION} —by:Shaowei"

# ---------- 禁止多开（Windows 命名互斥体） ----------
_MUTEX_NAME = "Local\\XiaoxueChutiToolbox_SingleInstance"
_mutex_handle = None  # 保持引用，进程存活期间互斥体一直持有
ERROR_ALREADY_EXISTS = 183


def acquire_single_instance():
    """创建命名互斥体；若已存在说明程序已在运行，返回 False。"""
    global _mutex_handle
    kernel32 = ctypes.windll.kernel32
    _mutex_handle = kernel32.CreateMutexW(None, False, _MUTEX_NAME)
    return kernel32.GetLastError() != ERROR_ALREADY_EXISTS


def activate_existing_window():
    """找到已运行实例的主窗口并激活到前台。返回是否成功。"""
    user32 = ctypes.windll.user32
    hwnd = user32.FindWindowW(None, APP_TITLE)
    if not hwnd:
        # 标题可能因版本不同而变化，按前缀模糊查找
        found = []

        @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        def _enum(h, _):
            buf = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(h, buf, 256)
            if buf.value.startswith(APP_NAME):
                found.append(h)
                return False
            return True

        user32.EnumWindows(_enum, None)
        hwnd = found[0] if found else None
    if hwnd:
        SW_RESTORE = 9
        if user32.IsIconic(hwnd):   # 最小化则先还原
            user32.ShowWindow(hwnd, SW_RESTORE)
        user32.SetForegroundWindow(hwnd)
        return True
    return False


class MathGeneratorApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(APP_TITLE)
        self.root.geometry("700x700")
        self.root.resizable(False, False)
        self.root.configure(bg=BG_COLOR)

        # 尺寸固定，可以直接在屏幕中央出现，不会"从左上角滑入"
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"700x700+{(sw - 700) // 2}+{(sh - 700) // 2}")
        self.root.update_idletasks()
        self.root.deiconify()
        self.root.update()

        self._init_ui()

        self.notebook.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.root.update()

    def _init_ui(self):
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

        # 使用 ttk.Notebook（构建完成后由 __init__ 统一 pack）
        self.notebook = ttk.Notebook(self.root)

        # 各标签页：「说明」放最前面，软件打开默认显示它
        tabs = (
            ("dashang_tab", DashangTabWidget, " 说 明 "),
            ("math_tab", ShuxueTabWidget, " 数 学 "),
            ("zitie_tab", ZiTieTabWidget, " 字 帖 "),
            ("zuowen_tab", ZuowenTabWidget, " 作 文 "),
            ("zhenti_tab", ZhentiTabWidget, " 真 题 "),
            ("yingyu_tab", YingyuTabWidget, " 英 语 "),
            ("quwei_tab", QuweiTabWidget, " 趣 味 "),
        )
        for attr, cls, text in tabs:
            widget = cls(self.notebook)
            setattr(self, attr, widget)
            self.notebook.add(widget.frame, text=text)
            self.root.update()
    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    if not acquire_single_instance():
        # 已有实例：把它的窗口拉到前台；找不到窗口才弹提示
        if not activate_existing_window():
            _tip = tk.Tk()
            _tip.withdraw()
            messagebox.showwarning(APP_NAME, f"{APP_NAME}已在运行，请勿重复打开！")
            _tip.destroy()
        sys.exit(0)
    app = MathGeneratorApp()
    app.run()
