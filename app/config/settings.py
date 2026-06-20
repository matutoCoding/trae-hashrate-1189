import json
import os
from pathlib import Path


class AppSettings:
    def __init__(self):
        self.config_dir = Path.home() / ".guzheng_scheduler"
        self.config_file = self.config_dir / "settings.json"
        self.default_settings = {
            "theme": "light",
            "auto_release_minutes": 15,
            "notification_enabled": True,
            "recommend_weights": {
                "style_match": 0.30,
                "rating": 0.25,
                "level_match": 0.25,
                "availability": 0.10,
                "experience": 0.10
            }
        }

        self.light_stylesheet = """
        QMainWindow, QWidget { background-color: #f5f5f5; color: #333; }
        QTabWidget::pane { border: 1px solid #ddd; background: white; }
        QTabBar::tab { padding: 8px 16px; background: #e0e0e0; margin-right: 2px; }
        QTabBar::tab:selected { background: #2196F3; color: white; }
        QPushButton { padding: 6px 16px; background: #2196F3; color: white; border: none; border-radius: 4px; }
        QPushButton:hover { background: #1976D2; }
        QPushButton:pressed { background: #1565C0; }
        QTableWidget { background: white; gridline-color: #e0e0e0; }
        QHeaderView::section { background: #f0f0f0; padding: 6px; border: none; border-bottom: 2px solid #2196F3; }
        QComboBox, QLineEdit, QTextEdit, QSpinBox, QDateEdit, QDateTimeEdit {
            padding: 6px; border: 1px solid #ddd; border-radius: 4px; background: white;
        }
        QComboBox:focus, QLineEdit:focus, QTextEdit:focus { border-color: #2196F3; }
        QGroupBox { border: 1px solid #ddd; border-radius: 4px; margin-top: 16px; padding-top: 16px; }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #666; }
        QMenuBar { background: #f0f0f0; }
        QMenuBar::item:selected { background: #2196F3; color: white; }
        QStatusBar { background: #e0e0e0; }
        """

        self.dark_stylesheet = """
        QMainWindow, QWidget { background-color: #1e1e1e; color: #e0e0e0; }
        QTabWidget::pane { border: 1px solid #444; background: #252525; }
        QTabBar::tab { padding: 8px 16px; background: #333; margin-right: 2px; color: #aaa; }
        QTabBar::tab:selected { background: #1976D2; color: white; }
        QPushButton { padding: 6px 16px; background: #1976D2; color: white; border: none; border-radius: 4px; }
        QPushButton:hover { background: #1E88E5; }
        QPushButton:pressed { background: #1565C0; }
        QTableWidget { background: #252525; gridline-color: #444; color: #e0e0e0; }
        QHeaderView::section { background: #333; padding: 6px; border: none; border-bottom: 2px solid #1976D2; color: #e0e0e0; }
        QComboBox, QLineEdit, QTextEdit, QSpinBox, QDateEdit, QDateTimeEdit {
            padding: 6px; border: 1px solid #555; border-radius: 4px; background: #2d2d2d; color: #e0e0e0;
            selection-background-color: #1976D2;
        }
        QComboBox:focus, QLineEdit:focus, QTextEdit:focus { border-color: #1976D2; }
        QGroupBox { border: 1px solid #444; border-radius: 4px; margin-top: 16px; padding-top: 16px; }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #aaa; }
        QMenuBar { background: #333; color: #e0e0e0; }
        QMenuBar::item:selected { background: #1976D2; color: white; }
        QMenu { background: #2d2d2d; color: #e0e0e0; }
        QMenu::item:selected { background: #1976D2; }
        QStatusBar { background: #333; color: #aaa; }
        QScrollBar:vertical { background: #333; width: 10px; }
        QScrollBar::handle:vertical { background: #555; min-height: 20px; }
        QScrollBar::handle:vertical:hover { background: #666; }
        """
        self._load_settings()

    def _load_settings(self):
        if not self.config_dir.exists():
            self.config_dir.mkdir(parents=True)
        if not self.config_file.exists():
            self._save_settings(self.default_settings)
        with open(self.config_file, "r", encoding="utf-8") as f:
            self.settings = json.load(f)
        for key, value in self.default_settings.items():
            if key not in self.settings:
                self.settings[key] = value

    def _save_settings(self, settings):
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings[key] = value
        self._save_settings(self.settings)

    def get_weight(self, weight_key):
        weights = self.settings.get("recommend_weights", {})
        return weights.get(weight_key, 0.0)

    def set_weight(self, weight_key, value):
        if "recommend_weights" not in self.settings:
            self.settings["recommend_weights"] = {}
        self.settings["recommend_weights"][weight_key] = value
        self._save_settings(self.settings)

    def get_all_weights(self):
        return self.settings.get("recommend_weights", self.default_settings["recommend_weights"])

    def set_all_weights(self, weights):
        self.settings["recommend_weights"] = weights
        self._save_settings(self.settings)

    def get_stylesheet(self, theme=None):
        if theme is None:
            theme = self.get("theme", "light")
        return self.dark_stylesheet if theme == "dark" else self.light_stylesheet
