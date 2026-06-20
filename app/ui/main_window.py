from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QPushButton, QStatusBar, QMenuBar, QMenu, QMessageBox,
    QDialog
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction
from app.config.settings import AppSettings
from app.ui.tabs.schedule_tab import ScheduleTab
from app.ui.tabs.waitlist_tab import WaitlistTab
from app.ui.tabs.recommend_tab import RecommendTab
from app.ui.tabs.archive_tab import ArchiveTab
from app.ui.tabs.settings_tab import SettingsTab
from app.ui.dialogs.data_manage_dialog import DataManageDialog


class MainWindow(QMainWindow):
    def __init__(self, db_manager, scheduler, recommender, waitlist):
        super().__init__()
        self.db = db_manager
        self.scheduler = scheduler
        self.recommender = recommender
        self.waitlist = waitlist
        self.settings = AppSettings()

        self.setWindowTitle("古筝培训排课系统")
        self.resize(1200, 800)

        self._init_menu()
        self._init_ui()
        self._init_timer()

    def _init_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("文件")
        manage_data_action = QAction("数据管理", self)
        manage_data_action.triggered.connect(self.open_data_manage)
        file_menu.addAction(manage_data_action)

        file_menu.addSeparator()
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        view_menu = menubar.addMenu("视图")
        self.theme_action = QAction("切换主题", self)
        self.theme_action.triggered.connect(self.toggle_theme)
        view_menu.addAction(self.theme_action)

        help_menu = menubar.addMenu("帮助")
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("古筝培训排课管理系统")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        header.addWidget(title)
        header.addStretch()

        self.refresh_btn = QPushButton("刷新数据")
        self.refresh_btn.clicked.connect(self.refresh_all_data)
        header.addWidget(self.refresh_btn)

        self.theme_btn = QPushButton("切换主题")
        self.theme_btn.clicked.connect(self.toggle_theme)
        header.addWidget(self.theme_btn)

        main_layout.addLayout(header)

        self.tabs = QTabWidget()
        self.schedule_tab = ScheduleTab(self.scheduler, self.recommender, self.waitlist)
        self.waitlist_tab = WaitlistTab(self.waitlist, self.scheduler)
        self.recommend_tab = RecommendTab(self.recommender, self.scheduler)
        self.archive_tab = ArchiveTab(self.scheduler)
        self.settings_tab = SettingsTab(self.settings, self.recommender)

        self.tabs.addTab(self.schedule_tab, "课程排期")
        self.tabs.addTab(self.waitlist_tab, "候补补位")
        self.tabs.addTab(self.recommend_tab, "多维推荐")
        self.tabs.addTab(self.archive_tab, "撮合归档")
        self.tabs.addTab(self.settings_tab, "系统设置")

        main_layout.addWidget(self.tabs, 1)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("系统就绪")

    def _init_timer(self):
        self.check_timer = QTimer(self)
        self.check_timer.timeout.connect(self.check_overdue)
        self.check_timer.start(60000)

    def check_overdue(self):
        try:
            released = self.scheduler.check_and_release_overdue()
            expired = self.waitlist.check_expired_notifications()
            archived = self.scheduler.archive_completed_courses()

            msg_parts = []
            if released:
                msg_parts.append(f"自动释放 {len(released)} 个超时名额")
            if expired:
                msg_parts.append(f"处理 {len(expired)} 个过期候补通知")
            if archived:
                msg_parts.append(f"归档 {archived} 个已完成课程")

            if msg_parts:
                self.status_bar.showMessage(" | ".join(msg_parts), 5000)
        except Exception as e:
            print(f"检查超时任务出错: {e}")

    def toggle_theme(self):
        current = self.settings.get("theme", "light")
        new_theme = "dark" if current == "light" else "light"
        self.settings.set("theme", new_theme)
        QApplication.instance().setStyleSheet(self.settings.get_stylesheet(new_theme))
        self.status_bar.showMessage(f"已切换到{'深色' if new_theme == 'dark' else '浅色'}主题", 3000)

    def open_data_manage(self):
        dialog = DataManageDialog(self.scheduler, self)
        dialog.exec()

    def refresh_all_data(self):
        self.schedule_tab.load_data()
        self.waitlist_tab.load_data()
        self.recommend_tab.load_data()
        self.archive_tab.load_data()
        self.status_bar.showMessage("数据已刷新", 3000)

    def show_about(self):
        QMessageBox.about(self, "关于", "古筝培训排课系统 v1.0\n\n"
                          "功能模块：\n"
                          "• 课程排期 - 琴室建档、课程管理\n"
                          "• 候补补位 - 候补排队、自动补位\n"
                          "• 多维推荐 - 智能匹配、权重可调\n"
                          "• 撮合归档 - 历史记录、考级曲库")
