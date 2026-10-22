# yingyu_ui.py — 英语标签页（重建设计：内容 / 方式 / 字体 / 方向）
import os
import random
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from widgets import GradientButton
from yingyu.yingyu_core import YingyuGenerator, FONT_OPTIONS

# 内容 / 方式 / 方向 选项
CONTENT_OPTIONS = ["单词", "课文", "表达句", "音标"]
STYLE_OPTIONS = ["字帖（描红）", "出题（默写）"]
DIRECTION_OPTIONS = ["随机出题", "汉译英", "英译汉"]
# 预览字体（tkinter）映射
TK_FONT_MAP = {"Helvetica": "Helvetica", "Courier": "Courier",
               "Times-Roman": "Times", "舒窈衡水体": "Microsoft YaHei",
               "手写体": "Microsoft YaHei"}
from yingyu.yingyu_core import (
    get_versions, get_grades, get_semesters,
    get_units, add_entry,
    get_common_categories, get_common_words,
)

# 「常用词句」下拉：默认项为「课内单词」（沿用原 版本/年级/学期/单元 逻辑）；
# 选其他分类（数字/星期/季节…）则改用分类词表，忽略 版本/年级/学期/单元。
COMMON_DEFAULT = "（课内单词）"

BG = "#f0f0f0"


class YingyuTabWidget:
    def __init__(self, parent):
        self.frame = tk.Frame(parent, bg=BG)
        self.gen = YingyuGenerator()
        self._last_items = None
        self._init_ui()

    def _init_ui(self):
        main = tk.Frame(self.frame, bg=BG)
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        # 顶部控制区
        ctrl = ttk.LabelFrame(main, text="设置")
        ctrl.pack(fill=tk.X, pady=(0, 6))
        inner = tk.Frame(ctrl, bg=BG)
        # 顶部 pady 0：让第一行（版本行）更贴近设置框上边框（tkinter 不允许负 padding，故用压缩顶部内边距实现上移）
        inner.pack(anchor="w", padx=6, pady=(0, 6))

        versions = get_versions()
        first_version = versions[0] if versions else ""

        def _default(preferred, options):
            return preferred if preferred in options else (options[0] if options else "")

        tk.Label(inner, text="版本:", bg=BG, font=("Microsoft YaHei", 10)).grid(row=0, column=0, sticky="w")
        self.version_var = tk.StringVar(value=first_version)
        self.version_combo = ttk.Combobox(inner, width=11, state="readonly", font=("Microsoft YaHei", 10),
                                          values=versions, textvariable=self.version_var)
        self.version_combo.grid(row=0, column=1, padx=(4, 0), sticky="w")
        self.version_combo.bind("<<ComboboxSelected>>", lambda e: self._on_version_changed())

        tk.Label(inner, text="年级:", bg=BG, font=("Microsoft YaHei", 10)).grid(row=0, column=2, padx=(4, 0), sticky="w")
        self.grade_var = tk.StringVar(value=_default("五年级", get_grades(first_version)))
        self.grade_combo = ttk.Combobox(inner, width=9, state="readonly", font=("Microsoft YaHei", 10),
                                        values=get_grades(first_version), textvariable=self.grade_var)
        self.grade_combo.grid(row=0, column=3, padx=(4, 0), sticky="w")
        self.grade_combo.bind("<<ComboboxSelected>>", lambda e: self._on_grade_changed())

        tk.Label(inner, text="学期:", bg=BG, font=("Microsoft YaHei", 10)).grid(row=0, column=4, padx=(4, 0), sticky="w")
        self.semester_var = tk.StringVar(value=_default("上学期", get_semesters(first_version, self.grade_var.get())))
        self.semester_combo = ttk.Combobox(inner, width=10, state="readonly", font=("Microsoft YaHei", 10),
                                           values=get_semesters(first_version, self.grade_var.get()),
                                           textvariable=self.semester_var)
        self.semester_combo.grid(row=0, column=5, padx=(4, 0), sticky="w")
        self.semester_combo.bind("<<ComboboxSelected>>", lambda e: (self._reset_common(), self._refresh_units(), self._update_preview()))

        tk.Label(inner, text="单元:", bg=BG, font=("Microsoft YaHei", 10)).grid(row=1, column=0, sticky="w")
        self.unit_var = tk.StringVar(value=get_units(self.version_var.get(),
                                                     self.grade_var.get(),
                                                     self.semester_var.get())[0])  # 默认 Unit 1
        # 单元下拉框（与版本/常用左对齐）
        u_frame = tk.Frame(inner, bg=BG)
        u_frame.grid(row=1, column=1, padx=(4, 0), sticky="w")
        self.unit_combo = ttk.Combobox(u_frame, width=7, state="readonly", font=("Microsoft YaHei", 10),
                                       values=get_units(self.version_var.get(),
                                                       self.grade_var.get(),
                                                       self.semester_var.get()),
                                       textvariable=self.unit_var)
        self.unit_combo.pack(side=tk.LEFT)
        self.unit_combo.bind("<<ComboboxSelected>>", lambda e: self._update_preview())

        def _refresh_units(reset_to_all=True):
            """按当前版本/年级/学期刷新单元下拉项数（陕旅版为 8 单元，其余多为 6）。
            reset_to_all=True 时自动切到「全部单元」（版本/年级/学期切换时用）。"""
            units = get_units(self.version_var.get(), self.grade_var.get(), self.semester_var.get())
            self.unit_combo.configure(values=units)
            if reset_to_all and units:
                self.unit_var.set(units[-1])  # 末位 = 全部单元
            elif self.unit_var.get() not in units:
                self.unit_var.set(units[0] if units else "")

        # 挂到实例上，供版本/年级/学期切换事件调用
        self._refresh_units = _refresh_units

        # 「灰字」勾选框：勾选后导出 PDF 的单词/句子文字为灰色（描红临摹用），置于内容下拉右侧
        self.gray_var = tk.BooleanVar(value=False)
        self.gray_check = tk.Checkbutton(inner, text="灰字", variable=self.gray_var,
                                         bg=BG, font=("Microsoft YaHei", 10))
        self.gray_check.grid(row=0, column=8, padx=(4, 0), sticky="w")

        # 第二行：内容 / 方式 / 字体 / 方向（内容已移至第一行末尾）
        tk.Label(inner, text="内容:", bg=BG, font=("Microsoft YaHei", 10)).grid(row=0, column=6, padx=(4, 0), sticky="w")
        self.content_var = tk.StringVar(value=CONTENT_OPTIONS[0])
        self.content_combo = ttk.Combobox(inner, width=8, state="readonly", font=("Microsoft YaHei", 10),
                                          values=CONTENT_OPTIONS, textvariable=self.content_var)
        self.content_combo.grid(row=0, column=7, padx=(4, 0), pady=(0, 0), sticky="w")
        self.content_combo.bind("<<ComboboxSelected>>", lambda e: self._on_content_changed())

        tk.Label(inner, text="方式:", bg=BG, font=("Microsoft YaHei", 10)).grid(row=1, column=2, padx=(4, 0), pady=(0, 0), sticky="w")
        self.style_var = tk.StringVar(value=STYLE_OPTIONS[0])
        self.style_combo = ttk.Combobox(inner, width=9, state="readonly", font=("Microsoft YaHei", 10),
                                        values=STYLE_OPTIONS, textvariable=self.style_var)
        self.style_combo.grid(row=1, column=3, padx=(4, 0), pady=(0, 0), sticky="w")
        self.style_combo.bind("<<ComboboxSelected>>", lambda e: (self._on_style_changed(), self._update_preview()))

        # 方向（下拉框，仅「出题」方式下可点；字帖时灰显）
        tk.Label(inner, text="方向:", bg=BG, font=("Microsoft YaHei", 10)).grid(row=1, column=4, padx=(4, 0), pady=(0, 0), sticky="w")
        self.direction_var = tk.StringVar(value=DIRECTION_OPTIONS[0])  # 默认随机
        self.direction_combo = ttk.Combobox(inner, width=10, state=tk.DISABLED, font=("Microsoft YaHei", 10),
                                            values=DIRECTION_OPTIONS, textvariable=self.direction_var)
        self.direction_combo.grid(row=1, column=5, padx=(4, 0), pady=(0, 0), sticky="w")
        self._on_style_changed()  # 同步初始状态（默认「字帖」→ 方向灰显）

        tk.Label(inner, text="字体:", bg=BG, font=("Microsoft YaHei", 10)).grid(row=1, column=6, padx=(4, 0), pady=(0, 0), sticky="w")
        self.font_var = tk.StringVar(value="舒窈衡水体")
        self.font_combo = ttk.Combobox(inner, width=10, state="readonly", font=("Microsoft YaHei", 10),
                                       values=FONT_OPTIONS, textvariable=self.font_var)
        self.font_combo.grid(row=1, column=7, padx=(4, 0), pady=(0, 0), sticky="w")
        self.font_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_preview_font())

        # 第三行：常用（独立于 版本/年级/学期/单元 的分类词表，如 数字/星期/季节…）
        tk.Label(inner, text="常用:", bg=BG, font=("Microsoft YaHei", 10)).grid(row=2, column=0, pady=(3, 0), sticky="w")
        self.common_var = tk.StringVar(value=COMMON_DEFAULT)
        self.common_combo = ttk.Combobox(inner, width=11, state="readonly", font=("Microsoft YaHei", 10),
                                         values=[COMMON_DEFAULT] + get_common_categories(),
                                         textvariable=self.common_var)
        self.common_combo.grid(row=2, column=1, padx=(4, 0), pady=(3, 0), sticky="w")
        self.common_combo.bind("<<ComboboxSelected>>", lambda e: self._on_common_changed())

        # 功能区（固定置于软件底边，按钮尺寸与其他模块一致）
        func = ttk.LabelFrame(main, text="功能区")
        func.pack(side=tk.BOTTOM, fill=tk.X, pady=(6, 0))
        finner = tk.Frame(func, bg=BG)
        finner.pack(padx=10, pady=10)

        # 「新增版本」按钮（管理类，绿色区分，置于最左）
        btn_add = GradientButton(finner, text="新增版本", width=100, height=32, command=self.on_add_version,
                                 color_top="#34d399", color_mid="#10b981", color_bot="#059669",
                                 hover_top="#6ee7b7", hover_mid="#34d399", hover_bot="#10b981")
        # 「添加单词」按钮（录入类，橙色区分）
        btn_addword = GradientButton(finner, text="添加单词", width=100, height=32, command=self.on_add_word,
                                     color_top="#fbbf24", color_mid="#f59e0b", color_bot="#d97706",
                                     hover_top="#fcd34d", hover_mid="#fbbf24", hover_bot="#f59e0b")
        btn_gen = GradientButton(finner, text="生成", width=100, height=32, command=self.on_generate)
        btn_clear = GradientButton(finner, text="清空", width=100, height=32, command=self.on_clear)
        btn_pdf = GradientButton(finner, text="导出PDF", width=100, height=32, command=self.on_export_pdf)

        # 「打开数据」小按钮：用记事本直接打开数据文件，客户也能自助维护词句
        btn_data = GradientButton(finner, text="打开数据", width=72, height=32,
                                  command=self.on_open_data,
                                  color_top="#93c5fd", color_mid="#60a5fa", color_bot="#3b82f6",
                                  hover_top="#bfdbfe", hover_mid="#93c5fd", hover_bot="#60a5fa")

        for i, b in enumerate((btn_add, btn_addword, btn_gen, btn_clear, btn_pdf), 1):
            finner.columnconfigure(i, weight=1)
            b.grid(row=0, column=i, padx=6)
        finner.columnconfigure(6, weight=0)
        btn_data.grid(row=0, column=6, padx=(4, 0))

        # 预览区（填充中部剩余空间，功能区固定在底边）
        prev_frame = tk.Frame(main, bg=BG)
        prev_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(6, 0))
        tk.Label(prev_frame, text="预览", bg=BG, font=("Microsoft YaHei", 10)).pack(anchor="w")
        scroll = tk.Scrollbar(prev_frame)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.text = tk.Text(prev_frame, bg="white", wrap=tk.WORD, height=16,
                            yscrollcommand=scroll.set, font=("Microsoft YaHei", 11))
        self.text.pack(fill=tk.BOTH, expand=True)
        scroll.config(command=self.text.yview)

        # 打开即按当前选择（默认 人教版PEP·五年级·上学期·Unit 1·单词·字帖）渲染预览
        self._update_preview()

    def _update_preview(self):
        """按当前「版本/年级/学期/单元/内容/方式」即时刷新预览文本框。"""
        version, grade, semester, content, style, unit_name, picked = self._collect()
        if not picked:
            self.text.delete("1.0", tk.END)
            self.text.insert("1.0",
                f"「{version} · {grade}{semester} · {unit_name} · {content}」暂无数据，请在对应数据文件中补充。")
            self._last_items = None
            return
        self._last_items = (version, grade, semester, content, style, unit_name, picked)
        if content == "音标":
            self._fill_phonetic_preview(picked)
            return
        text = self.gen.render_text(content, style, version, grade, semester, picked,
                                    unit_name=unit_name, direction=self.direction_var.get())
        if version == "常用":
            text = f"【常用 · {unit_name}】\n\n" + text
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", text)

    def _fill_phonetic_preview(self, items):
        """音标预览：层级化逐行显示，一级目录（元音/辅音）与二级目录（长元音等）分别加粗。
        结构：第一行一级目录 → 第二行二级目录 → 其后各音标条目每行一个。
        """
        self.text.tag_configure("phon_lv1", font=("Microsoft YaHei", 12, "bold"))
        self.text.tag_configure("phon_lv2", font=("Microsoft YaHei", 11, "bold"))
        self.text.tag_configure("phon_sym", font=("Microsoft YaHei", 13, "bold"))
        self.text.delete("1.0", tk.END)
        self.text.insert(tk.END, "【音标 · 国际音标表】\n\n")
        _g = None
        _s = None
        for it in items:
            g = it.get("group", "")
            s = it.get("sub", "")
            if g != _g:
                self.text.insert(tk.END, g + "\n", "phon_lv1")
                _g = g
                _s = None
            if s != _s:
                self.text.insert(tk.END, s + "\n", "phon_lv2")
                _s = s
            _mn = it.get("mnemonic", "")
            _prac = (it.get("symbol", "") or "").strip("[]")
            _tail = ""
            if _mn:
                _tail += f"   {_mn}"
            if _prac:
                _tail += f"   {_prac} {_prac} {_prac}"
            # 例词只取前 2 个
            _exs = [e for e in it.get("examples", "").split("；") if e.strip()][:2]
            _ex_str = "；".join(_exs)
            sym = it.get("symbol", "")
            rest = f"  {it.get('read',''):<10}{it.get('zh',''):<6}{_ex_str}{_tail}\n"
            # 音标符号单独加粗、增大字号（13pt bold），其余正文字号不变
            self.text.insert(tk.END, sym, "phon_sym")
            self.text.insert(tk.END, rest)

    def _on_version_changed(self):
        # 切换版本：刷新年级 / 学期 / 单元下拉（各版本年级、学期、单元数均从数据动态读取）
        self._reset_common()  # 若当前处于「常用」分类，先切回课内单词
        v = self.version_var.get()
        grades = get_grades(v)
        self.grade_combo.configure(values=grades)
        self.grade_var.set(grades[0] if grades else "")
        sems = get_semesters(v, self.grade_var.get())
        self.semester_combo.configure(values=sems)
        self.semester_var.set(sems[0] if sems else "")
        self._refresh_units()
        self._update_preview()

    def _on_grade_changed(self):
        # 切换年级：刷新学期 / 单元下拉
        self._reset_common()  # 若当前处于「常用」分类，先切回课内单词
        v = self.version_var.get()
        g = self.grade_var.get()
        sems = get_semesters(v, g)
        self.semester_combo.configure(values=sems)
        self.semester_var.set(sems[0] if sems else "")
        self._refresh_units()
        self._update_preview()

    def on_open_data(self):
        """打开「数据编辑」窗口，直接改当前 版本/年级 的那一个文本文件。

        数据按 版本/年级 分成 yingyu/data/<版本>/<年级>.txt（一个文件含上册+下册），
        打开时会自动定位并把光标停在当前选中的「学期 + 单元」，保存后立即重新载入，
        不需要重启软件，也不用手动去翻文件夹。
        """
        version = (self.version_var.get() or "").strip()
        grade = (self.grade_var.get() or "").strip()
        if not version or not grade:
            messagebox.showinfo("提示", "请先选择版本和年级。", parent=self.frame)
            return
        try:
            from yingyu import yingyu_store as store
            text = store.read_grade_text(version, grade)
            path = store.data_file(version, grade)
        except Exception as e:
            messagebox.showerror("打开失败", f"无法定位数据文件：{e}")
            return
        self._open_data_editor(version, grade, self.semester_var.get(),
                               self.unit_var.get(), path, text, store)

    def _open_data_editor(self, version, grade, semester, unit, path, text, store):
        """内置的轻量文本编辑器：定位到目标单元、高亮该行、Ctrl+S 保存即生效。"""
        old = getattr(self, "_editor", None)
        if old and old["win"].winfo_exists():
            old["win"].destroy()

        win = tk.Toplevel(self.frame)
        win.title("数据编辑 · %s · %s（上册 + 下册）" % (version, grade))
        win.geometry("900x660")
        win.minsize(660, 400)
        try:
            win.transient(self.frame.winfo_toplevel())
        except Exception:
            pass

        head = tk.Frame(win, bg="#f7f7f7")
        head.pack(fill=tk.X)
        tk.Label(head, text="%s · %s" % (version, grade), bg="#f7f7f7",
                 font=("Microsoft YaHei", 10, "bold")).pack(anchor="w", padx=10, pady=(6, 0))
        tk.Label(head, text=path, bg="#f7f7f7", fg="#888",
                 font=("Microsoft YaHei", 8)).pack(anchor="w", padx=10)
        tk.Label(head,
                 text="格式：[上学期] Unit 1  ｜  .单词 / .课文 / .表达句  ｜  "
                      "单词：单词 /音标/ 中文  ｜  句子：英文 || 中文  ｜  行首 * = 三会词",
                 bg="#f7f7f7", fg="#666", font=("Microsoft YaHei", 8)).pack(anchor="w", padx=10, pady=(2, 6))

        body = tk.Frame(win)
        body.pack(fill=tk.BOTH, expand=True, padx=8, pady=(6, 0))
        sb = ttk.Scrollbar(body)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        txt = tk.Text(body, wrap=tk.WORD, undo=True, font=("Microsoft YaHei", 10),
                      yscrollcommand=sb.set, padx=6, pady=4)
        txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.config(command=txt.yview)
        txt.insert("1.0", text)
        txt.edit_reset()          # 打开时不算一次可撤销操作

        bar = tk.Frame(win)
        bar.pack(fill=tk.X, padx=10, pady=8)
        status = tk.Label(bar, text="", fg="#059669", font=("Microsoft YaHei", 9))
        status.pack(side=tk.RIGHT, padx=(8, 0))

        def _goto_target():
            """把光标停在当前选中的 学期+单元 上，并高亮那一行。"""
            if unit and not unit.startswith("全部"):
                needle = "[%s] %s" % (semester, unit)
            else:
                needle = "[%s]" % semester
            idx = txt.search(needle, "1.0", stopindex=tk.END)
            if not idx:
                return False
            txt.tag_configure("hit", background="#fff3bf")
            txt.tag_remove("hit", "1.0", tk.END)
            txt.tag_add("hit", "%s linestart" % idx, "%s +1line linestart" % idx)
            txt.mark_set("insert", idx)
            txt.see(idx)
            return True

        def _dirty():
            return txt.get("1.0", "end-1c") != text

        def _save():
            content = txt.get("1.0", "end-1c")
            try:
                store.save_grade_text(version, grade, content)
            except ValueError as e:
                messagebox.showwarning("未保存", str(e), parent=win)
                return
            except Exception as e:
                messagebox.showerror("保存失败", str(e), parent=win)
                return
            status.config(text="已保存 ✓  数据已重新载入", fg="#059669")
            win.after(2600, lambda: status.config(text="") if status.winfo_exists() else None)
            self._after_data_saved()
            _goto_target()

        def _open_folder():
            try:
                os.startfile(os.path.dirname(path))
            except Exception as e:
                messagebox.showinfo("文件夹位置", "%s\n\n(%s)" % (os.path.dirname(path), e), parent=win)

        def _open_notepad():
            try:
                if _dirty() and not messagebox.askyesno(
                        "提示", "还有改动没保存，用外部程序打开会丢掉这些改动。继续？", parent=win):
                    return
                os.startfile(path)
            except Exception as e:
                messagebox.showinfo("文件位置", "%s\n\n(%s)" % (path, e), parent=win)

        def _close():
            if _dirty() and not messagebox.askyesno("关闭", "有改动还没保存，确定关闭？", parent=win):
                return
            win.destroy()

        GradientButton(bar, text="保存", width=88, height=30, command=_save,
                       color_top="#34d399", color_mid="#10b981", color_bot="#059669",
                       hover_top="#6ee7b7", hover_mid="#34d399", hover_bot="#10b981"
                       ).pack(side=tk.LEFT)
        GradientButton(bar, text="打开文件夹", width=96, height=30, command=_open_folder,
                       color_top="#e5e7eb", color_mid="#d1d5db", color_bot="#9ca3af",
                       hover_top="#f3f4f6", hover_mid="#e5e7eb", hover_bot="#d1d5db"
                       ).pack(side=tk.LEFT, padx=(8, 0))
        GradientButton(bar, text="用记事本打开", width=108, height=30, command=_open_notepad,
                       color_top="#93c5fd", color_mid="#60a5fa", color_bot="#3b82f6",
                       hover_top="#bfdbfe", hover_mid="#93c5fd", hover_bot="#60a5fa"
                       ).pack(side=tk.LEFT, padx=(8, 0))
        GradientButton(bar, text="关闭", width=80, height=30, command=_close,
                       color_top="#e5e7eb", color_mid="#d1d5db", color_bot="#9ca3af",
                       hover_top="#f3f4f6", hover_mid="#e5e7eb", hover_bot="#d1d5db"
                       ).pack(side=tk.LEFT, padx=(8, 0))

        if not _goto_target():
            status.config(text="未找到「%s」分节，已定位到文件开头" % semester, fg="#b45309")

        win.bind("<Control-s>", lambda e: (_save(), "break")[1])
        win.bind("<Control-S>", lambda e: (_save(), "break")[1])
        win.protocol("WM_DELETE_WINDOW", _close)
        win.after(60, lambda: txt.focus_set() if txt.winfo_exists() else None)
        txt.see("insert")
        self._editor = {"win": win, "txt": txt}

    def _after_data_saved(self):
        """数据文件保存后：让下拉框与预览跟着最新数据走。"""
        try:
            self.version_combo.configure(values=get_versions())
            grades = get_grades(self.version_var.get())
            self.grade_combo.configure(values=grades)
            if grades and self.grade_var.get() not in grades:
                self.grade_var.set(grades[0])
            self._refresh_units(reset_to_all=False)
            self._update_preview()
        except Exception:
            pass

    def on_add_version(self):
        # 弹窗输入版本名 → 在数据文件里建一个占位单元；成功则刷新并选中新版本
        name = simpledialog.askstring("新增版本", "请输入新版本名称（如：北师大版）：", parent=self.frame)
        if not name:
            return
        ok, msg = self.gen.add_version(name)
        if ok:
            self.version_combo.configure(values=get_versions())
            self.version_var.set(name)
            self._on_version_changed()
            messagebox.showinfo("成功", msg)
        else:
            messagebox.showerror("失败", msg)

    def on_add_word(self):
        # 「添加单词 / 课文 / 表达句」弹窗：客户选 版本/年级/学期/单元，
        # 填 单词·音标·意思 或 课文/表达句·中文，点保存由 add_entry() 自动写回数据文件。
        dlg = tk.Toplevel(self.frame)
        dlg.title("添加单词 / 课文 / 表达句")
        dlg.transient(self.frame)
        dlg.grab_set()
        dlg.resizable(False, False)
        pad = {"padx": 8, "pady": 4}

        tk.Label(dlg, text="版本:").grid(row=0, column=0, sticky="e", **pad)
        ver_var = tk.StringVar(value=self.version_var.get())
        ver_combo = ttk.Combobox(dlg, width=16, state="readonly", values=get_versions(), textvariable=ver_var)
        ver_combo.grid(row=0, column=1, **pad)

        tk.Label(dlg, text="年级:").grid(row=0, column=2, sticky="e", **pad)
        grade_var = tk.StringVar(value=self.grade_var.get())
        grade_combo = ttk.Combobox(dlg, width=8, state="readonly",
                                   values=get_grades(ver_var.get()), textvariable=grade_var)
        grade_combo.grid(row=0, column=3, **pad)

        tk.Label(dlg, text="学期:").grid(row=1, column=0, sticky="e", **pad)
        sem_var = tk.StringVar(value=self.semester_var.get())
        sem_combo = ttk.Combobox(dlg, width=8, state="readonly",
                                 values=get_semesters(ver_var.get(), grade_var.get()), textvariable=sem_var)
        sem_combo.grid(row=1, column=1, **pad)

        tk.Label(dlg, text="单元:").grid(row=1, column=2, sticky="e", **pad)
        unit_var = tk.StringVar(value="Unit 1")
        unit_combo = ttk.Combobox(dlg, width=8, state="readonly",
                                  values=get_units(ver_var.get(), grade_var.get(),
                                                  sem_var.get())[:-1], textvariable=unit_var)
        unit_combo.grid(row=1, column=3, **pad)

        def _refresh_gs():
            g = get_grades(ver_var.get())
            grade_combo.configure(values=g)
            if grade_var.get() not in g:
                grade_var.set(g[0] if g else "")
            s = get_semesters(ver_var.get(), grade_var.get())
            sem_combo.configure(values=s)
            if sem_var.get() not in s:
                sem_var.set(s[0] if s else "")
            # 单元项数随版本/年级/学期动态变化（如陕旅版为 8 单元）
            units = get_units(ver_var.get(), grade_var.get(), sem_var.get())[:-1]
            unit_combo.configure(values=units)
            if unit_var.get() not in units:
                unit_var.set(units[0] if units else "Unit 1")

        ver_combo.bind("<<ComboboxSelected>>", lambda e: _refresh_gs())
        grade_combo.bind("<<ComboboxSelected>>", lambda e: _refresh_gs())

        tk.Label(dlg, text="类型:").grid(row=2, column=0, sticky="e", **pad)
        type_var = tk.StringVar(value="单词")
        type_combo = ttk.Combobox(dlg, width=8, state="readonly",
                                  values=["单词", "课文", "表达句"], textvariable=type_var)
        type_combo.grid(row=2, column=1, **pad)

        frm = tk.Frame(dlg)
        frm.grid(row=3, column=0, columnspan=4, **pad)

        word_var = tk.StringVar(); ph_var = tk.StringVar(); mean_var = tk.StringVar()
        en_var = tk.StringVar(); zh_var = tk.StringVar()
        word_widgets = []; sent_widgets = []

        def _build_word():
            for w in word_widgets + sent_widgets:
                w.destroy()
            word_widgets.clear(); sent_widgets.clear()
            tk.Label(frm, text="单词:").grid(row=0, column=0, sticky="e", **pad)
            e1 = tk.Entry(frm, width=22, textvariable=word_var); e1.grid(row=0, column=1, **pad); word_widgets.append(e1)
            tk.Label(frm, text="音标:").grid(row=0, column=2, sticky="e", **pad)
            e2 = tk.Entry(frm, width=18, textvariable=ph_var); e2.grid(row=0, column=3, **pad); word_widgets.append(e2)
            tk.Label(frm, text="意思:").grid(row=1, column=0, sticky="e", **pad)
            e3 = tk.Entry(frm, width=46, textvariable=mean_var); e3.grid(row=1, column=1, columnspan=3, sticky="w", **pad); word_widgets.append(e3)

        def _build_sent():
            for w in word_widgets + sent_widgets:
                w.destroy()
            word_widgets.clear(); sent_widgets.clear()
            tk.Label(frm, text="英文:").grid(row=0, column=0, sticky="e", **pad)
            e1 = tk.Entry(frm, width=46, textvariable=en_var); e1.grid(row=0, column=1, columnspan=3, sticky="w", **pad); sent_widgets.append(e1)
            tk.Label(frm, text="中文:").grid(row=1, column=0, sticky="e", **pad)
            e2 = tk.Entry(frm, width=46, textvariable=zh_var); e2.grid(row=1, column=1, columnspan=3, sticky="w", **pad); sent_widgets.append(e2)

        def _on_type():
            if type_var.get() == "单词":
                _build_word()
            else:
                _build_sent()

        type_combo.bind("<<ComboboxSelected>>", lambda e: _on_type())
        _on_type()

        def _save():
            v = ver_var.get(); g = grade_var.get(); s = sem_var.get()
            units = get_units(v, g, s)[:-1]
            try:
                ui = units.index(unit_var.get())
            except ValueError:
                ui = 0
            t = type_var.get()
            if t == "单词":
                ok, msg = add_entry(v, g, s, ui, "word",
                                    word=word_var.get(), phonetic=ph_var.get(), meaning=mean_var.get())
            elif t == "课文":
                ok, msg = add_entry(v, g, s, ui, "sentence",
                                    en=en_var.get(), zh=zh_var.get())
            else:  # 表达句
                ok, msg = add_entry(v, g, s, ui, "expression",
                                    en=en_var.get(), zh=zh_var.get())
            if ok:
                messagebox.showinfo("成功", msg)
                # 清空输入，便于连续添加
                word_var.set(""); ph_var.set(""); mean_var.set("")
                en_var.set(""); zh_var.set("")
            else:
                messagebox.showerror("失败", msg)

        ttk.Button(dlg, text="保存", width=10, command=_save).grid(row=4, column=1, **pad)
        ttk.Button(dlg, text="关闭", width=10, command=dlg.destroy).grid(row=4, column=2, **pad)

        # 居中显示：构建完成后按屏幕尺寸计算并定位到屏幕正中
        dlg.update_idletasks()
        dw = dlg.winfo_width()
        dh = dlg.winfo_height()
        x = max(0, (dlg.winfo_screenwidth() - dw) // 2)
        y = max(0, (dlg.winfo_screenheight() - dh) // 2)
        dlg.geometry(f"{dw}x{dh}+{x}+{y}")

    def _on_style_changed(self):
        # 仅在「出题」方式下，方向下拉可点；字帖（描红）时灰显
        if self.style_var.get().startswith("出题"):
            self.direction_combo.configure(state="readonly")
        else:
            self.direction_combo.configure(state=tk.DISABLED)

    def _reset_common(self):
        """版本/年级/学期切换时：若「常用」下拉处于某分类、或内容为「音标」，重置为课内单词，
        使预览回到当前版本/年级/学期的课内单词。"""
        if self.common_var.get() != COMMON_DEFAULT:
            self.common_var.set(COMMON_DEFAULT)
            self.content_combo.configure(state="readonly")
        if self.content_var.get() == "音标":
            self.content_var.set("单词")

    def _on_common_changed(self):
        # 选中常用分类：内容强制为「单词」（常用词句均为单词），并禁用 内容 下拉；
        # 选回「（课内单词）」则恢复 内容 下拉（沿用 版本/年级/学期/单元 逻辑）。
        if self.common_var.get() != COMMON_DEFAULT:
            self.content_var.set("单词")
            self.content_combo.configure(state=tk.DISABLED)
        else:
            self.content_combo.configure(state="readonly")
        self._update_preview()

    def _on_content_changed(self):
        # 内容在「单词 / 课文 / 表达句」间切换：单元重置到第一单元（Unit 1）并刷新预览
        units = get_units(self.version_var.get(), self.grade_var.get(), self.semester_var.get())
        self.unit_var.set(units[0])  # "Unit 1"
        self._update_preview()

    def _collect(self):
        style = self.style_var.get()
        # ── 常用词句模式：选中分类时，忽略 版本/年级/学期/单元，直接取分类词表 ──
        common_cat = self.common_var.get()
        if common_cat and common_cat != COMMON_DEFAULT:
            items = self.gen.get_common_words(common_cat)
            picked = self.gen.sample(items, 0)
            # 仅「出题（默写）」方式下才允许随机：打乱顺序 + 每题随机分配方向
            if (self.direction_var.get() == "随机出题"
                    and style.startswith("出题")):
                picked = [dict(it) for it in picked]  # 浅拷贝，避免污染源数据
                random.shuffle(picked)
                for it in picked:
                    it['_dir'] = random.choice(("汉译英", "英译汉"))
            # 常用词句均为单词；文件名以「常用」前缀，不带 年级/学期
            return "常用", "", "", "单词", style, common_cat, picked

        # ── 音标模式：与版本/年级/学期/单元无关，直接取国际音标表 ──
        if self.content_var.get() == "音标":
            return "音标", "", "", "音标", style, "音标", self.gen.get_phonetic_items()

        version = self.version_var.get()
        grade = self.grade_var.get()
        semester = self.semester_var.get()
        content = self.content_var.get()
        unit_name = self.unit_var.get()
        unit_index = get_units(self.version_var.get(), self.grade_var.get(),
                               self.semester_var.get()).index(unit_name) if unit_name else 0
        if content == "单词":
            pool = self.gen.get_unit_words(version, grade, semester, unit_index)
        elif content == "课文":
            pool = self.gen.get_unit_sentences(version, grade, semester, unit_index)
        else:  # 表达句
            pool = self.gen.get_unit_expressions(version, grade, semester, unit_index)
        # 默认导出该单元全部
        picked = self.gen.sample(pool, 0)
        # 仅「出题（默写）」方式下才允许随机：打乱顺序 + 每题随机分配方向（汉译英/英译汉混合出题）
        # 字帖（描红）方式保持单词/句子原有顺序不乱
        if (self.direction_var.get() == "随机出题"
                and style.startswith("出题")
                and content in ("单词", "课文", "表达句")):
            picked = [dict(it) for it in picked]  # 浅拷贝，避免污染源数据
            random.shuffle(picked)
            for it in picked:
                it['_dir'] = random.choice(("汉译英", "英译汉"))
        return version, grade, semester, content, style, unit_name, picked

    def _apply_preview_font(self):
        name = self.font_var.get()
        self.text.configure(font=(TK_FONT_MAP.get(name, "Microsoft YaHei"), 11))

    def on_generate(self):
        version, grade, semester, content, style, unit_name, picked = self._collect()
        if not picked:
            messagebox.showwarning("提示",
                f"「{version} · {grade}{semester} · {unit_name} · {content} · {style}」暂无数据！\n请在该版本对应的数据文件中补充单词 / 课文 / 表达句。")
            return
        self._update_preview()

    def on_clear(self):
        self.text.delete("1.0", tk.END)

    def on_export_pdf(self):
        if not self._last_items:
            self.on_generate()
            if not self._last_items:
                return
        version, grade, semester, content, style, unit_name, picked = self._last_items
        if not picked:
            messagebox.showwarning("提示", "没有可导出的内容，请先生成。")
            return
        ok, info = self.gen.export_pdf(content, style, version, grade, semester, picked,
                                       unit_name=unit_name, font=self.font_var.get(),
                                       direction=self.direction_var.get(),
                                       gray=self.gray_var.get())
        if ok:
            messagebox.showinfo("导出成功", f"已保存到项目目录：\n{info}")
        else:
            messagebox.showerror("导出失败", str(info))
