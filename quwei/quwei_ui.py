# quwei/quwei_ui.py — 趣味选项卡：内嵌 4 个子选项卡（简笔画 / 迷宫运笔 / 数独 / 幻方）
import tkinter as tk
from tkinter import ttk, messagebox

from widgets import GradientButton
from constants import BG_COLOR as BG
from quwei.quwei_core import (
    get_jianbihua_categories, get_jianbihua_filtered,
    export_jianbihua, export_migong, export_shudu, export_huanfang,
)

MAZE_DIFFS = ["简单", "中等", "困难"]
SUDOKU_DIFFS = ["简单", "中等", "困难", "专家"]  # 数独难度（含专家）
MAZE_DIFFS4 = ["简单", "中等", "困难", "史诗"]  # 迷宫运笔专用（含史诗）
SUDOKU_SPECS = ["9×9", "6×6", "4×4"]
HUANFANG_ORDERS = ["3阶", "4阶", "5阶"]
FONT_UI = ("Microsoft YaHei", 10)


class QuweiTabWidget:
    """趣味标签页：子选项卡容器，每个子页 = 设置区 + 功能区（导出PDF）。"""

    def __init__(self, parent):
        self.frame = ttk.Frame(parent)
        nb = ttk.Notebook(self.frame)
        nb.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self._build_jianbihua(nb)
        self._build_migong(nb)
        self._build_shudu(nb)
        self._build_huanfang(nb)

    # ───────── 通用小部件 ─────────
    def _settings_frame(self, page, rows):
        """设置区：rows = [(标签, 宽度, 选项, 默认), ...]，两列一排往下排。
        玩法说明文字已移到功能区（见 _func_frame）。"""
        ctrl = ttk.LabelFrame(page, text="设置")
        ctrl.pack(fill=tk.X, padx=10, pady=(6, 4))
        inner = tk.Frame(ctrl, bg=BG)
        inner.pack(anchor="w", padx=6, pady=6)
        vars_ = {}
        for idx, (label, width, options, default) in enumerate(rows):
            r, col = divmod(idx, 3)
            tk.Label(inner, text=f"{label}:", bg=BG, font=FONT_UI).grid(
                row=r, column=col * 2, padx=(0 if col == 0 else 8, 0), sticky="w")
            var = tk.StringVar(value=default)
            combo = ttk.Combobox(inner, width=width, state="readonly",
                                 font=FONT_UI, values=options, textvariable=var)
            combo.grid(row=r, column=col * 2 + 1, padx=(4, 0), sticky="w")
            vars_[label] = var
        return vars_, inner

    def _make_preview_canvas(self, parent):
        """预览画布：图片居中自适应缩放到整个预览框（Canvas 尺寸不受图片影响）。"""
        if not hasattr(self, "_pv_pils"):
            self._pv_pils = {}  # canvas -> 原始 PIL 图
        canvas = tk.Canvas(parent, bg="white", bd=0, highlightthickness=0,
                           cursor="hand2")
        canvas.pack(fill=tk.BOTH, expand=True)
        self._pv_pils[canvas] = None
        canvas.bind("<Configure>", lambda e, w=canvas: self._fit_preview(w))
        return canvas

    def _fit_preview(self, canvas, force=False):
        """把预览图等比缩放铺满整个预览框并居中（保持长宽比，不裁切）。
        若存的是多张图（列表），按 2×2 四格平铺，尽量放大每张图。"""
        imgs = self._pv_pils.get(canvas)
        w, h = canvas.winfo_width(), canvas.winfo_height()
        if not imgs or w < 30 or h < 30:
            return
        if not isinstance(imgs, (list, tuple)):
            imgs = [imgs]
        n = len(imgs)
        cols = 2 if n > 1 else 1
        rows = (n + cols - 1) // cols
        pad = 6
        cw = (w - pad * (cols + 1)) / cols
        ch = (h - pad * (rows + 1)) / rows
        key = (w, h, n) + tuple(im.size for im in imgs)
        if not force and getattr(canvas, "_pv_key", None) == key:
            return  # 尺寸没变，跳过（避免 Configure 循环）
        canvas._pv_key = key
        try:
            from PIL import Image as PILImage, ImageTk
            canvas.delete("pv")
            photos = []
            for idx, img in enumerate(imgs):
                r, c = divmod(idx, cols)
                iw, ih = img.size
                scale = min(cw / iw, ch / ih)
                nw, nh = max(1, int(iw * scale)), max(1, int(ih * scale))
                photo = ImageTk.PhotoImage(img.resize((nw, nh), PILImage.LANCZOS))
                photos.append(photo)
                x = pad + c * (cw + pad) + (cw - nw) / 2
                y = pad + r * (ch + pad) + (ch - nh) / 2
                canvas.create_image(x, y, image=photo, anchor="nw", tags="pv")
            canvas._pv_photos = photos  # 防 GC
        except Exception:
            pass

    def _func_frame(self, page, on_export, hint=None):
        """功能区：左侧玩法说明（灰字），右侧「导出PDF」按钮。"""
        func = ttk.LabelFrame(page, text="功能区")
        func.pack(side=tk.BOTTOM, fill=tk.X, pady=(4, 10))
        finner = tk.Frame(func, bg=BG)
        finner.pack(fill=tk.X, padx=10, pady=6)
        btn = GradientButton(finner, text="导出PDF", width=100, height=32,
                             command=on_export)
        btn.pack(side=tk.RIGHT, padx=(6, 2), pady=2)
        if hint:
            tk.Label(finner, text=hint, bg=BG, fg="#555555",
                     font=("Microsoft YaHei", 9), justify="left", anchor="nw",
                     wraplength=520).pack(side=tk.LEFT, padx=2, pady=(2, 6),
                                         anchor="w", fill=tk.X, expand=True)
        return finner

    @staticmethod
    def _show_result(ok, path_or_msg):
        if ok:
            messagebox.showinfo("导出成功", f"PDF 已生成：\n{path_or_msg}")
        else:
            messagebox.showerror("导出失败", str(path_or_msg))

    # ───────── 子选项卡 1：简笔画 ─────────
    def _build_jianbihua(self, nb):
        page = tk.Frame(nb, bg=BG)
        nb.add(page, text=" 简 笔 画 ")

        # 分类分组框：全部 / 动物 / 食物 / 交通建筑 / 花草物品
        cat_frame = ttk.LabelFrame(page, text="分类")
        cat_frame.pack(fill=tk.X, padx=10, pady=(10, 4))
        cats = [c for c in get_jianbihua_categories() if c != "全部"]
        self.jb_cat_var = tk.StringVar(value="全部")
        self.jb_selected = set()   # 预览框中左键选中的图案名
        for i, cname in enumerate(["全部"] + cats):
            tk.Radiobutton(cat_frame, text=cname, variable=self.jb_cat_var,
                           value=cname, bg=BG, font=FONT_UI, selectcolor="white",
                           activebackground=BG, cursor="hand2",
                           command=self._on_jb_category_change).grid(
                row=0, column=i, sticky="w", padx=(4, 12), pady=2)

        # 设置分组框（练习模式 / 数量）
        st = ttk.LabelFrame(page, text="设置")
        st.pack(fill=tk.X, padx=10, pady=4)
        inner = tk.Frame(st, bg=BG)
        inner.pack(anchor="w", padx=6, pady=6)
        tk.Label(inner, text="练习模式:", bg=BG, font=FONT_UI).grid(row=0, column=0, sticky="w")
        self.jb_mode_var = tk.StringVar(value="描红练习")
        ttk.Combobox(inner, width=10, state="readonly", font=FONT_UI,
                     values=["描红练习", "对比临摹"],
                     textvariable=self.jb_mode_var).grid(row=0, column=1, padx=(4, 0), sticky="w")
        tk.Label(inner, text="数量:", bg=BG, font=FONT_UI).grid(row=0, column=2, padx=(12, 0), sticky="w")
        self.jb_count_var = tk.StringVar(value="1")
        tk.Entry(inner, textvariable=self.jb_count_var, width=5, font=FONT_UI,
                 bd=2, relief="groove", bg="white", justify="center").grid(row=0, column=3, padx=(4, 0), sticky="w")
        tk.Label(inner, text="(1-20)", bg=BG, fg="#999999",
                 font=("Microsoft YaHei", 9)).grid(row=0, column=4, padx=(4, 0), sticky="w")
        # 随机勾选（默认勾选）：未勾选时按分类顺序取前 N 张
        self.jb_random_var = tk.BooleanVar(value=True)
        tk.Checkbutton(inner, text="随机", variable=self.jb_random_var,
                       bg=BG, font=FONT_UI, activebackground=BG,
                       cursor="hand2").grid(row=0, column=5, padx=(16, 0), sticky="w")

        # 功能区先打包（side=BOTTOM），预览框再占位，避免按钮/说明被裁切
        self._func_frame(page, self.on_export_jianbihua,
                         hint="描红练习：照着淡淡的图案描画；对比临摹：左边看原图、右边自己画。\n"
                              "在预览框里左键单击图案选中、右键单击取消；A4 每页 4 幅。\n"
                              "已选中的图案优先导出，未选中则按「数量」随机抽取。")

        # 预览分组框（固定高度，不挤压功能区；内容可上下滚动）
        self.pv_frame = ttk.LabelFrame(page, text="预览(左键选中/右键取消)", height=365)
        self.pv_frame.pack(fill=tk.X, padx=10, pady=4)
        self.pv_frame.pack_propagate(False)  # 锁定高度，不被内容撑开
        self.pv_canvas = tk.Canvas(self.pv_frame, bg="white", bd=0,
                                   highlightthickness=0)
        self.pv_scroll = ttk.Scrollbar(self.pv_frame, orient="vertical",
                                       command=self.pv_canvas.yview)
        self.pv_canvas.configure(yscrollcommand=self.pv_scroll.set)
        self.pv_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 4), pady=4)
        self.pv_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True,
                            padx=(6, 0), pady=4)
        self.pv_inner = tk.Frame(self.pv_canvas, bg="white")
        self.pv_window = self.pv_canvas.create_window(
            (0, 0), window=self.pv_inner, anchor="nw")
        self.pv_inner.bind("<Configure>",
                           lambda e: self.pv_canvas.configure(
                               scrollregion=self.pv_canvas.bbox("all")))
        self.pv_canvas.bind("<Configure>", lambda e: self.pv_canvas.itemconfigure(
            self.pv_window, width=e.width))
        # 滚轮滚动（悬停在图片上也能滚）
        self.pv_canvas.bind("<MouseWheel>", self._on_pv_mousewheel)
        self.pv_canvas.bind("<Button-4>", self._on_pv_mousewheel)
        self.pv_canvas.bind("<Button-5>", self._on_pv_mousewheel)
        self.pv_inner.bind("<MouseWheel>", self._on_pv_mousewheel)
        # 鼠标中键（按住拖动）滚动预览
        self.pv_canvas.bind("<ButtonPress-2>", self._on_pv_middle_down)
        self.pv_canvas.bind("<B2-Motion>", self._on_pv_middle_move)
        self.pv_canvas.bind("<ButtonRelease-2>", self._on_pv_middle_up)
        self._pv_thumbs = []  # 防 PhotoImage 被回收
        self._pv_drag_y = None

        self._refresh_jb_preview()

    def _on_pv_mousewheel(self, event):
        """预览框滚轮滚动：向上滚 / 向下滚（悬停在缩略图上同样生效）。"""
        try:
            delta = getattr(event, "delta", 0)
            if delta:
                units = -3 if delta > 0 else 3
            else:
                num = getattr(event, "num", 0)
                units = -3 if num == 4 else 3
            self.pv_canvas.yview_scroll(units, "units")
        except Exception:
            pass

    def _on_pv_middle_down(self, event):
        """鼠标中键按下：记录起始位置，准备拖动滚动。"""
        self._pv_drag_y = event.y

    def _on_pv_middle_move(self, event):
        """鼠标中键拖动：上下滚动预览框中的图片。"""
        if self._pv_drag_y is None:
            return
        dy = event.y - self._pv_drag_y
        self._pv_drag_y = event.y
        if dy == 0:
            return
        units = int(-dy / 20) or (-1 if dy < 0 else 1)
        self.pv_canvas.yview_scroll(units, "units")

    def _on_pv_middle_up(self, _event):
        self._pv_drag_y = None

    def _on_jb_category_change(self):
        """切换分类：清空已选图案并刷新预览。"""
        self.jb_selected.clear()
        self._refresh_jb_preview()

    def _jb_toggle_select(self, name, cell):
        """预览框左键单击：切换选中状态（已选中则取消）。"""
        if name in self.jb_selected:
            self.jb_selected.discard(name)
            self._jb_mark_cell(cell, False)
        else:
            self.jb_selected.add(name)
            self._jb_mark_cell(cell, True)

    def _jb_unselect(self, name, cell):
        """预览框右键单击：取消选中。"""
        if name in self.jb_selected:
            self.jb_selected.discard(name)
        self._jb_mark_cell(cell, False)

    @staticmethod
    def _jb_mark_cell(cell, on):
        """选中/取消的视觉标记：蓝框高亮。"""
        try:
            color = "#3b82f6" if on else "#e2e2e2"
            cell.configure(highlightbackground=color, highlightcolor=color)
        except Exception:
            pass

    def _refresh_jb_preview(self):
        """刷新预览框：当前分类下的全部图案缩略图，每行 5 个，可滚动。
        左键选中、右键取消选中（蓝框高亮）。"""
        for w in self.pv_inner.grid_slaves():
            w.destroy()
        self._pv_thumbs.clear()
        self.pv_canvas.yview_moveto(0)  # 刷新后回到顶部
        names = get_jianbihua_filtered(self.jb_cat_var.get())
        if not names:
            return
        try:
            from PIL import Image as PILImage, ImageTk
        except Exception:
            return
        from quwei.quwei_core import _scan_images
        available = _scan_images()
        cols = 5
        for i, name in enumerate(names):
            try:
                img = PILImage.open(available[name])
                img.thumbnail((96, 96))
                photo = ImageTk.PhotoImage(img)
                self._pv_thumbs.append(photo)
                cell = tk.Frame(self.pv_inner, bg="white",
                                highlightthickness=2,
                                highlightbackground="#e2e2e2",
                                highlightcolor="#e2e2e2")
                lbl = tk.Label(cell, image=photo, bg="white", cursor="hand2")
                lbl.image = photo
                lbl.pack(padx=2, pady=2)
                cell.grid(row=i // cols, column=i % cols, padx=3, pady=3)
                # 左键切换选中，右键取消选中
                lbl.bind("<Button-1>",
                         lambda e, n=name, c=cell: self._jb_toggle_select(n, c))
                lbl.bind("<Button-3>",
                         lambda e, n=name, c=cell: self._jb_unselect(n, c))
                cell.bind("<Button-1>",
                          lambda e, n=name, c=cell: self._jb_toggle_select(n, c))
                cell.bind("<Button-3>",
                          lambda e, n=name, c=cell: self._jb_unselect(n, c))
                # 悬停在图片上也能用滚轮滚动
                lbl.bind("<MouseWheel>", self._on_pv_mousewheel)
                lbl.bind("<Button-4>", self._on_pv_mousewheel)
                lbl.bind("<Button-5>", self._on_pv_mousewheel)
                self._createToolTip(lbl, name)
                if name in self.jb_selected:
                    self._jb_mark_cell(cell, True)
            except Exception:
                continue

    @staticmethod
    def _createToolTip(widget, text):
        """鼠标悬停显示图案名。"""
        tip = []

        def enter(_e):
            t = tk.Toplevel(widget)
            t.wm_overrideredirect(True)
            t.wm_geometry(f"+{widget.winfo_rootx() + 10}+{widget.winfo_rooty() + 30}")
            tk.Label(t, text=text, bg="#ffffe0", fg="#333333", bd=1,
                     relief="solid", font=("Microsoft YaHei", 9),
                     padx=4, pady=1).pack()
            tip.append(t)

        def leave(_e):
            if tip:
                tip.pop().destroy()
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)

    def on_export_jianbihua(self):
        try:
            count = int(self.jb_count_var.get())
        except ValueError:
            count = 4
        # 预览中选中的图案优先导出；未选中则按设置里的「随机」勾选抽取
        selected = sorted(self.jb_selected)
        ok, r = export_jianbihua(self.jb_mode_var.get(),
                                 self.jb_cat_var.get(), count,
                                 selected=selected,
                                 random_pick=self.jb_random_var.get())
        self._show_result(ok, r)

    # ───────── 子选项卡 2：迷宫运笔 ─────────
    def _build_migong(self, nb):
        page = tk.Frame(nb, bg=BG)
        nb.add(page, text=" 迷宫运笔 ")
        self.mg_vars, inner = self._settings_frame(page, [
            ("难度", 8, MAZE_DIFFS4, "简单"),
            ("页数", 4, ["1", "2", "3", "4", "5"], "1"),
        ])
        self.mg_answer_var = tk.BooleanVar(value=False)
        tk.Checkbutton(inner, text="生成答案", variable=self.mg_answer_var,
                       bg=BG, font=FONT_UI, activebackground=BG,
                       cursor="hand2").grid(row=0, column=4, padx=(16, 0), sticky="w")
        inner.winfo_children()[1].bind("<<ComboboxSelected>>",
                                       lambda e: self._refresh_mg_preview())
        # 功能区先打包（side=BOTTOM），预览框再撑满剩余空间，避免功能区被压扁
        self._func_frame(page, self.on_export_migong,
                         hint="从入口出发，沿白色通道一笔画到出口，不能穿墙。\n"
                              "难度越高迷宫越大：简单 3×3~4×4，中等 5×5~6×6，"
                              "困难 6×6~8×8，史诗 9×9~12×12。\n"
                              "勾选「生成答案」额外生成一份红色箭头答案卷；A4 每页 4 题。")
        # 预览分组框（撑满设置框到功能区之间的剩余空间）
        self.mg_pv = ttk.LabelFrame(page, text="预览(点击图片刷新)", height=400)
        self.mg_pv.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)
        self.mg_pv.pack_propagate(False)
        self.mg_canvas = self._make_preview_canvas(self.mg_pv)
        self.mg_canvas.bind("<Button-1>", lambda e: self._refresh_mg_preview())

        self._refresh_mg_preview()

    def _refresh_mg_preview(self):
        """刷新迷宫预览：按当前难度随机生成一页 4 道迷宫，按导出页的
        2×2 上下左右排布同屏显示（点击图片可换一组）。"""
        try:
            from quwei.quwei_core import render_maze_preview
            img, _n = render_maze_preview(self.mg_vars["难度"].get())
            self._pv_pils[self.mg_canvas] = img
            self._fit_preview(self.mg_canvas, force=True)
        except Exception:
            self._pv_pils[self.mg_canvas] = None

    def on_export_migong(self):
        ok, r = export_migong(self.mg_vars["难度"].get(),
                              int(self.mg_vars["页数"].get()),
                              self.mg_answer_var.get())
        self._show_result(ok, r)

    # ───────── 子选项卡 3：数独 ─────────
    def _build_shudu(self, nb):
        page = tk.Frame(nb, bg=BG)
        nb.add(page, text=" 数 独 ")
        self.sd_vars, sd_inner = self._settings_frame(page, [
            ("规格", 8, SUDOKU_SPECS, "4×4"),
            ("难度", 8, SUDOKU_DIFFS, "简单"),
            ("页数", 4, ["1", "2", "3", "4"], "1"),
        ])
        # 生成答案勾选框（同一设置行右侧，默认勾选）
        self.sd_answer_var = tk.BooleanVar(value=True)
        tk.Checkbutton(sd_inner, text="生成答案", variable=self.sd_answer_var,
                       bg=BG, font=FONT_UI, activebackground=BG,
                       cursor="hand2").grid(row=0, column=6, padx=(16, 0), sticky="w")
        # 功能区先打包（side=BOTTOM），预览框再撑满剩余空间，避免功能区被压扁
        self._func_frame(page, self.on_export_shudu,
                         hint="每行、每列、每个粗框宫内的数字都不重复（1~N）。\n"
                              "规格 4×4 / 6×6 / 9×9，难度越高给出的提示数越少。\n"
                              "勾选「生成答案」额外生成一份完整答案卷；A4 每页 4 题。")
        # 预览分组框（撑满设置框到功能区上边）
        self.sd_pv = ttk.LabelFrame(page, text="预览(点击图片刷新)", height=400)
        self.sd_pv.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)
        self.sd_pv.pack_propagate(False)
        self.sd_canvas = self._make_preview_canvas(self.sd_pv)
        self.sd_canvas.bind("<Button-1>", lambda e: self._refresh_sd_preview())
        # 规格/难度变化时刷新预览（Combobox 位于 inner 偶数索引+1）
        for wgt in (sd_inner.winfo_children()[1], sd_inner.winfo_children()[3]):
            wgt.bind("<<ComboboxSelected>>",
                     lambda e: self._refresh_sd_preview())
        self._refresh_sd_preview()

    def _refresh_sd_preview(self):
        """刷新数独预览：按规格+难度随机生成一道并显示（点击图片换一道）。"""
        try:
            from quwei.quwei_core import render_sudoku_preview
            spec, diff = self.sd_vars["规格"].get(), self.sd_vars["难度"].get()
            img, _clues = render_sudoku_preview(spec, diff)
            self._pv_pils[self.sd_canvas] = img
            self._fit_preview(self.sd_canvas, force=True)
        except Exception:
            self._pv_pils[self.sd_canvas] = None

    def on_export_shudu(self):
        ok, r = export_shudu(self.sd_vars["规格"].get(),
                             self.sd_vars["难度"].get(),
                             int(self.sd_vars["页数"].get()),
                             self.sd_answer_var.get())
        self._show_result(ok, r)

    # ───────── 子选项卡 4：幻方 ─────────
    def _build_huanfang(self, nb):
        page = tk.Frame(nb, bg=BG)
        nb.add(page, text=" 幻 方 ")
        self.hf_vars, hf_inner = self._settings_frame(page, [
            ("阶数", 8, HUANFANG_ORDERS, "3阶"),
            ("页数", 4, ["1", "2", "3", "4"], "1"),
        ])
        # 生成答案勾选框（同一设置行右侧，默认勾选）
        self.hf_answer_var = tk.BooleanVar(value=True)
        tk.Checkbutton(hf_inner, text="生成答案", variable=self.hf_answer_var,
                       bg=BG, font=FONT_UI, activebackground=BG,
                       cursor="hand2").grid(row=0, column=4, padx=(16, 0), sticky="w")
        # 功能区先打包（side=BOTTOM），预览框再撑满剩余空间，避免功能区被压扁
        self._func_frame(page, self.on_export_huanfang,
                         hint="把 1~N² 填入空格，使每行、每列、每条对角线之和都等于幻和。\n"
                              "幻和：3阶=15，4阶=34，5阶=65；挖空的格子自动随机。\n"
                              "勾选「生成答案」额外生成一份完整答案卷；A4 每页 4 题。")
        # 预览分组框（撑满设置框到功能区上边）
        self.hf_pv = ttk.LabelFrame(page, text="预览(点击图片刷新)", height=400)
        self.hf_pv.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)
        self.hf_pv.pack_propagate(False)
        self.hf_canvas = self._make_preview_canvas(self.hf_pv)
        self.hf_canvas.bind("<Button-1>", lambda e: self._refresh_hf_preview())
        hf_inner.winfo_children()[1].bind(
            "<<ComboboxSelected>>", lambda e: self._refresh_hf_preview())
        self._refresh_hf_preview()

    def _refresh_hf_preview(self):
        """刷新幻方预览：按阶数随机生成一道并显示（点击图片换一道）。"""
        try:
            from quwei.quwei_core import render_huanfang_preview
            img, _blanks = render_huanfang_preview(self.hf_vars["阶数"].get())
            self._pv_pils[self.hf_canvas] = img
            self._fit_preview(self.hf_canvas, force=True)
        except Exception:
            self._pv_pils[self.hf_canvas] = None

    def on_export_huanfang(self):
        ok, r = export_huanfang(self.hf_vars["阶数"].get(),
                                int(self.hf_vars["页数"].get()),
                                self.hf_answer_var.get())
        self._show_result(ok, r)
