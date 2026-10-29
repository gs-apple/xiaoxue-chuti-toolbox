# zhenti_ui.py — 真题下载标签页
import json
import os
import queue
import threading
import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk

from widgets import GradientButton
from constants import (
    BG_COLOR,
    FAVORITES_FILE,
    GRADE_KEYWORDS,
    GRADE_MAP,
    GRADES,
    SUBJECT_KEYWORDS,
    ZHENTI_DOWNLOAD_DIR,
)
from zhenti import zhenti_core

BG = BG_COLOR


# 平台清单：唯一来源是 zhenti_core.PLATFORM_CONFIGS（键=平台码，值=配置）。
# 原先这里另有一份 PLATFORMS 字面量，加平台要改 7 处、漏改还是静默失败。
PLATFORMS = {cfg.name: key for key, cfg in zhenti_core.PLATFORM_CONFIGS.items()}
PLATFORM_NAMES = {key: name for name, key in PLATFORMS.items()}

# 平台下拉的首项：一次搜索依次跑全部平台（各平台按自己的翻页深度抓，慢的排在后面）。
ALL_PLATFORMS_TEXT = "全部平台"

DEFAULT_GRADE = "五年级"
DEFAULT_STATUS = "就绪 - 选好年级和学科后点搜索"
YEAR_CHOICES = ["不限"] + [str(y) for y in range(2027, 2014, -1)]

# 学科配置 - 按年级递进，年级越高科目越多（不是从一年级就把九科全列出来）。
# 口径以"站上真能搜到"为准（第一试卷网 2026-10-28 逐栏目实测）：
#   语文/数学/英语 1~12 年级都有；科学三年级起；
#   生物/历史/地理/政治 七年级起；物理八年级起；化学九年级起。
# 注意"政治"一并代表初中的「道德与法治」（站内只有 sjzz 一个栏目）。
SUBJECTS_BY_GRADE = {
    # 小学
    "一年级": ["全部", "语文", "数学", "英语"],
    "二年级": ["全部", "语文", "数学", "英语"],
    "三年级": ["全部", "语文", "数学", "英语", "科学"],
    "四年级": ["全部", "语文", "数学", "英语", "科学"],
    "五年级": ["全部", "语文", "数学", "英语", "科学"],
    "六年级": ["全部", "语文", "数学", "英语", "科学"],
    # 初中
    "七年级": ["全部", "语文", "数学", "英语", "生物", "历史", "地理", "政治"],
    "八年级": ["全部", "语文", "数学", "英语", "物理", "生物", "历史", "地理", "政治"],
    "九年级": ["全部", "语文", "数学", "英语", "物理", "化学", "历史", "政治"],
    # 高中
    "高一": ["全部", "语文", "数学", "英语", "物理", "化学", "生物", "历史", "地理", "政治"],
    "高二": ["全部", "语文", "数学", "英语", "物理", "化学", "生物", "历史", "地理", "政治"],
    "高三": ["全部", "语文", "数学", "英语", "物理", "化学", "生物", "历史", "地理", "政治"],
}


def subject_choices(grade):
    """该年级学科下拉的全集。

    只按课程表给，**不按当前平台裁**：三年级本来就有科学，第一试卷网没有
    科学栏目不代表软件里不该出现这一项。平台缺的科目由 core 在搜索时提示、
    UI 在开搜前问要不要换平台。
    """
    return list(SUBJECTS_BY_GRADE.get(grade, ["全部"]))


class ZhentiTabWidget:
    # 状态栏固定像素宽度：700px 窗口下按钮区占 3×70+边距≈224px，这里留足余量
    STATUS_WIDTH = 380
    # 该宽度下大约能放下的汉字数，超出用省略号，完整内容存在 _status_full
    STATUS_MAX_CHARS = 27

    def __init__(self, parent):
        self.frame = tk.Frame(parent, bg=BG)
        self.search_results = []
        self.search_worker = None
        self._queue = queue.Queue()
        self.result_count = 0
        self._skipped_count = 0

        # 结果行的稳定标识：iid 单调计数器 + 映射表。
        # 不能用标题/url 反查（同名结果很常见，会把动作作用到别的行），
        # 也不能直接拿 url 当 iid（重复或空串会让 Tk 抛 TclError）。
        self._by_iid = {}
        self._next_iid = 0
        self._checked = set()               # 打勾的 iid 集合（下载只作用于这些行）

        self._downloading = False
        self._dl_queue = queue.Queue()
        self._multi_running = False
        self._multi_queue = queue.Queue()
        self._multi_stop = threading.Event()
        self._multi_results = []
        self._status_full = ""
        self._view_mode = "search"          # search / favorites
        self._capability_hint = False        # 状态栏当前显示的是不是"本平台没这科"的提示
        self._deferred_warnings = []

        self.favorites = [fav for fav in self._load_json(FAVORITES_FILE, [])
                          if isinstance(fav, dict) and fav.get("url")]
        self._init_ui()

        for warning in self._deferred_warnings:
            messagebox.showwarning("配置文件读取失败", warning)
        self._deferred_warnings.clear()

    # ══════════════════════════════════════════════════════
    #  持久化
    # ══════════════════════════════════════════════════════

    def _load_json(self, path, default):
        """读 JSON。文件不存在=正常首次运行；文件损坏=备份并留一条待提示警告。"""
        if not os.path.exists(path):
            return default
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError) as e:
            backup = path + ".corrupt"
            try:
                os.replace(path, backup)
            except OSError:
                backup = ""
            note = f"（已备份为 {os.path.basename(backup)}）" if backup else ""
            self._deferred_warnings.append(f"{os.path.basename(path)} 解析失败：{e}{note}")
            return default
        if not isinstance(data, list):
            self._deferred_warnings.append(f"{os.path.basename(path)} 内容格式不对，已忽略")
            return default
        return data

    def _save_json(self, path, data):
        """原子写 JSON。返回 bool —— 调用方必须据此决定要不要报成功。"""
        tmp_path = path + ".tmp"
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, path)
            return True
        except (OSError, TypeError, ValueError):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            return False

    # ══════════════════════════════════════════════════════
    #  界面构建
    # ══════════════════════════════════════════════════════

    def _init_ui(self):
        main = tk.Frame(self.frame, bg=BG)
        main.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self._build_custom_search(main)
        self._build_result_tree(main)
        self._build_func_bar(main)
        self._create_context_menu()
        self._on_grade_changed()          # 初始学科下拉也要按平台能力裁一次

    def _build_custom_search(self, parent):
        custom_frame = ttk.LabelFrame(parent, text="搜索条件")
        custom_frame.pack(fill=tk.X, pady=(0, 5))

        custom_inner = tk.Frame(custom_frame, bg=BG)
        custom_inner.pack(fill=tk.X, padx=5, pady=5)

        # 第一行：平台 + 年级 + 学科 + 年份
        row1 = tk.Frame(custom_inner, bg=BG)
        row1.pack(fill=tk.X, pady=2)

        tk.Label(row1, text="平台:", font=("Microsoft YaHei", 10), width=5).pack(side=tk.LEFT)
        self.platform_combo = ttk.Combobox(row1, width=12, state="readonly",
                                           values=[ALL_PLATFORMS_TEXT] + list(PLATFORMS.keys()))
        # 默认仍停在第一试卷网（最快），"全部平台"放首项方便随时切
        self.platform_combo.current(1)
        self.platform_combo.pack(side=tk.LEFT, padx=(0, 8))
        self.platform_combo.bind("<<ComboboxSelected>>", lambda e: self._on_platform_changed())

        tk.Label(row1, text="年级:", font=("Microsoft YaHei", 10), width=5).pack(side=tk.LEFT)
        self.grade_combo = ttk.Combobox(row1, width=8, state="readonly", values=GRADES)
        self.grade_combo.set(DEFAULT_GRADE)
        self.grade_combo.pack(side=tk.LEFT, padx=(0, 8))
        self.grade_combo.bind("<<ComboboxSelected>>", lambda e: self._on_grade_changed())

        tk.Label(row1, text="学科:", font=("Microsoft YaHei", 10), width=5).pack(side=tk.LEFT)
        self.subject_combo = ttk.Combobox(row1, width=9, state="readonly",
                                          values=subject_choices(DEFAULT_GRADE))
        self.subject_combo.set("全部")
        self.subject_combo.pack(side=tk.LEFT, padx=(0, 8))
        # 换学科也要刷新状态栏提示（"本平台没这科"/"全部平台会搜几家"都跟学科有关）
        self.subject_combo.bind("<<ComboboxSelected>>", lambda e: self._on_grade_changed())

        tk.Label(row1, text="年份:", font=("Microsoft YaHei", 10), width=5).pack(side=tk.LEFT)
        self.year_combo = ttk.Combobox(row1, width=7, state="readonly", values=YEAR_CHOICES)
        self.year_combo.set("不限")
        self.year_combo.pack(side=tk.LEFT)

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

    def _build_result_tree(self, parent):
        result_frame = ttk.LabelFrame(parent, text="搜索结果")
        result_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        result_inner = tk.Frame(result_frame, bg=BG)
        result_inner.pack(fill=tk.BOTH, expand=True, padx=3, pady=5)

        # 第一列是勾选框（☐/☑）：下载只作用于打勾的行，与"选中行"分开
        columns = ("sel", "platform", "title", "subject", "grade", "year", "answer")
        self.result_tree = ttk.Treeview(result_inner, columns=columns,
                                        show="headings", selectmode="browse")
        for col, text, width, minwidth, stretch in (
            ("sel", "☐", 30, 28, False),
            ("platform", "平台", 80, 60, False),
            ("title", "标题", 240, 150, True),
            ("subject", "学科", 55, 45, False),
            ("grade", "年级", 60, 50, False),
            ("year", "年份", 62, 50, False),
            ("answer", "答案", 44, 40, False),
        ):
            anchor = "center" if col == "sel" else "w"
            self.result_tree.heading(col, text=text, anchor=anchor)
            self.result_tree.column(col, width=width, minwidth=minwidth, stretch=stretch)

        tree_scroll = ttk.Scrollbar(result_inner, orient=tk.VERTICAL,
                                    command=self.result_tree.yview)
        self.result_tree.configure(yscrollcommand=tree_scroll.set)
        self.result_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.result_tree.bind("<Double-1>", self._on_tree_double_click)
        self.result_tree.bind("<Button-1>", self._on_tree_click)

    def _build_func_bar(self, parent):
        func_group = ttk.LabelFrame(parent, text="功能区")
        func_group.pack(side=tk.BOTTOM, fill=tk.X, pady=(3, 0))
        func_inner = tk.Frame(func_group, bg=BG)
        func_inner.pack(fill=tk.X, padx=5, pady=3)

        # 右侧按钮区先 pack，保证按钮永远优先拿到自己的宽度；
        # 否则状态文字一长就把按钮挤出可视区。
        btn_frame = tk.Frame(func_inner, bg=BG)
        btn_frame.pack(side=tk.RIGHT)

        self.btn_favorites = GradientButton(btn_frame, text="收藏夹", width=70, height=28,
                                            command=self._show_favorites)
        self.btn_favorites.pack(side=tk.LEFT, padx=2)

        self.btn_download = GradientButton(btn_frame, text="下载试卷", width=70, height=28,
                                           command=self._download_selected)
        self.btn_download.pack(side=tk.LEFT, padx=2)

        self.btn_clear = GradientButton(btn_frame, text="清空", width=70, height=28,
                                        command=self.clear_results)
        self.btn_clear.pack(side=tk.LEFT, padx=2)

        status_frame = tk.Frame(func_inner, bg="#e8e8e8", relief="sunken", bd=1,
                                width=self.STATUS_WIDTH, height=28)
        status_frame.pack(side=tk.LEFT, padx=(0, 10))
        status_frame.pack_propagate(False)

        self.status_label = tk.Label(status_frame, text=DEFAULT_STATUS,
                                     bg="#e8e8e8", fg="#333", font=("Microsoft YaHei", 9),
                                     anchor="w", padx=5, pady=2)
        self.status_label.pack(fill=tk.BOTH, expand=True)

    def _create_context_menu(self):
        self.context_menu = tk.Menu(self.frame, tearoff=0)
        self.context_menu.add_command(label="打开链接", command=self._open_selected)
        self.context_menu.add_command(label="复制链接", command=self._copy_link)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="下载试卷", command=self._download_selected)
        self.context_menu.add_command(label="收藏", command=self._add_favorite)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="取消收藏", command=self._remove_favorite)

        self.result_tree.bind("<Button-3>", self._show_context_menu)

    def _show_context_menu(self, event):
        item = self.result_tree.identify_row(event.y)
        if item:
            # 多选模式下右键：点中的行已在选区里就保留整个选区，
            # 只有右键到选区外才切换成单选（否则一次多选一点右键就没了）
            if item not in self.result_tree.selection():
                self.result_tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    # ══════════════════════════════════════════════════════
    #  弹窗
    # ══════════════════════════════════════════════════════

    DIALOG_BODY_SIZE = 11        # 弹窗正文字号（messagebox 大概 9）
    DIALOG_WRAP_PX = 470         # 正文折行宽度：一行放不下就折行，不硬挤

    def _show_dialog(self, title, body, tone="info"):
        """自绘提示框。

        messagebox 的字号跟系统走、改不了，文件路径一长就挤成一行，
        批量下载的汇总信息更是小到看不清。这里用 Toplevel 自己排版。
        弹窗内不重复标题、也不画分隔线（标题只在窗口标题栏上），
        结果好坏靠按钮底色区分：ok=绿 / warn=橙 / info=蓝。
        """
        skins = {
            "ok": ("#22c55e", "#16a34a", "#15803d", "#4ade80", "#22c55e", "#16a34a"),
            "warn": ("#f59e0b", "#d97706", "#b45309", "#fbbf24", "#f59e0b", "#d97706"),
        }
        colors = skins.get(tone)

        dlg = tk.Toplevel(self.frame)
        dlg.title(title)
        dlg.configure(bg="white")
        dlg.resizable(False, False)
        dlg.transient(self.frame.winfo_toplevel())

        body_frame = tk.Frame(dlg, bg="white", padx=20, pady=16)
        body_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(body_frame, text=body, bg="white", fg="#222", anchor="w",
                 justify=tk.LEFT, wraplength=self.DIALOG_WRAP_PX,
                 font=("Microsoft YaHei", self.DIALOG_BODY_SIZE)).pack(fill=tk.BOTH, expand=True)

        btn_kw = {} if colors is None else dict(
            color_top=colors[0], color_mid=colors[1], color_bot=colors[2],
            hover_top=colors[3], hover_mid=colors[4], hover_bot=colors[5])
        GradientButton(body_frame, text="知道了", width=96, height=32,
                       font=("Microsoft YaHei", 11, "bold"),
                       command=dlg.destroy, **btn_kw).pack(pady=(16, 0))

        dlg.update_idletasks()
        w, h = dlg.winfo_reqwidth(), dlg.winfo_reqheight()
        root = self.frame.winfo_toplevel()
        x = root.winfo_rootx() + max((root.winfo_width() - w) // 2, 0)
        y = root.winfo_rooty() + max((root.winfo_height() - h) // 3, 0)
        dlg.geometry(f"+{x}+{y}")
        dlg.bind("<Escape>", lambda e: dlg.destroy())
        dlg.grab_set()
        dlg.wait_window()

    def _set_status(self, text, color="#333"):
        """统一写状态栏：固定宽度内放不下就截断加省略号。"""
        full = str(text)
        self._status_full = full
        if len(full) > self.STATUS_MAX_CHARS:
            shown = full[:self.STATUS_MAX_CHARS - 1] + "…"
        else:
            shown = full
        self.status_label.config(text=shown, fg=color)

    def _current_platform_key(self):
        return PLATFORMS.get(self.platform_combo.get(), "")

    def _on_platform_changed(self):
        self._on_grade_changed()

    def _on_grade_changed(self):
        """年级/平台变化时重建学科下拉。

        下拉按**课程**给全集，不按当前平台裁。三年级本来就有科学，
        第一试卷网没有科学栏目不代表这一项不该出现在软件里（用户明确要求）；
        平台缺的科目选中后，搜索时会问要不要换到有这科的平台。
        """
        grade = self.grade_combo.get()
        if grade not in GRADES:
            grade = DEFAULT_GRADE
            self.grade_combo.set(grade)

        subjects = subject_choices(grade)
        current = self.subject_combo.get()
        self.subject_combo.config(values=subjects)
        self.subject_combo.set(current if current in subjects else "全部")

        platform_key = self._current_platform_key()
        platform_name = self.platform_combo.get()
        if platform_name == ALL_PLATFORMS_TEXT:
            # 全部平台：只报"这个年级/学科有几家能搜"，不逐个提示缺科目
            # （总有一家是全的，提示反而变成噪声）
            subject = self.subject_combo.get()
            keys = list(PLATFORMS.values())
            scope = grade
            if subject and subject != "全部":
                usable = zhenti_core.platforms_with_subject(subject, grade)
                if usable:
                    keys = [k for k in keys if k in usable]
                scope = f"{grade}{subject}"
            n_ok = sum(1 for key in keys
                       if zhenti_core.platform_supports_grade(key, grade))
            self._capability_hint = True
            self._set_status(f"全部平台：{scope}将依次搜索 {n_ok}/{len(PLATFORMS)} 家平台", "#2563eb")
            return

        if not zhenti_core.platform_supports_grade(platform_key, grade):
            supported = zhenti_core.platform_grade_names(platform_key)
            scope = f"{supported[0]}～{supported[-1]}" if len(supported) > 1 else "无"
            self._capability_hint = True
            self._set_status(f"{platform_name}没有{grade}（仅{scope}）", "#d97706")
            return

        missing = [s for s in subjects
                   if s != "全部" and s not in zhenti_core.platform_subjects(platform_key, grade)]
        if missing:
            self._capability_hint = True
            self._set_status(
                f"{platform_name}没有{'、'.join(missing)}栏目，选中后会提示换平台", "#d97706")
        elif self._capability_hint:
            # 换到有这科的平台后，上一条"某平台没有科学"的提示会一直挂着，
            # 用户会以为新平台也没有。这类提示只在说它的时候有効。
            self._capability_hint = False
            self._set_status(DEFAULT_STATUS, "#666")

    # ══════════════════════════════════════════════════════
    #  搜索
    # ══════════════════════════════════════════════════════

    def _parse_keyword(self, keyword):
        """解析关键词开头自带的年级/学科。

        - "一年级数学" -> grade="1", subject="数学", remaining=""
        - "三年级语文试卷" -> grade="3", subject="语文", remaining="试卷"
        - "数学" -> grade=None, subject="数学", remaining=""

        返回的 grade 是 GRADE_MAP 的数字码**字符串**（不是 int）。
        """
        if not keyword:
            return None, None, ""

        grade = None
        subject = None
        remaining = keyword

        for grade_kw, grade_val in GRADE_KEYWORDS.items():
            if remaining.startswith(grade_kw):
                grade = grade_val
                remaining = remaining[len(grade_kw):].strip()
                break

        for subj_kw, subj_val in SUBJECT_KEYWORDS.items():
            if remaining.startswith(subj_kw):
                subject = subj_val
                remaining = remaining[len(subj_kw):].strip()
                break

        return grade, subject, remaining

    def start_search(self):
        """开始搜索。"""
        if self.search_worker and self.search_worker.is_running_thread():
            # 不能静默 return：用户点了按钮毫无反应，会以为程序卡死
            self._set_status("上一次搜索还没结束，请稍候", "#d97706")
            return

        # 平台：选「全部平台」就依次跑全部（慢，但一次点完）
        all_platforms = self.platform_combo.get() == ALL_PLATFORMS_TEXT
        platform_names = list(PLATFORMS.keys()) if all_platforms else [self.platform_combo.get()]

        # 年级必须落在值域内。Combobox 的 readonly 只挡键入、不挡程序 .set()，
        # 脏值（如旧配置里的"高中"）会让 core 收到非法年级。
        grade_name = self.grade_combo.get()
        if grade_name not in GRADES:
            grade_name = DEFAULT_GRADE
            self.grade_combo.set(grade_name)
            self._on_grade_changed()
        grade = GRADE_MAP[grade_name]

        keyword = self.keyword_edit.get().strip()
        parsed_grade, parsed_subject, remaining = self._parse_keyword(keyword)
        if parsed_grade:
            grade = parsed_grade
            grade_name = next((k for k, v in GRADE_MAP.items() if v == parsed_grade), grade_name)
        if parsed_grade or parsed_subject:
            # 前缀被消费掉之后就只留剩余部分做标题过滤。
            # 原先只在 remaining 非空时回填，导致关键词正好是"一年级数学"时
            # 仍拿整串去比标题，必然 0 条。
            keyword = remaining.strip()

        if self.subject_combo.get() == "全部":
            subjects = [None]
        else:
            subjects = [self.subject_combo.get()]
        if parsed_subject:
            subjects = [parsed_subject]

        # 只搜支持该年级的平台；一个都不支持就明确告诉用户，而不是"搜索完成 0 条"
        skipped = [name for name in platform_names
                   if not zhenti_core.platform_supports_grade(PLATFORMS[name], grade_name)]
        platform_keys = [PLATFORMS[name] for name in platform_names if name not in skipped]
        if not platform_keys:
            messagebox.showinfo("提示", f"所选平台都没有{grade_name}的栏目，请换平台或换年级。")
            return

        # 学科可用性：当前平台没有这科时当场问要不要换平台。
        # 三年级科学只有中小学试卷网有（第一试卷网 9 个栏目里根本没有科学），
        # 只丢一句"没有科学栏目"，用户下一步还得自己挨个试平台。
        subject = subjects[0]
        if all_platforms:
            # 全部平台时不问"要不要换平台"：没这科的直接跳过，一家都没有才提示
            if subject:
                usable = zhenti_core.platforms_with_subject(subject, grade_name)
                if usable:
                    platform_keys = [k for k in platform_keys if k in usable]
                if not platform_keys:
                    messagebox.showinfo("提示", f"没有平台有{grade_name}{subject}栏目。")
                    return
        elif subject:
            current_key = platform_keys[0]
            usable = zhenti_core.platforms_with_subject(subject, grade_name)
            if usable and current_key not in usable:
                alt_names = [PLATFORM_NAMES.get(key, key) for key in usable]
                if messagebox.askyesno(
                        "该平台没有这个学科",
                        f"{self.platform_combo.get()} 没有{grade_name}{subject}栏目。\n\n"
                        f"有这科的平台：{'、'.join(alt_names)}\n\n"
                        f"是否切到 {alt_names[0]} 搜索？"):
                    platform_keys = [usable[0]]
                    self.platform_combo.set(alt_names[0])
                    self._on_platform_changed()      # 新平台学科表重新裁一次
                    self.subject_combo.set(subject)  # 别被重置成"全部"
                else:
                    self._set_status(
                        f"{self.platform_combo.get()}没有{subject}栏目，已取消搜索", "#d97706")
                    return

        year = self.year_combo.get()
        year = "" if year in ("", "不限") else year

        self._reset_results()
        self._skipped_count = len(skipped)
        self.btn_search.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.btn_download.config(state="normal")
        hint = f"正在搜索 {grade_name}..."
        if skipped:
            hint = f"跳过{len(skipped)}个无此年级的平台，正在搜索..."
        self._set_status(hint, "#2563eb")

        self.search_worker = SearchWorker(
            self._queue, platform_keys, subjects, grade, keyword, year)
        self.search_worker.start()
        self._poll_queue()

    def _poll_queue(self):
        try:
            while True:
                msg_type, data = self._queue.get_nowait()
                if msg_type == "result":
                    self._on_result_found(data)
                elif msg_type == "progress":
                    self._set_status(data, "#2563eb")
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

    def _add_result(self, item):
        """插入一行结果，并登记 iid -> item 映射（勾选框默认不勾）。"""
        iid = str(self._next_iid)
        self._next_iid += 1
        self._by_iid[iid] = item
        self.search_results.append(item)
        self.result_count += 1
        self.result_tree.insert("", tk.END, iid=iid, values=(
            "☐",
            item.get("platform", ""),
            item.get("title", ""),
            item.get("subject", ""),
            item.get("grade", ""),
            item.get("year", ""),
            "有" if item.get("has_answer") else "",
        ))

    # ── 勾选框 ─────────────────────────────────────────────

    def _on_tree_double_click(self, event):
        """双击数据行才打开网页；双击表头/勾选列一律吞掉。

        以前这里直接 lambda 调 _open_selected：连点表头的"☐"（全选）时，
        第二下会被 Tk 识别成双击，于是把当前选中行——通常就是第一条——
        的网页打开了。所以双击必须自己判断点在哪。
        """
        region = self.result_tree.identify_region(event.x, event.y)
        if region != "cell":
            return "break"                       # 表头 / 分隔线 / 空白区
        if self.result_tree.identify_column(event.x) == "#1":
            return "break"                       # 勾选列：交给单击切换
        if not self.result_tree.identify_row(event.y):
            return "break"
        self._open_selected()
        return "break"

    def _on_tree_click(self, event):
        """点第一列（☐）切换勾选；点表头（☐）全选/全不选。"""
        region = self.result_tree.identify_region(event.x, event.y)
        if self.result_tree.identify_column(event.x) != "#1":
            return None
        if region == "heading":
            self._toggle_check_all()
            return "break"
        if region != "cell":
            return None
        iid = self.result_tree.identify_row(event.y)
        if iid:
            self._toggle_check(iid)
            return "break"          # 拦掉默认行为，点方框不会改动当前选中行
        return None

    def _toggle_check(self, iid):
        if iid in self._checked:
            self._checked.discard(iid)
            self.result_tree.set(iid, "sel", "☐")
        else:
            self._checked.add(iid)
            self.result_tree.set(iid, "sel", "☑")

    def _toggle_check_all(self):
        children = self.result_tree.get_children()
        check_all = len(self._checked) < len(children)   # 没全勾就全勾，全勾了就全取消
        for iid in children:
            self.result_tree.set(iid, "sel", "☑" if check_all else "☐")
        self._checked = set(children) if check_all else set()
        self._set_status(f"已勾选 {len(self._checked)} 条" if check_all else "已取消全部勾选", "#2563eb")

    def _checked_items_in_order(self):
        """按显示顺序返回已勾选的结果项（跳过的行不存在，天然忽略）。"""
        return [self._by_iid[iid] for iid in self.result_tree.get_children()
                if iid in self._checked and (self._by_iid.get(iid) or {}).get("url")]

    def _on_result_found(self, item):
        self._view_mode = "search"
        self._add_result(item)
        self._set_status(f"已找到 {self.result_count} 个结果...", "#2563eb")

    def _on_search_finished(self, results):
        self.btn_search.config(state="normal")
        self.btn_stop.config(state="disabled")
        text = f"搜索完成，共 {len(self.search_results)} 个结果"
        if self._skipped_count:
            text += f"（跳过{self._skipped_count}个平台）"
        self._set_status(text, "#16a34a")
        self.search_worker = None

    def _on_search_error(self, error_msg):
        self.btn_search.config(state="normal")
        self.btn_stop.config(state="disabled")
        self._set_status(f"出错: {error_msg}", "#dc2626")
        self.search_worker = None

    def stop_search(self):
        if self._multi_running:
            # 「停止」按钮在批量下载期间复用为取消
            self._multi_stop.set()
            self._set_status("正在停止下载...", "#d97706")
            return
        if self.search_worker and self.search_worker.is_running_thread():
            self._set_status("正在停止...", "#d97706")
            self.search_worker.stop()
            self.btn_stop.config(state="disabled")
            self._wait_worker_exit()

    def _wait_worker_exit(self, tries=0):
        """等旧线程真正退出再放行搜索按钮。

        requests 阻塞在 read 上，stop() 只是置标志位，线程可能还要几秒才返回；
        原先固定 after(1000) 后就把 worker 置 None，若线程仍活着，再点搜索会
        被 start_search 静默挡掉（用户点按钮没反应）。
        """
        worker = self.search_worker
        if worker is None:
            return
        if worker.is_running_thread() and tries < 60:      # 最多再等 18 秒
            self.frame.after(300, lambda: self._wait_worker_exit(tries + 1))
            return
        still_alive = worker.is_running_thread()
        self.search_worker = None
        self.btn_search.config(state="normal")
        self.btn_stop.config(state="disabled")
        suffix = "（仍有请求在收尾）" if still_alive else ""
        self._set_status(f"已停止，共 {len(self.search_results)} 个结果{suffix}", "#d97706")

    # ══════════════════════════════════════════════════════
    #  结果项操作
    # ══════════════════════════════════════════════════════

    def _require_selected(self):
        """取选中行对应的结果项；没选中就提示一次并返回 None。"""
        selection = self.result_tree.selection()
        item = self._by_iid.get(selection[0]) if selection else None
        if item is None:
            messagebox.showinfo("提示", "请先在列表里选择一个结果")
        return item

    def _reset_results(self):
        """清空结果列表（三件套 + iid 映射，少清一处就会残留旧映射）。"""
        children = self.result_tree.get_children()
        if children:
            self.result_tree.delete(*children)
        self.search_results = []
        self._by_iid = {}
        self._next_iid = 0
        self._checked = set()
        self.result_count = 0
        self._skipped_count = 0
        self._view_mode = "search"

    def clear_results(self):
        self._reset_results()
        self._set_status("已清空结果", "#666")

    def _open_selected(self):
        item = self._require_selected()
        if not item:
            return
        url = item.get("url", "")
        if not url:
            messagebox.showinfo("提示", "该条目没有链接")
            return
        webbrowser.open(url)
        self._set_status(f"正在打开: {item.get('title', '')[:20]}...", "#16a34a")

    def _copy_link(self):
        item = self._require_selected()
        if not item:
            return
        url = item.get("url", "")
        if not url:
            messagebox.showinfo("提示", "该条目没有链接")
            return
        self.frame.clipboard_clear()
        self.frame.clipboard_append(url)
        self._set_status(f"已复制链接: {item.get('title', '')[:20]}...", "#16a34a")

    # ══════════════════════════════════════════════════════
    #  下载
    # ══════════════════════════════════════════════════════

    def _download_selected(self):
        """下载：作用于**勾选**的行（1 条走单个流程，多条逐个下载）。

        没勾任何行时退回"当前选中行"，兼容原来的单选下载习惯。
        底部按钮和右键菜单共用这一个 handler。
        """
        if self._downloading or self._multi_running:
            # 只用按钮 state 挡不住右键二次触发
            self._set_status("正在下载中，请稍候", "#d97706")
            return
        if self.search_worker and self.search_worker.is_running_thread():
            self._set_status("正在搜索，等搜索结束再下载", "#d97706")
            return

        targets = self._checked_items_in_order()
        if not targets:
            # 没打勾就退回"当前选中行"（沿用原来的单选习惯），两者都没有才提示
            selection = self.result_tree.selection()
            item = self._by_iid.get(selection[0]) if selection else None
            if item is None:
                messagebox.showinfo(
                    "提示", "请先勾选要下载的试卷（点每行最左边的方框）\n"
                            "勾选多条后点下载，会依次下载；需要网页的会一起打开")
                return
            targets = [item]

        if len(targets) == 1:
            self._start_single_download(targets[0])
        else:
            self._start_multi_download(targets)

    def _start_single_download(self, item):
        url = item.get("url", "")
        if not url:
            messagebox.showinfo("提示", "该条目没有链接")
            return

        platform_key = PLATFORMS.get(item.get("platform", ""), "")
        if zhenti_core.platform_download_kind(platform_key) == "none":
            answer = messagebox.askyesno(
                "该平台不提供直链",
                f"{item.get('platform', '该平台')}的试卷只能在网页里查看/手动保存，\n"
                "程序拿不到直链文件。\n\n要打开试卷页面吗？")
            if answer:
                webbrowser.open(url)
                self._set_status("已打开网页（无直链可下）", "#d97706")
            else:
                self._set_status("该平台无直链可下", "#d97706")
            return

        self._downloading = True
        self.btn_download.config(state="disabled")
        self._set_status("正在获取下载链接...", "#2563eb")

        # 下载线程只往队列里塞消息，界面更新一律在主线程的 _poll_download 里做。
        # 从子线程直接调 frame.after() 是不可靠的（主循环没起来时会直接抛
        # RuntimeError: main thread is not in main loop，下载成功了界面也不知道）。
        self._dl_queue = queue.Queue()

        def worker():
            try:
                scraper = zhenti_core._get_scraper()
                info = scraper.get_download_info(url)
                if info["type"] == "direct":
                    result = scraper.download_file(
                        info["url"], ZHENTI_DOWNLOAD_DIR,
                        referer=info.get("referer") or url,
                        progress_callback=lambda msg: self._dl_queue.put(("progress", msg)))
                    self._dl_queue.put(("result", result))
                elif info["type"] == "page":
                    self._dl_queue.put(("page", (url, info.get("message", ""))))
                else:
                    self._dl_queue.put(("no_link", (url, info.get("message", ""))))
            except Exception as e:
                self._dl_queue.put(("result", {"success": False, "filepath": "",
                                               "message": str(e)}))

        threading.Thread(target=worker, daemon=True).start()
        self._poll_download()

    def _poll_download(self):
        while True:
            try:
                kind, data = self._dl_queue.get_nowait()
            except queue.Empty:
                break
            if kind == "progress":
                self._set_status(data, "#2563eb")
            elif kind == "result":
                self._on_download_complete(data)
            elif kind == "page":
                self._on_download_page(*data)
            elif kind == "no_link":
                self._on_download_no_link(*data)
        if self._downloading:
            self.frame.after(100, self._poll_download)

    def _finish_download(self):
        self._downloading = False
        self.btn_download.config(state="normal")

    def _on_download_complete(self, result):
        self._finish_download()
        if result.get("success"):
            filepath = result.get("filepath", "")
            self._set_status(f"下载成功: {os.path.basename(filepath)}", "#16a34a")
            self._show_dialog("下载成功", f"文件已保存到:\n{filepath}", tone="ok")
        else:
            message = result.get("message", "未知错误")
            self._set_status(f"下载失败: {message}", "#dc2626")
            self._show_dialog("下载失败", message, tone="warn")

    @staticmethod
    def _done_body(total, ok, fail, pages, stopped=False, fail_lines=None):
        """下载/打开页面的结果文案。

        单条「需要提取码」与批量下载共用这一份措辞，避免两处说法不一致：
        第一行固定是「页面已打开！」（只有真的打开了网页才写），
        第二行是条数汇总，之后才是失败明细。
        """
        lines = []
        if pages:
            lines.append("页面已打开！")
        lines.append(f"共处理 {total} 份：下载成功 {ok}，失败 {fail}，"
                     f"打开网页 {pages}。")
        if stopped:
            lines.append("（已手动停止，未处理的试卷不再继续。）")
        lines.extend(fail_lines or [])
        return "\n".join(lines)

    def _on_download_page(self, page_url, message):
        """网盘/提取码类站点：打开试卷详情页，让用户在页面里扫码拿码、自己下载。"""
        self._finish_download()
        webbrowser.open(page_url)
        self._set_status("已打开试卷页面", "#16a34a")
        # 与批量下载同款文案：页面已经替用户打开了，不必再把链接贴一遍
        self._show_dialog("下载完成", self._done_body(1, 0, 0, 1), tone="ok")

    def _on_download_no_link(self, page_url, message):
        self._finish_download()
        self._set_status("没有找到直链", "#d97706")
        # 不再谎称"页面里可以下载"——找不到就是找不到，只问要不要去看一眼
        if messagebox.askyesno("提示", f"{message or '页面里没有找到可用的下载链接'}\n\n要打开试卷页面吗？"):
            webbrowser.open(page_url)

    # ══════════════════════════════════════════════════════
    #  多选下载（勾选多条时）
    # ══════════════════════════════════════════════════════

    def _start_multi_download(self, items):
        self._multi_running = True
        self._multi_stop = threading.Event()
        self._multi_queue = queue.Queue()
        self._multi_results = []
        self.btn_download.config(state="disabled")
        self.btn_stop.config(state="normal")
        self._set_status(f"下载 0/{len(items)}...", "#2563eb")

        # 与单个下载同样的原则：子线程只往队列塞消息，界面全在主线程刷新
        threading.Thread(target=self._multi_worker, args=(items,),
                         daemon=True).start()
        self._poll_multi()

    def _multi_worker(self, items):
        results, pages = [], []
        total = len(items)
        for idx, item in enumerate(items, 1):
            if self._multi_stop.is_set():
                break
            title = item.get("title", "")
            url = item.get("url", "")
            self._multi_queue.put(
                ("progress", f"下载 {idx}/{total}: {title[:18]}…"))
            entry = {"title": title, "ok": False, "msg": "", "page": False}
            try:
                key = PLATFORMS.get(item.get("platform", ""), "")
                if zhenti_core.platform_download_kind(key) == "none":
                    # 无直链平台：不浪费请求，直接记成"稍后打开网页"
                    entry["page"] = True
                    entry["msg"] = "平台无直链，打开网页"
                    pages.append(url)
                else:
                    scraper = zhenti_core._get_scraper()
                    info = scraper.get_download_info(url)
                    if info["type"] == "direct":
                        r = scraper.download_file(
                            info["url"], ZHENTI_DOWNLOAD_DIR,
                            referer=info.get("referer") or url,
                            stop_event=self._multi_stop)
                        if self._multi_stop.is_set():
                            break
                        entry["ok"] = bool(r.get("success"))
                        entry["path"] = r.get("filepath", "")
                        entry["msg"] = r.get("message", "")
                    else:
                        # 网盘/需提取码：勾了多条就一起打开，用户自己页内下载
                        entry["page"] = True
                        entry["msg"] = "需提取码，打开试卷页面"
                        pages.append(url)
            except Exception as e:
                entry["msg"] = str(e)
            results.append(entry)
            self._multi_queue.put(("item", entry))
        self._multi_queue.put(("done", {"results": results, "pages": pages,
                                        "stopped": self._multi_stop.is_set()}))

    def _poll_multi(self):
        while True:
            try:
                kind, data = self._multi_queue.get_nowait()
            except queue.Empty:
                break
            if kind == "progress":
                self._set_status(data, "#2563eb")
            elif kind == "item":
                self._multi_results.append(data)
                ok = sum(1 for r in self._multi_results if r["ok"])
                self._set_status(
                    f"已处理 {len(self._multi_results)}（成功 {ok}）", "#2563eb")
            elif kind == "done":
                self._on_multi_done(data)
                return
        if self._multi_running:
            self.frame.after(100, self._poll_multi)

    def _on_multi_done(self, summary):
        self._multi_running = False
        self.btn_download.config(state="normal")
        if not (self.search_worker and self.search_worker.is_running_thread()):
            self.btn_stop.config(state="disabled")

        results = summary["results"]
        pages = summary["pages"]
        ok = [r for r in results if r["ok"]]
        fail = [r for r in results if not r["ok"] and not r["page"]]

        # 需要网页的：勾了几条就同时打开几条（用户明确要求）
        opened = 0
        for url in pages:
            if url and webbrowser.open(url):
                opened += 1
            elif url:
                opened += 1        # open() 返回 False 也多半已交给系统浏览器，按已打开计

        fail_lines = []
        for r in fail[:8]:
            fail_lines.append(f"✗ {r['title'][:24]}：{r['msg'][:30]}")
        if len(fail) > 8:
            fail_lines.append(f"…… 其余 {len(fail) - 8} 个失败原因类似")

        body = self._done_body(len(results), len(ok), len(fail), len(pages),
                               stopped=summary["stopped"], fail_lines=fail_lines)

        if not fail and not pages:
            color = "#16a34a"
        elif fail:
            color = "#d97706"
        else:
            color = "#16a34a"
        self._set_status(
            f"完成：下载{len(ok)} 失败{len(fail)} 开网页{len(pages)}"
            + ("（已停止）" if summary["stopped"] else ""), color)

        if fail:
            self._show_dialog("下载完成", body, tone="warn")
        else:
            self._show_dialog("下载完成", body, tone="ok")

    # ══════════════════════════════════════════════════════
    #  收藏夹
    # ══════════════════════════════════════════════════════

    def _add_favorite(self):
        """收藏选中的这条。判重用 URL（同名试卷很常见，按标题判会误判）。"""
        item = self._require_selected()
        if not item:
            return
        url = item.get("url", "")
        if any(fav.get("url") == url for fav in self.favorites):
            messagebox.showinfo("提示", "该试卷已在收藏夹中")
            return
        self.favorites.append(item)
        self._save_json(FAVORITES_FILE, self.favorites)
        self._set_status(f"已收藏: {item.get('title', '')[:20]}...", "#16a34a")

    def _remove_favorite(self):
        """取消收藏。当前正在看收藏夹的话顺手把列表刷一遍。"""
        item = self._require_selected()
        if not item:
            return
        url = item.get("url", "")
        kept = [fav for fav in self.favorites if fav.get("url") != url]
        if len(kept) == len(self.favorites):
            messagebox.showinfo("提示", "这条不在收藏夹里")
            return
        self.favorites = kept
        self._save_json(FAVORITES_FILE, self.favorites)
        self._set_status(f"已取消收藏: {item.get('title', '')[:20]}...", "#d97706")
        if self._view_mode == "favorites":
            self._show_favorites()

    def _show_favorites(self):
        """把收藏夹填进结果列表，并把视图切成 favorites。"""
        if not self.favorites:
            messagebox.showinfo("收藏夹", "收藏夹为空")
            return
        self._reset_results()                        # 它内部会把 _view_mode 摆回 search
        self._view_mode = "favorites"
        for fav in self.favorites:
            self._add_result(fav)
        self._set_status(f"收藏夹: 共 {len(self.favorites)} 个", "#2563eb")


class SearchWorker:
    """搜索工作线程。

    线程只往队列里塞四种消息（result / progress / finished / error），
    界面更新一律交给主线程的 _poll_queue —— 子线程直接碰 Tk 控件，
    轻则不刷新、重则整个 GUI 卡死。
    """

    def __init__(self, queue_ref, platforms, subjects, grade, keyword, year=""):
        self._queue = queue_ref
        self.platforms = platforms
        self.subjects = subjects
        self.grade = grade
        self.keyword = keyword
        self.year = year or ""
        self.stop_event = threading.Event()
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        try:
            def result_callback(item):
                if not self.stop_event.is_set():
                    self._queue.put(("result", item))

            def progress_callback(msg):
                if not self.stop_event.is_set():
                    self._queue.put(("progress", msg))

            all_results = []
            for platform in self.platforms:
                if self.stop_event.is_set():
                    break
                for subject in self.subjects:
                    if self.stop_event.is_set():
                        break
                    all_results.extend(zhenti_core.search_papers(
                        platform, subject or "", self.grade, self.year,
                        self.keyword,
                        result_callback=result_callback,
                        stop_event=self.stop_event,
                        progress_callback=progress_callback))
            if not self.stop_event.is_set():
                self._queue.put(("finished", all_results))
        except Exception as e:
            if not self.stop_event.is_set():
                self._queue.put(("error", str(e)))

    def stop(self):
        self.stop_event.set()

    def is_running_thread(self):
        return self.thread is not None and self.thread.is_alive()

    def wait(self, timeout=None):
        if self.thread:
            self.thread.join(timeout=timeout)
