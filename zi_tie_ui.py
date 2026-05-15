from PyQt5.QtWidgets import (QGroupBox, QRadioButton, QComboBox, QPushButton,
                             QTextEdit, QHBoxLayout, QVBoxLayout, QWidget, QGridLayout, QLineEdit,
                             QLabel, QFileDialog, QMessageBox, QButtonGroup, QCheckBox)
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QFont
from zitie_core import ZitieGenerator, ZitieConfig, add_custom_font, register_builtin_fonts
from zitie_data import GRADE_CHARACTERS, PINYIN_DATA, NUMBER_DATA, GRADES, VERSIONS
from datetime import datetime
import os


class ZiTieTabWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # 初始化控件引用，用于后续批量控制显隐
        self.semester_widget = None
        self.content_widget = None
        self.content_ext_widget = None
        self.other_widget = None
        self.import_widget = None
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 0, 0)
        main_layout.setSpacing(0)

        # ========== 顶部：模式选择 + 字体选择 ==========
        mode_group = QGroupBox("模式选择")
        mode_group.setFixedHeight(50)
        mode_group.setStyleSheet("QGroupBox { font-size: 15px; font-family: '楷体', 'KaiTi'; }")
        mode_layout = QHBoxLayout(mode_group)
        mode_layout.setContentsMargins(5, 0, 5, 0)
        mode_layout.setSpacing(15)
        self.rb_zitie = QRadioButton("字帖生成")
        self.rb_blank = QRadioButton("空白模板")
        self.rb_zitie.setChecked(True)
        self.rb_zitie.setStyleSheet("font-size: 13px;")
        self.rb_blank.setStyleSheet("font-size: 13px;")
        mode_layout.addWidget(self.rb_zitie)
        mode_layout.addSpacing(4)  # 字帖生成与空白模板间距4mm
        mode_layout.addWidget(self.rb_blank)
        mode_layout.addSpacing(5)  # 空白模板与编辑框间距5mm（左移）

        self.page_count_edit = QLineEdit("5")
        self.page_count_edit.setFixedWidth(40)
        self.page_count_edit.setStyleSheet("font-size: 13px; padding: 2px;")
        mode_layout.addWidget(self.page_count_edit)

        font_select_group = QGroupBox("字体选择")
        font_select_group.setFixedHeight(50)
        font_select_group.setStyleSheet("QGroupBox { font-size: 15px; font-family: '楷体', 'KaiTi'; }")
        font_select_layout = QHBoxLayout(font_select_group)
        font_select_layout.setContentsMargins(5, 0, 5, 0)
        font_select_layout.setSpacing(5)  # 按钮间距紧凑

        self.rb_kai = QRadioButton("楷体")
        self.rb_xingshu = QRadioButton("行书")
        self.rb_xingkai = QRadioButton("行楷")
        self.rb_custom_font = QRadioButton("自定义")
        self.rb_kai.setChecked(True)
        self.rb_kai.setStyleSheet("font-size: 13px;")
        self.rb_xingshu.setStyleSheet("font-size: 13px;")
        self.rb_xingkai.setStyleSheet("font-size: 13px;")
        self.rb_custom_font.setStyleSheet("font-size: 13px;")

        self.edit_custom_font = QLineEdit()
        self.edit_custom_font.setFixedWidth(120)  # 进一步缩短，避免压着预览按钮
        self.edit_custom_font.setStyleSheet("font-size: 13px; padding: 2px;")
        self.edit_custom_font.setEnabled(False)

        self.btn_preview_font = QPushButton("预览")
        self.btn_preview_font.setFixedSize(QSize(50, 28))
        self.btn_preview_font.setStyleSheet("""
            QPushButton {
                font-size: 13px;
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
        self.btn_preview_font.setEnabled(False)

        font_select_layout.addWidget(self.rb_kai)
        font_select_layout.addWidget(self.rb_xingshu)
        font_select_layout.addWidget(self.rb_xingkai)
        font_select_layout.addWidget(self.rb_custom_font)
        font_select_layout.addWidget(self.edit_custom_font)
        font_select_layout.addWidget(self.btn_preview_font)
        font_select_layout.addStretch()

        self.rb_kai.clicked.connect(self.on_font_radio_changed)
        self.rb_xingshu.clicked.connect(self.on_font_radio_changed)
        self.rb_xingkai.clicked.connect(self.on_font_radio_changed)
        self.rb_custom_font.clicked.connect(self.on_font_radio_changed)

        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(10)
        top_layout.addWidget(mode_group)
        top_layout.addWidget(font_select_group, 1)
        main_layout.addLayout(top_layout)

        # ========== 样式选择 ==========
        style_group = QGroupBox("样式")
        style_group.setFixedHeight(40)
        style_layout = QHBoxLayout(style_group)
        style_layout.setContentsMargins(5, 0, 5, 0)
        style_layout.setSpacing(6)
        style_group.setStyleSheet("QGroupBox { font-size: 15px; font-family: '楷体', 'KaiTi'; }")

        self.rb_tian = QRadioButton("田字格")
        self.rb_fang = QRadioButton("方格")
        self.rb_mi = QRadioButton("米字格")
        self.rb_gong = QRadioButton("数学格")
        self.rb_sheng = QRadioButton("生字格")
        self.rb_pinyin = QRadioButton("拼音格")
        self.rb_zuowen = QRadioButton("作文本")
        self.rb_jiaoan = QRadioButton("教案格")
        self.rb_dakai = QRadioButton("大楷本")
        self.rb_tian.setChecked(True)

        for rb in [self.rb_tian, self.rb_fang, self.rb_mi, self.rb_gong, self.rb_sheng, self.rb_pinyin, self.rb_zuowen,
                   self.rb_jiaoan, self.rb_dakai]:
            rb.setStyleSheet("font-size: 13px;")
            style_layout.addWidget(rb)

        style_layout.addStretch()

        style_container = QWidget()
        style_container_layout = QHBoxLayout(style_container)
        style_container_layout.setContentsMargins(0, 8, 0, 0)
        style_container_layout.addWidget(style_group)
        main_layout.addWidget(style_container)

        # ========== 文字内容（核心优化区域） ==========
        content_group = QGroupBox("文字内容")
        content_group.setStyleSheet("QGroupBox { font-size: 15px; font-family: '楷体', 'KaiTi'; }")
        content_group_layout = QHBoxLayout(content_group)
        content_group_layout.setContentsMargins(8, 8, 8, 8)
        content_group_layout.setSpacing(5)

        # 左侧布局容器（独立Widget包裹，避免布局错乱）
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)
        left_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        label_width = 40
        combo_width = 80
        rb_style = "font-size: 13px;"
        label_style = "font-size: 13px;"

        # ========== 第1行：年级 ==========
        row1 = QHBoxLayout()
        row1.setContentsMargins(0, 0, 0, 0)
        row1.setSpacing(5)
        grade_label = QLabel("年级:")
        grade_label.setStyleSheet(label_style)
        grade_label.setFixedWidth(label_width)
        self.grade_combo = QComboBox()
        self.grade_combo.addItems(["一年级", "二年级", "三年级", "四年级", "五年级", "六年级"])
        self.grade_combo.setStyleSheet("font-size: 13px;")
        self.grade_combo.setFixedWidth(combo_width)
        row1.addWidget(grade_label)
        row1.addWidget(self.grade_combo)
        row1.addStretch()
        left_layout.addLayout(row1)

        # ========== 第2行：版本 ==========
        row2 = QHBoxLayout()
        row2.setContentsMargins(0, 0, 0, 0)
        row2.setSpacing(5)
        version_label = QLabel("版本:")
        version_label.setStyleSheet(label_style)
        version_label.setFixedWidth(label_width)
        self.version_combo = QComboBox()
        self.version_combo.addItems(["人教版", "国学"])
        self.version_combo.setStyleSheet("font-size: 13px;")
        self.version_combo.setFixedWidth(combo_width)
        self.version_combo.currentTextChanged.connect(self.on_version_changed)
        row2.addWidget(version_label)
        row2.addWidget(self.version_combo)
        row2.addStretch()
        left_layout.addLayout(row2)

        # ========== 国学著作行（仅国学版本显示） ==========
        self.classic_widget = QWidget()
        classic_layout = QHBoxLayout(self.classic_widget)
        classic_layout.setContentsMargins(0, 0, 0, 0)
        classic_layout.setSpacing(5)
        classic_label = QLabel("著作:")
        classic_label.setStyleSheet(label_style)
        classic_label.setFixedWidth(label_width)
        self.classic_combo = QComboBox()
        self.classic_combo.addItems(["千字文", "道德经", "三字经", "弟子规", "百家姓"])
        self.classic_combo.setStyleSheet("font-size: 13px;")
        self.classic_combo.setFixedWidth(combo_width)
        classic_layout.addWidget(classic_label)
        classic_layout.addWidget(self.classic_combo)
        classic_layout.addStretch()
        self.classic_widget.setVisible(False)
        left_layout.addWidget(self.classic_widget)

        # ========== 第3行：学期（封装为独立Widget，方便控制显隐） ==========
        self.semester_widget = QWidget()
        semester_layout = QHBoxLayout(self.semester_widget)
        semester_layout.setContentsMargins(0, 0, 0, 0)
        semester_layout.setSpacing(8)
        self.cb_first_semester = QCheckBox("上册")
        self.cb_second_semester = QCheckBox("下册")
        self.cb_first_semester.setStyleSheet(rb_style)
        self.cb_second_semester.setStyleSheet(rb_style)
        self.cb_first_semester.clicked.connect(self.on_semester_changed)
        self.cb_second_semester.clicked.connect(self.on_semester_changed)
        semester_layout.addWidget(self.cb_first_semester)
        semester_layout.addWidget(self.cb_second_semester)
        semester_layout.addStretch()
        left_layout.addWidget(self.semester_widget)

        # ========== 第4行：内容（封装为独立Widget） ==========
        self.content_widget = QWidget()
        content_layout = QHBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(8)
        self.rb_shengzi = QRadioButton("生字")
        self.rb_ciyu = QRadioButton("词语")
        for rb in [self.rb_shengzi, self.rb_ciyu]:
            rb.setStyleSheet(rb_style)
        content_layout.addWidget(self.rb_shengzi)
        content_layout.addWidget(self.rb_ciyu)
        content_layout.addStretch()
        left_layout.addWidget(self.content_widget)

        # ========== 第5行：内容扩展（封装为独立Widget） ==========
        self.content_ext_widget = QWidget()
        content_ext_layout = QHBoxLayout(self.content_ext_widget)
        content_ext_layout.setContentsMargins(0, 0, 0, 0)
        content_ext_layout.setSpacing(8)
        self.rb_gushi = QRadioButton("诗词")
        self.rb_wenyan = QRadioButton("文言文")
        self.rb_gushi.setStyleSheet(rb_style)
        self.rb_wenyan.setStyleSheet(rb_style)
        content_ext_layout.addWidget(self.rb_gushi)
        content_ext_layout.addWidget(self.rb_wenyan)
        content_ext_layout.addStretch()
        left_layout.addWidget(self.content_ext_widget)

        # ========== 第6行：其他（封装为独立Widget） ==========
        self.other_widget = QWidget()
        other_layout = QHBoxLayout(self.other_widget)
        other_layout.setContentsMargins(0, 0, 0, 0)
        other_layout.setSpacing(8)
        self.rb_shuzi = QRadioButton("数字")
        self.rb_pinyin_text = QRadioButton("拼音")
        self.rb_shuzi.setStyleSheet(rb_style)
        self.rb_pinyin_text.setStyleSheet(rb_style)
        self.rb_shuzi.setEnabled(True)
        self.rb_pinyin_text.setEnabled(True)
        self.rb_shuzi.clicked.connect(self.on_content_radio_changed)
        self.rb_pinyin_text.clicked.connect(self.on_content_radio_changed)
        other_layout.addWidget(self.rb_shuzi)
        other_layout.addWidget(self.rb_pinyin_text)
        other_layout.addStretch()
        left_layout.addWidget(self.other_widget)

        # ========== 第7行：大楷/待定（封装为独立Widget） ==========
        self.dakai_widget = QWidget()
        dakai_layout = QHBoxLayout(self.dakai_widget)
        dakai_layout.setContentsMargins(0, 0, 0, 0)
        dakai_layout.setSpacing(8)
        self.rb_gaiding = QRadioButton("大楷")
        self.rb_ding = QRadioButton("待定")
        self.rb_gaiding.setStyleSheet(rb_style)
        self.rb_ding.setStyleSheet(rb_style)
        self.rb_ding.setEnabled(False)
        dakai_layout.addWidget(self.rb_gaiding)
        dakai_layout.addWidget(self.rb_ding)
        dakai_layout.addStretch()
        left_layout.addWidget(self.dakai_widget)

        # ========== 第8行：一键导入（封装为独立Widget） ==========
        self.import_widget = QWidget()
        import_layout = QHBoxLayout(self.import_widget)
        import_layout.setContentsMargins(25, 14, 0, 0)
        import_layout.setSpacing(5)
        self.btn_import = QPushButton("一键导入")
        self.btn_import.setFixedSize(QSize(100, 32))
        self.btn_import.setStyleSheet("""
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
        self.btn_import.clicked.connect(self.on_import_content)
        import_layout.addWidget(self.btn_import)
        import_layout.addStretch()
        left_layout.addWidget(self.import_widget)

        # 内容单选按钮组（生字、词语、诗词、文言文、数字、拼音、大楷 七选一互斥）- 使用实例变量避免被垃圾回收
        self.content_button_group = QButtonGroup()
        self.content_button_group.addButton(self.rb_shengzi)
        self.content_button_group.addButton(self.rb_ciyu)
        self.content_button_group.addButton(self.rb_gushi)
        self.content_button_group.addButton(self.rb_wenyan)
        self.content_button_group.addButton(self.rb_gaiding)
        self.content_button_group.addButton(self.rb_shuzi)
        self.content_button_group.addButton(self.rb_pinyin_text)

        # 绑定信号（内容类）
        self.rb_shengzi.clicked.connect(self.on_content_radio_changed)
        self.rb_gushi.clicked.connect(self.on_content_radio_changed)
        self.rb_wenyan.clicked.connect(self.on_content_radio_changed)
        self.rb_ciyu.clicked.connect(self.on_content_radio_changed)
        self.rb_gaiding.clicked.connect(self.on_content_radio_changed)

        # 右侧文本编辑框
        self.text_content = QTextEdit()
        self.text_content.setStyleSheet("font-size: 13px; padding: 5px;")
        self.text_content.textChanged.connect(self.update_grid_type_enabled)
        content_group_layout.addWidget(left_container, 1)  # 用Widget包裹左侧布局
        content_group_layout.addWidget(self.text_content, 5)

        content_container = QWidget()
        content_container_layout = QHBoxLayout(content_container)
        content_container_layout.setContentsMargins(0, 5, 0, 0)
        content_container_layout.addWidget(content_group)
        main_layout.addWidget(content_container)

        # ========== 类型选择 ==========
        type_group = QGroupBox("类型")
        type_group.setStyleSheet("QGroupBox { font-size: 15px; font-family: '楷体', 'KaiTi'; }")
        type_layout = QGridLayout(type_group)
        type_layout.setContentsMargins(5, 5, 5, 5)
        type_layout.setSpacing(8)

        self.cb_huizi = QCheckBox("灰字")
        self.rb_duozi = QRadioButton("单字")
        self.rb_bishun = QRadioButton("笔顺")
        self.rb_duoju = QRadioButton("多句")
        self.rb_wenzhang = QRadioButton("文章")
        for rb in [self.cb_huizi, self.rb_duozi, self.rb_bishun, self.rb_duoju, self.rb_wenzhang]:
            rb.setStyleSheet("font-size: 12px;")
        type_layout.addWidget(self.cb_huizi, 0, 0)
        type_layout.addWidget(self.rb_duozi, 0, 1)
        type_layout.addWidget(self.rb_bishun, 0, 2)
        type_layout.addWidget(self.rb_duoju, 0, 3)
        type_layout.addWidget(self.rb_wenzhang, 0, 4)

        self.cb_miaohong = QCheckBox("描红")
        self.cb_miaohong.setEnabled(False)
        self.rb_duozi1 = QRadioButton("单字+1行")
        self.rb_bishun1 = QRadioButton("笔顺+1行")
        self.rb_duoju1 = QRadioButton("多句+1行")
        self.rb_wenzhang1 = QRadioButton("文章+1行")
        for rb in [self.cb_miaohong, self.rb_duozi1, self.rb_bishun1, self.rb_duoju1, self.rb_wenzhang1]:
            rb.setStyleSheet("font-size: 12px;")
        type_layout.addWidget(self.cb_miaohong, 1, 0)
        type_layout.addWidget(self.rb_duozi1, 1, 1)
        type_layout.addWidget(self.rb_bishun1, 1, 2)
        type_layout.addWidget(self.rb_duoju1, 1, 3)
        type_layout.addWidget(self.rb_wenzhang1, 1, 4)

        # 绑定信号（类型 RadioButton - 笔顺等切换时更新格子可用状态）
        self.rb_bishun.clicked.connect(self.update_grid_type_enabled)
        self.rb_bishun1.clicked.connect(self.update_grid_type_enabled)
        self.rb_duozi.clicked.connect(self.update_grid_type_enabled)
        self.rb_duozi1.clicked.connect(self.update_grid_type_enabled)
        self.rb_duoju.clicked.connect(self.update_grid_type_enabled)
        self.rb_duoju1.clicked.connect(self.update_grid_type_enabled)
        self.rb_wenzhang.clicked.connect(self.update_grid_type_enabled)
        self.rb_wenzhang1.clicked.connect(self.update_grid_type_enabled)

        self.rb_duozi.setChecked(True)
        main_layout.addWidget(type_group)

        # ========== 功能区 ==========
        func_group = QGroupBox("功能区")
        func_group.setStyleSheet("QGroupBox { font-size: 15px; font-family: '楷体', 'KaiTi'; }")
        func_layout = QHBoxLayout(func_group)
        func_layout.setContentsMargins(5, 5, 5, 5)
        func_layout.addStretch()

        self.btn_clear = QPushButton("清空")
        self.btn_generate = QPushButton("生成")
        self.btn_export_pdf = QPushButton("导出PDF")
        
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
        
        for btn in [self.btn_clear, self.btn_generate, self.btn_export_pdf]:
            btn.setFixedSize(QSize(80, 32))
            btn.setStyleSheet(btn_style)
            func_layout.addWidget(btn)

        self.btn_generate.hide()

        func_layout.addStretch()
        main_layout.addWidget(func_group)

        # ========== 信号绑定 ==========
        self.btn_clear.clicked.connect(self.clear_content)
        self.btn_generate.clicked.connect(self.generate_zitie)
        self.btn_export_pdf.clicked.connect(self.export_pdf)
        self.btn_preview_font.clicked.connect(self.on_select_font)

        self.generated_pages = []
        self.last_generated_path = ""

        # 注册内置字体（荆霄鹏-行书、田英章-行楷、欧阳询书法字体-大楷）
        self.builtin_fonts = register_builtin_fonts()

    def on_version_changed(self, version):
        """
        版本切换逻辑：
        - 国学模式：显示著作选择，隐藏学期/内容/其他 Widget
        - 人教版：显示学期/内容/其他
        - 所有控件始终可用，不变灰
        """
        is_guoxue = version == "国学"

        self.classic_widget.setVisible(is_guoxue)
        self.semester_widget.setVisible(not is_guoxue)
        self.content_widget.setVisible(not is_guoxue)
        self.content_ext_widget.setVisible(not is_guoxue)
        self.other_widget.setVisible(not is_guoxue)
        self.import_widget.setVisible(True)

        # 重置所有选中状态
        self.cb_first_semester.setChecked(False)
        self.cb_second_semester.setChecked(False)
        self.rb_shengzi.setChecked(False)
        self.rb_gushi.setChecked(False)
        self.rb_ciyu.setChecked(False)
        self.rb_gaiding.setChecked(False)
        self.rb_shuzi.setChecked(False)
        self.rb_pinyin_text.setChecked(False)

        self.text_content.clear()
        self.update_grid_type_enabled()
        self.layout().update()
        self.adjustSize()

    def on_semester_changed(self):
        """
        上下册变化：仅清空文本区，等用户点"一键导入"时再加载数据。
        所有控件始终可用，不变灰。
        """
        self.text_content.clear()
        self.update_grid_type_enabled()

    def on_content_radio_changed(self):
        """
        内容单选变化：
        - 选中"大楷"时，强制选中"大楷格"，并在编辑框填入七言绝句
        - 其他选项清空文本区，等待用户操作
        """
        # 选中"大楷"时，填入默认七言绝句（每行一句），默认单字模式
        if self.rb_gaiding.isChecked():
            self.text_content.clear()
            self.text_content.append("远上寒山石径斜")
            self.text_content.append("白云深处有人家")
            self.text_content.append("停车坐爱枫林晚")
            self.text_content.append("霜叶红于二月花")
            self.rb_dakai.setChecked(True)
            self.rb_duozi.setChecked(True)  # 默认单字模式
        else:
            self.text_content.clear()
        
        self.update_grid_type_enabled()
    
    def update_grid_type_enabled(self):
        """
        根据编辑框内容类型启用/禁用格子：
        - 勾选"大楷"：只能使用大楷格，其他全部禁用
        - 勾选"笔顺"/"笔顺+1行"：只能使用田字格、方格、米字格，其他禁用
        - 汉字：田字格、方格、米字格、生字格、教案格、大楷本
        - 拼音：生字格、拼音格、教案格
        - 数字：田字格、数学格、教案格
        """
        # 优先处理"大楷"：只要勾选了，只能用大楷格
        if self.rb_gaiding.isChecked():
            self.rb_tian.setEnabled(False)
            self.rb_fang.setEnabled(False)
            self.rb_mi.setEnabled(False)
            self.rb_gong.setEnabled(False)
            self.rb_sheng.setEnabled(False)
            self.rb_pinyin.setEnabled(False)
            self.rb_zuowen.setEnabled(False)
            self.rb_jiaoan.setEnabled(False)
            self.rb_dakai.setEnabled(True)
            self.rb_dakai.setChecked(True)
            return
        
        # 处理"笔顺"/"笔顺+1行"：只能用田字格、方格、米字格
        if self.rb_bishun.isChecked() or self.rb_bishun1.isChecked():
            enabled_rbs = [self.rb_tian, self.rb_fang, self.rb_mi]
            disabled_rbs = [self.rb_gong, self.rb_sheng, self.rb_pinyin,
                           self.rb_zuowen, self.rb_jiaoan, self.rb_dakai]
            for rb in enabled_rbs:
                rb.setEnabled(True)
            for rb in disabled_rbs:
                rb.setEnabled(False)
            # 如果当前选中的是被禁用的格子，切换到田字格
            current_checked = any(rb.isChecked() for rb in disabled_rbs)
            if current_checked and not self.rb_tian.isChecked():
                self.rb_tian.setChecked(True)
            return
        
        content = self.text_content.toPlainText().strip()
        
        if not content:
            # 空内容时全部可用
            for rb in [self.rb_tian, self.rb_fang, self.rb_mi, self.rb_gong,
                       self.rb_sheng, self.rb_pinyin, self.rb_zuowen,
                       self.rb_jiaoan, self.rb_dakai]:
                rb.setEnabled(True)
            return
        
        content_type = self._detect_content_type(content)
        
        if content_type == "hanzi":
            # 汉字：田字格、方格、米字格、生字格、教案格（大楷格只在勾选"大楷"时可用）
            self.rb_tian.setEnabled(True)
            self.rb_fang.setEnabled(True)
            self.rb_mi.setEnabled(True)
            self.rb_gong.setEnabled(False)
            self.rb_sheng.setEnabled(True)
            self.rb_pinyin.setEnabled(False)
            self.rb_zuowen.setEnabled(False)
            self.rb_jiaoan.setEnabled(True)
            self.rb_dakai.setEnabled(False)
            
            # 如果当前选中的是被禁用的格子，切换到田字格
            if self.rb_gong.isChecked() or self.rb_pinyin.isChecked() or self.rb_zuowen.isChecked():
                self.rb_tian.setChecked(True)
                
        elif content_type == "pinyin":
            # 拼音：生字格、拼音格、教案格
            self.rb_tian.setEnabled(False)
            self.rb_fang.setEnabled(False)
            self.rb_mi.setEnabled(False)
            self.rb_gong.setEnabled(False)
            self.rb_sheng.setEnabled(True)
            self.rb_pinyin.setEnabled(True)
            self.rb_zuowen.setEnabled(False)
            self.rb_jiaoan.setEnabled(True)
            self.rb_dakai.setEnabled(False)
            
            # 如果当前选中的是被禁用的格子，切换到拼音格
            if (self.rb_tian.isChecked() or self.rb_fang.isChecked() or 
                self.rb_mi.isChecked() or self.rb_gong.isChecked() or 
                self.rb_zuowen.isChecked() or self.rb_dakai.isChecked()):
                self.rb_pinyin.setChecked(True)
                
        elif content_type == "number":
            # 数字：田字格、数学格、教案格
            self.rb_tian.setEnabled(True)
            self.rb_fang.setEnabled(False)
            self.rb_mi.setEnabled(False)
            self.rb_gong.setEnabled(True)
            self.rb_sheng.setEnabled(False)
            self.rb_pinyin.setEnabled(False)
            self.rb_zuowen.setEnabled(False)
            self.rb_jiaoan.setEnabled(True)
            self.rb_dakai.setEnabled(False)
            
            # 如果当前选中的是被禁用的格子，切换到数学格
            if (self.rb_fang.isChecked() or self.rb_mi.isChecked() or 
                self.rb_sheng.isChecked() or self.rb_pinyin.isChecked() or 
                self.rb_zuowen.isChecked() or self.rb_dakai.isChecked()):
                self.rb_gong.setChecked(True)
                
        else:
            # 未知类型，全部可用
            for rb in [self.rb_tian, self.rb_fang, self.rb_mi, self.rb_gong,
                       self.rb_sheng, self.rb_pinyin, self.rb_zuowen,
                       self.rb_jiaoan, self.rb_dakai]:
                rb.setEnabled(True)
    
    def _detect_content_type(self, content):
        content = content.replace('\n', '').replace('\r', '').replace(' ', '')
        
        has_hanzi = False
        has_number = False
        has_pinyin = False
        
        for char in content:
            if '\u4e00' <= char <= '\u9fff':
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
        if self.rb_shuzi.isChecked():
            self.text_content.setPlainText(NUMBER_DATA)
            return
        
        if self.rb_pinyin_text.isChecked():
            self.text_content.setPlainText(PINYIN_DATA)
            return

        version = self.version_combo.currentText()

        if version == "国学":
            classic = self.classic_combo.currentText()
            from zitie_data import CLASSIC_DATA
            data = CLASSIC_DATA.get(classic, "")
            self.text_content.setPlainText(data)
            return

        grade = self.grade_combo.currentText()
        if not grade:
            return

        version_key = VERSIONS.get(version)
        if not version_key:
            return

        grade_key = GRADES.get(grade)
        if not grade_key:
            return

        has_first = self.cb_first_semester.isChecked()
        has_second = self.cb_second_semester.isChecked()

        if self.rb_shengzi.isChecked():
            data = ""
            if has_first:
                data += GRADE_CHARACTERS.get(version_key, {}).get(grade_key, {}).get("first", {}).get("生字表", "")
            if has_second:
                if data:
                    data += "\n\n"
                data += GRADE_CHARACTERS.get(version_key, {}).get(grade_key, {}).get("second", {}).get("生字表", "")
            self.text_content.setPlainText(data)
        elif self.rb_gushi.isChecked():
            data = ""
            if has_first:
                data += GRADE_CHARACTERS.get(version_key, {}).get(grade_key, {}).get("first", {}).get("古诗词", "")
            if has_second:
                if data:
                    data += "\n\n"
                data += GRADE_CHARACTERS.get(version_key, {}).get(grade_key, {}).get("second", {}).get("古诗词", "")
            self.text_content.setPlainText(data)
        elif self.rb_wenyan.isChecked():
            data = ""
            
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
                        content = ''.join(content_lines)
                        result.append(f"{title}\n{author}\n{content}")
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
            self.text_content.setPlainText(data)
        elif self.rb_ciyu.isChecked():
            data = ""
            if has_first:
                data += GRADE_CHARACTERS.get(version_key, {}).get(grade_key, {}).get("first", {}).get("词语表", "")
            if has_second:
                if data:
                    data += "\n\n"
                data += GRADE_CHARACTERS.get(version_key, {}).get(grade_key, {}).get("second", {}).get("词语表", "")
            self.text_content.setPlainText(data)

    def on_import_content(self):
        self.on_content_type_changed()

    def clear_content(self):
        self.text_content.clear()

    def get_grid_type(self):
        if self.rb_tian.isChecked():
            return "田字格"
        elif self.rb_fang.isChecked():
            return "方格"
        elif self.rb_mi.isChecked():
            return "米字格"
        elif self.rb_gong.isChecked():
            return "数学格"
        elif self.rb_sheng.isChecked():
            return "生字格"
        elif self.rb_pinyin.isChecked():
            return "四线三格"
        elif self.rb_zuowen.isChecked():
            return "作文本"
        elif self.rb_jiaoan.isChecked():
            return "教案格"
        elif self.rb_dakai.isChecked():
            return "大楷本"
        return "田字格"

    def get_char_type(self):
        if self.cb_miaohong.isChecked():
            return "描红"
        
        base_type = ""
        if self.rb_duozi.isChecked():
            base_type = "单字"
        elif self.rb_bishun.isChecked():
            base_type = "笔顺"
        elif self.rb_duoju.isChecked():
            base_type = "多句"
        elif self.rb_wenzhang.isChecked():
            base_type = "文章"
        elif self.rb_duozi1.isChecked():
            base_type = "单字+1行"
        elif self.rb_bishun1.isChecked():
            base_type = "笔顺+1行"
        elif self.rb_duoju1.isChecked():
            base_type = "多句+1行"
        elif self.rb_wenzhang1.isChecked():
            base_type = "文章+1行"
        
        if self.cb_huizi.isChecked():
            return "灰字" + base_type if base_type else "灰字"
        
        return base_type if base_type else "单字"

    def generate_zitie(self):
        config = ZitieConfig()

        if self.rb_blank.isChecked():
            config.mode = "blank"
            try:
                config.page_count = int(self.page_count_edit.text())
            except ValueError:
                config.page_count = 1
        else:
            config.mode = "zitie"
            config.chars = self.text_content.toPlainText()
            config.char_type = self.get_char_type()
            config.content_type = self.get_content_name()

        config.grid_type = self.get_grid_type()
        config.font_name = self.get_font_name()

        generator = ZitieGenerator()
        generator.set_config(config)

        try:
            self.last_generated_path = generator.generate()
            if self.last_generated_path:
                QMessageBox.information(self, "生成成功", f"字帖已生成！\n文件路径：{self.last_generated_path}")
            else:
                QMessageBox.warning(self, "生成失败", "未能生成字帖！")
        except Exception as e:
            QMessageBox.critical(self, "生成错误", f"生成过程中发生错误：{str(e)}")

    def get_content_name(self):
        version = self.version_combo.currentText()
        if version == "国学":
            return self.classic_combo.currentText()
        
        if self.rb_shengzi.isChecked():
            return "生字"
        elif self.rb_gushi.isChecked():
            return "诗词"
        elif self.rb_ciyu.isChecked():
            return "词语"
        elif self.rb_wenyan.isChecked():
            return "文言文"
        elif self.rb_shuzi.isChecked():
            return "数字"
        elif self.rb_pinyin_text.isChecked():
            return "拼音"
        return "字帖"

    def export_pdf(self):
        config = ZitieConfig()
        config.grid_type = self.get_grid_type()
        
        config.font_name = self.get_font_name()

        if self.rb_blank.isChecked():
            config.mode = "blank"
            try:
                config.page_count = int(self.page_count_edit.text())
            except ValueError:
                config.page_count = 5
        else:
            content = self.text_content.toPlainText().strip()
            if not content:
                QMessageBox.warning(self, "提示", "请先在编辑框中输入内容！")
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
            
            if self.rb_blank.isChecked():
                file_name = f"{grid_name}模板_{config.page_count}页_{time_str}.pdf"
            else:
                char_type = self.get_char_type()
                file_name = f"{grid_name}{content_name}_{char_type}_{time_str}.pdf"
            
            file_path = os.path.join(os.getcwd(), file_name)

            success = generator.save_pdf(file_path)
            if success:
                QMessageBox.information(self, "导出成功", f"PDF文件已保存到：\n{file_path}")
            else:
                QMessageBox.critical(self, "导出失败", "保存PDF文件失败！")
        except Exception as e:
            QMessageBox.critical(self, "导出错误", f"导出过程中发生错误：{str(e)}")

    def on_font_radio_changed(self):
        """字体选择变化：只有自定义字体时才启用编辑框和预览按钮"""
        is_custom = self.rb_custom_font.isChecked()
        self.edit_custom_font.setEnabled(is_custom)
        self.btn_preview_font.setEnabled(is_custom)

    def get_font_name(self):
        """获取当前选择的字体名称"""
        # 拼音内容类型默认使用拼音字体
        if self.rb_pinyin_text.isChecked():
            return "GB PINYINOK-B_A"
        if self.rb_kai.isChecked():
            return "楷体_GB2312"
        elif self.rb_xingshu.isChecked():
            return "荆霄鹏"
        elif self.rb_xingkai.isChecked():
            return "田英章"
        elif self.rb_gaiding.isChecked():
            return "欧阳询书法字体"
        else:
            return self.edit_custom_font.text() or "楷体_GB2312"

    def on_select_font(self):
        font_path, _ = QFileDialog.getOpenFileName(
            self, "选择字体文件", "", "字体文件 (*.ttf *.ttc *.otf)"
        )

        if font_path:
            font_name = add_custom_font(font_path)
            if font_name:
                self.edit_custom_font.setText(font_name)
                QMessageBox.information(self, "字体添加成功",
                                        f"字体 '{font_name}' 已添加成功！\n下次启动软件时会自动加载。")
            else:
                QMessageBox.warning(self, "字体添加失败", 
                                   "无法添加该字体文件，请尝试以下解决方法：\n\n"
                                   "1. 确保选择的是有效的TTF、TTC或OTF字体文件\n"
                                   "2. 尝试使用系统字体目录中的字体（如 C:\\Windows\\Fonts\\）\n"
                                   "3. 检查字体文件是否被其他程序占用\n"
                                   "4. 字体文件路径不要包含中文或特殊字符")

    


# 独立main函数调试入口
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = ZiTieTabWidget()
    window.setWindowTitle("小学出题工具箱 - 字帖")
    window.resize(800, 600)
    window.show()
    sys.exit(app.exec_())