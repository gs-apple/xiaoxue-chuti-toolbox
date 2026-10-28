# dashang/dashang_core.py — 打赏模块核心：收款码图片加载
import base64
import io
import tkinter as tk

from dashang.qr_data import QR_PNG_B64

# 致谢语（展示用，大字体标签）
DEFAULT_THANKS = (
    "感谢您的使用与支持！\n"
    "如果这款小工具帮到了您或孩子，\n"
    "欢迎扫码打赏 ☕\n"
    "您的鼓励是我持续更新、免费分享的最大动力～"
)


def load_qr_image(max_size=260):
    """加载收款码图片（从内嵌 base64 解码，软件自带、不依赖外部文件）。

    优先使用 Pillow（缩放质量好）；未安装 Pillow 时回退到
    tkinter.PhotoImage（Tk 8.6 原生支持 base64 PNG）。失败返回 None。
    """
    try:
        from PIL import Image, ImageTk
        img = Image.open(io.BytesIO(base64.b64decode(QR_PNG_B64)))
        img.thumbnail((max_size, max_size))
        return ImageTk.PhotoImage(img)
    except ImportError:
        # 无 Pillow：tk.PhotoImage 直接吃 base64 PNG 数据
        try:
            return tk.PhotoImage(data=QR_PNG_B64)
        except Exception:
            return None
    except Exception:
        return None
