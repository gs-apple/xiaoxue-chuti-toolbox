# zi_tie_ui.py — 字帖标签页 (tkinter 版，保留原版布局)
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from widgets import GradientButton
from zitie_core import ZitieGenerator, ZitieConfig, add_custom_font, register_builtin_fonts
from zitie_data import GRADE_CHARACTERS, PINYIN_DATA, NUMBER_DATA, GRADES, VERSIONS
from datetime import datetime
import os
import opencc

BG = "#f0f0f0"
MODERN_BTN = dict(bg="#2563eb", fg="white", font=("Microsoft YaHei", 10, "bold"),
                   bd=0, relief="flat", activebackground="#1d4ed8",
                   activeforeground="white", width=10, height=1,
                   cursor="hand2")

# 内容类型禁用规则表（人教版 · 主模块驱动附加模块1+2）
# style_disabled: 禁用的样式索引 (0=田字格,1=方格,2=米字格,3=数学格,4=生字格,5=拼音格,6=作文本,7=教案格,8=大楷本)
# type_disabled:  禁用的类型按钮文本
# style_default:  切换到该内容类型时，样式主动设为此默认值
# type_default:   切换到该内容类型时，类型主动设为此默认值 (None=自动选第一个可用)
_CONTENT_DISABLE_RULES = {
    "shengzi":    {"style_disabled": [3, 4, 5, 6, 7, 8, 9],        "type_disabled": [],                                                          "style_default": 0, "type_default": "duozi"},
    "ciyu":       {"style_disabled": [3, 4, 5, 6, 7, 8, 9],        "type_disabled": ["笔顺", "笔顺+1行"],                                        "style_default": 0, "type_default": "duozi"},
    "gushi":      {"style_disabled": [3, 5, 6, 8, 9],              "type_disabled": ["单字", "整行", "笔顺", "单字+1行", "整行+1行", "笔顺+1行"],  "style_default": 7, "type_default": "wenzhang_wz"},
    "wenyan":     {"style_disabled": [3, 5, 6, 8, 9],              "type_disabled": ["单字", "整行", "笔顺", "单字+1行", "整行+1行", "笔顺+1行"],  "style_default": 7, "type_default": "wenzhang_wz"},
    "shuzi":      {"style_disabled": [3, 4, 5, 6, 7, 8, 9],        "type_disabled": ["笔顺", "笔顺+1行", "带拼音", "带拼音+1行"],                  "style_default": 0, "type_default": "duozi"},
    "pinyin_text":{"style_disabled": [0, 1, 2, 3, 4, 6, 7, 8, 9], "type_disabled": ["笔顺", "笔顺+1行", "带拼音", "带拼音+1行"],                  "style_default": 5, "type_default": "duozi"},
    "gaiding":    {"style_disabled": [0, 1, 2, 3, 4, 5, 6, 7, 9], "type_disabled": ["笔顺", "笔顺+1行", "带拼音", "带拼音+1行"],                  "style_default": 8, "type_default": "wenzhang_wz"},
    "gushu":      {"style_disabled": [0, 1, 2, 3, 4, 5, 6, 7, 8], "type_disabled": ["单字", "整行", "笔顺", "带拼音", "单字+1行", "整行+1行", "笔顺+1行", "带拼音+1行"], "style_default": 9, "type_default": "wenzhang_wz"},
}

# 仅在"带拼音"类型下可用的样式索引（需要与内容类型规则联动）
_PINYIN_ONLY_STYLES = {4}  # 4=生字格

# 类型按钮文本 → 变量值映射
_TYPE_TEXT_TO_VALUE = {
    "单字": "duozi", "整行": "wenzhang",
    "笔顺": "bishun", "带拼音": "duoju", "文章": "wenzhang_wz",
    "单字+1行": "duozi1", "整行+1行": "wenzhang1",
    "笔顺+1行": "bishun1", "带拼音+1行": "duoju1",
}


class ZiTieTabWidget:
    def __init__(self, parent):
        self.frame = tk.Frame(parent, bg=BG)
        self.generated_pages = []
        self.last_generated_path = ""
        self.builtin_fonts = register_builtin_fonts()
        self._init_ui()

    def _init_ui(self):
        main_layout = tk.Frame(self.frame, bg=BG)
        main_layout.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # ========== 顶部：模式选择 + 字体选择 ==========
        top_frame = tk.Frame(main_layout, bg=BG)
        top_frame.pack(fill=tk.X, pady=(0, 0))

        # 模式选择
        mode_group = ttk.LabelFrame(top_frame, text="模式选择")
        mode_group.pack(side=tk.LEFT, padx=(0, 10))
        mode_inner = tk.Frame(mode_group, bg=BG)
        mode_inner.pack(fill=tk.X, padx=5, pady=5)

        self._mode_var = tk.IntVar(value=0)  # 0=字帖生成, 1=空白模板
        self.rb_zitie = tk.Radiobutton(mode_inner, text="字帖生成",
                                        variable=self._mode_var, value=0,
                                        font=("Microsoft YaHei", 10),
                                        command=self._on_mode_changed)
        self.rb_zitie.pack(side=tk.LEFT)
        self.rb_blank = tk.Radiobutton(mode_inner, text="空白模板",
                                        variable=self._mode_var, value=1,
                                        font=("Microsoft YaHei", 10),
                                        command=self._on_mode_changed)
        self.rb_blank.pack(side=tk.LEFT, padx=(4, 0))

        self.page_count_edit = tk.Entry(mode_inner, width=4, justify="center",
                                         font=("Microsoft YaHei", 10))
        self.page_count_edit.insert(0, "5")
        self.page_count_edit.pack(side=tk.LEFT, padx=(5, 0))

        # 字体选择
        font_group = ttk.LabelFrame(top_frame, text="字体选择")
        font_group.pack(side=tk.LEFT, fill=tk.X, expand=True)
        font_inner = tk.Frame(font_group, bg=BG)
        font_inner.pack(fill=tk.X, padx=5, pady=5)

        self._font_var = tk.IntVar(value=0)  # 0=默认, 1=楷体, 2=行书, 3=行楷, 4=自定义
        self.rb_default_font = tk.Radiobutton(font_inner, text="默认",
                                              variable=self._font_var, value=0,
                                              font=("Microsoft YaHei", 10),
                                              command=self.on_font_radio_changed)
        self.rb_default_font.pack(side=tk.LEFT)
        self.rb_kai = tk.Radiobutton(font_inner, text="楷体",
                                      variable=self._font_var, value=1,
                                      font=("Microsoft YaHei", 10),
                                      command=self.on_font_radio_changed)
        self.rb_kai.pack(side=tk.LEFT)
        self.rb_xingshu = tk.Radiobutton(font_inner, text="行书",
                                          variable=self._font_var, value=2,
                                          font=("Microsoft YaHei", 10),
                                          command=self.on_font_radio_changed)
        self.rb_xingshu.pack(side=tk.LEFT)
        self.rb_xingkai = tk.Radiobutton(font_inner, text="行楷",
                                          variable=self._font_var, value=3,
                                          font=("Microsoft YaHei", 10),
                                          command=self.on_font_radio_changed)
        self.rb_xingkai.pack(side=tk.LEFT)
        self.rb_custom_font = tk.Radiobutton(font_inner, text="自定义",
                                              variable=self._font_var, value=4,
                                              font=("Microsoft YaHei", 10),
                                              command=self.on_font_radio_changed)
        self.rb_custom_font.pack(side=tk.LEFT)

        self.edit_custom_font = tk.Entry(font_inner, width=10, state="disabled",
                                          font=("Microsoft YaHei", 10))
        self.edit_custom_font.pack(side=tk.LEFT, padx=(5, 0))

        self.btn_preview_font = tk.Button(font_inner, text="预览", width=4,
                                           state="disabled",
                                           command=self.on_select_font)
        self.btn_preview_font.pack(side=tk.LEFT, padx=(3, 0))

        # ========== 文字内容 ==========
        content_container = tk.Frame(main_layout, bg=BG)
        content_container.pack(fill=tk.BOTH, expand=True, pady=(3, 0))

        content_group = ttk.LabelFrame(content_container, text="文字内容")
        content_group.pack(fill=tk.BOTH, expand=True)
        content_inner = tk.Frame(content_group, bg=BG)
        content_inner.pack(fill=tk.BOTH, expand=True, padx=3, pady=2)

        # 左侧控件
        left_frame = tk.Frame(content_inner, bg=BG)
        left_frame.pack(side=tk.LEFT, fill=tk.Y)

        label_width = 40
        combo_width = 8

        # 年级
        row1 = tk.Frame(left_frame, bg=BG)
        row1.pack(fill=tk.X, pady=1)
        tk.Label(row1, text="年级:", width=4, anchor="w",
                 font=("Microsoft YaHei", 10)).pack(side=tk.LEFT)
        self.grade_combo = ttk.Combobox(row1, width=8, state="readonly",
                                         values=["一年级", "二年级", "三年级",
                                                 "四年级", "五年级", "六年级"])
        self.grade_combo.current(0)
        self.grade_combo.pack(side=tk.LEFT)

        # 版本
        row2 = tk.Frame(left_frame, bg=BG)
        row2.pack(fill=tk.X, pady=1)
        tk.Label(row2, text="版本:", width=4, anchor="w",
                 font=("Microsoft YaHei", 10)).pack(side=tk.LEFT)
        self.version_combo = ttk.Combobox(row2, width=8, state="readonly",
                                           values=["人教版"])
        self.version_combo.current(0)
        self.version_combo.pack(side=tk.LEFT)
        self.version_combo.bind("<<ComboboxSelected>>", lambda e: self.on_version_changed(
            self.version_combo.get()))

        # 学期
        self.semester_widget = tk.Frame(left_frame, bg=BG)
        semester_row = tk.Frame(self.semester_widget, bg=BG)
        semester_row.pack(fill=tk.X, pady=1)
        self._first_sem_var = tk.IntVar()
        self._second_sem_var = tk.IntVar()
        self.cb_first_semester = tk.Checkbutton(semester_row, text="上册",
                                                 variable=self._first_sem_var,
                                                 command=self.on_semester_changed,
                                                 font=("Microsoft YaHei", 10))
        self.cb_first_semester.pack(side=tk.LEFT)
        self.cb_second_semester = tk.Checkbutton(semester_row, text="下册",
                                                  variable=self._second_sem_var,
                                                  command=self.on_semester_changed,
                                                  font=("Microsoft YaHei", 10))
        self.cb_second_semester.pack(side=tk.LEFT, padx=(8, 0))

        # 内容 (生字/词语)
        self.content_widget = tk.Frame(left_frame, bg=BG)
        content_row = tk.Frame(self.content_widget, bg=BG)
        content_row.pack(fill=tk.X, pady=1)
        self._content_var = tk.StringVar()
        self.rb_shengzi = ttk.Radiobutton(content_row, text="生字",
                                          variable=self._content_var, value="shengzi",
                                          command=self.on_content_radio_changed)
        self.rb_shengzi.pack(side=tk.LEFT)
        self.rb_ciyu = ttk.Radiobutton(content_row, text="词语",
                                       variable=self._content_var, value="ciyu",
                                       command=self.on_content_radio_changed)
        self.rb_ciyu.pack(side=tk.LEFT, padx=(8, 0))

        # 内容扩展 (诗词/文言文)
        self.content_ext_widget = tk.Frame(left_frame, bg=BG)
        ext_row = tk.Frame(self.content_ext_widget, bg=BG)
        ext_row.pack(fill=tk.X, pady=1)
        self.rb_gushi = ttk.Radiobutton(ext_row, text="诗词",
                                        variable=self._content_var, value="gushi",
                                        command=self.on_content_radio_changed)
        self.rb_gushi.pack(side=tk.LEFT)
        self.rb_wenyan = ttk.Radiobutton(ext_row, text="文言文",
                                         variable=self._content_var, value="wenyan",
                                         command=self.on_content_radio_changed)
        self.rb_wenyan.pack(side=tk.LEFT, padx=(8, 0))

        # 其他 (数字/拼音)
        self.other_widget = tk.Frame(left_frame, bg=BG)
        other_row = tk.Frame(self.other_widget, bg=BG)
        other_row.pack(fill=tk.X, pady=1)
        self.rb_shuzi = ttk.Radiobutton(other_row, text="数字",
                                        variable=self._content_var, value="shuzi",
                                        command=self.on_content_radio_changed)
        self.rb_shuzi.pack(side=tk.LEFT)
        self.rb_pinyin_text = ttk.Radiobutton(other_row, text="拼音",
                                              variable=self._content_var, value="pinyin_text",
                                              command=self.on_content_radio_changed)
        self.rb_pinyin_text.pack(side=tk.LEFT, padx=(8, 0))

        # 大楷/古书
        self.dakai_widget = tk.Frame(left_frame, bg=BG)
        dakai_row = tk.Frame(self.dakai_widget, bg=BG)
        dakai_row.pack(fill=tk.X, pady=1)
        self.rb_gaiding = ttk.Radiobutton(dakai_row, text="大楷",
                                          variable=self._content_var, value="gaiding",
                                          command=self.on_content_radio_changed)
        self.rb_gaiding.pack(side=tk.LEFT)
        self.rb_ding = ttk.Radiobutton(dakai_row, text="古书",
                                       variable=self._content_var, value="gushu",
                                       command=self.on_content_radio_changed)
        self.rb_ding.pack(side=tk.LEFT, padx=(8, 0))

        # 国学著作（在古书下方显示）
        self.classic_widget = tk.Frame(left_frame, bg=BG)
        classic_row = tk.Frame(self.classic_widget, bg=BG)
        classic_row.pack(fill=tk.X, pady=1)
        tk.Label(classic_row, text="著作:", width=4, anchor="w",
                 font=("Microsoft YaHei", 10)).pack(side=tk.LEFT)
        self.classic_combo = ttk.Combobox(classic_row, width=8, state="readonly",
                                           values=["千字文", "道德经", "三字经",
                                                   "弟子规", "百家姓", "阴符经",
                                                   "金刚经", "心经"])
        self.classic_combo.current(0)
        self.classic_combo.pack(side=tk.LEFT)

        # 简体/繁体单选框
        convert_row = tk.Frame(self.classic_widget, bg=BG)
        convert_row.pack(fill=tk.X, pady=1)
        tk.Label(convert_row, text="字体:", width=4, anchor="w",
                 font=("Microsoft YaHei", 10)).pack(side=tk.LEFT)
        self._font_variant_var = tk.IntVar(value=0)  # 0=简体, 1=繁体
        self.rb_jianti = tk.Radiobutton(convert_row, text="简",
                                         variable=self._font_variant_var, value=0,
                                         font=("Microsoft YaHei", 10),
                                         command=self.on_font_variant_changed)
        self.rb_jianti.pack(side=tk.LEFT)
        self.rb_fanti = tk.Radiobutton(convert_row, text="繁",
                                        variable=self._font_variant_var, value=1,
                                        font=("Microsoft YaHei", 10),
                                        command=self.on_font_variant_changed)
        self.rb_fanti.pack(side=tk.LEFT, padx=(0, 0))
        self.classic_widget.pack_forget()

        # 配置单选按钮样式（不改变主题，避免覆盖选项卡样式）
        style = ttk.Style()
        style.configure("TRadiobutton", font=("Microsoft YaHei", 10))

        # 一键导入（向上移动8mm）
        self.import_widget = tk.Frame(left_frame, bg=BG)
        import_row = tk.Frame(self.import_widget, bg=BG)
        import_row.pack(fill=tk.X, pady=(6, 0), padx=(25, 0))  # 修改pady从14改为6，向上移动8mm
        self.btn_import = tk.Button(import_row, text="一键导入", width=8,
                                     command=self.on_import_content)
        self.btn_import.pack(side=tk.LEFT)

        # 右侧文本编辑框 (占据剩余空间)
        text_frame = tk.Frame(content_inner, bg=BG)
        text_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(3, 0))
        tk.Label(text_frame, text="内容编辑", font=("Microsoft YaHei", 10)).pack(anchor="w")
        text_scroll = tk.Scrollbar(text_frame)
        text_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_content = tk.Text(text_frame, bg="white", wrap=tk.WORD, height=14,
                                     yscrollcommand=text_scroll.set,
                                     font=("Microsoft YaHei", 10))
        self.text_content.pack(fill=tk.BOTH, expand=True)
        text_scroll.config(command=self.text_content.yview)
        self.text_content.bind("<<Modified>>", lambda e: self._on_text_modified())

        # ========== 样式选择 ==========
        style_container = tk.Frame(main_layout, bg=BG)
        style_container.pack(fill=tk.X, pady=(3, 0))

        style_group = ttk.LabelFrame(style_container, text="样式")
        style_group.pack(fill=tk.X)
        style_inner = tk.Frame(style_group, bg=BG)
        style_inner.pack(fill=tk.X, padx=5, pady=5)

        self._style_var = tk.IntVar(value=0)
        style_names = [
            ("田字格", 0), ("方格", 1), ("米字格", 2), ("数学格", 3),
            ("生字格", 4), ("拼音格", 5), ("作文本", 6), ("教案格", 7), ("大楷本", 8), ("竖行", 9)
        ]
        self._style_rbs = []
        for name, val in style_names:
            rb = tk.Radiobutton(style_inner, text=name,
                                 variable=self._style_var, value=val,
                                 font=("Microsoft YaHei", 10),
                                 command=self._on_style_changed)
            rb.pack(side=tk.LEFT)
            self._style_rbs.append(rb)

        # ========== 类型选择 ==========
        type_group = ttk.LabelFrame(main_layout, text="类型")
        type_group.pack(fill=tk.X, pady=(2, 0))
        type_inner = tk.Frame(type_group, bg=BG)
        type_inner.pack(fill=tk.X, padx=5, pady=3)

        type_grid = tk.Frame(type_inner, bg=BG)
        type_grid.pack(fill=tk.X, pady=1)

        self._huizi_var = tk.IntVar()
        self.cb_huizi = tk.Checkbutton(type_grid, text="灰字",
                                        variable=self._huizi_var,
                                        font=("Microsoft YaHei", 10))
        self.cb_huizi.grid(row=0, column=0, sticky="w")

        self._miaohong_var = tk.IntVar()
        self.cb_miaohong = tk.Checkbutton(type_grid, text="描红",
                                           variable=self._miaohong_var,
                                           state="disabled",
                                           font=("Microsoft YaHei", 10))
        self.cb_miaohong.grid(row=1, column=0, sticky="w")

        self._type_var = tk.StringVar(value="duozi")
        type_opts_a = [("单字", "duozi"), ("整行", "wenzhang"),
                        ("笔顺", "bishun"), ("带拼音", "duoju"), ("文章", "wenzhang_wz")]
        type_opts_b = [("单字+1行", "duozi1"), ("整行+1行", "wenzhang1"),
                        ("笔顺+1行", "bishun1"), ("带拼音+1行", "duoju1")]
        self._type_rbs = []
        for i, (text_a, val_a) in enumerate(type_opts_a):
            col = i + 1
            rb_a = tk.Radiobutton(type_grid, text=text_a, variable=self._type_var, value=val_a,
                                   command=self._on_type_changed,
                                   font=("Microsoft YaHei", 10))
            rb_a.grid(row=0, column=col, sticky="w")
            self._type_rbs.append(rb_a)
        for i, (text_b, val_b) in enumerate(type_opts_b):
            col = i + 1
            rb_b = tk.Radiobutton(type_grid, text=text_b, variable=self._type_var, value=val_b,
                                   command=self._on_type_changed,
                                   font=("Microsoft YaHei", 10))
            rb_b.grid(row=1, column=col, sticky="w")
            self._type_rbs.append(rb_b)

        # ========== 功能区 ==========
        func_group = ttk.LabelFrame(main_layout, text="功能区")
        func_group.pack(fill=tk.X, pady=(2, 0))
        func_inner = tk.Frame(func_group, bg=BG)
        func_inner.pack(padx=5, pady=3)

        self.btn_clear = GradientButton(func_inner, text="清空", width=100, height=32,
                                         command=self.clear_content)
        self.btn_generate = GradientButton(func_inner, text="生成", width=100, height=32,
                                            command=self.generate_zitie)

        self.btn_export_pdf = GradientButton(func_inner, text="导出PDF", width=100, height=32,
                                              command=self.export_pdf)

        func_inner.columnconfigure(0, weight=1)
        func_inner.columnconfigure(4, weight=1)
        self.btn_clear.grid(row=0, column=1, padx=3)
        self.btn_generate.grid(row=0, column=2, padx=3)
        self.btn_generate.grid_remove()
        self.btn_export_pdf.grid(row=0, column=3, padx=3)

        # 初始化：设置默认版本状态（与原版 PyQt5 一致）
        self.on_version_changed("人教版")

    def _on_text_modified(self):
        if self.text_content.edit_modified():
            # 仅在没有选中内容类型时自动检测（用于国学版或手动输入场景）
            if not self._content_var.get():
                self.update_grid_type_enabled()
            self.text_content.edit_modified(False)

    def _on_type_changed(self):
        """类型切换时，动态控制生字格的可用性"""
        current_type = self._type_var.get()
        content_type = self._content_var.get()
        rule = _CONTENT_DISABLE_RULES.get(content_type)

        if not rule:
            return

        is_pinyin_type = current_type in ("duoju", "duoju1")
        disabled_set = set(rule["style_disabled"])

        if is_pinyin_type:
            # 带拼音类型：解除生字格禁用，并自动切到生字格
            disabled_set -= _PINYIN_ONLY_STYLES
            for i, rb in enumerate(self._style_rbs):
                rb.config(state="disabled" if i in disabled_set else "normal")
            self._style_var.set(4)  # 生字格
        else:
            # 非带拼音类型：生字格保持禁用
            for i, rb in enumerate(self._style_rbs):
                rb.config(state="disabled" if i in disabled_set else "normal")
            # 从带拼音切换到其他类型时，强制切换到默认样式
            # 或者如果当前选中的是生字格，回退到默认样式
            if self._style_var.get() in disabled_set or self._style_var.get() == 4:
                self._style_var.set(rule["style_default"])

    def _on_style_changed(self):
        """样式切换时，处理生字格与其他样式的联动"""
        current_style = self._style_var.get()
        current_type = self._type_var.get()
        content_type = self._content_var.get()

        # 如果选择了生字格（索引4），自动切换到带拼音类型
        if current_style == 4:
            # 如果当前已经是带拼音类型，不做改变
            if current_type in ("duoju", "duoju1"):
                return
            # 否则切换到带拼音类型
            self._type_var.set("duoju")
        # 如果从生字格切换到其他样式，且当前类型是带拼音，切换到默认类型
        elif current_type in ("duoju", "duoju1"):
            rule = _CONTENT_DISABLE_RULES.get(content_type)
            if rule and rule["type_default"]:
                self._type_var.set(rule["type_default"])

    def _on_mode_changed(self):
        """模式切换时，控制文字内容和类型的可用性"""
        is_blank_mode = self._mode_var.get() == 1

        # 文字内容区域的控件
        content_widgets = [
            self.grade_combo, self.version_combo, self.classic_combo,
            self.cb_first_semester, self.cb_second_semester,
            self.rb_shengzi, self.rb_ciyu, self.rb_gushi, self.rb_wenyan,
            self.rb_shuzi, self.rb_pinyin_text, self.rb_gaiding, self.rb_ding,
            self.btn_import, self.text_content
        ]

        # 类型区域的控件
        type_widgets = [
            self.cb_huizi, self.cb_miaohong
        ] + self._type_rbs

        # 设置文字内容区域的可用性
        for widget in content_widgets:
            if is_blank_mode:
                if isinstance(widget, tk.Entry) or isinstance(widget, tk.Text):
                    widget.config(state="disabled")
                elif isinstance(widget, ttk.Combobox):
                    widget.config(state="disabled")
                else:
                    widget.config(state="disabled")
            else:
                if isinstance(widget, tk.Entry):
                    widget.config(state="normal")
                elif isinstance(widget, tk.Text):
                    widget.config(state="normal")
                elif isinstance(widget, ttk.Combobox):
                    widget.config(state="readonly")
                else:
                    widget.config(state="normal")

        # 设置类型区域的可用性
        for widget in type_widgets:
            if is_blank_mode:
                widget.config(state="disabled")
            else:
                widget.config(state="normal")

    def on_version_changed(self, version):
        # 版本切换时，显示/隐藏学期选择
        is_renjiao = version == "人教版"

        if is_renjiao:
            self.semester_widget.pack(fill=tk.X, pady=1)
        else:
            self.semester_widget.pack_forget()

        # 显示所有内容控件
        self.content_widget.pack(fill=tk.X, pady=1)
        self.content_ext_widget.pack(fill=tk.X, pady=1)
        self.other_widget.pack(fill=tk.X, pady=1)
        self.dakai_widget.pack(fill=tk.X, pady=1)

        # 一键导入按钮向上移动8mm
        self.import_widget.pack(fill=tk.X, pady=(6, 0), padx=(25, 0))

        self._first_sem_var.set(0)
        self._second_sem_var.set(0)
        self._content_var.set("")
        self.text_content.delete("1.0", tk.END)
        self.update_grid_type_enabled()

    def on_semester_changed(self):
        self.text_content.delete("1.0", tk.END)
        self.update_grid_type_enabled()

    def on_content_radio_changed(self):
        val = self._content_var.get()

        # 大楷特殊处理：填入默认内容并默认选中文章类型
        if val == "gaiding":
            self.text_content.delete("1.0", tk.END)
            self.text_content.insert("1.0", "远上寒山石径斜\n白云深处有人家\n停车坐爱枫林晚\n霜叶红于二月花")
            self._type_var.set("wenzhang_wz")
            # 隐藏国学著作选择框
            self.classic_widget.pack_forget()
            # 启用所有内容控件
            self._set_content_widgets_state("normal")
        # 古书特殊处理：显示国学著作选择框，启用文字内容
        elif val == "gushu":
            self.text_content.delete("1.0", tk.END)
            # 显示国学著作选择框
            self.classic_widget.pack(fill=tk.X, pady=1)
            # 启用其他文字内容
            self._set_content_widgets_state("normal")
            # 启用一键导入按钮
            self.btn_import.config(state="normal")
            # 启用内容编辑框
            self.text_content.config(state="normal")
            # 默认选中文章类型
            self._type_var.set("wenzhang_wz")
            # 默认选中竖行样式
            self._style_var.set(9)
        else:
            self.text_content.delete("1.0", tk.END)
            # 隐藏国学著作选择框
            self.classic_widget.pack_forget()
            # 启用其他文字内容
            self._set_content_widgets_state("normal")

        # 根据内容类型（主模块）驱动附加模块1（样式）和附加模块2（类型）的禁用状态
        self._apply_content_disable_rules(val)

    def _set_content_widgets_state(self, state):
        """设置文字内容区域控件的状态（古书模式下禁用其他内容，但保留古书单选框）"""
        # 文字内容区域的控件（排除古书单选框和一键导入按钮）
        content_widgets = [
            self.grade_combo, self.version_combo,
            self.cb_first_semester, self.cb_second_semester,
            self.rb_shengzi, self.rb_ciyu, self.rb_gushi, self.rb_wenyan,
            self.rb_shuzi, self.rb_pinyin_text,
            self.text_content
        ]

        for widget in content_widgets:
            if isinstance(widget, tk.Entry) or isinstance(widget, tk.Text):
                widget.config(state=state)
            elif isinstance(widget, ttk.Combobox):
                if state == "disabled":
                    widget.config(state="disabled")
                else:
                    widget.config(state="readonly")
            else:
                widget.config(state=state)

    def _apply_content_disable_rules(self, content_type):
        """根据内容类型（主模块）驱动附加模块1（样式）和附加模块2（类型）的禁用状态"""
        rule = _CONTENT_DISABLE_RULES.get(content_type)

        if not rule:
            # 无规则（空内容类型 / 国学版），全部启用
            for rb in self._style_rbs:
                rb.config(state="normal")
            for widget in self._type_rbs:
                widget.config(state="normal")
            return

        # ── 附加模块1：样式 ──
        disabled_set = set(rule["style_disabled"])

        # 如果当前类型是"带拼音"类，解除"仅带拼音可用"样式的禁用
        is_pinyin_type = self._type_var.get() in ("duoju", "duoju1")
        if is_pinyin_type:
            disabled_set -= _PINYIN_ONLY_STYLES

        for i, rb in enumerate(self._style_rbs):
            rb.config(state="disabled" if i in disabled_set else "normal")

        # 切换内容类型时，主动设置样式为该类型的默认值
        # 但如果当前是带拼音类型，优先选生字格
        if is_pinyin_type and 4 not in disabled_set:
            self._style_var.set(4)  # 生字格
        else:
            self._style_var.set(rule["style_default"])

        # 如果当前选中的样式被禁用，回退到默认值
        if self._style_var.get() in disabled_set:
            self._style_var.set(rule["style_default"])

        # ── 附加模块2：类型 ──
        for widget in self._type_rbs:
            text = widget.cget("text")
            widget.config(state="disabled" if text in rule["type_disabled"] else "normal")

        # 切换内容类型时，主动设置类型为该类型的默认值（或第一个可用类型）
        if rule["type_default"]:
            self._type_var.set(rule["type_default"])
        else:
            for widget in self._type_rbs:
                if widget.cget("state") != "disabled":
                    text = widget.cget("text")
                    if text in _TYPE_TEXT_TO_VALUE:
                        self._type_var.set(_TYPE_TEXT_TO_VALUE[text])
                        break

    def update_grid_type_enabled(self):
        val = self._content_var.get()

        # 如果已选中内容类型，使用规则表驱动（主模块优先）
        if val in _CONTENT_DISABLE_RULES:
            self._apply_content_disable_rules(val)
            return

        # 无内容类型时的回退逻辑（国学版或手动输入场景）
        content = self.text_content.get("1.0", tk.END).strip()
        if not content:
            for rb in self._style_rbs:
                rb.config(state="normal")
            return

        content_type = self._detect_content_type(content)
        if content_type == "hanzi":
            for i in [0, 1, 2, 4, 7]:
                self._style_rbs[i].config(state="normal")
            for i in [3, 5, 6, 8]:
                self._style_rbs[i].config(state="disabled")
            if self._style_var.get() in [3, 5, 6, 8]:
                self._style_var.set(0)
        elif content_type == "pinyin":
            for i in [4, 5, 7]:
                self._style_rbs[i].config(state="normal")
            for i in [0, 1, 2, 3, 6, 8]:
                self._style_rbs[i].config(state="disabled")
            if self._style_var.get() in [0, 1, 2, 3, 6, 8]:
                self._style_var.set(5)
        elif content_type == "number":
            for i in [0, 3, 7]:
                self._style_rbs[i].config(state="normal")
            for i in [1, 2, 4, 5, 6, 8]:
                self._style_rbs[i].config(state="disabled")
            if self._style_var.get() in [1, 2, 4, 5, 6]:
                self._style_var.set(3)
        else:
            for rb in self._style_rbs:
                rb.config(state="normal")

    def _detect_content_type(self, content):
        content = content.replace('\n', '').replace('\r', '').replace(' ', '')
        has_hanzi = False
        has_number = False
        has_pinyin = False
        for char in content:
            if '一' <= char <= '鿿':
                has_hanzi = True
            elif char.isdigit():
                has_number = True
            elif 'a' <= char.lower() <= 'z':
                has_pinyin = True
        if has_hanzi and not has_number and not has_pinyin:
            return "hanzi"
        elif has_number and not has_hanzi:
            return "number"
        elif has_pinyin and not has_hanzi and not has_number:
            return "pinyin"
        else:
            return "mixed"

    def on_content_type_changed(self):
        val = self._content_var.get()
        if val == "shuzi":
            self.text_content.delete("1.0", tk.END)
            self.text_content.insert("1.0", NUMBER_DATA)
            return
        if val == "pinyin_text":
            self.text_content.delete("1.0", tk.END)
            self.text_content.insert("1.0", PINYIN_DATA)
            return

        # 古书模式：从国学著作选择框中获取内容
        if val == "gushu":
            classic = self.classic_combo.get()
            from zitie_data import CLASSIC_DATA
            data = CLASSIC_DATA.get(classic, "")
            self.text_content.delete("1.0", tk.END)
            self.text_content.insert("1.0", data)
            return

        grade = self.grade_combo.get()
        if not grade:
            return

        version = self.version_combo.get()
        version_key = VERSIONS.get(version)
        if not version_key:
            return
        grade_key = GRADES.get(grade)
        if not grade_key:
            return

        has_first = self._first_sem_var.get()
        has_second = self._second_sem_var.get()

        data = ""
        if val == "shengzi":
            if has_first:
                data += GRADE_CHARACTERS.get(version_key, {}).get(grade_key, {}).get("first", {}).get("生字表", "")
            if has_second:
                if data:
                    data += "\n\n"
                data += GRADE_CHARACTERS.get(version_key, {}).get(grade_key, {}).get("second", {}).get("生字表", "")
        elif val == "gushi":
            if has_first:
                data += GRADE_CHARACTERS.get(version_key, {}).get(grade_key, {}).get("first", {}).get("古诗词", "")
            if has_second:
                if data:
                    data += "\n\n"
                data += GRADE_CHARACTERS.get(version_key, {}).get(grade_key, {}).get("second", {}).get("古诗词", "")
        elif val == "wenyan":
            def process_wenyan(wenyan_text):
                lines = wenyan_text.replace('\r\n', '\n').split('\n')
                lines = [line.strip() for line in lines if line.strip()]
                result = []
                i = 0
                while i < len(lines):
                    if i + 2 < len(lines):
                        title = lines[i]
                        author = lines[i+1]
                        content_lines = []
                        j = i + 2
                        while j < len(lines) and not (j + 2 < len(lines) and len(lines[j]) <= 10 and len(lines[j+1]) <= 20):
                            content_lines.append(lines[j])
                            j += 1
                        content_text = ''.join(content_lines)
                        result.append(f"{title}\n{author}\n{content_text}")
                        i = j
                    else:
                        break
                return '\n\n'.join(result)

            if has_first:
                wenyan_first = GRADE_CHARACTERS.get(version_key, {}).get(grade_key, {}).get("first", {}).get("文言文", "")
                data = process_wenyan(wenyan_first)
            if has_second:
                wenyan_second = GRADE_CHARACTERS.get(version_key, {}).get(grade_key, {}).get("second", {}).get("文言文", "")
                wenyan_second = process_wenyan(wenyan_second)
                if data:
                    data += "\n\n"
                data += wenyan_second
        elif val == "ciyu":
            if has_first:
                data += GRADE_CHARACTERS.get(version_key, {}).get(grade_key, {}).get("first", {}).get("词语表", "")
            if has_second:
                if data:
                    data += "\n\n"
                data += GRADE_CHARACTERS.get(version_key, {}).get(grade_key, {}).get("second", {}).get("词语表", "")

        self.text_content.delete("1.0", tk.END)
        self.text_content.insert("1.0", data)
        self.update_grid_type_enabled()

    def on_import_content(self):
        # 古书模式下，导入国学著作内容
        val = self._content_var.get()
        if val == "gushu":
            classic = self.classic_combo.get()
            from zitie_data import CLASSIC_DATA
            data = CLASSIC_DATA.get(classic, "")
            # 确保文本编辑框可用
            self.text_content.config(state="normal")
            self.text_content.delete("1.0", tk.END)
            self.text_content.insert("1.0", data)
        else:
            self.on_content_type_changed()

    def convert_to_fanti(self):
        """将内容编辑框中的简体字转换为繁体字"""
        content = self.text_content.get("1.0", tk.END).strip()
        if not content:
            messagebox.showwarning("提示", "内容编辑框为空，请先输入或导入内容！")
            return

        try:
            # 使用 opencc 将简体字转换为繁体字
            converter = opencc.OpenCC('s2t')
            fanti_content = converter.convert(content)
            # 清空内容编辑框并插入繁体字内容
            self.text_content.delete("1.0", tk.END)
            self.text_content.insert("1.0", fanti_content)
            messagebox.showinfo("转换成功", "已将内容转换为繁体字！")
        except Exception as e:
            messagebox.showerror("转换失败", f"繁体字转换失败：{str(e)}")

    def on_font_variant_changed(self):
        """简体/繁体单选框切换时，转换内容编辑框中的文字"""
        content = self.text_content.get("1.0", tk.END).strip()
        if not content:
            return

        try:
            if self._font_variant_var.get() == 1:
                # 繁体：简体转繁体
                converter = opencc.OpenCC('s2t')
                converted_content = converter.convert(content)
            else:
                # 简体：繁体转简体
                converter = opencc.OpenCC('t2s')
                converted_content = converter.convert(content)

            # 清空内容编辑框并插入转换后的内容
            self.text_content.delete("1.0", tk.END)
            self.text_content.insert("1.0", converted_content)
        except Exception as e:
            messagebox.showerror("转换失败", f"字体转换失败：{str(e)}")

    def clear_content(self):
        self.text_content.delete("1.0", tk.END)

    def get_grid_type(self):
        style_map = {
            0: "田字格", 1: "方格", 2: "米字格", 3: "数学格",
            4: "生字格", 5: "四线三格", 6: "作文本", 7: "教案格", 8: "大楷本", 9: "竖行"
        }
        return style_map.get(self._style_var.get(), "田字格")

    def get_char_type(self):
        if self._miaohong_var.get():
            return "描红"

        type_val = self._type_var.get()
        base_map = {
            "duozi": "单字", "bishun": "笔顺", "duoju": "带拼音", "wenzhang": "整行", "wenzhang_wz": "文章",
            "duozi1": "单字+1行", "bishun1": "笔顺+1行", "duoju1": "带拼音+1行", "wenzhang1": "整行+1行"
        }
        base_type = base_map.get(type_val, "单字")

        if self._huizi_var.get():
            return "灰字" + base_type
        return base_type

    def generate_zitie(self):
        config = ZitieConfig()

        if self._mode_var.get() == 1:
            config.mode = "blank"
            try:
                config.page_count = int(self.page_count_edit.get())
            except ValueError:
                config.page_count = 1
        else:
            config.mode = "zitie"
            config.chars = self.text_content.get("1.0", tk.END).strip()
            config.char_type = self.get_char_type()
            config.content_type = self.get_content_name()

        config.grid_type = self.get_grid_type()
        config.font_name = self.get_font_name()

        generator = ZitieGenerator()
        generator.set_config(config)

        try:
            self.last_generated_path = generator.generate()
            if self.last_generated_path:
                messagebox.showinfo("生成成功",
                                    f"字帖已生成！\n文件路径：{self.last_generated_path}")
            else:
                messagebox.showwarning("生成失败", "未能生成字帖！")
        except Exception as e:
            messagebox.showerror("生成错误", f"生成过程中发生错误：{str(e)}")

    def get_content_name(self):
        # 古书模式：返回国学著作名称
        if self._content_var.get() == "gushu":
            return self.classic_combo.get()

        content_names = {
            "shengzi": "生字", "gushi": "诗词", "ciyu": "词语",
            "wenyan": "文言文", "shuzi": "数字", "pinyin_text": "拼音",
            "gaiding": "大楷"
        }
        return content_names.get(self._content_var.get(), "字帖")

    def export_pdf(self):
        config = ZitieConfig()
        config.grid_type = self.get_grid_type()
        config.font_name = self.get_font_name()

        if self._mode_var.get() == 1:
            config.mode = "blank"
            try:
                config.page_count = int(self.page_count_edit.get())
            except ValueError:
                config.page_count = 5
        else:
            content = self.text_content.get("1.0", tk.END).strip()
            if not content:
                messagebox.showwarning("提示", "请先在编辑框中输入内容！")
                return
            config.mode = "zitie"
            config.chars = content
            config.char_type = self.get_char_type()
            config.content_type = self.get_content_name()

        generator = ZitieGenerator()
        generator.set_config(config)

        try:
            grid_name = self.get_grid_type()
            content_name = self.get_content_name()
            time_str = datetime.now().strftime("%H%M%S")

            if self._mode_var.get() == 1:
                file_name = f"{grid_name}_{config.page_count}页.pdf"
            else:
                char_type = self.get_char_type()
                file_name = f"{grid_name}{content_name}_{char_type}_{time_str}.pdf"

            file_path = os.path.join(os.getcwd(), file_name)
            success = generator.save_pdf(file_path)
            if not success:
                messagebox.showerror("导出失败", "保存PDF文件失败！")
        except Exception as e:
            messagebox.showerror("导出错误", f"导出过程中发生错误：{str(e)}")

    def on_font_radio_changed(self):
        is_custom = self._font_var.get() == 4
        self.edit_custom_font.config(state="normal" if is_custom else "disabled")
        self.btn_preview_font.config(state="normal" if is_custom else "disabled")
        # 选择其他字体时，清空自定义字体输入框
        if not is_custom:
            self.edit_custom_font.delete(0, tk.END)

    def get_font_name(self):
        if self._content_var.get() == "pinyin_text":
            return "pinyin-me"

        # 大楷模式使用欧阳询书法字体
        if self._content_var.get() == "gaiding":
            return "欧阳询书法字体"

        # 古书模式使用行楷（田英章）
        if self._content_var.get() == "gushu":
            return "田英章"

        font_val = self._font_var.get()
        # 自定义字体优先级最高
        if font_val == 4:
            custom_font = self.edit_custom_font.get().strip()
            if custom_font:
                return custom_font
            else:
                return "楷体_GB2312"  # 如果没有输入自定义字体，使用默认楷体
        elif font_val == 0:
            # 默认字体：数字模式使用楷体，其他模式也使用楷体
            return "楷体_GB2312"
        elif font_val == 1:
            return "楷体_GB2312"
        elif font_val == 2:
            return "荆霄鹏"
        elif font_val == 3:
            return "田英章"
        else:
            return "楷体_GB2312"

    def on_select_font(self):
        font_path = filedialog.askopenfilename(
            title="选择字体文件",
            filetypes=[("字体文件", "*.ttf *.ttc *.otf")]
        )
        if font_path:
            font_name = add_custom_font(font_path)
            if font_name:
                self.edit_custom_font.delete(0, tk.END)
                self.edit_custom_font.insert(0, font_name)
            else:
                messagebox.showwarning("字体添加失败",
                                       "无法添加该字体文件，请尝试以下解决方法：\n\n"
                                       "1. 确保选择的是有效的TTF、TTC或OTF字体文件\n"
                                       "2. 尝试使用系统字体目录中的字体（如 C:\\Windows\\Fonts\\）\n"
                                       "3. 检查字体文件是否被其他程序占用\n"
                                       "4. 字体文件路径不要包含中文或特殊字符")
