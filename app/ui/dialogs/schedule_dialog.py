from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox, QDateTimeEdit,
    QSpinBox, QTextEdit, QDialogButtonBox, QMessageBox, QLabel
)
from PySide6.QtCore import QDateTime
from datetime import datetime


class ScheduleDialog(QDialog):
    def __init__(self, scheduler, parent=None, schedule=None):
        super().__init__(parent)
        self.scheduler = scheduler
        self.schedule = schedule
        self.setWindowTitle("编辑排课" if schedule else "新增排课")
        self.resize(500, 600)
        self._init_ui()

    def _init_ui(self):
        layout = QFormLayout(self)

        self.course_name_edit = QLineEdit()
        layout.addRow(QLabel("课程名称:"), self.course_name_edit)

        self.course_type_combo = QComboBox()
        self.course_type_combo.addItems(["一对一", "小组课", "集体课", "考级辅导", "乐理课"])
        layout.addRow(QLabel("课程类型:"), self.course_type_combo)

        self.room_combo = QComboBox()
        for room in self.scheduler.get_all_rooms("active"):
            self.room_combo.addItem(room.name, room.id)
        layout.addRow(QLabel("琴室:"), self.room_combo)

        self.teacher_combo = QComboBox()
        for teacher in self.scheduler.get_all_teachers("active"):
            self.teacher_combo.addItem(teacher.name, teacher.id)
        layout.addRow(QLabel("老师:"), self.teacher_combo)

        self.start_time_edit = QDateTimeEdit()
        self.start_time_edit.setCalendarPopup(True)
        self.start_time_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.start_time_edit.setDateTime(QDateTime.currentDateTime())
        layout.addRow(QLabel("开始时间:"), self.start_time_edit)

        self.end_time_edit = QDateTimeEdit()
        self.end_time_edit.setCalendarPopup(True)
        self.end_time_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.end_time_edit.setDateTime(QDateTime.currentDateTime().addSecs(3600))
        layout.addRow(QLabel("结束时间:"), self.end_time_edit)

        self.max_students_spin = QSpinBox()
        self.max_students_spin.setRange(1, 20)
        self.max_students_spin.setValue(1)
        layout.addRow(QLabel("最大学员数:"), self.max_students_spin)

        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(100)
        layout.addRow(QLabel("备注:"), self.notes_edit)

        if self.schedule:
            self.course_name_edit.setText(self.schedule.course_name)
            idx = self.course_type_combo.findText(self.schedule.course_type or "一对一")
            if idx >= 0:
                self.course_type_combo.setCurrentIndex(idx)
            idx = self.room_combo.findData(self.schedule.room_id)
            if idx >= 0:
                self.room_combo.setCurrentIndex(idx)
            idx = self.teacher_combo.findData(self.schedule.teacher_id)
            if idx >= 0:
                self.teacher_combo.setCurrentIndex(idx)
            self.start_time_edit.setDateTime(QDateTime.fromString(self.schedule.start_time.strftime("%Y-%m-%d %H:%M"), "yyyy-MM-dd HH:mm"))
            self.end_time_edit.setDateTime(QDateTime.fromString(self.schedule.end_time.strftime("%Y-%m-%d %H:%M"), "yyyy-MM-dd HH:mm"))
            self.max_students_spin.setValue(self.schedule.max_students)
            self.notes_edit.setPlainText(self.schedule.notes or "")

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def accept(self):
        course_name = self.course_name_edit.text().strip()
        if not course_name:
            QMessageBox.warning(self, "提示", "请输入课程名称")
            return

        room_id = self.room_combo.currentData()
        teacher_id = self.teacher_combo.currentData()
        start_time = self.start_time_edit.dateTime().toPython()
        end_time = self.end_time_edit.dateTime().toPython()

        if start_time >= end_time:
            QMessageBox.warning(self, "提示", "结束时间必须晚于开始时间")
            return

        try:
            if self.schedule:
                self.scheduler.update_schedule(
                    self.schedule.id,
                    course_name=course_name,
                    course_type=self.course_type_combo.currentText(),
                    room_id=room_id,
                    teacher_id=teacher_id,
                    start_time=start_time,
                    end_time=end_time,
                    max_students=self.max_students_spin.value(),
                    notes=self.notes_edit.toPlainText()
                )
            else:
                self.scheduler.add_schedule(
                    room_id=room_id,
                    teacher_id=teacher_id,
                    course_name=course_name,
                    course_type=self.course_type_combo.currentText(),
                    start_time=start_time,
                    end_time=end_time,
                    max_students=self.max_students_spin.value(),
                    notes=self.notes_edit.toPlainText()
                )
            super().accept()
        except ValueError as e:
            QMessageBox.warning(self, "错误", str(e))
