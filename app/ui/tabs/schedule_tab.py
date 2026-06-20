from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QComboBox, QDateEdit, QMessageBox, QHeaderView,
    QDialog, QFormLayout, QLineEdit, QSpinBox, QDateTimeEdit, QTextEdit,
    QSplitter, QGroupBox, QListWidget, QListWidgetItem, QAbstractItemView
)
from PySide6.QtCore import Qt, QDate
from datetime import datetime, timedelta
from app.database.models import Schedule, Enrollment
from app.ui.dialogs.schedule_dialog import ScheduleDialog
from app.ui.dialogs.enroll_dialog import EnrollDialog


class ScheduleTab(QWidget):
    def __init__(self, scheduler, recommender, waitlist):
        super().__init__()
        self.scheduler = scheduler
        self.recommender = recommender
        self.waitlist = waitlist
        self.current_schedules = []
        self._init_ui()
        self.load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("日期范围:"))

        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate())
        self.start_date.setCalendarPopup(True)
        filter_layout.addWidget(self.start_date)

        filter_layout.addWidget(QLabel("至"))

        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate().addDays(30))
        self.end_date.setCalendarPopup(True)
        filter_layout.addWidget(self.end_date)

        filter_layout.addWidget(QLabel("状态:"))
        self.status_combo = QComboBox()
        self.status_combo.addItems(["全部", "scheduled", "in_progress", "completed", "cancelled"])
        filter_layout.addWidget(self.status_combo)

        filter_layout.addWidget(QLabel("琴室:"))
        self.room_combo = QComboBox()
        self.room_combo.addItem("全部", None)
        filter_layout.addWidget(self.room_combo)

        filter_layout.addWidget(QLabel("老师:"))
        self.teacher_combo = QComboBox()
        self.teacher_combo.addItem("全部", None)
        filter_layout.addWidget(self.teacher_combo)

        self.search_btn = QPushButton("查询")
        self.search_btn.clicked.connect(self.load_data)
        filter_layout.addWidget(self.search_btn)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        splitter = QSplitter(Qt.Horizontal)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("新增排课")
        self.add_btn.clicked.connect(self.add_schedule)
        btn_layout.addWidget(self.add_btn)

        self.edit_btn = QPushButton("编辑")
        self.edit_btn.clicked.connect(self.edit_schedule)
        btn_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("删除")
        self.delete_btn.clicked.connect(self.delete_schedule)
        btn_layout.addWidget(self.delete_btn)

        left_layout.addLayout(btn_layout)

        self.schedule_table = QTableWidget()
        self.schedule_table.setColumnCount(7)
        self.schedule_table.setHorizontalHeaderLabels([
            "ID", "课程名称", "类型", "琴室", "老师", "时间", "人数"
        ])
        self.schedule_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.schedule_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.schedule_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.schedule_table.itemSelectionChanged.connect(self.on_schedule_selected)
        left_layout.addWidget(self.schedule_table, 1)

        splitter.addWidget(left_panel)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        info_group = QGroupBox("课程详情")
        info_layout = QFormLayout(info_group)
        self.detail_labels = {}
        for key in ["course_name", "course_type", "room", "teacher", "time", "students", "status", "notes"]:
            label = QLabel("-")
            label.setWordWrap(True)
            self.detail_labels[key] = label
            info_layout.addRow(QLabel(f"{key}:"), label)
        right_layout.addWidget(info_group)

        enroll_group = QGroupBox("已报名学员")
        enroll_layout = QVBoxLayout(enroll_group)

        enroll_btn_layout = QHBoxLayout()
        self.enroll_btn = QPushButton("报名")
        self.enroll_btn.clicked.connect(self.enroll_student)
        enroll_btn_layout.addWidget(self.enroll_btn)

        self.confirm_btn = QPushButton("确认")
        self.confirm_btn.clicked.connect(self.confirm_enrollment)
        enroll_btn_layout.addWidget(self.confirm_btn)

        self.checkin_btn = QPushButton("签到")
        self.checkin_btn.clicked.connect(self.checkin_student)
        enroll_btn_layout.addWidget(self.checkin_btn)

        self.cancel_enroll_btn = QPushButton("取消")
        self.cancel_enroll_btn.clicked.connect(self.cancel_enrollment)
        enroll_btn_layout.addWidget(self.cancel_enroll_btn)

        enroll_layout.addLayout(enroll_btn_layout)

        self.enrollment_list = QListWidget()
        enroll_layout.addWidget(self.enrollment_list, 1)

        right_layout.addWidget(enroll_group, 1)

        splitter.addWidget(right_panel)
        splitter.setSizes([700, 500])

        layout.addWidget(splitter, 1)

    def load_data(self):
        self._load_filters()

        start_dt = datetime.combine(self.start_date.date().toPython(), datetime.min.time())
        end_dt = datetime.combine(self.end_date.date().toPython(), datetime.max.time())

        status = self.status_combo.currentText()
        if status == "全部":
            status = None

        room_id = self.room_combo.currentData()
        teacher_id = self.teacher_combo.currentData()

        self.current_schedules = self.scheduler.get_schedules(
            start_date=start_dt,
            end_date=end_dt,
            status=status,
            room_id=room_id,
            teacher_id=teacher_id
        )

        self.schedule_table.setRowCount(len(self.current_schedules))
        for row, schedule in enumerate(self.current_schedules):
            self.schedule_table.setItem(row, 0, QTableWidgetItem(str(schedule.id)))
            self.schedule_table.setItem(row, 1, QTableWidgetItem(schedule.course_name))
            self.schedule_table.setItem(row, 2, QTableWidgetItem(schedule.course_type or "-"))
            self.schedule_table.setItem(row, 3, QTableWidgetItem(schedule.room.name if schedule.room else "-"))
            self.schedule_table.setItem(row, 4, QTableWidgetItem(schedule.teacher.name if schedule.teacher else "-"))
            time_str = f"{schedule.start_time.strftime('%m-%d %H:%M')} - {schedule.end_time.strftime('%H:%M')}"
            self.schedule_table.setItem(row, 5, QTableWidgetItem(time_str))
            students_str = f"{schedule.current_students}/{schedule.max_students}"
            self.schedule_table.setItem(row, 6, QTableWidgetItem(students_str))

        self._update_detail_panel()
        self._load_enrollments()

    def _load_filters(self):
        current_room = self.room_combo.currentData()
        current_teacher = self.teacher_combo.currentData()

        self.room_combo.clear()
        self.room_combo.addItem("全部", None)
        for room in self.scheduler.get_all_rooms("active"):
            self.room_combo.addItem(room.name, room.id)

        self.teacher_combo.clear()
        self.teacher_combo.addItem("全部", None)
        for teacher in self.scheduler.get_all_teachers("active"):
            self.teacher_combo.addItem(teacher.name, teacher.id)

        if current_room:
            idx = self.room_combo.findData(current_room)
            if idx >= 0:
                self.room_combo.setCurrentIndex(idx)
        if current_teacher:
            idx = self.teacher_combo.findData(current_teacher)
            if idx >= 0:
                self.teacher_combo.setCurrentIndex(idx)

    def on_schedule_selected(self):
        self._update_detail_panel()
        self._load_enrollments()

    def _get_selected_schedule(self):
        current_row = self.schedule_table.currentRow()
        if current_row >= 0 and current_row < len(self.current_schedules):
            return self.current_schedules[current_row]
        return None

    def _update_detail_panel(self):
        schedule = self._get_selected_schedule()
        if not schedule:
            for label in self.detail_labels.values():
                label.setText("-")
            return

        self.detail_labels["course_name"].setText(schedule.course_name)
        self.detail_labels["course_type"].setText(schedule.course_type or "-")
        self.detail_labels["room"].setText(schedule.room.name if schedule.room else "-")
        self.detail_labels["teacher"].setText(schedule.teacher.name if schedule.teacher else "-")
        time_str = f"{schedule.start_time.strftime('%Y-%m-%d %H:%M')} - {schedule.end_time.strftime('%H:%M')}"
        self.detail_labels["time"].setText(time_str)
        self.detail_labels["students"].setText(f"{schedule.current_students}/{schedule.max_students}")
        self.detail_labels["status"].setText(schedule.status)
        self.detail_labels["notes"].setText(schedule.notes or "-")

    def _load_enrollments(self):
        self.enrollment_list.clear()
        schedule = self._get_selected_schedule()
        if not schedule:
            return

        enrollments = self.scheduler.get_enrollments(schedule_id=schedule.id)
        for enroll in enrollments:
            student = self.scheduler.db.get_by_id(type(enroll.student), enroll.student_id)
            if student:
                text = f"[{enroll.status}] {student.name} - 报名:{enroll.enroll_time.strftime('%H:%M')}"
                item = QListWidgetItem(text)
                item.setData(Qt.UserRole, enroll.id)
                self.enrollment_list.addItem(item)

    def add_schedule(self):
        dialog = ScheduleDialog(self.scheduler, self)
        if dialog.exec() == QDialog.Accepted:
            self.load_data()
            QMessageBox.information(self, "成功", "排课创建成功")

    def edit_schedule(self):
        schedule = self._get_selected_schedule()
        if not schedule:
            QMessageBox.warning(self, "提示", "请先选择要编辑的课程")
            return

        dialog = ScheduleDialog(self.scheduler, self, schedule)
        if dialog.exec() == QDialog.Accepted:
            self.load_data()
            QMessageBox.information(self, "成功", "排课更新成功")

    def delete_schedule(self):
        schedule = self._get_selected_schedule()
        if not schedule:
            QMessageBox.warning(self, "提示", "请先选择要删除的课程")
            return

        reply = QMessageBox.question(self, "确认", f"确定要删除课程「{schedule.course_name}」吗？")
        if reply == QMessageBox.Yes:
            if self.scheduler.delete_schedule(schedule.id):
                self.load_data()
                QMessageBox.information(self, "成功", "删除成功")

    def enroll_student(self):
        schedule = self._get_selected_schedule()
        if not schedule:
            QMessageBox.warning(self, "提示", "请先选择课程")
            return

        if schedule.current_students >= schedule.max_students:
            QMessageBox.warning(self, "提示", "课程已满，学员将加入候补队列")

        dialog = EnrollDialog(self.scheduler, self.recommender, self.waitlist, schedule, self)
        if dialog.exec() == QDialog.Accepted:
            self.load_data()
            QMessageBox.information(self, "成功", "操作成功")

    def _get_selected_enrollment(self):
        item = self.enrollment_list.currentItem()
        if item:
            return item.data(Qt.UserRole)
        return None

    def confirm_enrollment(self):
        enroll_id = self._get_selected_enrollment()
        if not enroll_id:
            QMessageBox.warning(self, "提示", "请先选择要确认的报名记录")
            return

        if self.scheduler.confirm_enrollment(enroll_id):
            self.load_data()
            QMessageBox.information(self, "成功", "确认成功")

    def checkin_student(self):
        enroll_id = self._get_selected_enrollment()
        if not enroll_id:
            QMessageBox.warning(self, "提示", "请先选择要签到的报名记录")
            return

        if self.scheduler.checkin_student(enroll_id):
            self.load_data()
            QMessageBox.information(self, "成功", "签到成功")

    def cancel_enrollment(self):
        enroll_id = self._get_selected_enrollment()
        if not enroll_id:
            QMessageBox.warning(self, "提示", "请先选择要取消的报名记录")
            return

        reply = QMessageBox.question(self, "确认", "确定要取消该报名吗？")
        if reply == QMessageBox.Yes:
            if self.scheduler.cancel_enrollment(enroll_id):
                self.load_data()
                QMessageBox.information(self, "成功", "已取消")
