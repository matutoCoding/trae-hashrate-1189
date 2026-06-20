from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox, QSpinBox,
    QTextEdit, QDialogButtonBox, QMessageBox, QLabel
)


class MusicPieceDialog(QDialog):
    def __init__(self, scheduler, parent=None, piece=None):
        super().__init__(parent)
        self.scheduler = scheduler
        self.piece = piece
        self.setWindowTitle("编辑曲目" if piece else "添加曲目")
        self.resize(500, 550)
        self._init_ui()

    def _init_ui(self):
        layout = QFormLayout(self)

        self.name_edit = QLineEdit()
        layout.addRow(QLabel("曲目名称:"), self.name_edit)

        self.composer_edit = QLineEdit()
        layout.addRow(QLabel("作曲家:"), self.composer_edit)

        self.style_combo = QComboBox()
        self.style_combo.addItems(["", "传统", "现代", "流行", "古典", "民间", "摇滚", "爵士"])
        layout.addRow(QLabel("风格:"), self.style_combo)

        self.difficulty_combo = QComboBox()
        self.difficulty_combo.addItems(["", "入门", "初级", "中级", "高级", "专业"])
        layout.addRow(QLabel("难度级别:"), self.difficulty_combo)

        self.exam_category_combo = QComboBox()
        self.exam_category_combo.addItems([
            "", "中央音乐学院", "中国音乐学院", "上海音乐学院",
            "中国音乐家协会", "中国民族管弦乐学会"
        ])
        layout.addRow(QLabel("考级类别:"), self.exam_category_combo)

        self.exam_level_combo = QComboBox()
        self.exam_level_combo.addItems([
            "", "一级", "二级", "三级", "四级", "五级",
            "六级", "七级", "八级", "九级", "十级"
        ])
        layout.addRow(QLabel("考级级别:"), self.exam_level_combo)

        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 300)
        self.duration_spin.setSuffix(" 分钟")
        layout.addRow(QLabel("时长:"), self.duration_spin)

        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(120)
        layout.addRow(QLabel("描述:"), self.description_edit)

        if self.piece:
            self.name_edit.setText(self.piece.name)
            self.composer_edit.setText(self.piece.composer or "")
            idx = self.style_combo.findText(self.piece.style or "")
            if idx >= 0:
                self.style_combo.setCurrentIndex(idx)
            idx = self.difficulty_combo.findText(self.piece.difficulty_level or "")
            if idx >= 0:
                self.difficulty_combo.setCurrentIndex(idx)
            idx = self.exam_category_combo.findText(self.piece.exam_category or "")
            if idx >= 0:
                self.exam_category_combo.setCurrentIndex(idx)
            idx = self.exam_level_combo.findText(self.piece.exam_level or "")
            if idx >= 0:
                self.exam_level_combo.setCurrentIndex(idx)
            if self.piece.duration_minutes:
                self.duration_spin.setValue(self.piece.duration_minutes)
            self.description_edit.setPlainText(self.piece.description or "")

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def accept(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入曲目名称")
            return

        try:
            style = self.style_combo.currentText() or None
            difficulty = self.difficulty_combo.currentText() or None
            exam_category = self.exam_category_combo.currentText() or None
            exam_level = self.exam_level_combo.currentText() or None

            if self.piece:
                self.scheduler.update_music_piece(
                    self.piece.id,
                    name=name,
                    composer=self.composer_edit.text().strip() or None,
                    style=style,
                    difficulty_level=difficulty,
                    exam_category=exam_category,
                    exam_level=exam_level,
                    duration_minutes=self.duration_spin.value() if self.duration_spin.value() > 0 else None,
                    description=self.description_edit.toPlainText().strip() or None
                )
            else:
                self.scheduler.add_music_piece(
                    name=name,
                    composer=self.composer_edit.text().strip() or None,
                    style=style,
                    difficulty_level=difficulty,
                    exam_category=exam_category,
                    exam_level=exam_level,
                    duration_minutes=self.duration_spin.value() if self.duration_spin.value() > 0 else None,
                    description=self.description_edit.toPlainText().strip() or None
                )
            super().accept()
        except Exception as e:
            QMessageBox.warning(self, "错误", str(e))
