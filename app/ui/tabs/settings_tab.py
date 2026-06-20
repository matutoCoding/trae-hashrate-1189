from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QSpinBox, QPushButton, QCheckBox, QMessageBox, QComboBox,
    QApplication
)
from PySide6.QtCore import Qt


class SettingsTab(QWidget):
    def __init__(self, settings, recommender):
        super().__init__()
        self.settings = settings
        self.recommender = recommender
        self._init_ui()
        self.load_settings()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        general_group = QGroupBox("常规设置")
        general_layout = QFormLayout(general_group)

        theme_layout = QHBoxLayout()
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["light", "dark"])
        theme_layout.addWidget(self.theme_combo)

        self.apply_theme_btn = QPushButton("应用主题")
        self.apply_theme_btn.clicked.connect(self.apply_theme)
        theme_layout.addWidget(self.apply_theme_btn)
        general_layout.addRow(QLabel("主题:"), theme_layout)

        auto_release_layout = QHBoxLayout()
        self.auto_release_spin = QSpinBox()
        self.auto_release_spin.setRange(1, 120)
        self.auto_release_spin.setSuffix(" 分钟")
        auto_release_layout.addWidget(self.auto_release_spin)
        auto_release_layout.addWidget(QLabel("（报名后超时未确认自动释放名额）"))
        general_layout.addRow(QLabel("自动释放时间:"), auto_release_layout)

        self.notification_check = QCheckBox("启用通知")
        general_layout.addRow(QLabel("通知:"), self.notification_check)

        layout.addWidget(general_group)

        weights_group = QGroupBox("推荐权重配置")
        weights_layout = QFormLayout(weights_group)
        weights_layout.addRow(QLabel("以下权重之和必须等于 1.0"))

        from PySide6.QtWidgets import QDoubleSpinBox
        self.weight_spins = {}
        weight_labels = {
            "style_match": "曲风匹配权重:",
            "rating": "老师评分权重:",
            "level_match": "级别匹配权重:",
            "availability": "时间可用权重:",
            "experience": "教学经验权重:"
        }

        for key, label_text in weight_labels.items():
            spin = QDoubleSpinBox()
            spin.setRange(0.0, 1.0)
            spin.setSingleStep(0.05)
            spin.setDecimals(2)
            self.weight_spins[key] = spin
            weights_layout.addRow(QLabel(label_text), spin)

        self.total_label = QLabel("当前权重和: 0.00")
        self.total_label.setStyleSheet("font-weight: bold;")
        weights_layout.addRow(QLabel(""), self.total_label)

        for spin in self.weight_spins.values():
            spin.valueChanged.connect(self.update_total_weight)

        btn_row = QHBoxLayout()
        self.save_weights_btn = QPushButton("保存权重")
        self.save_weights_btn.clicked.connect(self.save_weights)
        btn_row.addWidget(self.save_weights_btn)

        self.reset_weights_btn = QPushButton("重置默认")
        self.reset_weights_btn.clicked.connect(self.reset_weights)
        btn_row.addWidget(self.reset_weights_btn)
        weights_layout.addRow(btn_row)

        layout.addWidget(weights_group)

        info_group = QGroupBox("关于")
        info_layout = QVBoxLayout(info_group)
        info_label = QLabel(
            "古筝培训排课系统 v1.0\n\n"
            "功能模块：\n"
            "• 课程排期 - 琴室建档、课程管理\n"
            "• 候补补位 - 候补排队、自动补位\n"
            "• 多维推荐 - 智能匹配、权重可调\n"
            "• 撮合归档 - 历史记录、考级曲库\n\n"
            "© 2024 古筝培训管理系统"
        )
        info_label.setAlignment(Qt.AlignTop)
        info_layout.addWidget(info_label)
        layout.addWidget(info_group)

        layout.addStretch()

    def load_settings(self):
        theme = self.settings.get("theme", "light")
        idx = self.theme_combo.findText(theme)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)

        auto_release = self.settings.get("auto_release_minutes", 15)
        self.auto_release_spin.setValue(auto_release)

        notification = self.settings.get("notification_enabled", True)
        self.notification_check.setChecked(notification)

        weights = self.recommender.get_current_weights()
        for key, value in weights.items():
            if key in self.weight_spins:
                self.weight_spins[key].setValue(value)

        self.update_total_weight()

    def update_total_weight(self):
        total = sum(spin.value() for spin in self.weight_spins.values())
        self.total_label.setText(f"当前权重和: {total:.2f}")
        if abs(total - 1.0) > 0.01:
            self.total_label.setStyleSheet("color: red; font-weight: bold;")
        else:
            self.total_label.setStyleSheet("color: green; font-weight: bold;")

    def apply_theme(self):
        theme = self.theme_combo.currentText()
        self.settings.set("theme", theme)
        QApplication.instance().setStyleSheet(self.settings.get_stylesheet(theme))
        QMessageBox.information(self, "成功", f"已切换到{'深色' if theme == 'dark' else '浅色'}主题")

    def save_weights(self):
        new_weights = {}
        for key, spin in self.weight_spins.items():
            new_weights[key] = spin.value()

        try:
            self.recommender.update_weights(new_weights)
            QMessageBox.information(self, "成功", "权重配置已保存")
        except ValueError as e:
            QMessageBox.warning(self, "错误", str(e))

    def reset_weights(self):
        reply = QMessageBox.question(self, "确认", "确定要重置为默认权重吗？")
        if reply == QMessageBox.Yes:
            defaults = self.recommender.reset_weights()
            for key, value in defaults.items():
                if key in self.weight_spins:
                    self.weight_spins[key].setValue(value)
            self.update_total_weight()
            QMessageBox.information(self, "成功", "权重已重置为默认值")

    def save_settings(self):
        self.settings.set("auto_release_minutes", self.auto_release_spin.value())
        self.settings.set("notification_enabled", self.notification_check.isChecked())
