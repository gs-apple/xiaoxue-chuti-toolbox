import sys
import asyncio
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QLabel, QProgressBar, QAbstractItemView, QLineEdit, QMessageBox
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QFont

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
        "一年级": "1",
        "二年级": "2",
        "三年级": "3",
        "四年级": "4",
        "五年级": "5",
        "六年级": "6",
        "七年级": "7",
        "八年级": "8",
        "九年级": "9",
        "全部年级": "",
    },
    "szxuexiao": {
        "一年级": "1",
        "二年级": "2",
        "三年级": "3",
        "四年级": "4",
        "五年级": "5",
        "六年级": "6",
        "全部年级": "",
    },
    "yishijuan": {
        "一年级": "1",
        "二年级": "2",
        "三年级": "3",
        "四年级": "4",
        "五年级": "5",
        "六年级": "6",
        "七年级": "7",
        "八年级": "8",
        "九年级": "9",
        "全部年级": "",
    },
}

YEARS = {
    "全部年份": "",
    "2026年": "2026",
    "2025年": "2025",
    "2024年": "2024",
    "2023年": "2023",
    "2022年": "2022",
    "2021年": "2021",
    "2020年": "2020",
    "2019年": "2019",
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


class SearchWorker(QThread):
    result_found = pyqtSignal(dict)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, platform, subject, grade, year, keyword):
        super().__init__()
        self.platform = platform
        self.subject = subject
        self.grade = grade
        self.year = year
        self.keyword = keyword
        self.is_running = True
        self.stop_event = None

    def run(self):
        results = []
        loop = None
        try:
            def result_callback(item):
                if self.is_running:
                    self.result_found.emit(item)
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.stop_event = asyncio.Event()
            
            results = loop.run_until_complete(
                self._do_search(result_callback)
            )
            
            if self.is_running:
                self.finished.emit(results)
                
        except Exception as e:
            if self.is_running:
                self.error.emit(str(e))
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


class ZhentiTabWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.search_results = []
        self.search_worker = None
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        search_group = QGroupBox("搜索条件")
        search_group.setStyleSheet("QGroupBox { font-size: 14px; font-family: 'Microsoft YaHei'; }")
        search_layout = QGridLayout(search_group)
        search_layout.setContentsMargins(8, 12, 8, 8)
        search_layout.setSpacing(6)

        label_style = "font-size: 15px; font-family: '楷体', 'KaiTi', 'STKaiti';"

        platform_label = QLabel("平台:")
        platform_label.setStyleSheet(label_style)
        platform_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        platform_label.setFixedWidth(50)
        search_layout.addWidget(platform_label, 0, 0)

        self.platform_combo = QComboBox()
        self.platform_combo.addItems(list(PLATFORMS.keys()))
        self.platform_combo.setStyleSheet("font-size: 13px; min-width: 90px; padding: 2px;")
        self.platform_combo.currentTextChanged.connect(self.on_platform_changed)
        search_layout.addWidget(self.platform_combo, 0, 1)

        search_layout.setColumnMinimumWidth(2, 15)

        subject_label = QLabel("学科:")
        subject_label.setStyleSheet(label_style)
        subject_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        subject_label.setFixedWidth(50)
        search_layout.addWidget(subject_label, 0, 3)

        self.subject_combo = QComboBox()
        self.subject_combo.addItems(list(SUBJECTS["shijuan1"].keys()))
        self.subject_combo.setStyleSheet("font-size: 13px; min-width: 90px; padding: 2px;")
        search_layout.addWidget(self.subject_combo, 0, 4)

        grade_label = QLabel("年级:")
        grade_label.setStyleSheet(label_style)
        grade_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        grade_label.setFixedWidth(50)
        search_layout.addWidget(grade_label, 1, 0)

        self.grade_combo = QComboBox()
        self.grade_combo.addItems(list(GRADES["shijuan1"].keys()))
        self.grade_combo.setStyleSheet("font-size: 13px; min-width: 90px; padding: 2px;")
        self.grade_combo.currentTextChanged.connect(self.on_grade_changed)
        search_layout.addWidget(self.grade_combo, 1, 1)

        search_layout.setColumnMinimumWidth(2, 15)

        year_label = QLabel("年份:")
        year_label.setStyleSheet(label_style)
        year_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        year_label.setFixedWidth(50)
        search_layout.addWidget(year_label, 1, 3)

        self.year_combo = QComboBox()
        self.year_combo.addItems(list(YEARS.keys()))
        self.year_combo.setStyleSheet("font-size: 13px; min-width: 90px; padding: 2px;")
        search_layout.addWidget(self.year_combo, 1, 4)

        keyword_label = QLabel("关键词:")
        keyword_label.setStyleSheet(label_style)
        keyword_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        keyword_label.setFixedWidth(50)
        search_layout.addWidget(keyword_label, 2, 0)

        self.keyword_edit = QLineEdit()
        self.keyword_edit.setPlaceholderText("如: 期末、期中、单元测...")
        self.keyword_edit.setStyleSheet("font-size: 13px; padding: 2px;")
        self.keyword_edit.returnPressed.connect(self.start_search)
        search_layout.addWidget(self.keyword_edit, 2, 1, 1, 4)

        main_layout.addWidget(search_group)

        result_group = QGroupBox("搜索结果")
        result_group.setStyleSheet("QGroupBox { font-size: 14px; font-family: 'Microsoft YaHei'; }")
        result_layout = QVBoxLayout(result_group)
        result_layout.setContentsMargins(3, 5, 3, 3)

        self.result_table = QTableWidget()
        self.result_table.setColumnCount(5)
        self.result_table.setHorizontalHeaderLabels(["平台", "标题", "学科", "年级", "操作"])
        self.result_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.result_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.result_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.result_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.result_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self.result_table.setColumnWidth(0, 70)
        self.result_table.setColumnWidth(2, 60)
        self.result_table.setColumnWidth(3, 60)
        self.result_table.setColumnWidth(4, 90)
        self.result_table.horizontalHeader().setStretchLastSection(False)
        self.result_table.verticalHeader().setVisible(False)
        self.result_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.result_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.result_table.verticalHeader().setDefaultSectionSize(35)
        self.result_table.setStyleSheet("""
            QTableWidget {
                font-size: 13px;
                gridline-color: #dee2e6;
            }
            QTableWidget::item {
                padding: 3px;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 5px;
                border: 1px solid #dee2e6;
                font-weight: bold;
            }
            QHeaderView {
                border: none;
            }
        """)
        result_layout.addWidget(self.result_table)

        main_layout.addWidget(result_group, 1)

        bottom_layout = QVBoxLayout()
        bottom_layout.setSpacing(5)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_clear = QPushButton("清空结果")
        self.btn_clear.setFixedSize(80, 32)
        self.btn_clear.setStyleSheet("""
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
        self.btn_clear.clicked.connect(self.clear_results)
        btn_layout.addWidget(self.btn_clear)

        self.btn_search = QPushButton("开始搜索")
        self.btn_search.setFixedSize(100, 32)
        self.btn_search.setStyleSheet("""
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
        self.btn_search.clicked.connect(self.start_search)
        btn_layout.addWidget(self.btn_search)

        self.btn_stop = QPushButton("停止搜索")
        self.btn_stop.setFixedSize(80, 32)
        self.btn_stop.setStyleSheet("""
            QPushButton {
                font-size: 13px;
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:disabled {
                background-color: #adb5bd;
            }
        """)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_search)
        btn_layout.addWidget(self.btn_stop)

        bottom_layout.addLayout(btn_layout)

        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #666; font-size: 12px; padding: 2px;")
        bottom_layout.addWidget(self.status_label)

        main_layout.addLayout(bottom_layout)

    def on_platform_changed(self, platform_name):
        platform_key = PLATFORMS.get(platform_name, "shijuan1")
        subjects = SUBJECTS.get(platform_key, SUBJECTS["shijuan1"])
        grades = GRADES.get(platform_key, GRADES["shijuan1"])
        
        self.subject_combo.blockSignals(True)
        self.subject_combo.clear()
        self.subject_combo.addItems(list(subjects.keys()))
        self.subject_combo.blockSignals(False)
        
        self.grade_combo.blockSignals(True)
        self.grade_combo.clear()
        self.grade_combo.addItems(list(grades.keys()))
        self.grade_combo.blockSignals(False)
        
        self.keyword_edit.clear()
        
        self.update_subjects_by_grade()

    def on_grade_changed(self, grade_name):
        self.update_subjects_by_grade()

    def update_subjects_by_grade(self):
        platform_name = self.platform_combo.currentText()
        platform_key = PLATFORMS.get(platform_name, "shijuan1")
        
        if platform_key != "yishijuan":
            return
        
        grade_name = self.grade_combo.currentText()
        grade_key = GRADES["yishijuan"].get(grade_name, "")
        
        if not grade_key:
            return
        
        grade_int = int(grade_key)
        
        self.subject_combo.blockSignals(True)
        self.subject_combo.clear()
        
        if grade_int <= 2:
            self.subject_combo.addItems(["语文试卷", "数学试卷", "英语试卷", "全科试卷"])
        elif grade_int <= 6:
            self.subject_combo.addItems(["语文试卷", "数学试卷", "英语试卷", "科学试卷", "全科试卷"])
        else:
            self.subject_combo.addItems(["语文试卷", "数学试卷", "英语试卷", "物理试卷", "地理试卷", 
                                        "生物试卷", "历史试卷", "化学试卷", "道德与法治", "全科试卷"])
        
        self.subject_combo.blockSignals(False)

    def start_search(self):
        if self.search_worker and self.search_worker.isRunning():
            return

        platform = PLATFORMS.get(self.platform_combo.currentText(), "")
        platform_subjects = SUBJECTS.get(platform, SUBJECTS["shijuan1"])
        platform_grades = GRADES.get(platform, GRADES["shijuan1"])
        subject = platform_subjects.get(self.subject_combo.currentText(), "")
        grade = platform_grades.get(self.grade_combo.currentText(), "")
        year = YEARS.get(self.year_combo.currentText(), "")
        keyword = self.keyword_edit.text().strip()

        if not self.validate_subject_grade(platform, subject, grade):
            return

        self.result_table.setRowCount(0)
        self.search_results = []
        self.result_count = 0

        self.btn_search.setEnabled(False)
        self.btn_search.setText("搜索中...")
        self.btn_stop.setEnabled(True)
        self.status_label.setText("正在搜索...")

        self.search_worker = SearchWorker(platform, subject, grade, year, keyword)
        self.search_worker.result_found.connect(self.on_result_found)
        self.search_worker.finished.connect(self.on_search_finished)
        self.search_worker.error.connect(self.on_search_error)
        self.search_worker.start()

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
                QMessageBox.warning(self, "年级学段不匹配", 
                    f"选择的年级和学段不匹配！\n\n"
                    f"年级: {grade_display}\n"
                    f"{grade_display}属于{grade_level}，请选择对应学段的试卷。",
                    QMessageBox.Ok
                )
                return False

        if not subject or subject == "":
            return True

        subject_grade_map = PLATFORM_SUBJECT_GRADE_MAP.get(platform, {})
        valid_grades = subject_grade_map.get(subject, [])

        if valid_grades and grade not in valid_grades:
            subject_display = SUBJECT_DISPLAY_MAP.get(platform, {}).get(subject, subject)
            grade_display = {v: k for k, v in GRADES.get(platform, GRADES["shijuan1"]).items()}.get(grade, grade)
            
            QMessageBox.warning(self, "学科年级不匹配", 
                f"选择的年级和学科不匹配！\n\n"
                f"年级: {grade_display}\n"
                f"学科: {subject_display}\n\n"
                f"{grade_display}没有{subject_display}学科，请选择其他学科。",
                QMessageBox.Ok
            )
            return False

        return True

    def stop_search(self):
        if self.search_worker and self.search_worker.isRunning():
            self.status_label.setText("正在停止...")
            self.search_worker.stop()
            self.btn_stop.setEnabled(False)
            QTimer.singleShot(1000, self.on_search_stopped)
    
    def on_search_stopped(self):
        if self.search_worker:
            self.search_worker.wait(2000)
            self.btn_search.setEnabled(True)
            self.btn_search.setText("开始搜索")
            self.btn_stop.setEnabled(False)
            self.status_label.setText(f"搜索已停止，共找到 {len(self.search_results)} 个结果")
            self.search_worker = None

    def on_result_found(self, item):
        self.result_count += 1
        self.search_results.append(item)

        row = self.result_table.rowCount()
        self.result_table.insertRow(row)

        self.result_table.setItem(row, 0, QTableWidgetItem(item.get("platform", "")))
        
        title = item.get("title", "")
        title_item = QTableWidgetItem(title)
        title_item.setToolTip(title)
        self.result_table.setItem(row, 1, title_item)
        
        self.result_table.setItem(row, 2, QTableWidgetItem(item.get("subject", "")))
        self.result_table.setItem(row, 3, QTableWidgetItem(item.get("grade", "")))

        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setContentsMargins(2, 2, 2, 2)

        open_btn = QPushButton("预览下载")
        open_btn.setFixedSize(75, 25)
        open_btn.setStyleSheet("""
            QPushButton {
                font-size: 11px;
                background-color: #4dabf7;
                color: white;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #339af0;
            }
        """)
        open_btn.clicked.connect(lambda _, r=item: self.open_link(r))
        btn_layout.addWidget(open_btn)

        self.result_table.setCellWidget(row, 4, btn_widget)

        self.status_label.setText(f"已找到 {self.result_count} 个结果...")

    def on_search_finished(self, results):
        self.search_results = results
        
        self.btn_search.setEnabled(True)
        self.btn_search.setText("开始搜索")
        self.btn_stop.setEnabled(False)
        self.status_label.setText(f"搜索完成，共找到 {len(results)} 个结果")
        
        self.search_worker = None

    def on_search_error(self, error_msg):
        self.btn_search.setEnabled(True)
        self.btn_search.setText("开始搜索")
        self.btn_stop.setEnabled(False)
        self.status_label.setText(f"搜索出错: {error_msg}")
        
        self.search_worker = None

    def display_results(self, results):
        self.result_table.setRowCount(0)

        for i, item in enumerate(results):
            self.result_table.insertRow(i)
            
            self.result_table.setItem(i, 0, QTableWidgetItem(item.get("platform", "")))
            
            title = item.get("title", "")
            title_item = QTableWidgetItem(title)
            title_item.setToolTip(title)
            self.result_table.setItem(i, 1, title_item)
            
            self.result_table.setItem(i, 2, QTableWidgetItem(item.get("subject", "")))
            self.result_table.setItem(i, 3, QTableWidgetItem(item.get("grade", "")))

            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(2, 2, 2, 2)

            open_btn = QPushButton("预览下载")
            open_btn.setFixedSize(75, 25)
            open_btn.setStyleSheet("""
                QPushButton {
                    font-size: 11px;
                    background-color: #4dabf7;
                    color: white;
                    border: none;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #339af0;
                }
            """)
            open_btn.clicked.connect(lambda _, r=item: self.open_link(r))
            btn_layout.addWidget(open_btn)

            self.result_table.setCellWidget(i, 4, btn_widget)

        self.result_table.setColumnWidth(0, 70)
        self.result_table.setColumnWidth(2, 60)
        self.result_table.setColumnWidth(3, 60)
        self.result_table.setColumnWidth(4, 90)

    def open_link(self, item):
        import webbrowser
        url = item.get("url", "")
        if url:
            webbrowser.open(url)
            self.status_label.setText(f"正在打开: {item.get('title', '')[:30]}...")

    def clear_results(self):
        self.result_table.setRowCount(0)
        self.search_results = []
        self.status_label.setText("已清空结果")

    def closeEvent(self, event):
        if self.search_worker:
            self.search_worker.stop()
            self.search_worker.wait()
        event.accept()