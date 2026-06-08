# zuowen_ui.py — 作文标签页
import os
import tkinter as tk
from tkinter import ttk, messagebox
from zuowen_core import ZuowenEngine, open_ai_web, get_ai_web_urls, export_worksheet
from widgets import GradientButton

# 软件目录
_APP_DIR = os.path.dirname(os.path.abspath(__file__))

BG = "#f0f0f0"
FONT = ("Microsoft YaHei", 10)
FONT_BOLD = ("Microsoft YaHei", 10, "bold")
FONT_TITLE = ("Microsoft YaHei", 12, "bold")

MODES = ["课本作文", "中高考作文"]


class ZuowenTabWidget:
    def __init__(self, parent):
        self.frame = tk.Frame(parent, bg=BG)
        self.engine = ZuowenEngine()
        self._current_data = None
        self._init_ui()

    def _init_ui(self):
        main = tk.Frame(self.frame, bg=BG)
        main.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # ========== 功能区（先 pack 到底部，确保始终可见）==========
        func_group = ttk.LabelFrame(main, text="功能区")
        func_group.pack(side=tk.BOTTOM, fill=tk.X, pady=(6, 0))
        func_inner = tk.Frame(func_group, bg=BG)
        func_inner.pack(padx=5, pady=3)

        self.btn_export_pdf = GradientButton(func_inner, text="导出PDF", width=100, height=32,
                                             command=self._on_export_pdf)
        self.btn_save = GradientButton(func_inner, text="保存例文", width=100, height=32,
                                       command=self._on_save_example)
        self.btn_clear = GradientButton(func_inner, text="清空", width=100, height=32,
                                        command=self._on_clear)

        func_inner.columnconfigure(0, weight=1)
        func_inner.columnconfigure(4, weight=1)
        self.btn_export_pdf.grid(row=0, column=1, padx=3)
        self.btn_save.grid(row=0, column=2, padx=3)
        self.btn_clear.grid(row=0, column=3, padx=3)

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
        # 中高考作文的年份列表
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
        self.req_text = tk.Text(req_frame, bg="white", font=FONT, wrap=tk.WORD,
                                height=7, state="disabled")  # 和左侧item_list高度完全一致
        self.req_text.pack(fill=tk.BOTH, expand=True)

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
            self._load_textbook()
        elif mode == "中高考作文":
            # 切换为中考/高考 + 年份
            self.grade_label.config(text="类型:")
            self.grade_combo.config(values=["中考作文", "高考作文"], state="readonly")
            self.grade_var.set("中考作文")
            self.sem_label.config(text="年份:")
            years = [str(y) for y in self.engine.get_exam_years()]
            self.sem_combo.config(values=years, state="readonly")
            self.sem_var.set("2026")
            self.filter_label.config(text="")
            self._load_custom()

    def _on_grade_changed(self):
        mode = self.mode_var.get()
        if mode == "课本作文":
            self._load_textbook()
        elif mode == "中高考作文":
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
                label += f"（{t['paper']}）"
            self.item_list.insert(tk.END, label)
        # 默认选中第一个
        if self._cache:
            self.item_list.selection_set(0)
            self._on_item_selected()
        else:
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
        if wc:
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
        example = self.engine.get_example_essay(item["title"])
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
        meta = f"{exam_type} {year}年"
        if item.get("paper"):
            meta += f" {item['paper']}"
        self.detail_meta.config(text=meta)
        self.req_text.config(state="normal")
        self.req_text.delete("1.0", tk.END)
        self.req_text.insert("1.0", item.get("requires", ""))
        self.req_text.config(state="disabled")
        self.content_text.delete("1.0", tk.END)
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
        """将修改后的内容保存到 zuowen_data.py"""
        import os
        data_file = os.path.join(os.path.dirname(__file__), "zuowen_data.py")

        # 读取现有文件内容
        with open(data_file, 'r', encoding='utf-8') as f:
            file_content = f.read()

        # 查找并替换例文内容
        # 使用正则表达式匹配 EXAMPLE_ESSAYS 中对应标题的 content 字段
        import re

        # 构建匹配模式：找到标题对应的条目，然后替换 content 字段
        # 匹配 "标题": {..., "content": "...", ...}
        pattern = r'("' + re.escape(title) + r'":\s*\{[^}]*"content":\s*")(.*?)(",[^}]*\})'

        def replace_content(match):
            prefix = match.group(1)
            suffix = match.group(3)
            # 转义新内容中的特殊字符
            escaped_content = new_content.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
            return prefix + escaped_content + suffix

        new_file_content, count = re.subn(pattern, replace_content, file_content, flags=re.DOTALL)

        if count == 0:
            raise Exception(f"未找到标题为《{title}》的例文数据")

        # 写入文件
        with open(data_file, 'w', encoding='utf-8') as f:
            f.write(new_file_content)

        # 更新内存中的数据
        from zuowen_data import EXAMPLE_ESSAYS
        if title in EXAMPLE_ESSAYS:
            EXAMPLE_ESSAYS[title]["content"] = new_content

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
            filepath = os.path.join(_APP_DIR, f"{title}.pdf")
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
            filepath = os.path.join(_APP_DIR, f"{title}.pdf")
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
