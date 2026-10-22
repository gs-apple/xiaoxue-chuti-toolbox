# dashang/dashang_core.py — 打赏模块核心：收款码图片加载
import os
import tkinter as tk

try:
    from constants import BASE_DIR
except Exception:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 微信赞赏码（收款码）固定路径 —— 用户下载到桌面，直接使用
WECHAT_QR_PATH = r"C:\Users\Administrator\Desktop\微信图片_20260724222749_9_59.png"

# 致谢语（展示用，大字体标签）
DEFAULT_THANKS = (
    "感谢您的使用与支持！\n"
    "如果这款小工具帮到了您或孩子，\n"
    "欢迎扫码打赏 ☕\n"
    "您的鼓励是我持续更新、免费分享的最大动力～"
)


def load_qr_image(path, max_size=260):
    """加载收款码图片。

    优先使用 Pillow（支持 JPG/PNG 等格式并缩放）；
    若未安装 Pillow，回退到 tkinter.PhotoImage（仅支持 PNG/GIF）。
    文件不存在或加载失败时返回 None。
    """
    if not path or not os.path.exists(path):
        return None
    try:
        from PIL import Image, ImageTk
        img = Image.open(path).convert("RGBA")
        img.thumbnail((max_size, max_size))
        return ImageTk.PhotoImage(img)
    except ImportError:
        # 无 Pillow：仅能处理 PNG/GIF；JPG 会失败，由调用方给出提示
        try:
            return tk.PhotoImage(file=path)
        except Exception:
            return None
    except Exception:
        return None
