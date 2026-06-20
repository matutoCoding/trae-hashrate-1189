import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from app.ui.main_window import MainWindow
from app.config.settings import AppSettings
from app.database.db_manager import DatabaseManager
from app.services.scheduler import SchedulerService
from app.services.recommender import RecommenderService
from app.services.waitlist import WaitlistService


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("古筝培训排课系统")
    app.setOrganizationName("GuZhengStudio")

    settings = AppSettings()
    theme = settings.get("theme", "light")
    app.setStyleSheet(settings.get_stylesheet(theme))

    db_manager = DatabaseManager()
    db_manager.init_db()

    scheduler = SchedulerService(db_manager)
    recommender = RecommenderService(db_manager)
    waitlist = WaitlistService(db_manager, scheduler)
    scheduler.set_release_callback(waitlist.auto_notify_next)

    window = MainWindow(db_manager, scheduler, recommender, waitlist)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
