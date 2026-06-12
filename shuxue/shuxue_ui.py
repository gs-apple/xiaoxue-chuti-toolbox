# shuxue_ui.py — 数学标签页 (tkinter 版，保留原版布局)
import re
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from widgets import GradientButton
import queue

from shuxue.shuxue_core import generate_questions, generate_quick_questions, compute_answers, export_pdf

BG = "#f0f0f0"
FRAC_RE = re.compile(r'FRAC\[(\d+),(\d+)\]')


def _frac_to_text(s):
    return FRAC_RE.sub(lambda m: f"{m.group(1)}/{m.group(2)}", s)


class ShuxueTabWidget:
    # display text → generator map key
    _ATTR_MAP = {
        "10以内": "cb_10in", "20以内": "cb_20in", "100以内": "cb_100in",
        "万以内": "cb_10000in", "小数加减": "cb_dec_addsub", "分数加减": "cb_frac_addsub",
        "表内乘法": "cb_mul_table", "两位×一位": "cb_mul_2x1", "三位×一位": "cb_mul_3x1",
        "两位×两位": "cb_mul_2x2", "三位×两位": "cb_mul_3x2",
        "小数乘法": "cb_mul_dec", "分数乘法": "cb_mul_frac", "乘法简便运算": "cb_mul_simple",
        "表内除法": "cb_div_table", "带余数除法": "cb_div_remain", "整除": "cb_div_int",
        "除数是一位数": "cb_div_1digit", "除数是两位数": "cb_div_2digit",
        "小数除法": "cb_div_dec", "分数除法": "cb_div_frac",
        "连加连减": "cb_mix_addsub", "加减乘": "cb_mix_addmul",
        "加减乘除": "cb_mix_addmulsub", "小数混合": "cb_mix_dec", "分数混合": "cb_mix_frac",
        "找规律填数": "cb_find_rule", "等差数列": "cb_arithmetic", "简便运算": "cb_simple_calc",
        "分数运用": "cb_frac_skill", "比例应用": "cb_new_op",
        "和差倍": "cb_sum_diff", "年龄问题": "cb_age", "植树问题": "cb_tree",
        "鸡兔同笼": "cb_chicken_rabbit", "盈亏问题": "cb_duck",
        "工程问题": "cb_project", "行程问题": "cb_form", "浓度问题": "cb_concentration",
        "图形计数": "cb_graph_count", "图形分割": "cb_graph_split",
        "周长面积": "cb_perimeter", "立体图形": "cb_3d_graph", "等积变形": "cb_equal_area",
        "奇偶分析": "cb_odd_even", "整除问题": "cb_whole_div", "余数问题": "cb_remainder",
        "质/合问题": "cb_prime", "公约数/倍数": "cb_gcd_lcm",
        "推理问题": "cb_logic", "统筹问题": "cb_arrange", "最优化": "cb_best",
        "抽屉问题": "cb_draw", "容斥问题": "cb_container",
        "分配问题": "cb_assign", "测量计算": "cb_measure",
    }

    def __init__(self, parent):
        self.frame = tk.Frame(parent, bg=BG)
        self._questions_data = None
        self._is_onekey = False
        self._gen_thread = None
        self._queue = queue.Queue()
        self._checkboxes = []
        self._init_math_tab()

    def _init_math_tab(self):
        math_layout = tk.Frame(self.frame, bg=BG)
        math_layout.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # --- 计算题主区域：2列2行网格 ---
        calc_grid = tk.Frame(math_layout, bg=BG)
        calc_grid.pack(fill=tk.X)
        for c in range(4):
            calc_grid.columnconfigure(c, weight=1)

        # 1. 加减法
        addsub = ttk.LabelFrame(calc_grid, text="加减法")
        addsub.grid(row=0, column=0, padx=1, pady=0, sticky="nsew")
        self.cb_10in = self._cb_spin(addsub, "10以内")
        self.cb_20in = self._cb_spin(addsub, "20以内")
        self.cb_100in = self._cb_spin(addsub, "100以内")
        self.cb_10000in = self._cb_spin(addsub, "万以内")
        self.cb_dec_addsub = self._cb_spin(addsub, "小数加减")
        self.cb_frac_addsub = self._cb_spin(addsub, "分数加减")

        # 2. 乘法
        mul = ttk.LabelFrame(calc_grid, text="乘法")
        mul.grid(row=0, column=1, rowspan=2, padx=1, pady=0, sticky="nsew")
        self.cb_mul_table = self._cb_spin(mul, "表内乘法")
        self.cb_mul_2x1 = self._cb_spin(mul, "两位×一位")
        self.cb_mul_3x1 = self._cb_spin(mul, "三位×一位")
        self.cb_mul_2x2 = self._cb_spin(mul, "两位×两位")
        self.cb_mul_3x2 = self._cb_spin(mul, "三位×两位")
        self.cb_mul_dec = self._cb_spin(mul, "小数乘法")
        self.cb_mul_frac = self._cb_spin(mul, "分数乘法")
        self.cb_mul_simple = self._cb_spin(mul, "乘法简便运算")

        # 3. 除法
        div = ttk.LabelFrame(calc_grid, text="除法")
        div.grid(row=0, column=2, rowspan=2, padx=1, pady=0, sticky="nsew")
        self.cb_div_table = self._cb_spin(div, "表内除法")
        self.cb_div_remain = self._cb_spin(div, "带余数除法")
        self.cb_div_int = self._cb_spin(div, "整除")
        self.cb_div_1digit = self._cb_spin(div, "除数是一位数")
        self.cb_div_2digit = self._cb_spin(div, "除数是两位数")
        self.cb_div_dec = self._cb_spin(div, "小数除法")
        self.cb_div_frac = self._cb_spin(div, "分数除法")

        # 4. 四则混合
        mix = ttk.LabelFrame(calc_grid, text="四则混合")
        mix.grid(row=0, column=3, padx=1, pady=0, sticky="nsew")
        self.cb_mix_addsub = self._cb_spin(mix, "连加连减")
        self.cb_mix_addmul = self._cb_spin(mix, "加减乘")
        self.cb_mix_addmulsub = self._cb_spin(mix, "加减乘除")
        self.cb_mix_dec = self._cb_spin(mix, "小数混合")
        self.cb_mix_frac = self._cb_spin(mix, "分数混合")

        # 5. 快速出题
        quick = ttk.LabelFrame(calc_grid, text="快速出题")
        quick.grid(row=1, column=0, padx=1, pady=0, sticky="nsew")
        qrow = tk.Frame(quick, bg=BG)
        qrow.pack(fill=tk.X, padx=2, pady=1)
        self.grade_combo = ttk.Combobox(qrow, width=7, state="readonly",
                                        values=["一年级", "二年级", "三年级",
                                                "四年级", "五年级", "六年级"])
        self.grade_combo.current(0)
        self.grade_combo.pack(side=tk.LEFT)
        self.quick_count_edit = tk.Entry(qrow, width=5, justify="center")
        self.quick_count_edit.insert(0, "30")
        self.quick_count_edit.pack(side=tk.LEFT, padx=4)
        self.btn_onekey = tk.Button(quick, text="一键出题", width=12,
                                    command=self.do_onekey)
        self.btn_onekey.pack(pady=2)

        # 6. 附加
        addf = ttk.LabelFrame(calc_grid, text="附加")
        addf.grid(row=1, column=3, padx=1, pady=0, sticky="nsew")
        self._bracket_var = tk.IntVar()
        self._vertical_var = tk.IntVar()
        self._answer_var = tk.IntVar(value=1)
        b1 = tk.Frame(addf, bg=BG)
        b1.pack(fill=tk.X, padx=2, pady=1)
        tk.Checkbutton(b1, text="带括号", variable=self._bracket_var).pack(side=tk.LEFT)
        tk.Checkbutton(b1, text="竖式", variable=self._vertical_var).pack(side=tk.RIGHT)
        tk.Checkbutton(addf, text="包含答案", variable=self._answer_var).pack(anchor="w", padx=2)

        # --- 提升题 ---
        adv_frame = ttk.LabelFrame(math_layout, text="提升题")
        adv_frame.pack(fill=tk.X, pady=(1, 0))
        adv_grid = tk.Frame(adv_frame, bg=BG)
        adv_grid.pack(fill=tk.X, padx=1, pady=0)
        for c in range(5):
            adv_grid.columnconfigure(c, weight=1)

        calc_adv = ttk.LabelFrame(adv_grid, text="计算类")
        calc_adv.grid(row=0, column=0, padx=1, pady=0, sticky="nsew")
        self.cb_find_rule = self._cb_spin(calc_adv, "找规律填数")
        self.cb_arithmetic = self._cb_spin(calc_adv, "等差数列")
        self.cb_simple_calc = self._cb_spin(calc_adv, "简便运算")
        self.cb_frac_skill = self._cb_spin(calc_adv, "分数运用")
        self.cb_new_op = self._cb_spin(calc_adv, "比例应用")

        app = ttk.LabelFrame(adv_grid, text="应用类")
        app.grid(row=0, column=1, padx=1, pady=0, sticky="nsew")
        self.cb_sum_diff = self._cb_spin(app, "和差倍")
        self.cb_age = self._cb_spin(app, "年龄问题")
        self.cb_tree = self._cb_spin(app, "植树问题")
        self.cb_chicken_rabbit = self._cb_spin(app, "鸡兔同笼")
        self.cb_duck = self._cb_spin(app, "盈亏问题")
        self.cb_project = self._cb_spin(app, "工程问题")
        self.cb_form = self._cb_spin(app, "行程问题")
        self.cb_concentration = self._cb_spin(app, "浓度问题")
        self.cb_assign = self._cb_spin(app, "分配问题")
        self.cb_measure = self._cb_spin(app, "测量计算")

        geo = ttk.LabelFrame(adv_grid, text="几何类")
        geo.grid(row=0, column=2, padx=1, pady=0, sticky="nsew")
        self.cb_graph_count = self._cb_spin(geo, "图形计数")
        self.cb_graph_split = self._cb_spin(geo, "图形分割")
        self.cb_perimeter = self._cb_spin(geo, "周长面积")
        self.cb_3d_graph = self._cb_spin(geo, "立体图形")
        self.cb_equal_area = self._cb_spin(geo, "等积变形")

        num = ttk.LabelFrame(adv_grid, text="数论类")
        num.grid(row=0, column=3, padx=1, pady=0, sticky="nsew")
        self.cb_odd_even = self._cb_spin(num, "奇偶分析")
        self.cb_whole_div = self._cb_spin(num, "整除问题")
        self.cb_remainder = self._cb_spin(num, "余数问题")
        self.cb_prime = self._cb_spin(num, "质/合问题")
        self.cb_gcd_lcm = self._cb_spin(num, "公约数/倍数")

        logic = ttk.LabelFrame(adv_grid, text="逻辑类")
        logic.grid(row=0, column=4, padx=1, pady=0, sticky="nsew")
        self.cb_logic = self._cb_spin(logic, "推理问题")
        self.cb_arrange = self._cb_spin(logic, "统筹问题")
        self.cb_best = self._cb_spin(logic, "最优化")
        self.cb_draw = self._cb_spin(logic, "抽屉问题")
        self.cb_container = self._cb_spin(logic, "容斥问题")

        # --- 功能区 (先 pack，放底部) ---
        func_group = ttk.LabelFrame(math_layout, text="功能区")
        func_group.pack(side=tk.BOTTOM, fill=tk.X, pady=(1, 0))
        func_inner = tk.Frame(func_group, bg=BG)
        func_inner.pack(padx=5, pady=3)
        self.btn_clear_preview = GradientButton(func_inner, text="清空预览", width=100, height=32,
                                                 command=lambda: self.preview_text.delete("1.0", tk.END))
        self.btn_generate = GradientButton(func_inner, text="生成题目", width=100, height=32,
                                            command=self.do_generate)
        self.btn_export_pdf = GradientButton(func_inner, text="导出PDF", width=100, height=32,
                                              command=self.do_export_pdf)
        self.btn_clear_all = GradientButton(func_inner, text="全部清空", width=100, height=32,
                                             command=self.clear_all_checks)
        # centering: spacer col 0 + 5 with weight, buttons in 1-4
        func_inner.columnconfigure(0, weight=1)
        func_inner.columnconfigure(5, weight=1)
        for i, btn in enumerate([self.btn_clear_preview, self.btn_generate,
                                  self.btn_export_pdf, self.btn_clear_all], 1):
            btn.grid(row=0, column=i, padx=3)

        # --- 预览 ---
        preview = ttk.LabelFrame(math_layout, text="题目预览")
        preview.pack(fill=tk.BOTH, expand=True, pady=(1, 0))
        self.preview_text = tk.Text(preview, bg="white", height=13, wrap=tk.WORD)
        sb = ttk.Scrollbar(preview, command=self.preview_text.yview)
        self.preview_text.config(yscrollcommand=sb.set)
        self.preview_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

    def _cb_spin(self, parent, text):
        f = tk.Frame(parent, bg=BG)
        f.pack(fill=tk.X, padx=0, pady=0)
        var = tk.IntVar()
        cb = tk.Checkbutton(f, text=text, variable=var, anchor="w",
                             pady=0, highlightthickness=0, borderwidth=0)
        cb.pack(side=tk.LEFT)
        e = tk.Entry(f, width=4, justify="center", highlightthickness=0)
        e.insert(0, "20")
        e.pack(side=tk.RIGHT)
        attr = self._ATTR_MAP.get(text, text)
        self._checkboxes.append((var, e, attr))
        return f

    def clear_all_checks(self):
        for var, entry, _ in self._checkboxes:
            var.set(0)
            entry.delete(0, tk.END)
            entry.insert(0, "20")
        self.preview_text.delete("1.0", tk.END)
        self._questions_data = None

    def _get_selections(self):
        selections = {}
        for var, entry, attr in self._checkboxes:
            if var.get():
                try:
                    count = int(entry.get())
                    count = max(1, min(count, 10000))
                except (ValueError, TypeError):
                    count = 20
                selections[attr] = count
        return selections

    def do_generate(self):
        self._is_onekey = False
        selections = self._get_selections()
        if not selections:
            self.preview_text.delete("1.0", tk.END)
            self.preview_text.insert("1.0", "请先勾选题型！")
            return
        use_bracket = self._bracket_var.get()
        grade = self.grade_combo.current() + 1

        self.btn_generate.config(state="disabled", text="生成中...")
        self._gen_thread = threading.Thread(
            target=self._run_generate,
            args=(generate_questions, selections, use_bracket, grade),
            daemon=True
        )
        self._gen_thread.start()
        self._poll_queue()

    def do_onekey(self):
        self._is_onekey = True
        grade = self.grade_combo.get()
        try:
            count = int(self.quick_count_edit.get())
            count = max(1, min(count, 10000))
        except (ValueError, TypeError):
            count = 30

        self.btn_onekey.config(state="disabled", text="生成中...")
        self._gen_thread = threading.Thread(
            target=self._run_generate,
            args=(generate_quick_questions, grade, count),
            daemon=True
        )
        self._gen_thread.start()
        self._poll_queue()

    def _run_generate(self, func, *args):
        try:
            result = func(*args)
            self._queue.put(("ok", result))
        except Exception as e:
            self._queue.put(("error", str(e)))

    def _poll_queue(self):
        try:
            status, data = self._queue.get_nowait()
            if status == "ok":
                self._questions_data = data
                self._show_preview()
            else:
                messagebox.showwarning("出题失败", f"生成题目时出错：{data}")
            self.btn_generate.config(state="normal", text="生成题目")
            self.btn_onekey.config(state="normal", text="一键出题")
            return
        except queue.Empty:
            pass
        self.frame.after(50, self._poll_queue)

    def _show_preview(self):
        if not self._questions_data:
            return
        basic_qs = self._questions_data.get("basic", [])
        advance_qs = self._questions_data.get("advance", [])
        total_count = len(basic_qs) + len(advance_qs)

        lines = [f"日期：______年_____月_____日         出题总量：{total_count} 题", ""]

        if basic_qs:
            lines.append("【基础题】")
            # 每行4题，与PDF导出格式一致
            col_width = 22
            for row_start in range(0, len(basic_qs), 4):
                row_items = basic_qs[row_start:row_start + 4]
                row_parts = []
                for local_idx, item in enumerate(row_items):
                    global_idx = row_start + local_idx + 1
                    q = item[1] if len(item) >= 2 else item[0]
                    cell = f"{global_idx:3d}. {_frac_to_text(q)}"
                    row_parts.append(cell.ljust(col_width))
                lines.append("".join(row_parts))
            lines.append("")

        if advance_qs:
            lines.append("【提升题】")
            offset = len(basic_qs)
            for idx, item in enumerate(advance_qs, offset + 1):
                q = item[1] if len(item) >= 2 else item[0]
                lines.append(f"{idx:3d}. {_frac_to_text(q)}")
            lines.append("")

        if self._answer_var.get():
            lines.append("【参考答案】")
            answers = compute_answers(self._questions_data)
            for i, (_, _, ans) in enumerate(answers, 1):
                if isinstance(ans, tuple):
                    ans_str = f"{ans[0]}余{ans[1]}"
                elif isinstance(ans, float):
                    ans_str = f"{ans:g}"
                else:
                    ans_str = _frac_to_text(str(ans))
                lines.append(f"{i:3d}. {ans_str}")

        self.preview_text.delete("1.0", tk.END)
        self.preview_text.insert("1.0", "\n".join(lines))

    def do_export_pdf(self):
        if not self._questions_data:
            self.preview_text.delete("1.0", tk.END)
            self.preview_text.insert("1.0", "请先生成题目！")
            return
        try:
            use_vertical = self._vertical_var.get()
            use_answer = self._answer_var.get()
            use_bracket = self._bracket_var.get()
            mode = "onekey" if self._is_onekey else "export"
            grade = self.grade_combo.get() if self._is_onekey else ""
            filepath = export_pdf(self._questions_data, use_vertical, use_answer,
                                  show_titles=self._is_onekey, mode=mode, grade=grade, use_bracket=use_bracket)
            messagebox.showinfo("导出成功", "导出成功")
        except Exception as e:
            messagebox.showerror("导出失败", f"导出失败：{e}")
