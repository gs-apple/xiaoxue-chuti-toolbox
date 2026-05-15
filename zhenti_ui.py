# zhenti_ui.py — 真题下载标签页 (tkinter 版，保留原版布局)
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from widgets import GradientButton
import queue
import asyncio
import webbrowser

BG = "#f0f0f0"
MODERN_BTN = dict(bg="#2563eb", fg="white", font=("Microsoft YaHei", 10, "bold"),
                   bd=0, relief="flat", activebackground="#1d4ed8",
                   activeforeground="white", width=10, height=1,
                   cursor="hand2")

PLATFORMS = {
    "第一试卷网": "shijuan1",
    "中小学试卷网": "szxuexiao",
    "新一试卷": "yishijuan",
}

SUBJECTS = {
    "shijuan1": {
        "语文试卷": "yuwen",
        "数学试卷": "shuxue",
        "英语试卷": "yingyu",
        "物理试卷": "wuli",
        "化学试卷": "huaxue",
        "政治试卷": "daode",
        "历史试卷": "lishi",
        "地理试卷": "dili",
        "生物试卷": "shengwu",
        "全部学科": "",
    },
    "szxuexiao": {
        "语文试卷": "语文",
        "数学试卷": "数学",
        "英语试卷": "英语",
        "科学试卷": "科学",
        "全部学科": "",
    },
    "yishijuan": {
        "语文试卷": "yuwen",
        "数学试卷": "shuxue",
        "英语试卷": "yingyu",
        "科学试卷": "kexue",
        "物理试卷": "wuli",
        "地理试卷": "dili",
        "生物试卷": "shengwu",
        "历史试卷": "lishi",
        "化学试卷": "huaxue",
        "道德与法治": "daode",
        "全科试卷": "quanke",
        "全部学科": "",
    },
}

GRADES = {
    "shijuan1": {
        "一年级": "1", "二年级": "2", "三年级": "3",
        "四年级": "4", "五年级": "5", "六年级": "6",
        "七年级": "7", "八年级": "8", "九年级": "9",
        "全部年级": "",
    },
    "szxuexiao": {
        "一年级": "1", "二年级": "2", "三年级": "3",
        "四年级": "4", "五年级": "5", "六年级": "6",
        "全部年级": "",
    },
    "yishijuan": {
        "一年级": "1", "二年级": "2", "三年级": "3",
        "四年级": "4", "五年级": "5", "六年级": "6",
        "七年级": "7", "八年级": "8", "九年级": "9",
        "全部年级": "",
    },
}

YEARS = {
    "全部年份": "",
    "2026年": "2026", "2025年": "2025", "2024年": "2024",
    "2023年": "2023", "2022年": "2022", "2021年": "2021",
    "2020年": "2020", "2019年": "2019",
}

PLATFORM_SUBJECT_GRADE_MAP = {
    "shijuan1": {
        "yuwen": ["1", "2", "3", "4", "5", "6", "7", "8", "9"],
        "shuxue": ["1", "2", "3", "4", "5", "6", "7", "8", "9"],
        "yingyu": ["1", "2", "3", "4", "5", "6", "7", "8", "9"],
        "wuli": ["8", "9"],
        "huaxue": ["9"],
        "daode": ["7", "8", "9"],
        "lishi": ["7", "8", "9"],
        "dili": ["7", "8", "9"],
        "shengwu": ["7", "8"],
    },
    "szxuexiao": {
        "语文": ["1", "2", "3", "4", "5", "6"],
        "数学": ["1", "2", "3", "4", "5", "6"],
        "英语": ["1", "2", "3", "4", "5", "6"],
        "科学": ["3", "4", "5", "6"],
    },
    "yishijuan": {
        "yuwen": ["1", "2", "3", "4", "5", "6", "7", "8", "9"],
        "shuxue": ["1", "2", "3", "4", "5", "6", "7", "8", "9"],
        "yingyu": ["1", "2", "3", "4", "5", "6", "7", "8", "9"],
        "kexue": ["3", "4", "5", "6"],
        "wuli": ["8", "9"],
        "huaxue": ["9"],
        "lishi": ["7", "8", "9"],
        "dili": ["7", "8", "9"],
        "shengwu": ["7", "8"],
        "daode": ["7", "8", "9"],
        "quanke": ["1", "2", "3", "4", "5", "6", "7", "8", "9"],
    },
}

PLATFORM_GRADE_LEVEL_MAP = {
    "shijuan1": {
        "1": "小学", "2": "小学", "3": "小学", "4": "小学", "5": "小学", "6": "小学",
        "7": "初中", "8": "初中", "9": "初中",
    },
    "szxuexiao": {
        "1": "小学", "2": "小学", "3": "小学", "4": "小学", "5": "小学", "6": "小学",
    },
    "yishijuan": {
        "1": "小学", "2": "小学", "3": "小学", "4": "小学", "5": "小学", "6": "小学",
        "7": "初中", "8": "初中", "9": "初中",
    },
}

SUBJECT_DISPLAY_MAP = {
    "shijuan1": {
        "yuwen": "语文", "shuxue": "数学", "yingyu": "英语",
        "wuli": "物理", "huaxue": "化学", "daode": "政治",
        "lishi": "历史", "dili": "地理", "shengwu": "生物",
    },
    "szxuexiao": {
        "语文": "语文", "数学": "数学", "英语": "英语", "科学": "科学",
    },
    "yishijuan": {
        "yuwen": "语文", "shuxue": "数学", "yingyu": "英语", "kexue": "科学",
        "wuli": "物理", "huaxue": "化学", "lishi": "历史",
        "dili": "地理", "shengwu": "生物", "daode": "道德与法治", "quanke": "全科",
    },
}


class SearchWorker:
    def __init__(self, queue_ref, platform, subject, grade, year, keyword):
        self._queue = queue_ref
        self.platform = platform
        self.subject = subject
        self.grade = grade
        self.year = year
        self.keyword = keyword
        self.is_running = True
        self.stop_event = None
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        results = []
        loop = None
        try:
            def result_callback(item):
                if self.is_running:
                    self._queue.put(("result", item))

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.stop_event = asyncio.Event()

            results = loop.run_until_complete(self._do_search(result_callback))

            if self.is_running:
                self._queue.put(("finished", results))
        except Exception as e:
            if self.is_running:
                self._queue.put(("error", str(e)))
        finally:
            if loop:
                loop.stop()
                loop.close()

    async def _do_search(self, result_callback):
        from spider.scraper import MultiPlatformScraper
        scraper = MultiPlatformScraper(headless=True)
        try:
            await scraper.launch()
            return await scraper.search(
                self.platform, self.subject, self.grade,
                self.year, self.keyword, result_callback,
                stop_event=self.stop_event
            )
        finally:
            await scraper.close()

    def stop(self):
        self.is_running = False
        if self.stop_event:
            self.stop_event.set()

    def is_running_thread(self):
        return self.thread is not None and self.thread.is_alive()

    def wait(self, timeout=None):
        if self.thread:
            self.thread.join(timeout=timeout)


class ZhentiTabWidget:
    def __init__(self, parent):
        self.frame = tk.Frame(parent, bg=BG)
        self.search_results = []
        self.search_worker = None
        self._queue = queue.Queue()
        self.result_count = 0
        self._init_ui()

    def _init_ui(self):
        main_layout = tk.Frame(self.frame, bg=BG)
        main_layout.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # ========== 搜索条件 ==========
        search_group = ttk.LabelFrame(main_layout, text="搜索条件")
        search_group.pack(fill=tk.X, pady=(0, 5))

        search_inner = tk.Frame(search_group, bg=BG)
        search_inner.pack(fill=tk.X, padx=8, pady=8)

        lbl_kw = dict(font=("Microsoft YaHei", 11), anchor="w", width=5)

        row0 = tk.Frame(search_inner, bg=BG)
        row0.pack(fill=tk.X, pady=2)
        tk.Label(row0, text="平台:", **lbl_kw).pack(side=tk.LEFT)
        self.platform_combo = ttk.Combobox(row0, width=12, state="readonly",
                                            values=list(PLATFORMS.keys()))
        self.platform_combo.current(0)
        self.platform_combo.pack(side=tk.LEFT, padx=(0, 15))
        self.platform_combo.bind("<<ComboboxSelected>>", lambda e: self.on_platform_changed())

        tk.Label(row0, text="学科:", **lbl_kw).pack(side=tk.LEFT)
        self.subject_combo = ttk.Combobox(row0, width=12, state="readonly",
                                           values=list(SUBJECTS["shijuan1"].keys()))
        self.subject_combo.current(0)
        self.subject_combo.pack(side=tk.LEFT)

        row1 = tk.Frame(search_inner, bg=BG)
        row1.pack(fill=tk.X, pady=2)
        tk.Label(row1, text="年级:", **lbl_kw).pack(side=tk.LEFT)
        self.grade_combo = ttk.Combobox(row1, width=12, state="readonly",
                                         values=list(GRADES["shijuan1"].keys()))
        self.grade_combo.current(0)
        self.grade_combo.pack(side=tk.LEFT, padx=(0, 15))
        self.grade_combo.bind("<<ComboboxSelected>>", lambda e: self.on_grade_changed())

        tk.Label(row1, text="年份:", **lbl_kw).pack(side=tk.LEFT)
        self.year_combo = ttk.Combobox(row1, width=12, state="readonly",
                                        values=list(YEARS.keys()))
        self.year_combo.current(0)
        self.year_combo.pack(side=tk.LEFT)

        row2 = tk.Frame(search_inner, bg=BG)
        row2.pack(fill=tk.X, pady=2)
        tk.Label(row2, text="关键词:", **lbl_kw).pack(side=tk.LEFT)
        self.keyword_edit = tk.Entry(row2, font=("Microsoft YaHei", 10))
        self.keyword_edit.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.keyword_edit.bind("<Return>", lambda e: self.start_search())

        # ========== 搜索结果 ==========
        result_group = ttk.LabelFrame(main_layout, text="搜索结果")
        result_group.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        result_inner = tk.Frame(result_group, bg=BG)
        result_inner.pack(fill=tk.BOTH, expand=True, padx=3, pady=5)

        columns = ("platform", "title", "subject", "grade")
        self.result_tree = ttk.Treeview(result_inner, columns=columns,
                                         show="headings", selectmode="browse")
        self.result_tree.heading("platform", text="平台")
        self.result_tree.heading("title", text="标题")
        self.result_tree.heading("subject", text="学科")
        self.result_tree.heading("grade", text="年级")
        self.result_tree.column("platform", width=70, minwidth=70, stretch=False)
        self.result_tree.column("title", width=300, minwidth=100, stretch=True)
        self.result_tree.column("subject", width=60, minwidth=60, stretch=False)
        self.result_tree.column("grade", width=60, minwidth=60, stretch=False)

        tree_scroll = ttk.Scrollbar(result_inner, orient=tk.VERTICAL,
                                     command=self.result_tree.yview)
        self.result_tree.configure(yscrollcommand=tree_scroll.set)
        self.result_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 预览下载按钮（固定在右下角）
        self.btn_open = tk.Button(result_inner, text="预览下载", width=8,
                                   command=self._on_open_selected)
        self.btn_open.place(relx=1.0, rely=1.0, anchor="se", x=-5, y=-5)

        # ========== 底部按钮 ==========
        bottom_frame = tk.Frame(main_layout, bg=BG)
        bottom_frame.pack(fill=tk.X, pady=(0, 5))

        self.status_label = tk.Label(bottom_frame, text="就绪",
                                      fg="#666", font=("Microsoft YaHei", 9))
        self.status_label.pack(side=tk.LEFT, padx=4)

        func_group = ttk.LabelFrame(bottom_frame, text="功能区")
        func_group.pack(side=tk.RIGHT, padx=(10, 0))
        func_inner = tk.Frame(func_group, bg=BG)
        func_inner.pack(padx=5, pady=3)

        self.btn_stop = GradientButton(func_inner, text="停止搜索", width=100, height=32,
                                        command=self.stop_search)
        self.btn_search = GradientButton(func_inner, text="开始搜索", width=100, height=32,
                                          command=self.start_search)
        self.btn_clear = GradientButton(func_inner, text="清空结果", width=100, height=32,
                                         command=self.clear_results)

        func_inner.columnconfigure(0, weight=1)
        func_inner.columnconfigure(4, weight=1)
        self.btn_stop.grid(row=0, column=1, padx=3)
        self.btn_search.grid(row=0, column=2, padx=3)
        self.btn_clear.grid(row=0, column=3, padx=3)

    def on_platform_changed(self):
        platform_name = self.platform_combo.get()
        platform_key = PLATFORMS.get(platform_name, "shijuan1")
        subjects = SUBJECTS.get(platform_key, SUBJECTS["shijuan1"])
        grades = GRADES.get(platform_key, GRADES["shijuan1"])

        self.subject_combo.config(values=list(subjects.keys()))
        self.subject_combo.current(0)
        self.grade_combo.config(values=list(grades.keys()))
        self.grade_combo.current(0)
        self.keyword_edit.delete(0, tk.END)
        self.update_subjects_by_grade()

    def on_grade_changed(self):
        self.update_subjects_by_grade()

    def update_subjects_by_grade(self):
        platform_name = self.platform_combo.get()
        platform_key = PLATFORMS.get(platform_name, "shijuan1")
        if platform_key != "yishijuan":
            return

        grade_name = self.grade_combo.get()
        grade_key = GRADES["yishijuan"].get(grade_name, "")
        if not grade_key:
            return

        grade_int = int(grade_key)
        if grade_int <= 2:
            items = ["语文试卷", "数学试卷", "英语试卷", "全科试卷"]
        elif grade_int <= 6:
            items = ["语文试卷", "数学试卷", "英语试卷", "科学试卷", "全科试卷"]
        else:
            items = ["语文试卷", "数学试卷", "英语试卷", "物理试卷", "地理试卷",
                     "生物试卷", "历史试卷", "化学试卷", "道德与法治", "全科试卷"]

        self.subject_combo.config(values=items)
        self.subject_combo.current(0)

    def start_search(self):
        if self.search_worker and self.search_worker.is_running_thread():
            return

        platform = PLATFORMS.get(self.platform_combo.get(), "")
        platform_subjects = SUBJECTS.get(platform, SUBJECTS["shijuan1"])
        platform_grades = GRADES.get(platform, GRADES["shijuan1"])
        subject = platform_subjects.get(self.subject_combo.get(), "")
        grade = platform_grades.get(self.grade_combo.get(), "")
        year = YEARS.get(self.year_combo.get(), "")
        keyword = self.keyword_edit.get().strip()

        if not self.validate_subject_grade(platform, subject, grade):
            return

        for item in self.result_tree.get_children():
            self.result_tree.delete(item)
        self.search_results = []
        self.result_count = 0

        self.btn_search.config(state="disabled", text="搜索中...")
        self.btn_stop.set_disabled(False)
        self.status_label.config(text="正在搜索...")

        self.search_worker = SearchWorker(self._queue, platform, subject, grade, year, keyword)
        self.search_worker.start()
        self._poll_queue()

    def _poll_queue(self):
        try:
            while True:
                msg_type, data = self._queue.get_nowait()
                if msg_type == "result":
                    self.on_result_found(data)
                elif msg_type == "finished":
                    self.on_search_finished(data)
                    return
                elif msg_type == "error":
                    self.on_search_error(data)
                    return
        except queue.Empty:
            pass
        if self.search_worker and self.search_worker.is_running_thread():
            self.frame.after(100, self._poll_queue)

    def validate_subject_grade(self, platform, subject, grade):
        if not grade or grade == "":
            return True

        grade_level_map = PLATFORM_GRADE_LEVEL_MAP.get(platform, {})
        grade_level = grade_level_map.get(grade, "")

        if platform == "yishijuan":
            if grade in ["1", "2", "3", "4", "5", "6"]:
                expected_level = "小学"
            elif grade in ["7", "8", "9"]:
                expected_level = "初中"
            else:
                expected_level = ""

            if grade_level and grade_level != expected_level:
                grade_display = {v: k for k, v in GRADES.get(platform, GRADES["shijuan1"]).items()}.get(grade, grade)
                messagebox.showwarning("年级学段不匹配",
                    f"选择的年级和学段不匹配！\n\n"
                    f"年级: {grade_display}\n"
                    f"{grade_display}属于{grade_level}，请选择对应学段的试卷。")
                return False

        if not subject or subject == "":
            return True

        subject_grade_map = PLATFORM_SUBJECT_GRADE_MAP.get(platform, {})
        valid_grades = subject_grade_map.get(subject, [])

        if valid_grades and grade not in valid_grades:
            subject_display = SUBJECT_DISPLAY_MAP.get(platform, {}).get(subject, subject)
            grade_display = {v: k for k, v in GRADES.get(platform, GRADES["shijuan1"]).items()}.get(grade, grade)
            messagebox.showwarning("学科年级不匹配",
                f"选择的年级和学科不匹配！\n\n"
                f"年级: {grade_display}\n"
                f"学科: {subject_display}\n\n"
                f"{grade_display}没有{subject_display}学科，请选择其他学科。")
            return False

        return True

    def stop_search(self):
        if self.search_worker and self.search_worker.is_running_thread():
            self.status_label.config(text="正在停止...")
            self.search_worker.stop()
            self.btn_stop.set_disabled(True)
            self.frame.after(1000, self._on_search_stopped)

    def _on_search_stopped(self):
        if self.search_worker:
            self.search_worker.wait(2)
            self.btn_search.config(state="normal", text="开始搜索")
            self.btn_stop.set_disabled(True)
            self.status_label.config(text=f"搜索已停止，共找到 {len(self.search_results)} 个结果")
            self.search_worker = None

    def on_result_found(self, item):
        self.result_count += 1
        self.search_results.append(item)

        platform = item.get("platform", "")
        title = item.get("title", "")
        subject = item.get("subject", "")
        grade = item.get("grade", "")

        self.result_tree.insert("", tk.END, values=(platform, title, subject, grade))
        self.status_label.config(text=f"已找到 {self.result_count} 个结果...")

    def on_search_finished(self, results):
        self.search_results = results
        self.btn_search.config(state="normal", text="开始搜索")
        self.btn_stop.set_disabled(True)
        self.status_label.config(text=f"搜索完成，共找到 {len(results)} 个结果")
        self.search_worker = None

    def on_search_error(self, error_msg):
        self.btn_search.config(state="normal", text="开始搜索")
        self.btn_stop.set_disabled(True)
        self.status_label.config(text=f"搜索出错: {error_msg}")
        self.search_worker = None

    def _on_open_selected(self):
        sel = self.result_tree.selection()
        if not sel:
            return
        item_vals = self.result_tree.item(sel[0], "values")
        if not item_vals:
            return
        title = item_vals[1]
        for item in self.search_results:
            if item.get("title") == title:
                self.open_link(item)
                return

    def open_link(self, item):
        url = item.get("url", "")
        if url:
            webbrowser.open(url)
            self.status_label.config(text=f"正在打开: {item.get('title', '')[:30]}...")

    def clear_results(self):
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)
        self.search_results = []
        self.status_label.config(text="已清空结果")
