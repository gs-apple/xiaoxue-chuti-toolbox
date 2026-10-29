# zuowen_ui.py — 作文标签页
import datetime
import os
import tkinter as tk
from tkinter import ttk, messagebox
from constants import BASE_DIR
from zuowen.zuowen_core import ZuowenEngine, open_ai_web, get_ai_web_urls, export_worksheet
from zuowen.zuowen_data import GAOKAO, ZHONGKAO, XIAOSHENGCHU, MANFEN
from widgets import GradientButton

BG = "#f0f0f0"
FONT = ("Microsoft YaHei", 10)
FONT_BOLD = ("Microsoft YaHei", 10, "bold")
FONT_TITLE = ("Microsoft YaHei", 12, "bold")

MODES = ["课本作文", "中高考作文"]

# 「中高考作文」里的类型下拉。小升初/中考原本收的是甘肃平凉（庄浪、静宁）本地卷，
# 外地用不上，2026-10-29 已把那些题目和例文清空；但选项仍保留——
# 各地卷子不同，用户可以用「添加题目」自己往这两个类型里录本地题。
EXAM_TYPES = ["小升初", "中考作文", "高考作文", "满分原文"]


class ZuowenTabWidget:
    def __init__(self, parent):
        self.frame = tk.Frame(parent, bg=BG)
        self.engine = ZuowenEngine()
        self._current_data = None
        self._init_ui()

    def _init_ui(self):
        main = tk.Frame(self.frame, bg=BG)
        main.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # ========== 功能区 ==========
        func_group = ttk.LabelFrame(main, text="功能区")
        func_group.pack(side=tk.BOTTOM, fill=tk.X, pady=(6, 0))
        func_inner = tk.Frame(func_group, bg=BG)
        func_inner.pack(padx=5, pady=3)

        # 固定列宽，防止切换模式时按钮移位
        func_inner.columnconfigure(0, weight=1)
        func_inner.columnconfigure(1, minsize=100)
        func_inner.columnconfigure(2, minsize=100)
        func_inner.columnconfigure(3, minsize=100)
        func_inner.columnconfigure(4, minsize=100)
        func_inner.columnconfigure(5, weight=1)

        # 三个蓝色按钮，位置固定
        self.btn_export_pdf = GradientButton(func_inner, text="导出PDF", width=100, height=32,
                                             command=self._on_export_pdf)
        self.btn_save = GradientButton(func_inner, text="保存例文", width=100, height=32,
                                       command=self._on_save_example)
        self.btn_clear = GradientButton(func_inner, text="清空", width=100, height=32,
                                        command=self._on_clear)

        self.btn_export_pdf.grid(row=0, column=1, padx=3)
        self.btn_save.grid(row=0, column=2, padx=3)
        self.btn_clear.grid(row=0, column=3, padx=3)

        # 添加按钮，默认隐藏
        self.btn_add = GradientButton(func_inner, text="添加", width=100, height=32,
                                      color_top="#d97706", color_mid="#b45309", color_bot="#92400e",
                                      command=self._on_add_exam)
        self.btn_add.grid(row=0, column=4, padx=3)
        self.btn_add.grid_remove()

        # ========== 顶部：模式选择分组 + 搜索 ==========
        top_group = ttk.LabelFrame(main, text="作文模式")
        top_group.pack(fill=tk.X, pady=(0, 6))
        top_inner = tk.Frame(top_group, bg=BG)
        top_inner.pack(fill=tk.X, padx=6, pady=4)

        self.mode_var = tk.StringVar(value=MODES[0])
        for mode in MODES:
            tk.Radiobutton(top_inner, text=mode, variable=self.mode_var, value=mode,
                           font=FONT_BOLD, bg=BG, command=self._on_mode_changed
                           ).pack(side=tk.LEFT, padx=(0, 16))

        GradientButton(top_inner, text="AI写作", width=60, height=26,
                       color_top="#10b981", color_mid="#059669", color_bot="#047857",
                       hover_top="#34d399", hover_mid="#10b981", hover_bot="#059669",
                       command=self._on_ai_write).pack(side=tk.RIGHT)
        GradientButton(top_inner, text="搜索", width=60, height=26,
                       command=self._on_web_search).pack(side=tk.RIGHT, padx=(0, 4))
        self.search_var = tk.StringVar()
        tk.Entry(top_inner, textvariable=self.search_var, font=FONT,
                 width=25).pack(side=tk.RIGHT, padx=(0, 19), pady=2)

        # ========== 中部：上排(列表+信息) + 下排(例文全宽) ==========
        mid = tk.Frame(main, bg=BG)
        mid.pack(fill=tk.BOTH, expand=True)

        # --- 上排：左侧列表 + 右侧信息（关键：强制同高+消除间距）---
        top_row = tk.Frame(mid, bg=BG)
        top_row.pack(fill=tk.X, padx=0, pady=0)
        top_row.columnconfigure(0, minsize=276, weight=0)
        top_row.columnconfigure(1, weight=1)

        # 左侧：题目选择分组栏（1号点）
        # 左侧：题目选择分组栏（带滚动条，固定显示9行）
        left_group = ttk.LabelFrame(top_row, text="题目选择")
        left_group.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=0)
        left_group.pack_propagate(False)
        # 调高容器高度，适配9行题目（和右侧作文信息框高度保持一致）
        left_group.config(height=230)

        filter_row = tk.Frame(left_group, bg=BG)
        filter_row.pack(fill=tk.X, padx=6, pady=(4, 2))
        self.grade_label = tk.Label(filter_row, text="年级:", font=FONT, bg=BG)
        self.grade_label.pack(side=tk.LEFT)
        grades = self.engine.get_grades()
        self.grade_var = tk.StringVar(value="四年级")
        self.grade_combo = ttk.Combobox(filter_row, textvariable=self.grade_var,
                                        values=grades, state="readonly", width=8, font=FONT)
        self.grade_combo.pack(side=tk.LEFT, padx=(4, 0))
        self.grade_combo.bind("<<ComboboxSelected>>", lambda e: self._on_grade_changed())

        self.sem_label = tk.Label(filter_row, text="学期:", font=FONT, bg=BG)
        self.sem_label.pack(side=tk.LEFT, padx=(8, 0))
        self.sem_var = tk.StringVar(value="下学期")
        self.sem_combo = ttk.Combobox(filter_row, textvariable=self.sem_var,
                                      values=["上学期", "下学期"], state="readonly", width=6, font=FONT)
        self.sem_combo.pack(side=tk.LEFT, padx=(4, 0))
        self.sem_combo.bind("<<ComboboxSelected>>", lambda e: self._on_filter_changed())

        # 保存原始值
        self._original_grades = grades
        self._original_semesters = ["上学期", "下学期"]
        # 中高考作文的年份列表（按实际有数据的年份生成，含 2001 满分作文）
        self._custom_years = [str(y) for y in range(2000, 2027)]

        self.filter_label = tk.Label(filter_row, text="", font=FONT, bg=BG, fg="#2563eb")
        self.filter_label.pack(side=tk.LEFT, padx=(10, 0))

        # 带滚动条的列表框，固定显示9行
        list_frame = tk.Frame(left_group, bg="white", relief=tk.SUNKEN, bd=1)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 4))

        list_scroll = tk.Scrollbar(list_frame)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.item_list = tk.Listbox(
            list_frame,
            font=FONT,
            height=9,  # 关键：固定显示9个题目，超出自动滚动
            yscrollcommand=list_scroll.set,
            activestyle="dotbox",
            selectbackground="#2563eb",
            selectforeground="white"
        )
        self.item_list.pack(fill=tk.BOTH, expand=True)
        list_scroll.config(command=self.item_list.yview)
        self.item_list.bind("<<ListboxSelect>>", lambda e: self._on_item_selected())

        # 右侧：作文信息分组栏（2号点，和左侧完全同高）
        right_group = ttk.LabelFrame(top_row, text="作文信息")
        right_group.grid(row=0, column=1, sticky="nsew", pady=0)
        right_group.pack_propagate(False)
        right_group.config(height=200)  # 和左侧left_group高度完全一致

        right = tk.Frame(right_group, bg=BG)
        right.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        self.detail_title = tk.Label(right, text="请从左侧选择", font=FONT_TITLE, bg=BG,
                                     anchor="w", wraplength=300)
        self.detail_title.pack(fill=tk.X, pady=(0, 0))

        self.detail_meta = tk.Label(right, text="", font=FONT, bg=BG, fg="#2563eb")
        self.detail_meta.pack(anchor="w", pady=(0, 2))

        req_frame = tk.Frame(right, bg="white", relief=tk.SUNKEN, bd=1)
        req_frame.pack(fill=tk.BOTH, expand=True)
        req_scroll = tk.Scrollbar(req_frame)
        req_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.req_text = tk.Text(req_frame, bg="white", font=FONT, wrap=tk.WORD,
                                height=7, state="disabled",
                                yscrollcommand=req_scroll.set)  # 和左侧item_list高度完全一致
        self.req_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        req_scroll.config(command=self.req_text.yview)

        # --- 下排：例文内容（3号点，彻底消除和上排的缝隙）---
        content_group = ttk.LabelFrame(mid, text="例文内容")
        content_group.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 0))  # pady从(2,0)改成(0,0)，彻底贴紧

        content_inner = tk.Frame(content_group, bg="white")
        content_inner.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)
        content_scroll = tk.Scrollbar(content_inner)
        content_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.content_text = tk.Text(content_inner, bg="white", font=FONT, wrap=tk.WORD,
                                    yscrollcommand=content_scroll.set)
        self.content_text.pack(fill=tk.BOTH, expand=True)
        content_scroll.config(command=self.content_text.yview)

        # 初始化
        self._on_mode_changed()

    # ============================================================
    # 模式切换
    # ============================================================
    def _on_mode_changed(self):
        mode = self.mode_var.get()
        self._current_data = None
        self.item_list.delete(0, tk.END)
        self._clear_detail()

        if mode == "课本作文":
            # 恢复原始下拉选项
            self.grade_label.config(text="年级:")
            self.grade_combo.config(values=self._original_grades, state="readonly")
            self.grade_var.set("四年级")
            self.sem_label.config(text="学期:")
            self.sem_combo.config(values=self._original_semesters, state="readonly")
            self.sem_var.set("下学期")
            self.filter_label.config(text="")
            self.btn_add.grid_remove()  # 隐藏
            self._load_textbook()
        elif mode == "中高考作文":
            # 小升初/中考的本地卷已清空，默认落在第一个真正有题目的类型上
            # （现在就是高考作文），免得一进页面就是空列表
            self.grade_label.config(text="类型:")
            self.grade_combo.config(
                values=EXAM_TYPES,
                state="readonly")
            default_type = next(
                (t for t in EXAM_TYPES if self._years_of(t)), EXAM_TYPES[0])
            self.grade_var.set(default_type)
            self.sem_label.config(text="年份:")
            self._refresh_years(default_type)
            self.filter_label.config(text="")
            self.btn_add.grid()  # 显示
            self._load_custom()

    def _years_of(self, exam_type):
        """按类型返回实际有数据的年份（倒序）。没有数据的年份不再列出。"""
        if exam_type == "小升初":
            data = XIAOSHENGCHU
        elif exam_type == "中考作文":
            data = ZHONGKAO
        elif exam_type == "满分原文":
            data = MANFEN
        else:
            data = GAOKAO
        ys = [y for y, v in data.items() if v]
        return sorted(ys, key=lambda x: int(x), reverse=True)

    def _refresh_years(self, exam_type):
        """切换类型时刷新「年份」下拉。"""
        years = self._years_of(exam_type)
        self.sem_combo.config(values=years, state="readonly")
        if years:
            if self.sem_var.get() not in years:
                self.sem_var.set(years[0])
        else:
            # 这个类型还没有任何题目（如刚清空的小升初/中考）：
            # 年份留上一个类型的值会让「添加题目」预填错年份，直接落到今年
            self.sem_var.set(str(datetime.date.today().year))

    def _on_grade_changed(self):
        mode = self.mode_var.get()
        if mode == "课本作文":
            self._load_textbook()
        elif mode == "中高考作文":
            self._refresh_years(self.grade_var.get())
            self._load_custom()

    def _on_filter_changed(self):
        mode = self.mode_var.get()
        if mode == "课本作文":
            self._load_textbook()
        elif mode == "中高考作文":
            self._load_custom()

    # ============================================================
    # 课本作文
    # ============================================================
    def _load_textbook(self):
        grade = self.grade_var.get()
        semester = self.sem_var.get()
        units = self.engine.get_units(grade, semester)
        self._cache = []
        self.item_list.delete(0, tk.END)

        for u in units:
            self._cache.append({"_type": "textbook", **u})
            self.item_list.insert(tk.END, u["title"])

        # 默认选中第一个题目
        if self._cache:
            self.item_list.selection_set(0)
            self._on_item_selected()

    # ============================================================
    # 中高考作文
    # ============================================================
    def _load_custom(self):
        exam_type = self.grade_var.get()
        year = int(self.sem_var.get()) if self.sem_var.get().isdigit() else 2026
        topics = self.engine.get_exam_topics(exam_type, year)
        self._cache = [{"_type": "exam", **t} for t in topics]
        self.item_list.delete(0, tk.END)
        for t in topics:
            label = t["title"]
            if t.get("paper"):
                # 标题本身已带括号，再用（）包一层会出现「（二选一）（平凉卷）」的嵌套
                label += f" · {t['paper']}"
            self.item_list.insert(tk.END, label)
        # 默认选中第一个
        if self._cache:
            self.filter_label.config(fg="#2563eb", text="")
            self.item_list.selection_set(0)
            self._on_item_selected()
        else:
            # 小升初/中考等类型清空后是空的，提示一句可以自己录入，
            # 否则空列表看着像软件出问题
            if not self._years_of(exam_type):
                self.filter_label.config(
                    fg="#d97706",
                    text=f"「{exam_type}」暂无题目，可点下方「添加题目」录入本地卷")
            else:
                self.filter_label.config(fg="#2563eb", text="")
            self._clear_detail()

    # ============================================================
    # 列表选中
    # ============================================================
    def _on_item_selected(self):
        sel = self.item_list.curselection()
        if not sel or not hasattr(self, '_cache'):
            return
        idx = sel[0]
        if idx >= len(self._cache):
            return
        item = self._cache[idx]
        mode = self.mode_var.get()

        if mode == "课本作文":
            self._show_textbook_detail(item)
        elif mode == "中高考作文":
            self._show_exam_detail(item)

    # 各年级字数要求
    _WORD_COUNT = {
        "一年级": "50-80字", "二年级": "100-150字", "三年级": "200-250字",
        "四年级": "250-300字", "五年级": "350-400字", "六年级": "400-500字",
    }

    def _show_textbook_detail(self, item):
        grade = self.grade_var.get()
        self.search_var.set(item["title"])
        self.detail_title.config(text=item["title"])
        self.detail_meta.config(text=f"年级: {grade}　类型: {item['type']}")
        # 要求 + 字数 + 写作思路
        wc = self._WORD_COUNT.get(grade, "")
        req = item["requires"]
        # 应用文、口语交际不能按年级作文区间要求：留言条写清事由即可，
        # 口语交际本来就不成篇，标成「100-150字」会让孩子以为自己写少了
        note = item.get("wc_note", "")
        if not note and item.get("type") == "口语交际":
            note = "口语交际不写成篇作文，能大大方方说清楚就行"
        if note:
            req = f"{req}\n字数说明：{note}"
        elif wc:
            req = f"{req}\n字数要求：{wc}"
        # 添加写作思路
        tip = item.get("tip", "")
        if tip:
            req = f"{req}\n\n写作思路：\n{tip}"
        self.req_text.config(state="normal")
        self.req_text.delete("1.0", tk.END)
        self.req_text.insert("1.0", req)
        self.req_text.config(state="disabled")
        # 例文 + 写作提示
        example = self.engine.get_example_essay(item["title"], grade, self.sem_var.get())
        self.content_text.delete("1.0", tk.END)
        if example:
            self.content_text.insert("1.0", example.get("content", ""))
            self._current_data = {"title": item["title"], "grade": grade, **example}
        else:
            self.content_text.insert("1.0", "（暂无例文）")
            self._current_data = {"title": item["title"], "grade": grade,
                                  "type": item["type"], "requires": item["requires"],
                                  "tip": tip}

    def _show_exam_detail(self, item):
        """显示中考/高考作文详情"""
        exam_type = self.grade_var.get()
        year = self.sem_var.get()
        self.search_var.set(item["title"])
        self.detail_title.config(text=item["title"])
        # 「满分原文」不是考试类型，单独叫「历年满分原文」，避免写成「满分原文 2001年」
        label = "历年满分原文" if exam_type == "满分原文" else exam_type
        meta = f"{label} {year}年"
        if item.get("paper"):
            meta += f" · {item['paper']}"
        kind = item.get("essay_kind")
        if kind == "考场满分原文":
            meta += "　【考场满分原文】"
        elif kind:
            meta += f"　【{kind}·非考场原文】"
        self.detail_meta.config(text=meta)
        self.req_text.config(state="normal")
        self.req_text.delete("1.0", tk.END)
        body = item.get("requires", "")
        if item.get("essay_note"):
            body += "\n\n【例文性质】" + item["essay_note"].strip()
        self.req_text.insert("1.0", body)
        self.req_text.config(state="disabled")
        self.content_text.delete("1.0", tk.END)
        # 加载例文（如果存在）
        example = self.engine.get_example_essay(item["title"])
        if example and example.get("content"):
            self.content_text.insert("1.0", example["content"])
            self._current_data = {"title": item["title"], "grade": exam_type,
                                  "type": item.get("paper", ""),
                                  "requires": item.get("requires", ""),
                                  "content": example["content"]}
        else:
            self.content_text.insert("1.0", "（暂无例文，可使用AI写作生成）")
            self._current_data = {"title": item["title"], "grade": exam_type,
                                  "type": item.get("paper", ""),
                                  "requires": item.get("requires", "")}

    def _clear_detail(self):
        self.detail_title.config(text="请从左侧选择")
        self.detail_meta.config(text="")
        self.req_text.config(state="normal")
        self.req_text.delete("1.0", tk.END)
        self.req_text.config(state="disabled")
        self.content_text.delete("1.0", tk.END)
        self._current_data = None

    # ============================================================
    # 功能区操作
    # ============================================================
    def _on_save_example(self):
        """保存修改后的例文"""
        if not self._current_data:
            messagebox.showinfo("提示", "请先选择一个作文题目")
            return

        title = self._current_data.get("title", "")
        if not title:
            messagebox.showinfo("提示", "无法确定作文题目")
            return

        # 获取修改后的内容
        new_content = self.content_text.get("1.0", tk.END).strip()
        if not new_content or new_content == "（暂无例文）":
            messagebox.showinfo("提示", "没有可保存的内容")
            return

        # 确认保存
        if not messagebox.askyesno("确认保存", f"确定要保存对《{title}》例文的修改吗？"):
            return

        # 保存到数据文件
        try:
            self._save_to_data_file(title, new_content)
            messagebox.showinfo("保存成功", f"《{title}》的例文已更新")
        except Exception as e:
            messagebox.showerror("保存失败", f"保存时出错：{e}")

    def _save_to_data_file(self, title, new_content):
        """将修改后的例文保存到 zuowen_data.json（原子写入）"""
        import json
        import os
        import tempfile

        data_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "zuowen_data.json")

        # 1. 读取现有数据（文件不存在则初始化空字典）
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            data = {}
        except json.JSONDecodeError:
            raise Exception("zuowen_data.json 格式损坏，请手动修复")

        # 2. 字段合法性校验
        if "EXAMPLE_ESSAYS" not in data:
            data["EXAMPLE_ESSAYS"] = {}
        essays = data["EXAMPLE_ESSAYS"]
        # 不存在则自动创建
        if title not in essays:
            essays[title] = {"content": "", "word_count": ""}
        if not isinstance(new_content, str):
            raise Exception("例文内容必须是字符串")

        # 3. 更新数据
        essays[title]["content"] = new_content
        data["EXAMPLE_ESSAYS"] = essays

        # 4. 原子写入：先写临时文件，成功后替换原文件
        dir_name = os.path.dirname(data_file)
        fd, tmp_path = tempfile.mkstemp(suffix=".tmp", dir=dir_name)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, data_file)  # 原子替换
        except Exception:
            # 写入失败，清理临时文件
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

        # 5. 同步更新内存中的数据
        from zuowen.zuowen_data import EXAMPLE_ESSAYS
        if title not in EXAMPLE_ESSAYS:
            EXAMPLE_ESSAYS[title] = {"content": "", "word_count": ""}
        EXAMPLE_ESSAYS[title]["content"] = new_content

    def _on_add_exam(self):
        """弹窗录入中高考作文题目，确认后保存到 zuowen_data.json"""
        import json
        import os
        import tempfile

        # 预填当前选择
        exam_type = self.grade_var.get()
        year = self.sem_var.get()

        # 弹窗
        dialog = tk.Toplevel(self.frame)
        dialog.title("添加中高考作文题目")
        dialog.geometry("420x380")
        dialog.resizable(False, False)
        dialog.transient(self.frame)
        dialog.grab_set()
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 420) // 2
        y = (dialog.winfo_screenheight() - 380) // 2
        dialog.geometry(f"420x380+{x}+{y}")

        # 类型 + 年份
        row0 = tk.Frame(dialog, bg=BG)
        row0.pack(fill=tk.X, padx=15, pady=(15, 5))
        tk.Label(row0, text="类型:", font=FONT, bg=BG).pack(side=tk.LEFT)
        type_var = tk.StringVar(value=exam_type)
        ttk.Combobox(row0, textvariable=type_var, values=EXAM_TYPES,
                     state="readonly", width=10, font=FONT).pack(side=tk.LEFT, padx=(4, 15))
        tk.Label(row0, text="年份:", font=FONT, bg=BG).pack(side=tk.LEFT)
        year_var = tk.StringVar(value=year)
        ttk.Combobox(row0, textvariable=year_var,
                     values=[str(y) for y in range(2000, 2027)],
                     state="readonly", width=6, font=FONT).pack(side=tk.LEFT, padx=4)

        # 试卷名称（高考用）
        row1 = tk.Frame(dialog, bg=BG)
        row1.pack(fill=tk.X, padx=15, pady=5)
        tk.Label(row1, text="试卷:", font=FONT, bg=BG).pack(side=tk.LEFT)
        paper_var = tk.StringVar(value="")
        tk.Entry(row1, textvariable=paper_var, font=FONT, width=30).pack(side=tk.LEFT, padx=4, fill=tk.X, expand=True)

        # 标题
        row2 = tk.Frame(dialog, bg=BG)
        row2.pack(fill=tk.X, padx=15, pady=5)
        tk.Label(row2, text="标题:", font=FONT, bg=BG).pack(side=tk.LEFT)
        title_var = tk.StringVar(value="")
        tk.Entry(row2, textvariable=title_var, font=FONT, width=30).pack(side=tk.LEFT, padx=4, fill=tk.X, expand=True)

        # 作文要求
        tk.Label(dialog, text="作文要求:", font=FONT, bg=BG, anchor="w").pack(fill=tk.X, padx=15, pady=(5, 0))
        req_frame = tk.Frame(dialog, bg="white", relief=tk.SUNKEN, bd=1)
        req_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 5))
        req_text = tk.Text(req_frame, bg="white", font=FONT, wrap=tk.WORD, height=6)
        req_text.pack(fill=tk.BOTH, expand=True)

        def on_confirm():
            title = title_var.get().strip()
            requires = req_text.get("1.0", "end-1c").strip()
            paper = paper_var.get().strip()
            etype = type_var.get()
            yr = year_var.get()

            if not title:
                messagebox.showinfo("提示", "标题不能为空", parent=dialog)
                return
            if not requires:
                messagebox.showinfo("提示", "作文要求不能为空", parent=dialog)
                return

            json_key = {"小升初": "XIAOSHENGCHU", "中考作文": "ZHONGKAO",
                        "高考作文": "GAOKAO", "满分原文": "MANFEN"}[etype]
            new_topic = {"title": title, "requires": requires}
            if paper:
                new_topic["paper"] = paper

            # 读取 JSON
            data_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "zuowen_data.json")
            try:
                with open(data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except FileNotFoundError:
                data = {}
            except json.JSONDecodeError:
                messagebox.showerror("错误", "zuowen_data.json 格式损坏", parent=dialog)
                return

            if json_key not in data:
                data[json_key] = {}
            if yr not in data[json_key]:
                data[json_key][yr] = []

            # 检查重复，二次确认
            for t in data[json_key][yr]:
                if t.get("title") == title:
                    if not messagebox.askyesno("题目已存在", f"《{title}》已存在于 {etype} {yr}年，确定要重复添加吗？", parent=dialog):
                        return
                    break

            data[json_key][yr].append(new_topic)

            # 同时在 EXAMPLE_ESSAYS 中创建空例文条目
            if "EXAMPLE_ESSAYS" not in data:
                data["EXAMPLE_ESSAYS"] = {}
            if title not in data["EXAMPLE_ESSAYS"]:
                data["EXAMPLE_ESSAYS"][title] = {"content": "", "word_count": ""}

            # 原子写入
            fd, tmp_path = tempfile.mkstemp(suffix=".tmp", dir=os.path.dirname(data_file))
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                os.replace(tmp_path, data_file)
            except Exception:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                messagebox.showerror("错误", "保存失败", parent=dialog)
                return

            # 同步内存（满分原文原先漏在映射外，选它会 KeyError）
            from zuowen import zuowen_data as zd
            target = {"XIAOSHENGCHU": zd.XIAOSHENGCHU, "ZHONGKAO": zd.ZHONGKAO,
                      "GAOKAO": zd.GAOKAO, "MANFEN": zd.MANFEN}[json_key]
            if yr not in target:
                target[yr] = []
            target[yr].append(new_topic)
            # 同步例文内存
            if title not in zd.EXAMPLE_ESSAYS:
                zd.EXAMPLE_ESSAYS[title] = {"content": "", "word_count": ""}

            messagebox.showinfo("添加成功", f"《{title}》已保存到 {etype} {yr}年", parent=dialog)
            dialog.destroy()
            # 刷新题目列表：先把类型/年份对齐到刚添加的那条，
            # 否则在「小升初」这类空类型里添加完仍看不到自己的题
            self.grade_var.set(etype)
            self._refresh_years(etype)
            self.sem_var.set(yr)
            self._load_custom()

        # 按钮
        btn_frame = tk.Frame(dialog, bg=BG)
        btn_frame.pack(pady=(0, 15))
        tk.Button(btn_frame, text="确定添加", font=FONT_BOLD, width=10,
                  command=on_confirm).pack(side=tk.LEFT, padx=6)
        tk.Button(btn_frame, text="取消", font=FONT, width=8,
                  command=dialog.destroy).pack(side=tk.LEFT, padx=6)

    def _on_web_search(self):
        """用浏览器搜索搜索框中的关键词"""
        import webbrowser
        keyword = self.search_var.get().strip()
        if not keyword:
            # 如果搜索框为空，用当前选中题目
            keyword = self.detail_title.cget("text")
            if not keyword or keyword == "请从左侧选择":
                messagebox.showinfo("提示", "请输入搜索关键词或选择一个作文题目")
                return
        url = f"https://www.baidu.com/s?wd={keyword} 作文 范文"
        webbrowser.open(url)

    def _on_ai_write(self):
        """AI写作 — 打开网页版AI或调用自定义API"""

        topic = self.search_var.get().strip()
        if not topic:
            topic = self.detail_title.cget("text")
            if not topic or topic == "请从左侧选择":
                messagebox.showinfo("提示", "请先输入作文题目或选择一个题目")
                return

        # 弹出选择对话框
        dialog = tk.Toplevel(self.frame)
        dialog.title("AI写作 — 选择平台")
        dialog.geometry("380x420")
        dialog.resizable(False, False)
        dialog.transient(self.frame)
        dialog.grab_set()

        # 居中显示
        dialog.update_idletasks()
        sw = dialog.winfo_screenwidth()
        sh = dialog.winfo_screenheight()
        x = (sw - 380) // 2
        y = (sh - 420) // 2
        dialog.geometry(f"380x420+{x}+{y}")

        tk.Label(dialog, text=f"题目：{topic}", font=FONT_BOLD, wraplength=340).pack(pady=(15, 5))

        # === 网页版选项 ===
        tk.Label(dialog, text="网页版（免费，推荐）:", font=FONT_BOLD, fg="#2563eb").pack(anchor="w", padx=30)

        service_var = tk.StringVar(value="豆包")
        services = list(get_ai_web_urls().keys())
        grid_frame = tk.Frame(dialog, bg=BG)
        grid_frame.pack(fill=tk.X, padx=30, pady=2)
        for i, s in enumerate(services):
            row, col = divmod(i, 3)
            tk.Radiobutton(grid_frame, text=s, variable=service_var, value=s,
                           font=FONT, bg=BG).grid(row=row, column=col, sticky="w", padx=(0, 10), pady=1)

        # === 分隔线 ===
        sep = tk.Frame(dialog, height=1, bg="#ccc")
        sep.pack(fill=tk.X, padx=30, pady=10)

        # === 自定义API选项 ===
        tk.Label(dialog, text="自定义API（需要API密钥）:", font=FONT_BOLD, fg="#059669").pack(anchor="w", padx=30)

        api_frame = tk.Frame(dialog, bg=BG)
        api_frame.pack(fill=tk.X, padx=30, pady=(5, 0))

        # 平台预设
        _API_PLATFORMS = {
            "DeepSeek": {"url": "https://api.deepseek.com/chat/completions", "model": "deepseek-chat"},
            "智谱AI": {"url": "https://open.bigmodel.cn/api/paas/v4/chat/completions", "model": "glm-4-flash"},
            "通义千问": {"url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions", "model": "qwen-turbo"},
            "豆包": {"url": "https://ark.cn-beijing.volces.com/api/v3/chat/completions", "model": "doubao-1-5-lite-32k"},
            "Kimi": {"url": "https://api.moonshot.cn/v1/chat/completions", "model": "moonshot-v1-8k"},
            "OpenAI": {"url": "https://api.openai.com/v1/chat/completions", "model": "gpt-3.5-turbo"},
            "自定义": {"url": "", "model": ""},
        }

        tk.Label(api_frame, text="平台:", font=FONT, bg=BG).grid(row=0, column=0, sticky="e", pady=2)
        platform_var = tk.StringVar(value="DeepSeek")
        platform_combo = ttk.Combobox(api_frame, textvariable=platform_var,
                                      values=list(_API_PLATFORMS.keys()),
                                      state="readonly", width=12, font=FONT)
        platform_combo.grid(row=0, column=1, sticky="w", pady=2, padx=(4, 0))

        # API地址 + 复制按钮
        tk.Label(api_frame, text="API地址:", font=FONT, bg=BG).grid(row=1, column=0, sticky="e", pady=2)
        api_url_var = tk.StringVar(value=_API_PLATFORMS["DeepSeek"]["url"])
        tk.Entry(api_frame, textvariable=api_url_var, font=FONT, width=25).grid(row=1, column=1, sticky="w", pady=2, padx=(4, 0))

        def copy_url():
            dialog.clipboard_clear()
            dialog.clipboard_append(api_url_var.get())
            copy_btn.config(text="已复制")
            dialog.after(1500, lambda: copy_btn.config(text="复制"))

        copy_btn = tk.Button(api_frame, text="复制", font=("Microsoft YaHei", 8),
                             command=copy_url, width=5, bd=1)
        copy_btn.grid(row=1, column=2, sticky="w", padx=(1, 0))

        # API密钥
        tk.Label(api_frame, text="API密钥:", font=FONT, bg=BG).grid(row=2, column=0, sticky="e", pady=2)
        api_key_var = tk.StringVar()
        key_entry = tk.Entry(api_frame, textvariable=api_key_var, font=FONT, width=25, show="*")
        key_entry.grid(row=2, column=1, sticky="w", pady=2, padx=(4, 0))

        def toggle_key():
            if key_entry.cget("show") == "*":
                key_entry.config(show="")
                toggle_btn.config(text="隐藏")
            else:
                key_entry.config(show="*")
                toggle_btn.config(text="显示")

        toggle_btn = tk.Button(api_frame, text="显示", font=("Microsoft YaHei", 8),
                               command=toggle_key, width=5, bd=1)
        toggle_btn.grid(row=2, column=2, sticky="w", padx=(1, 0))

        # 模型
        tk.Label(api_frame, text="模型:", font=FONT, bg=BG).grid(row=3, column=0, sticky="e", pady=2)
        api_model_var = tk.StringVar(value=_API_PLATFORMS["DeepSeek"]["model"])
        models = ["deepseek-chat", "gpt-3.5-turbo", "gpt-4o-mini", "glm-4-flash",
                  "qwen-turbo", "doubao-1-5-lite-32k", "moonshot-v1-8k"]
        ttk.Combobox(api_frame, textvariable=api_model_var, values=models,
                     state="readonly", width=23, font=FONT).grid(row=3, column=1, sticky="w", pady=2, padx=(4, 0))

        # 平台切换时自动填充地址和模型
        def on_platform_change(*_):
            p = platform_var.get()
            cfg = _API_PLATFORMS.get(p, {})
            api_url_var.set(cfg.get("url", ""))
            api_model_var.set(cfg.get("model", ""))

        platform_combo.bind("<<ComboboxSelected>>", on_platform_change)

        # 按钮
        def on_web():
            service = service_var.get()
            dialog.destroy()
            # 获取写作思路
            tip = self._current_data.get("tip", "") if self._current_data else ""
            grade = self._current_data.get("grade", "") if self._current_data else ""
            success, msg = open_ai_web(topic, service, tip=tip, grade=grade)
            if success:
                self.content_text.delete("1.0", tk.END)
                self.content_text.insert("1.0", f"已打开{service}，提示词已复制到剪贴板。\n\n在AI对话框中粘贴（Ctrl+V）即可生成作文。\n生成后复制作文内容，粘贴到此处。")
            else:
                messagebox.showerror("错误", msg)

        def on_api():
            url = api_url_var.get().strip()
            key = api_key_var.get().strip()
            model = api_model_var.get().strip()
            if not url or not key:
                messagebox.showwarning("提示", "请填写API地址和密钥", parent=dialog)
                return
            dialog.destroy()
            self._call_ai_api(topic, url, key, model)

        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=15)
        tk.Button(btn_frame, text="打开网页版", font=FONT_BOLD, width=12,
                  command=on_web).pack(side=tk.LEFT, padx=6)
        tk.Button(btn_frame, text="调用API", font=FONT_BOLD, width=10,
                  command=on_api).pack(side=tk.LEFT, padx=6)
        tk.Button(btn_frame, text="取消", font=FONT, width=8,
                  command=dialog.destroy).pack(side=tk.LEFT, padx=6)

    def _call_ai_api(self, topic, api_url, api_key, model):
        """调用自定义API生成作文"""
        import threading
        import requests
        from urllib.parse import urlparse

        # 安全校验：仅允许 http/https，禁止 file://、ftp:// 等非常规协议
        parsed = urlparse(api_url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            self.content_text.delete("1.0", tk.END)
            self.content_text.insert(
                "1.0",
                f"AI生成失败：API 地址不合法（仅支持 http/https）：{api_url}"
            )
            return
        if parsed.scheme == "http":
            # 明文 http 会把 API 密钥以明文发送，存在窃听风险
            self.content_text.delete("1.0", tk.END)
            self.content_text.insert(
                "1.0",
                "警告：当前使用 http 明文传输，API 密钥可能被窃听，建议改用 https。\n正在继续请求……"
            )
            self.content_text.update()

        self.content_text.delete("1.0", tk.END)
        self.content_text.insert("1.0", "正在调用AI生成作文，请稍候...")
        self.content_text.update()

        def _do():
            try:
                prompt = f'请以"{topic}"为题，写一篇适合小学生的优秀作文范文。要求：语言通顺，用词恰当，内容真实感人，有具体事例，结构清晰，字数300-500字。直接输出作文内容，不要加标题和额外说明。'

                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                }
                data = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "你是一位优秀的小学语文老师，擅长写范文。"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 1000
                }

                resp = requests.post(api_url, headers=headers, json=data, timeout=30)
                resp.raise_for_status()
                result = resp.json()
                content = result["choices"][0]["message"]["content"].strip()
                self.frame.after(0, lambda: self._show_ai_result(content))
            except Exception as e:
                self.frame.after(0, lambda: self._show_ai_error(str(e)))

        threading.Thread(target=_do, daemon=True).start()

    def _show_ai_result(self, content):
        self.content_text.delete("1.0", tk.END)
        self.content_text.insert("1.0", content)

    def _show_ai_error(self, error):
        self.content_text.delete("1.0", tk.END)
        self.content_text.insert("1.0", f"AI生成失败：{error}")

    def _on_export_pdf(self):
        if not self._current_data:
            messagebox.showinfo("提示", "请先选择作文内容")
            return

        data = self._current_data
        mode = self.mode_var.get()

        if mode == "课本作文":
            title = data.get("title", "作文")
            grade = data.get("grade", "")
            content = self.content_text.get("1.0", "end-1c").strip()
            filepath = os.path.join(BASE_DIR, f"{title}.pdf")
            try:
                export_worksheet(title, content, grade, data.get("type", ""),
                                 filepath=filepath)
                messagebox.showinfo("成功", f"已导出:\n{filepath}")
            except Exception as e:
                messagebox.showerror("错误", f"导出失败: {e}")

        elif mode == "中高考作文":
            title = data.get("title", "中高考作文")
            content = self.content_text.get("1.0", "end-1c").strip()
            requirements = self.req_text.get("1.0", "end-1c").strip()
            filepath = os.path.join(BASE_DIR, f"{title}.pdf")
            try:
                export_worksheet(title, content, data.get("grade", ""),
                                 data.get("comp_type", ""), filepath=filepath)
                messagebox.showinfo("成功", f"已导出:\n{filepath}")
            except Exception as e:
                messagebox.showerror("错误", f"导出失败: {e}")

    def _on_clear(self):
        self._clear_detail()
        self.search_var.set("")
        self.filter_label.config(text="")
        self._refresh_list()
