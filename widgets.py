# widgets.py — Shared UI components
import tkinter as tk


class GradientButton(tk.Canvas):
    def __init__(self, parent, text="", command=None,
                 width=120, height=32,
                 color_top="#3b82f6", color_mid="#2563eb", color_bot="#1d4ed8",
                 hover_top="#60a5fa", hover_mid="#3b82f6", hover_bot="#2563eb",
                 text_color="white", font=("Microsoft YaHei", 10, "bold"),
                 **kwargs):
        super().__init__(parent, width=width, height=height,
                         highlightthickness=0, bd=0, **kwargs)
        self._cmd = command
        self._btn_w = width
        self._btn_h = height
        self._colors = (color_top, color_mid, color_bot)
        self._hcolors = (hover_top, hover_mid, hover_bot)
        self._text_color = text_color
        self._font = font
        self._text = text
        self._disabled = False
        self._draw(*self._colors)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def config(self, **kw):
        if "text" in kw:
            self._text = kw.pop("text")
        if "state" in kw:
            state = kw.pop("state")
            self.set_disabled(state == "disabled")
        if kw:
            super().config(**kw)
        self._draw(*self._colors if not self._disabled else ("#94a3b8", "#94a3b8", "#94a3b8"))

    def _draw(self, c1, c2, c3, text_color=None):
        self.delete("all")
        h = self._btn_h
        t = h // 3
        self._gradient_band(0, t, c1, c2)
        self._gradient_band(t, t * 2, c2, c2)
        self._gradient_band(t * 2, h, c2, c3)
        tc = text_color or self._text_color
        self.create_text(self._btn_w // 2, h // 2, text=self._text,
                         fill=tc, font=self._font)

    def _gradient_band(self, y0, y1, c_start, c_end):
        r0, g0, b0 = self._hex_to_rgb(c_start)
        r1, g1, b1 = self._hex_to_rgb(c_end)
        for y in range(y0, y1):
            ratio = (y - y0) / max(y1 - y0 - 1, 1)
            r = int(r0 + (r1 - r0) * ratio)
            g = int(g0 + (g1 - g0) * ratio)
            b = int(b0 + (b1 - b0) * ratio)
            color = f"#{r:02x}{g:02x}{b:02x}"
            self.create_line(0, y, self._btn_w, y, fill=color)

    @staticmethod
    def _hex_to_rgb(hex_color):
        h = hex_color.lstrip("#")
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

    def _on_enter(self, e):
        if not self._disabled:
            self._draw(*self._hcolors)

    def _on_leave(self, e):
        if not self._disabled:
            self._draw(*self._colors)

    def _on_press(self, e):
        if not self._disabled:
            r, g, b = self._hex_to_rgb(self._colors[2])
            r, g, b = max(r - 30, 0), max(g - 30, 0), max(b - 30, 0)
            self._draw(f"#{r:02x}{g:02x}{b:02x}",
                       f"#{r:02x}{g:02x}{b:02x}",
                       f"#{r:02x}{g:02x}{b:02x}")

    def _on_release(self, e):
        if not self._disabled:
            self._draw(*self._hcolors)
            if self._cmd:
                self._cmd()

    def set_disabled(self, disabled=True):
        self._disabled = disabled
        if disabled:
            self._draw("#94a3b8", "#94a3b8", "#94a3b8", text_color="#cbd5e1")
            self.configure(cursor="")
        else:
            self._draw(*self._colors)
            self.configure(cursor="hand2")
