import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget,
                             QVBoxLayout, QWidget)
# 导入各子页面
from shuxue_ui import ShuxueTabWidget
from zi_tie_ui import ZiTieTabWidget
from zuowen_ui import ZuowenTabWidget
from zhenti_ui import ZhentiTabWidget  # 新增真题下载


class MathGeneratorUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("小学出题工具箱")
        self.setFixedSize(750, 750)
        self.center()
        self.init_ui()

    def center(self):
        """将窗口移动到屏幕中央"""
        screen = QApplication.desktop().screenGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(5)

        # 顶部标签栏
        self.tab_bar = QTabWidget()
        self.tab_bar.setStyleSheet("""
            QTabWidget {
                font-family: 'Microsoft YaHei', 'SimHei';
                font-size: 13px;
                background-color: #f8f9fa;
            }
            QTabWidget::pane {
                border: 1px solid #e1e4e8;
                border-radius: 8px;
                background-color: white;
                margin-top: 5px;
            }
            QTabBar::tab {
                font-size: 14px;
                font-family: 'Microsoft YaHei', 'SimHei';
                padding: 8px 16px;
                margin-right: 3px;
                min-width: 50px;
                height: 15px;
                border-radius: 8px 8px 0 0;
                background-color: #e9ecef;
                color: #495057;
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                          stop:0 #4dabf7, stop:1 #339af0);
                color: white;
                border: 1px solid #339af0;
                border-bottom: none;
            }
            QTabBar::tab:hover:!selected {
                background-color: #dee2e6;
                color: #212529;
            }
        """)

        # 数学标签页
        self.math_tab = ShuxueTabWidget()
        self.tab_bar.addTab(self.math_tab, "数学")

        # 字帖标签页
        self.zitie_tab = ZiTieTabWidget()
        self.tab_bar.addTab(self.zitie_tab, "字帖")

        # 作文标签页
        self.zuowen_tab = ZuowenTabWidget()
        self.tab_bar.addTab(self.zuowen_tab, "作文")

        # 真题下载标签页
        self.zhenti_tab = ZhentiTabWidget()
        self.tab_bar.addTab(self.zhenti_tab, "真题下载")

        main_layout.addWidget(self.tab_bar)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MathGeneratorUI()
    window.show()
    sys.exit(app.exec_())
