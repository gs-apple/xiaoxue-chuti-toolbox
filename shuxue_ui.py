# shuxue_ui.py（数学标签页UI - 预览改为纯文本，彻底解决卡死）
import re
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QGroupBox, QCheckBox, QComboBox,
                             QPushButton, QTextEdit, QMessageBox, QLineEdit)
from PyQt5.QtCore import QSize, QThread, pyqtSignal, Qt

# 本地定义 FRAC_RE，避免从 shuxue_core 导入失败
FRAC_RE = re.compile(r'FRAC\[(\d+),(\d+)\]')

def _frac_to_html(numerator, denominator):
    """
    将分数转为小学课本标准上下格式（HTML）：
    分子在上，水平分数线在中间，分母在下
    （本函数仅在 PDF 导出时使用，预览中不再使用）
    """
    return (
        f'<span style="display:inline-flex;flex-direction:column;align-items:center;'
        f'vertical-align:middle;margin:0 1px;line-height:1.1;">'
        f'<span style="font-size:0.7em;border-bottom:1px solid currentColor;padding:0 2px 1px;">'
        f'{numerator}</span>'
        f'<span style="font-size:0.7em;padding:1px 2px 0;">{denominator}</span>'
        f'</span>'
    )

from shuxue_core import generate_questions, generate_quick_questions, compute_answers, ADVANCE_TYPES

def _frac_to_text(s):
    """FRAC[n,d] → n/d 文本"""
    return FRAC_RE.sub(lambda m: f"{m.group(1)}/{m.group(2)}", s)

# 以下两个函数仅用于 PDF 导出，预览不再使用
def _convert_fractions(text):
    """仅将 FRAC[n,d] 标记转为 HTML 上下格式，避免复杂正则回溯"""
    def _replace_frac(m):
        return _frac_to_html(m.group(1), m.group(2))
    text = FRAC_RE.sub(_replace_frac, text)
    return text


class _GenThread(QThread):
    """题目生成线程——完成后自动释放"""
    finished = pyqtSignal(object)

    def __init__(self, func, *args):
        super().__init__()
        self._func = func
        self._args = args

    def run(self):
        try:
            result = self._func(*self._args)
            self.finished.emit(result)
        except Exception as e:
            self.finished.emit({"_error": str(e)})


class ShuxueTabWidget(QWidget):
    """数学标签页"""

    def __init__(self):
        super().__init__()
        self._gen_thread = None  # 当前生成线程（保持引用，防止GC）
        self._questions_data = None
        self._init_math_tab()

    def _init_math_tab(self):
        """数学标签页初始化"""
        math_layout = QVBoxLayout(self)
        math_layout.setContentsMargins(3, 3, 3, 3)
        math_layout.setSpacing(5)

        # --- 计算题主区域：2列2行网格布局，4列等宽 ---#
        calc_grid = QGridLayout()
        calc_grid.setContentsMargins(0, 0, 0, 0)
        calc_grid.setSpacing(3)
        calc_grid.setColumnStretch(0, 1)
        calc_grid.setColumnStretch(1, 1)
        calc_grid.setColumnStretch(2, 1)
        calc_grid.setColumnStretch(3, 1)
        calc_grid.setRowStretch(0, 1)
        calc_grid.setRowStretch(1, 0)

        # 1. 加减法分组栏（左列上）
        addsub_group = QGroupBox("加减法")
        addsub_group.setStyleSheet("QGroupBox { font-size: 15px; font-family: '楷体', 'KaiTi'; }")
        addsub_group.setFixedSize(QSize(145, 138))
        addsub_layout = QVBoxLayout(addsub_group)
        addsub_layout.setContentsMargins(3, 3, 3, 3)
        addsub_layout.setSpacing(2)
        self.cb_10in = self._create_cb_spin("10以内", 20)
        self.cb_20in = self._create_cb_spin("20以内", 20)
        self.cb_100in = self._create_cb_spin("100以内", 20)
        self.cb_10000in = self._create_cb_spin("万以内", 20)
        self.cb_dec_addsub = self._create_cb_spin("小数加减", 20)
        self.cb_frac_addsub = self._create_cb_spin("分数加减", 20)
        for cb in [self.cb_10in, self.cb_20in, self.cb_100in, self.cb_10000in, self.cb_dec_addsub, self.cb_frac_addsub]:
            addsub_layout.addWidget(cb)
        calc_grid.addWidget(addsub_group, 0, 0)

        # 2. 乘法分组栏（中左列，跨两行）
        mul_group = QGroupBox("乘法")
        mul_group.setStyleSheet("QGroupBox { font-size: 15px; font-family: '楷体', 'KaiTi'; }")
        mul_group.setFixedSize(QSize(150, 215))
        mul_layout = QVBoxLayout(mul_group)
        mul_layout.setContentsMargins(3, 3, 3, 3)
        mul_layout.setSpacing(2)
        self.cb_mul_table = self._create_cb_spin("表内乘法", 20)
        self.cb_mul_2x1 = self._create_cb_spin("两位×一位", 20)
        self.cb_mul_3x1 = self._create_cb_spin("三位×一位", 20)
        self.cb_mul_2x2 = self._create_cb_spin("两位×两位", 20)
        self.cb_mul_3x2 = self._create_cb_spin("三位×两位", 20)
        self.cb_mul_dec = self._create_cb_spin("小数乘法", 20)
        self.cb_mul_frac = self._create_cb_spin("分数乘法", 20)
        self.cb_mul_simple = self._create_cb_spin("乘法简便运算", 20)
        for cb in [self.cb_mul_table, self.cb_mul_2x1, self.cb_mul_3x1, self.cb_mul_2x2, self.cb_mul_3x2, self.cb_mul_dec, self.cb_mul_frac, self.cb_mul_simple]:
            mul_layout.addWidget(cb)
        calc_grid.addWidget(mul_group, 0, 1, 2, 1)

        # 3. 除法分组栏（中右列，跨两行）
        div_group = QGroupBox("除法")
        div_group.setStyleSheet("QGroupBox { font-size: 15px; font-family: '楷体', 'KaiTi'; }")
        div_group.setFixedSize(QSize(150, 215))
        div_layout = QVBoxLayout(div_group)
        div_layout.setContentsMargins(3, 3, 3, 3)
        div_layout.setSpacing(2)
        self.cb_div_table = self._create_cb_spin("表内除法", 20)
        self.cb_div_remain = self._create_cb_spin("带余数除法", 20)
        self.cb_div_int = self._create_cb_spin("整除", 20)
        self.cb_div_1digit = self._create_cb_spin("除数是一位数", 20)
        self.cb_div_2digit = self._create_cb_spin("除数是两位数", 20)
        self.cb_div_dec = self._create_cb_spin("小数除法", 20)
        self.cb_div_frac = self._create_cb_spin("分数除法", 20)
        for cb in [self.cb_div_table, self.cb_div_remain, self.cb_div_int, self.cb_div_1digit, self.cb_div_2digit, self.cb_div_dec, self.cb_div_frac]:
            div_layout.addWidget(cb)
        calc_grid.addWidget(div_group, 0, 2, 2, 1)

        # 4. 四则混合分组栏（右列上）
        mix_group = QGroupBox("四则混合")
        mix_group.setStyleSheet("QGroupBox { font-size: 15px; font-family: '楷体', 'KaiTi'; }")
        mix_group.setFixedSize(QSize(145, 138))
        mix_layout = QVBoxLayout(mix_group)
        mix_layout.setContentsMargins(3, 3, 3, 3)
        mix_layout.setSpacing(2)
        self.cb_mix_addsub = self._create_cb_spin("连加连减", 20)
        self.cb_mix_addmul = self._create_cb_spin("加减乘", 20)
        self.cb_mix_addmulsub = self._create_cb_spin("加减乘除", 20)
        self.cb_mix_dec = self._create_cb_spin("小数混合", 20)
        self.cb_mix_frac = self._create_cb_spin("分数混合", 20)
        for cb in [self.cb_mix_addsub, self.cb_mix_addmul, self.cb_mix_addmulsub, self.cb_mix_dec, self.cb_mix_frac]:
            mix_layout.addWidget(cb)
        calc_grid.addWidget(mix_group, 0, 3)

        # 5. 快速出题分组栏（左列下，与加减法间距1px）
        quick_group = QGroupBox("快速出题")
        quick_group.setStyleSheet("QGroupBox { font-size: 15px; font-family: '楷体', 'KaiTi'; }")
        quick_group.setFixedSize(QSize(145, 76))
        quick_layout = QVBoxLayout(quick_group)
        quick_layout.setContentsMargins(3, 3, 3, 3)
        quick_layout.setSpacing(3)
        quick_row1 = QHBoxLayout()
        self.grade_combo = QComboBox()
        self.grade_combo.addItems(["一年级", "二年级", "三年级", "四年级", "五年级", "六年级"])
        quick_row1.addWidget(self.grade_combo)
        self.quick_count_edit = QLineEdit("30")
        self.quick_count_edit.setFixedWidth(55)
        self.quick_count_edit.setAlignment(Qt.AlignCenter)
        quick_row1.addWidget(self.quick_count_edit)
        quick_layout.addLayout(quick_row1)
        self.btn_onekey = QPushButton("一键出题")
        self.btn_onekey.setFixedSize(QSize(100, 32))
        self.btn_onekey.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                background-color: #4dabf7;
                color: white;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #339af0;
            }
            QPushButton:disabled {
                background-color: #adb5bd;
            }
        """)
        quick_layout.addWidget(self.btn_onekey)
        calc_grid.addWidget(quick_group, 1, 0)

        # 6. 附加分组栏（右列下，与四则混合间距1px）
        add_group = QGroupBox("附加")
        add_group.setStyleSheet("QGroupBox { font-size: 15px; font-family: '楷体', 'KaiTi'; }")
        add_group.setFixedSize(QSize(145, 76))
        add_layout = QVBoxLayout(add_group)
        add_layout.setContentsMargins(3, 3, 3, 3)
        add_layout.setSpacing(2)
        bracket_row = QHBoxLayout()
        bracket_row.setContentsMargins(0, 0, 0, 0)
        bracket_row.setSpacing(2)
        self.cb_bracket = QCheckBox("带括号")
        self.cb_vertical = QCheckBox("竖式")
        bracket_row.addWidget(self.cb_bracket)
        bracket_row.addStretch()
        bracket_row.addWidget(self.cb_vertical)
        add_layout.addLayout(bracket_row)
        self.cb_answer = QCheckBox("包含答案")
        self.cb_answer.setChecked(True)  # 默认勾选
        add_layout.addWidget(self.cb_answer)
        calc_grid.addWidget(add_group, 1, 3)

        math_layout.addLayout(calc_grid)

        # --- 提升题主区域（5个子分组，完全不变） ---#
        advance_main_group = QGroupBox("提升题")
        advance_main_group.setStyleSheet("QGroupBox { font-size: 15px; font-family: '楷体', 'KaiTi'; }")
        advance_main_layout = QHBoxLayout()
        advance_main_layout.setContentsMargins(3, 3, 3, 3)
        advance_main_layout.setSpacing(4)

        # 1. 计算类
        calc_adv_group = QGroupBox("计算类")
        calc_adv_group.setStyleSheet("QGroupBox { font-size: 15px; font-family: '楷体', 'KaiTi'; }")
        calc_adv_layout = QVBoxLayout(calc_adv_group)
        calc_adv_layout.setContentsMargins(3, 3, 3, 3)
        calc_adv_layout.setSpacing(2)
        self.cb_find_rule = self._create_cb_spin("找规律填数", 20)
        self.cb_arithmetic = self._create_cb_spin("等差数列", 20)
        self.cb_simple_calc = self._create_cb_spin("简便运算", 20)
        self.cb_frac_skill = self._create_cb_spin("分数巧算", 20)
        self.cb_new_op = self._create_cb_spin("定义新运算", 20)
        for cb in [self.cb_find_rule, self.cb_arithmetic, self.cb_simple_calc, self.cb_frac_skill, self.cb_new_op]:
            calc_adv_layout.addWidget(cb)
        advance_main_layout.addWidget(calc_adv_group)

        # 2. 应用类
        app_group = QGroupBox("应用类")
        app_group.setStyleSheet("QGroupBox { font-size: 15px; font-family: '楷体', 'KaiTi'; }")
        app_layout = QVBoxLayout(app_group)
        app_layout.setContentsMargins(3, 3, 3, 3)
        app_layout.setSpacing(2)
        self.cb_sum_diff = self._create_cb_spin("和差倍", 20)
        self.cb_age = self._create_cb_spin("年龄问题", 20)
        self.cb_tree = self._create_cb_spin("植树问题", 20)
        self.cb_chicken_rabbit = self._create_cb_spin("鸡兔同笼", 20)
        self.cb_duck = self._create_cb_spin("盈亏问题", 20)
        self.cb_project = self._create_cb_spin("工程问题", 20)
        self.cb_form = self._create_cb_spin("行程问题", 20)
        self.cb_concentration = self._create_cb_spin("浓度问题", 20)
        for cb in [self.cb_sum_diff, self.cb_age, self.cb_tree, self.cb_chicken_rabbit, self.cb_duck, self.cb_project, self.cb_form, self.cb_concentration]:
            app_layout.addWidget(cb)
        advance_main_layout.addWidget(app_group)

        # 3. 几何类
        geo_group = QGroupBox("几何类")
        geo_group.setStyleSheet("QGroupBox { font-size: 15px; font-family: '楷体', 'KaiTi'; }")
        geo_layout = QVBoxLayout(geo_group)
        geo_layout.setContentsMargins(3, 3, 3, 3)
        geo_layout.setSpacing(2)
        self.cb_graph_count = self._create_cb_spin("图形计数", 20)
        self.cb_graph_split = self._create_cb_spin("图形分割", 20)
        self.cb_perimeter = self._create_cb_spin("周长面积", 20)
        self.cb_3d_graph = self._create_cb_spin("立体图形", 20)
        self.cb_equal_area = self._create_cb_spin("等积变形", 20)
        for cb in [self.cb_graph_count, self.cb_graph_split, self.cb_perimeter, self.cb_3d_graph, self.cb_equal_area]:
            geo_layout.addWidget(cb)
        advance_main_layout.addWidget(geo_group)

        # 4. 数论类
        num_group = QGroupBox("数论类")
        num_group.setStyleSheet("QGroupBox { font-size: 15px; font-family: '楷体', 'KaiTi'; }")
        num_layout = QVBoxLayout(num_group)
        num_layout.setContentsMargins(3, 3, 3, 3)
        num_layout.setSpacing(2)
        self.cb_odd_even = self._create_cb_spin("奇偶分析", 20)
        self.cb_whole_div = self._create_cb_spin("整除问题", 20)
        self.cb_remainder = self._create_cb_spin("余数问题", 20)
        self.cb_prime = self._create_cb_spin("质/合问题", 20)
        self.cb_gcd_lcm = self._create_cb_spin("公约数/倍数", 20)
        for cb in [self.cb_odd_even, self.cb_whole_div, self.cb_remainder, self.cb_prime, self.cb_gcd_lcm]:
            num_layout.addWidget(cb)
        advance_main_layout.addWidget(num_group)

        # 5. 逻辑类
        logic_group = QGroupBox("逻辑类")
        logic_group.setStyleSheet("QGroupBox { font-size: 15px; font-family: '楷体', 'KaiTi'; }")
        logic_layout = QVBoxLayout(logic_group)
        logic_layout.setContentsMargins(3, 3, 3, 3)
        logic_layout.setSpacing(2)
        self.cb_logic = self._create_cb_spin("推理问题", 20)
        self.cb_arrange = self._create_cb_spin("统筹问题", 20)
        self.cb_best = self._create_cb_spin("最优化", 20)
        self.cb_draw = self._create_cb_spin("抽屉问题", 20)
        self.cb_container = self._create_cb_spin("容斥问题", 20)
        for cb in [self.cb_logic, self.cb_arrange, self.cb_best, self.cb_draw, self.cb_container]:
            logic_layout.addWidget(cb)
        advance_main_layout.addWidget(logic_group)

        advance_main_group.setLayout(advance_main_layout)
        math_layout.addWidget(advance_main_group)

        # --- 题目预览 ---#
        preview_group = QGroupBox("题目预览")
        preview_group.setStyleSheet("QGroupBox { font-size: 15px; font-family: '楷体', 'KaiTi'; }")
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.setContentsMargins(3, 3, 3, 3)
        self.preview_text = QTextEdit()
        self.preview_text.setFixedHeight(180)
        preview_layout.addWidget(self.preview_text)
        preview_group.setLayout(preview_layout)
        math_layout.addWidget(preview_group)

        # --- 功能区按钮 ---#
        func_layout = QHBoxLayout()
        func_layout.setSpacing(6)
        func_layout.addStretch()
        
        btn_style = """
            QPushButton {
                font-size: 14px;
                background-color: #4dabf7;
                color: white;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #339af0;
            }
            QPushButton:disabled {
                background-color: #adb5bd;
            }
        """
        
        self.btn_clear_preview = QPushButton("清空预览")
        self.btn_clear_preview.setFixedSize(QSize(80, 32))
        self.btn_clear_preview.setStyleSheet(btn_style)
        
        self.btn_generate = QPushButton("生成题目")
        self.btn_generate.setFixedSize(QSize(100, 32))
        self.btn_generate.setStyleSheet(btn_style)
        
        self.btn_export_pdf = QPushButton("导出PDF")
        self.btn_export_pdf.setFixedSize(QSize(100, 32))
        self.btn_export_pdf.setStyleSheet(btn_style)
        
        self.btn_clear_all = QPushButton("全部清空")
        self.btn_clear_all.setFixedSize(QSize(80, 32))
        self.btn_clear_all.setStyleSheet(btn_style)
        
        func_layout.addWidget(self.btn_clear_preview)
        func_layout.addWidget(self.btn_generate)
        func_layout.addWidget(self.btn_export_pdf)
        func_layout.addWidget(self.btn_clear_all)
        func_layout.addStretch()
        math_layout.addLayout(func_layout)

        # 绑定按钮事件
        self.btn_clear_preview.clicked.connect(self.preview_text.clear)
        self.btn_clear_all.clicked.connect(self.clear_all_checks)
        self.btn_generate.clicked.connect(self.do_generate)
        self.btn_export_pdf.clicked.connect(self.do_export_pdf)
        self.btn_onekey.clicked.connect(self.do_onekey)

    def _create_cb_spin(self, text, value):
        """创建统一的复选框+数量编辑框组件，纯文本输入，无上下箭头"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        cb = QCheckBox(text)
        layout.addWidget(cb)
        edit = QLineEdit(str(value))
        edit.setFixedWidth(45)
        edit.setAlignment(Qt.AlignCenter) if hasattr(Qt, 'AlignCenter') else None
        layout.addWidget(edit)
        return widget

    def clear_all_checks(self):
        """一键清空所有勾选和预览内容"""
        for cb in self.findChildren(QCheckBox):
            cb.setChecked(False)
        for edit in self.findChildren(QLineEdit):
            edit.setText("20")
        self.preview_text.clear()
        self._questions_data = None

    def _get_selections(self):
        """读取所有勾选的题型及数量，自动限制最大值"""
        selections = {}
        for attr_name in dir(self):
            widget = getattr(self, attr_name, None)
            if not attr_name.startswith("cb_"):
                continue
            if widget is None or not hasattr(widget, 'findChildren'):
                continue
            children = widget.findChildren(QCheckBox)
            if children:
                cb = children[0]
                edits = widget.findChildren(QLineEdit)
                if cb.isChecked() and edits:
                    try:
                        count = int(edits[0].text())
                        # 强制限制数量范围：1 ~ 200
                        count = max(1, min(count, 10000))
                    except (ValueError, TypeError):
                        count = 20
                    selections[attr_name] = count
        return selections

    def do_generate(self):
        """生成题目按钮（异步执行，防止UI卡死）"""
        selections = self._get_selections()
        if not selections:
            self.preview_text.setPlainText("请先勾选题型！")
            return
        use_bracket = self.cb_bracket.isChecked()
        
        # 获取年级设置（从快速出题配置或默认值）
        grade = getattr(self, '_current_grade', None)
        if grade is None:
            # 尝试从UI获取年级
            grade = self._get_grade_from_ui()

        # 安全断开旧线程连接
        self._safe_clean_thread()

        self.btn_generate.setEnabled(False)
        self.btn_generate.setText("生成中...")

        self._gen_thread = _GenThread(generate_questions, selections, use_bracket, grade)
        self._gen_thread.finished.connect(self._on_generate_done)
        self._gen_thread.start()
    
    def _get_grade_from_ui(self):
        """从UI获取年级设置"""
        # 如果有年级选择器，从这里获取
        grade_combo = getattr(self, 'grade_combo', None)
        if grade_combo:
            return grade_combo.currentIndex() + 1
        return None

    def _safe_clean_thread(self):
        """清理旧线程，确保信号断开"""
        if self._gen_thread is not None:
            try:
                self._gen_thread.finished.disconnect()
            except TypeError:
                pass  # 已断开或未连接
            if self._gen_thread.isRunning():
                self._gen_thread.quit()
                self._gen_thread.wait(1000)
            self._gen_thread.deleteLater()
            self._gen_thread = None

    def _on_generate_done(self, questions_data):
        """手动出题完成"""
        self._safe_clean_thread()

        if isinstance(questions_data, dict) and questions_data.get("_error"):
            QMessageBox.warning(self, "出题失败", f"生成题目时出错：{questions_data['_error']}")
        else:
            self._questions_data = questions_data
            self._show_preview()
        self.btn_generate.setEnabled(True)
        self.btn_generate.setText("生成题目")

    def do_onekey(self):
        """一键出题按钮（QThread后台执行）"""
        self._safe_clean_thread()

        grade = self.grade_combo.currentText()
        try:
            count = int(self.quick_count_edit.text())
            count = max(1, min(count, 10000))   # 保护上限
        except (ValueError, TypeError):
            count = 30

        self.btn_onekey.setEnabled(False)
        self.btn_onekey.setText("生成中...")

        self._gen_thread = _GenThread(generate_quick_questions, grade, count)
        self._gen_thread.finished.connect(self._on_onekey_done)
        self._gen_thread.start()

    def _on_onekey_done(self, questions_data):
        """一键出题完成后更新预览"""
        self._safe_clean_thread()

        if isinstance(questions_data, dict) and questions_data.get("_error"):
            QMessageBox.warning(self, "出题失败", f"生成题目时出错：{questions_data['_error']}")
        else:
            self._questions_data = questions_data
            self._show_preview()
        self.btn_onekey.setEnabled(True)
        self.btn_onekey.setText("一键出题")

    def _show_preview(self):
        """
        预览区显示题目（纯文本格式，速度极快，永不卡死）
        """
        if not self._questions_data:
            return

        basic_qs = self._questions_data.get("basic", [])
        advance_qs = self._questions_data.get("advance", [])
        total_count = len(basic_qs) + len(advance_qs)

        # 题目数量过多时，只显示提示信息
        MAX_PREVIEW_ITEMS = 10000
        if total_count > MAX_PREVIEW_ITEMS:
            self.preview_text.setPlainText(
                f"题目数量过多（共 {total_count} 题），请减少题目数量或直接导出 PDF 查看。\n"
                f"预览区最多显示 {MAX_PREVIEW_ITEMS} 题。"
            )
            return

        lines = []
        lines.append(f"日期：______年_____月_____日         出题总量：{total_count} 题")
        lines.append("")

        # 基础题部分
        if basic_qs:
            lines.append("【基础题】")
            for idx, item in enumerate(basic_qs, 1):
                q = item[1] if len(item) >= 2 else item[0]
                q_text = _frac_to_text(q)  # 分数转为 a/b
                lines.append(f"{idx:3d}. {q_text}")
            lines.append("")

        # 提升题部分
        if advance_qs:
            lines.append("【提升题】")
            offset = len(basic_qs)
            for idx, item in enumerate(advance_qs, offset + 1):
                q = item[1] if len(item) >= 2 else item[0]
                q_text = _frac_to_text(q)
                lines.append(f"{idx:3d}. {q_text}")
            lines.append("")

        # 答案部分（如果勾选）
        if self.cb_answer.isChecked():
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

        self.preview_text.setPlainText("\n".join(lines))

    def do_export_pdf(self):
        """导出PDF按钮（自动保存到软件目录）"""
        if not self._questions_data:
            self.preview_text.setPlainText("请先生成题目！")
            return
        try:
            from shuxue_export import export_pdf
            use_vertical = self.cb_vertical.isChecked()
            use_answer = self.cb_answer.isChecked()
            filepath = export_pdf(self._questions_data, use_vertical, use_answer)
            self.preview_text.append(
                f'\n✅ PDF导出成功：{filepath}'
            )
        except Exception as e:
            self.preview_text.append(
                f'\n❌ PDF导出失败：{e}'
            )