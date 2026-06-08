# zhenti_ui.py — 真题下载标签页 (重新设计)
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from widgets import GradientButton
import queue
import webbrowser
import json
import os

from constants import BG_COLOR, GRADES, GRADE_MAP, FAVORITES_FILE, HISTORY_FILE, GRADE_KEYWORDS, SUBJECT_KEYWORDS

BG = BG_COLOR

# 平台配置
PLATFORMS = {
    "第一试卷网": "shijuan1",
    "中小学试卷网": "szxuexiao",
    "新一试卷": "yishijuan",
    "试卷网": "shijuan_net",
    "心标教育": "xbjy",
}

# 学科配置 - 根据年级动态显示
SUBJECTS_BY_GRADE = {
    # 小学
    "一年级": ["全部", "语文", "数学"],
    "二年级": ["全部", "语文", "数学"],
    "三年级": ["全部", "语文", "数学", "英语"],
    "四年级": ["全部", "语文", "数学", "英语", "科学"],
    "五年级": ["全部", "语文", "数学", "英语", "科学"],
    "六年级": ["全部", "语文", "数学", "英语", "科学"],
    # 初中
    "七年级": ["全部", "语文", "数学", "英语", "科学", "物理", "化学", "历史", "地理", "生物", "道德与法治"],
    "八年级": ["全部", "语文", "数学", "英语", "物理", "化学", "历史", "地理", "生物", "道德与法治"],
    "九年级": ["全部", "语文", "数学", "英语", "物理", "化学", "历史", "地理", "生物", "道德与法治"],
    # 高中
    "高一": ["全部", "语文", "数学", "英语", "物理", "化学", "历史", "地理", "生物", "政治"],
    "高二": ["全部", "语文", "数学", "英语", "物理", "化学", "历史", "地理", "生物", "政治"],
    "高三": ["全部", "语文", "数学", "英语", "物理", "化学", "历史", "地理", "生物", "政治"],
}

# 年级配置
GRADES = ["一年级", "二年级", "三年级", "四年级", "五年级", "六年级",
          "七年级", "八年级", "九年级", "高一", "高二", "高三"]

# 快捷搜索年级
QUICK_GRADES = ["一年级", "二年级", "三年级", "四年级", "五年级", "六年级",
                "七年级", "八年级", "九年级", "高一", "高二", "高三"]

# 学科内部映射
SUBJECT_MAP = {
    "语文": {"shijuan1": "yuwen", "szxuexiao": "语文", "yishijuan": "yuwen", "shijuan_net": "yuwen", "xbjy": "yuwen"},
    "数学": {"shijuan1": "shuxue", "szxuexiao": "数学", "yishijuan": "shuxue", "shijuan_net": "shuxue", "xbjy": "shuxue"},
    "英语": {"shijuan1": "yingyu", "szxuexiao": "英语", "yishijuan": "yingyu", "shijuan_net": "yingyu", "xbjy": ""},
    "科学": {"shijuan1": "", "szxuexiao": "科学", "yishijuan": "kexue", "shijuan_net": "kexue", "xbjy": ""},
    "物理": {"shijuan1": "wuli", "szxuexiao": "", "yishijuan": "wuli", "shijuan_net": "", "xbjy": ""},
    "化学": {"shijuan1": "huaxue", "szxuexiao": "", "yishijuan": "huaxue", "shijuan_net": "", "xbjy": ""},
    "历史": {"shijuan1": "lishi", "szxuexiao": "", "yishijuan": "lishi", "shijuan_net": "", "xbjy": ""},
    "地理": {"shijuan1": "dili", "szxuexiao": "", "yishijuan": "dili", "shijuan_net": "", "xbjy": ""},
    "生物": {"shijuan1": "shengwu", "szxuexiao": "", "yishijuan": "shengwu", "shijuan_net": "", "xbjy": ""},
    "道德与法治": {"shijuan1": "daode", "szxuexiao": "", "yishijuan": "daode", "shijuan_net": "", "xbjy": ""},
    "政治": {"shijuan1": "daode", "szxuexiao": "", "yishijuan": "daode", "shijuan_net": "", "xbjy": ""},
}


class ZhentiTabWidget:
    def __init__(self, parent):
        self.frame = tk.Frame(parent, bg=BG)
        self.search_results = []
        self.search_worker = None
        self._queue = queue.Queue()
        self.result_count = 0
        self.favorites = self._load_json(FAVORITES_FILE, [])
        self.history = self._load_json(HISTORY_FILE, [])
        self._init_ui()

    def _load_json(self, path, default):
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return default

    def _save_json(self, path, data):
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _init_ui(self):
        main = tk.Frame(self.frame, bg=BG)
        main.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # ========== 快捷搜索区 ==========
        quick_frame = ttk.LabelFrame(main, text="快捷搜索")
        quick_frame.pack(fill=tk.X, pady=(0, 5))

        quick_inner = tk.Frame(quick_frame, bg=BG)
        quick_inner.pack(fill=tk.X, padx=5, pady=3)

        # 一排显示所有年级，平均分配宽度
        grades = ["一年级", "二年级", "三年级", "四年级", "五年级", "六年级",
                  "七年级", "八年级", "九年级", "高一", "高二", "高三"]

        # 配置列权重，使按钮平均分配
        for i in range(len(grades)):
            quick_inner.columnconfigure(i, weight=1)

        # 不同年级的颜色样式
        grade_styles = {
            # 小学：浅蓝色
            "一年级": {"bg": "#bbdefb", "activebackground": "#90caf9"},
            "二年级": {"bg": "#bbdefb", "activebackground": "#90caf9"},
            "三年级": {"bg": "#bbdefb", "activebackground": "#90caf9"},
            "四年级": {"bg": "#bbdefb", "activebackground": "#90caf9"},
            "五年级": {"bg": "#bbdefb", "activebackground": "#90caf9"},
            "六年级": {"bg": "#bbdefb", "activebackground": "#90caf9"},
            # 初中：浅绿色
            "七年级": {"bg": "#c8e6c9", "activebackground": "#a5d6a7"},
            "八年级": {"bg": "#c8e6c9", "activebackground": "#a5d6a7"},
            "九年级": {"bg": "#c8e6c9", "activebackground": "#a5d6a7"},
            # 高中：浅橙色
            "高一": {"bg": "#ffe0b2", "activebackground": "#ffcc80"},
            "高二": {"bg": "#ffe0b2", "activebackground": "#ffcc80"},
            "高三": {"bg": "#ffe0b2", "activebackground": "#ffcc80"},
        }

        # 统一样式的按钮
        for i, grade in enumerate(grades):
            style = grade_styles.get(grade, {"bg": "#e0e0e0", "activebackground": "#d0d0d0"})
            btn = tk.Button(quick_inner, text=grade,
                           font=("Microsoft YaHei", 9),
                           bg=style["bg"],
                           activebackground=style["activebackground"],
                           relief="raised",
                           bd=1,
                           height=1,
                           command=lambda g=grade: self._quick_search(g))
            btn.grid(row=0, column=i, padx=1, sticky="ew")

        # ========== 自定义搜索区 ==========
        custom_frame = ttk.LabelFrame(main, text="自定义搜索")
        custom_frame.pack(fill=tk.X, pady=(0, 5))

        custom_inner = tk.Frame(custom_frame, bg=BG)
        custom_inner.pack(fill=tk.X, padx=5, pady=5)

        # 第一行：平台 + 学科
        row1 = tk.Frame(custom_inner, bg=BG)
        row1.pack(fill=tk.X, pady=2)

        tk.Label(row1, text="平台:", font=("Microsoft YaHei", 10), width=5).pack(side=tk.LEFT)
        self.platform_combo = ttk.Combobox(row1, width=12, state="readonly",
                                           values=list(PLATFORMS.keys()))
        self.platform_combo.current(0)
        self.platform_combo.pack(side=tk.LEFT, padx=(0, 10))

        tk.Label(row1, text="年级:", font=("Microsoft YaHei", 10), width=5).pack(side=tk.LEFT)
        self.grade_combo = ttk.Combobox(row1, width=8, state="readonly",
                                        values=GRADES)
        self.grade_combo.set("四年级")  # 默认四年级
        self.grade_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.grade_combo.bind("<<ComboboxSelected>>", lambda e: self._on_grade_changed())

        tk.Label(row1, text="学科:", font=("Microsoft YaHei", 10), width=5).pack(side=tk.LEFT)
        self.subject_combo = ttk.Combobox(row1, width=10, state="readonly",
                                          values=SUBJECTS_BY_GRADE.get("四年级", ["全部"]))
        self.subject_combo.set("全部")  # 默认选中全部
        self.subject_combo.pack(side=tk.LEFT, padx=(0, 10))

        # 第二行：关键词 + 按钮
        row2 = tk.Frame(custom_inner, bg=BG)
        row2.pack(fill=tk.X, pady=2)

        tk.Label(row2, text="关键词:", font=("Microsoft YaHei", 10), width=5).pack(side=tk.LEFT)
        self.keyword_edit = tk.Entry(row2, font=("Microsoft YaHei", 10))
        self.keyword_edit.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.keyword_edit.bind("<Return>", lambda e: self.start_search())

        self.btn_search = GradientButton(row2, text="搜索", width=80, height=28,
                                         command=self.start_search)
        self.btn_search.pack(side=tk.LEFT, padx=2)

        self.btn_stop = GradientButton(row2, text="停止", width=80, height=28,
                                       command=self.stop_search, state="disabled")
        self.btn_stop.pack(side=tk.LEFT, padx=2)

        # ========== 搜索结果区 ==========
        result_frame = ttk.LabelFrame(main, text="搜索结果")
        result_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        result_inner = tk.Frame(result_frame, bg=BG)
        result_inner.pack(fill=tk.BOTH, expand=True, padx=3, pady=5)

        # 结果列表
        columns = ("platform", "title", "subject", "grade")
        self.result_tree = ttk.Treeview(result_inner, columns=columns,
                                        show="headings", selectmode="browse")
        self.result_tree.heading("platform", text="平台", anchor="w")
        self.result_tree.heading("title", text="标题", anchor="w")
        self.result_tree.heading("subject", text="学科", anchor="w")
        self.result_tree.heading("grade", text="年级", anchor="w")
        self.result_tree.column("platform", width=80, minwidth=60, stretch=False)
        self.result_tree.column("title", width=350, minwidth=150, stretch=True)
        self.result_tree.column("subject", width=60, minwidth=50, stretch=False)
        self.result_tree.column("grade", width=70, minwidth=50, stretch=False)

        tree_scroll = ttk.Scrollbar(result_inner, orient=tk.VERTICAL,
                                    command=self.result_tree.yview)
        self.result_tree.configure(yscrollcommand=tree_scroll.set)
        self.result_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 双击打开
        self.result_tree.bind("<Double-1>", lambda e: self._open_selected())

        # 右键菜单
        self._create_context_menu()

        # ========== 底部功能区 ==========
        func_group = ttk.LabelFrame(main, text="功能区")
        func_group.pack(side=tk.BOTTOM, fill=tk.X, pady=(3, 0))
        func_inner = tk.Frame(func_group, bg=BG)
        func_inner.pack(fill=tk.X, padx=5, pady=3)

        # 左侧状态区
        status_frame = tk.Frame(func_inner, bg="#e8e8e8", relief="sunken", bd=1)
        status_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        self.status_label = tk.Label(status_frame, text="就绪 - 选择年级快速搜索或右键操作",
                                     bg="#e8e8e8", fg="#333", font=("Microsoft YaHei", 9),
                                     anchor="w", padx=5, pady=2)
        self.status_label.pack(fill=tk.X)

        # 右侧按钮区
        btn_frame = tk.Frame(func_inner, bg=BG)
        btn_frame.pack(side=tk.RIGHT)

        self.btn_favorites = GradientButton(btn_frame, text="收藏夹", width=70, height=28,
                                            command=self._show_favorites)
        self.btn_favorites.pack(side=tk.LEFT, padx=2)

        self.btn_history = GradientButton(btn_frame, text="历史", width=70, height=28,
                                          command=self._show_history)
        self.btn_history.pack(side=tk.LEFT, padx=2)

        self.btn_download = GradientButton(btn_frame, text="下载试卷", width=70, height=28,
                                           command=self._download_selected)
        self.btn_download.pack(side=tk.LEFT, padx=2)

        self.btn_clear = GradientButton(btn_frame, text="清空", width=70, height=28,
                                        command=self.clear_results)
        self.btn_clear.pack(side=tk.LEFT, padx=2)

    def _on_grade_changed(self):
        """年级变化时更新学科下拉框"""
        grade = self.grade_combo.get()
        subjects = SUBJECTS_BY_GRADE.get(grade, ["全部"])
        self.subject_combo.config(values=subjects)
        self.subject_combo.set("全部")

    def _create_context_menu(self):
        """创建右键菜单"""
        self.context_menu = tk.Menu(self.frame, tearoff=0)
        self.context_menu.add_command(label="打开链接", command=self._open_selected)
        self.context_menu.add_command(label="复制链接", command=self._copy_link)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="下载试卷", command=self._download_selected)
        self.context_menu.add_command(label="收藏", command=self._add_favorite)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="取消收藏", command=self._remove_favorite)

        # 绑定右键事件
        self.result_tree.bind("<Button-3>", self._show_context_menu)

    def _show_context_menu(self, event):
        """显示右键菜单"""
        # 选中右键点击的行
        item = self.result_tree.identify_row(event.y)
        if item:
            self.result_tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def _parse_keyword(self, keyword):
        """解析关键词中的年级和学科信息

        支持格式：
        - "一年级数学" -> grade=1, subject=数学, keyword=""
        - "三年级语文试卷" -> grade=3, subject=语文, keyword="试卷"
        - "高一物理" -> grade=10, subject=物理, keyword=""
        - "七年级英语期末" -> grade=7, subject=英语, keyword="期末"
        - "数学" -> grade=None, subject=数学, keyword=""
        - "试卷" -> grade=None, subject=None, keyword="试卷"

        Returns:
            tuple: (grade, subject, remaining_keyword)
        """
        if not keyword:
            return None, None, ""

        grade = None
        subject = None
        remaining = keyword

        # 尝试匹配年级
        for grade_kw, grade_val in GRADE_KEYWORDS.items():
            if remaining.startswith(grade_kw):
                grade = grade_val
                remaining = remaining[len(grade_kw):].strip()
                break

        # 尝试匹配学科
        for subj_kw, subj_val in SUBJECT_KEYWORDS.items():
            if remaining.startswith(subj_kw):
                subject = subj_val
                remaining = remaining[len(subj_kw):].strip()
                break

        return grade, subject, remaining

    def _quick_search(self, grade):
        """快捷搜索指定年级"""
        # 设置搜索条件
        self.grade_combo.set(grade)
        self.keyword_edit.delete(0, tk.END)

        # 更新学科下拉框
        self._on_grade_changed()

        # 自动选择平台和学科（全部搜索）
        self.start_search(all_platforms=True, all_subjects=True)

    def start_search(self, all_platforms=False, all_subjects=False):
        """开始搜索"""
        if self.search_worker and self.search_worker.is_running_thread():
            return

        # 获取搜索条件
        if all_platforms:
            platforms = list(PLATFORMS.values())
        else:
            platform_name = self.platform_combo.get()
            platforms = [PLATFORMS.get(platform_name, "shijuan1")]

        # 处理学科选择
        subject_name = self.subject_combo.get()
        if all_subjects or subject_name == "全部":
            subjects = [None]  # None表示全部学科
        else:
            subjects = [SUBJECT_MAP.get(subject_name, {}).get(p, "") for p in platforms]

        grade_name = self.grade_combo.get()
        grade = GRADE_MAP.get(grade_name, "")
        keyword = self.keyword_edit.get().strip()

        # 解析关键词中的年级和学科
        parsed_grade, parsed_subject, remaining_keyword = self._parse_keyword(keyword)
        if parsed_grade:
            grade = parsed_grade
            grade_name = [k for k, v in GRADE_MAP.items() if v == parsed_grade][0] if parsed_grade else grade_name
        if parsed_subject:
            subjects = [SUBJECT_MAP.get(parsed_subject, {}).get(p, "") for p in platforms]
        if remaining_keyword:
            keyword = remaining_keyword

        # 清空结果
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)
        self.search_results = []
        self.result_count = 0

        # 更新UI状态
        self.btn_search.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.status_label.config(text="正在搜索...", fg="#2563eb")

        # 记录搜索历史
        self._add_to_history(grade_name, keyword)

        # 启动搜索线程
        self.search_worker = SearchWorker(
            self._queue, platforms, subjects, grade, keyword
        )
        self.search_worker.start()
        self._poll_queue()

    def _poll_queue(self):
        """轮询消息队列"""
        try:
            while True:
                msg_type, data = self._queue.get_nowait()
                if msg_type == "result":
                    self._on_result_found(data)
                elif msg_type == "progress":
                    self.status_label.config(text=data)
                elif msg_type == "finished":
                    self._on_search_finished(data)
                    return
                elif msg_type == "error":
                    self._on_search_error(data)
                    return
        except queue.Empty:
            pass
        if self.search_worker and self.search_worker.is_running_thread():
            self.frame.after(100, self._poll_queue)

    def _on_result_found(self, item):
        """单个结果找到"""
        self.result_count += 1
        self.search_results.append(item)

        platform = item.get("platform", "")
        title = item.get("title", "")
        subject = item.get("subject", "")
        grade = item.get("grade", "")

        self.result_tree.insert("", tk.END, values=(platform, title, subject, grade))
        self.status_label.config(text=f"已找到 {self.result_count} 个结果...", fg="#2563eb")

    def _on_search_finished(self, results):
        """搜索完成"""
        self.btn_search.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.status_label.config(text=f"搜索完成，共 {len(self.search_results)} 个结果", fg="#16a34a")
        self.search_worker = None

    def _on_search_error(self, error_msg):
        """搜索出错"""
        self.btn_search.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.status_label.config(text=f"出错: {error_msg}", fg="#dc2626")
        self.search_worker = None

    def stop_search(self):
        """停止搜索"""
        if self.search_worker and self.search_worker.is_running_thread():
            self.status_label.config(text="正在停止...", fg="#d97706")
            self.search_worker.stop()
            self.btn_stop.config(state="disabled")
            self.frame.after(1000, self._on_search_stopped)

    def _on_search_stopped(self):
        """搜索停止后"""
        if self.search_worker:
            self.search_worker.wait(2)
            self.btn_search.config(state="normal")
            self.btn_stop.config(state="disabled")
            self.status_label.config(text=f"已停止，共 {len(self.search_results)} 个结果", fg="#d97706")
            self.search_worker = None

    def _get_selected_item(self):
        """获取选中的结果项"""
        sel = self.result_tree.selection()
        if not sel:
            return None

        item_vals = self.result_tree.item(sel[0], "values")
        if not item_vals:
            return None

        title = item_vals[1]
        for item in self.search_results:
            if item.get("title") == title:
                return item
        return None

    def _download_selected(self):
        """下载选中的试卷"""
        selected_item = self._get_selected_item()
        if not selected_item:
            messagebox.showinfo("提示", "请先选择一个结果")
            return

        url = selected_item.get("url", "")
        if not url:
            messagebox.showinfo("提示", "该试卷没有链接")
            return

        # 在新线程中执行下载
        self.status_label.config(text="正在获取下载链接...", fg="#2563eb")
        self.btn_download.config(state="disabled")

        def download_thread():
            from zhenti_core import _get_scraper
            scraper = _get_scraper()

            # 获取下载信息
            info = scraper.get_download_info(url)

            if info["type"] == "direct":
                # 直接下载
                save_dir = os.path.join(os.path.dirname(__file__), "试卷下载")
                result = scraper.download_file(info["url"], save_dir)

                self.frame.after(0, lambda: self._on_download_complete(result))
            elif info["type"] == "cloud":
                # 网盘链接，打开浏览器
                webbrowser.open(info["url"])
                self.frame.after(0, lambda: self._on_download_cloud(info["url"]))
            else:
                # 没有下载链接，打开原页面
                webbrowser.open(url)
                self.frame.after(0, lambda: self._on_download_no_link())

        threading.Thread(target=download_thread, daemon=True).start()

    def _on_download_complete(self, result):
        """下载完成回调"""
        self.btn_download.config(state="normal")
        if result["success"]:
            self.status_label.config(text=f"下载成功: {os.path.basename(result['filepath'])}", fg="#16a34a")
            messagebox.showinfo("下载成功",
                                f"文件已保存到:\n{result['filepath']}")
        else:
            self.status_label.config(text=f"下载失败: {result['message']}", fg="#dc2626")
            messagebox.showwarning("下载失败", result["message"])

    def _on_download_cloud(self, cloud_url):
        """网盘链接回调"""
        self.btn_download.config(state="normal")
        self.status_label.config(text="已打开网盘链接", fg="#16a34a")
        messagebox.showinfo("网盘下载", f"已打开网盘链接:\n{cloud_url}\n\n请在浏览器中下载文件")

    def _on_download_no_link(self):
        """无下载链接回调"""
        self.btn_download.config(state="normal")
        self.status_label.config(text="已打开试卷页面", fg="#16a34a")
        messagebox.showinfo("提示", "该试卷需要在网页中下载，已为您打开页面")

    def _open_selected(self):
        """打开选中的链接"""
        selected_item = self._get_selected_item()
        if not selected_item:
            messagebox.showinfo("提示", "请先选择一个结果")
            return

        url = selected_item.get("url", "")
        if url:
            webbrowser.open(url)
            self.status_label.config(text=f"正在打开: {selected_item.get('title', '')[:30]}...", fg="#16a34a")

    def _copy_link(self):
        """复制选中链接"""
        selected_item = self._get_selected_item()
        if not selected_item:
            messagebox.showinfo("提示", "请先选择一个结果")
            return

        url = selected_item.get("url", "")
        if url:
            self.frame.clipboard_clear()
            self.frame.clipboard_append(url)
            self.status_label.config(text=f"已复制链接: {selected_item.get('title', '')[:30]}...", fg="#16a34a")

    def _add_favorite(self):
        """添加到收藏夹"""
        selected_item = self._get_selected_item()
        if not selected_item:
            messagebox.showinfo("提示", "请先选择一个结果")
            return

        # 检查是否已收藏
        for fav in self.favorites:
            if fav.get("url") == selected_item.get("url"):
                messagebox.showinfo("提示", "该试卷已在收藏夹中")
                return

        # 添加到收藏
        self.favorites.append(selected_item)
        self._save_json(FAVORITES_FILE, self.favorites)
        self.status_label.config(text=f"已收藏: {selected_item.get('title', '')[:30]}...", fg="#16a34a")
        messagebox.showinfo("收藏成功", f"已添加到收藏夹")

    def _remove_favorite(self):
        """取消收藏"""
        selected_item = self._get_selected_item()
        if not selected_item:
            return

        # 查找并移除
        for i, fav in enumerate(self.favorites):
            if fav.get("url") == selected_item.get("url"):
                self.favorites.pop(i)
                self._save_json(FAVORITES_FILE, self.favorites)
                self.status_label.config(text=f"已取消收藏: {selected_item.get('title', '')[:30]}...", fg="#d97706")
                # 如果当前显示的是收藏夹，刷新显示
                return

    def _show_favorites(self):
        """显示收藏夹"""
        if not self.favorites:
            messagebox.showinfo("收藏夹", "收藏夹为空")
            return

        # 清空当前结果
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)
        self.search_results = []
        self.result_count = 0

        # 显示收藏
        for fav in self.favorites:
            self.result_count += 1
            self.search_results.append(fav)
            platform = fav.get("platform", "")
            title = fav.get("title", "")
            subject = fav.get("subject", "")
            grade = fav.get("grade", "")
            self.result_tree.insert("", tk.END, values=(platform, title, subject, grade))

        self.status_label.config(text=f"收藏夹: 共 {len(self.favorites)} 个", fg="#2563eb")

    def _show_history(self):
        """显示搜索历史"""
        if not self.history:
            messagebox.showinfo("搜索历史", "暂无搜索历史")
            return

        # 创建历史窗口
        hist_win = tk.Toplevel(self.frame)
        hist_win.title("搜索历史")
        hist_win.geometry("400x300")
        hist_win.transient(self.frame)

        # 历史列表
        listbox = tk.Listbox(hist_win, font=("Microsoft YaHei", 10))
        listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        for h in reversed(self.history[-50:]):  # 最近50条
            text = f"{h.get('grade', '')} - {h.get('keyword', '') or '全部'}"
            listbox.insert(tk.END, text)

        def on_select(event):
            sel = listbox.curselection()
            if sel:
                idx = len(self.history) - 1 - sel[0]
                if 0 <= idx < len(self.history):
                    h = self.history[idx]
                    self.grade_combo.set(h.get("grade", "三年级"))
                    self.keyword_edit.delete(0, tk.END)
                    self.keyword_edit.insert(0, h.get("keyword", ""))
                    hist_win.destroy()

        listbox.bind("<Double-1>", on_select)

        # 提示
        tk.Label(hist_win, text="双击选择历史搜索", fg="#666",
                font=("Microsoft YaHei", 9)).pack(pady=5)

    def _add_to_history(self, grade, keyword):
        """添加搜索历史"""
        record = {
            "grade": grade,
            "keyword": keyword,
            "time": __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        self.history.append(record)
        # 只保留最近100条
        if len(self.history) > 100:
            self.history = self.history[-100:]
        self._save_json(HISTORY_FILE, self.history)

    def clear_results(self):
        """清空结果"""
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)
        self.search_results = []
        self.result_count = 0
        self.status_label.config(text="已清空结果", fg="#666")


class SearchWorker:
    """搜索工作线程"""

    def __init__(self, queue_ref, platforms, subjects, grade, keyword):
        self._queue = queue_ref
        self.platforms = platforms
        self.subjects = subjects
        self.grade = grade
        self.keyword = keyword
        self.is_running = True
        self.stop_event = threading.Event()
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        try:
            def result_callback(item):
                if self.is_running:
                    self._queue.put(("result", item))

            def progress_callback(msg):
                if self.is_running:
                    self._queue.put(("progress", msg))

            from zhenti_core import search_papers

            all_results = []

            for platform in self.platforms:
                if not self.is_running:
                    break

                for subject in self.subjects:
                    if not self.is_running:
                        break

                    results = search_papers(
                        platform, subject, self.grade, "",
                        self.keyword, result_callback,
                        stop_event=self.stop_event,
                        progress_callback=progress_callback
                    )
                    all_results.extend(results)

            if self.is_running:
                self._queue.put(("finished", all_results))
        except Exception as e:
            if self.is_running:
                self._queue.put(("error", str(e)))

    def stop(self):
        self.is_running = False
        if self.stop_event:
            self.stop_event.set()

    def is_running_thread(self):
        return self.thread is not None and self.thread.is_alive()

    def wait(self, timeout=None):
        if self.thread:
            self.thread.join(timeout=timeout)
