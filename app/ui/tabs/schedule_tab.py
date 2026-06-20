from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QComboBox, QDateEdit, QMessageBox, QHeaderView,
    QDialog, QFormLayout, QLineEdit, QSpinBox, QDateTimeEdit, QTextEdit,
    QSplitter, QGroupBox, QListWidget, QListWidgetItem, QAbstractItemView,
    QProgressBar, QDialogButtonBox
)
from PySide6.QtCore import Qt, QDate
from datetime import datetime, timedelta
from app.database.models import Schedule, Enrollment, Student
from app.ui.dialogs.schedule_dialog import ScheduleDialog
from app.ui.dialogs.enroll_dialog import EnrollDialog


ENROLLMENT_STATUS_LABELS = {
    "pending": "待确认",
    "confirmed": "已确认",
    "checked_in": "已签到",
    "completed": "已完成",
    "cancelled": "已取消",
    "released": "已释放"
}

SCHEDULE_STATUS_LABELS = {
    "scheduled": "待上课",
    "in_progress": "进行中",
    "completed": "已完成",
    "cancelled": "已取消"
}

NOTIFY_SOURCE_LABELS = {
    "cancel_release": "取消释放",
    "expired_release": "过期释放",
    "manual": "手动处理"
}


class LessonReviewDialog(QDialog):
    def __init__(self, parent=None, review_data=None):
        super().__init__(parent)
        self.setWindowTitle("课后记录")
        self.resize(600, 500)
        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.lesson_content_edit = QTextEdit()
        self.lesson_content_edit.setPlaceholderText("本节课的学习内容，如：练习《渔舟唱晚》快板部分...")
        self.lesson_content_edit.setFixedHeight(100)
        form.addRow(QLabel("学习内容:"), self.lesson_content_edit)

        self.teacher_review_edit = QTextEdit()
        self.teacher_review_edit.setPlaceholderText("老师对本节课的点评...")
        self.teacher_review_edit.setFixedHeight(100)
        form.addRow(QLabel("老师点评:"), self.teacher_review_edit)

        self.next_homework_edit = QTextEdit()
        self.next_homework_edit.setPlaceholderText("下次课的作业要求...")
        self.next_homework_edit.setFixedHeight(100)
        form.addRow(QLabel("下次作业:"), self.next_homework_edit)

        self.suggested_pieces_edit = QLineEdit()
        self.suggested_pieces_edit.setPlaceholderText("建议练习的曲目名称，多个用逗号分隔")
        form.addRow(QLabel("建议曲目:"), self.suggested_pieces_edit)

        layout.addLayout(form)

        if review_data:
            if review_data.get("lesson_content"):
                self.lesson_content_edit.setPlainText(review_data["lesson_content"])
            if review_data.get("teacher_review"):
                self.teacher_review_edit.setPlainText(review_data["teacher_review"])
            if review_data.get("next_homework"):
                self.next_homework_edit.setPlainText(review_data["next_homework"])
            if review_data.get("suggested_pieces"):
                self.suggested_pieces_edit.setText(review_data["suggested_pieces"])

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_data(self):
        return {
            "lesson_content": self.lesson_content_edit.toPlainText().strip() or None,
            "teacher_review": self.teacher_review_edit.toPlainText().strip() or None,
            "next_homework": self.next_homework_edit.toPlainText().strip() or None,
            "suggested_pieces": self.suggested_pieces_edit.text().strip() or None
        }


class ScheduleTab(QWidget):
    def __init__(self, scheduler, recommender, waitlist):
        super().__init__()
        self.scheduler = scheduler
        self.recommender = recommender
        self.waitlist = waitlist
        self.current_schedules = []
        self.current_enrollments = []
        self._after_enrollment_change_callback = None
        self._progress_cache = {}
        self._init_ui()
        self.load_data()

    def set_after_enrollment_change_callback(self, callback):
        self._after_enrollment_change_callback = callback

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
        for key, label in SCHEDULE_STATUS_LABELS.items():
            self.status_combo.addItem(label, key)
        self.status_combo.insertItem(0, "全部", "all")
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
        self.schedule_table.setColumnCount(9)
        self.schedule_table.setHorizontalHeaderLabels([
            "ID", "课程名称", "类型", "琴室", "老师", "时间", "人数", "课程进度", "课程状态"
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
        for key, label_text in [("course_name", "课程名称"), ("course_type", "课程类型"), ("room", "琴室"), ("teacher", "老师"), ("time", "时间"), ("students", "报名人数"), ("status", "课程状态"), ("notes", "备注")]:
            label = QLabel("-")
            label.setWordWrap(True)
            self.detail_labels[key] = label
            info_layout.addRow(QLabel(f"{label_text}:"), label)
        right_layout.addWidget(info_group)

        progress_group = QGroupBox("上课进度")
        progress_layout = QFormLayout(progress_group)

        self.progress_status_label = QLabel("-")
        self.progress_status_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        progress_layout.addRow(QLabel("进度状态:"), self.progress_status_label)

        progress_row = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(True)
        self.progress_count_label = QLabel("")
        progress_row.addWidget(self.progress_bar, 1)
        progress_row.addWidget(self.progress_count_label)
        progress_layout.addRow(QLabel("完成进度:"), progress_row)

        self.breakdown_label = QLabel("")
        self.breakdown_label.setStyleSheet("color: #555;")
        self.breakdown_label.setWordWrap(True)
        progress_layout.addRow(QLabel("明细:"), self.breakdown_label)

        self.review_hint_label = QLabel("")
        self.review_hint_label.setStyleSheet("color: #1976D2;")
        progress_layout.addRow(self.review_hint_label)

        right_layout.addWidget(progress_group)

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

        self.complete_btn = QPushButton("完成")
        self.complete_btn.clicked.connect(self.complete_enrollment)
        enroll_btn_layout.addWidget(self.complete_btn)

        self.cancel_enroll_btn = QPushButton("取消")
        self.cancel_enroll_btn.clicked.connect(self.cancel_enrollment)
        enroll_btn_layout.addWidget(self.cancel_enroll_btn)

        self.review_btn = QPushButton("课后记录")
        self.review_btn.clicked.connect(self.open_lesson_review)
        self.review_btn.setStyleSheet("background: #E3F2FD;")
        enroll_btn_layout.addWidget(self.review_btn)

        enroll_layout.addLayout(enroll_btn_layout)

        self.enrollment_list = QListWidget()
        enroll_layout.addWidget(self.enrollment_list, 1)

        right_layout.addWidget(enroll_group, 1)

        splitter.addWidget(right_panel)
        splitter.setSizes([700, 500])

        layout.addWidget(splitter, 1)

    def load_data(self):
        self._progress_cache.clear()
        self._load_filters()

        start_dt = datetime.combine(self.start_date.date().toPython(), datetime.min.time())
        end_dt = datetime.combine(self.end_date.date().toPython(), datetime.max.time())

        status_data = self.status_combo.currentData()
        status = None if status_data == "all" else status_data

        room_id = self.room_combo.currentData()
        teacher_id = self.teacher_combo.currentData()

        self.current_schedules = self.scheduler.get_schedules(
            start_date=start_dt, end_date=end_dt, status=status,
            room_id=room_id, teacher_id=teacher_id
        )

        self.schedule_table.setRowCount(len(self.current_schedules))
        for row, schedule in enumerate(self.current_schedules):
            progress = self.scheduler.get_schedule_progress(schedule.id)
            if progress:
                self._progress_cache[schedule.id] = progress

            self.schedule_table.setItem(row, 0, QTableWidgetItem(str(schedule.id)))
            self.schedule_table.setItem(row, 1, QTableWidgetItem(schedule.course_name))
            self.schedule_table.setItem(row, 2, QTableWidgetItem(schedule.course_type or "-"))
            self.schedule_table.setItem(row, 3, QTableWidgetItem(schedule.room.name if schedule.room else "-"))
            self.schedule_table.setItem(row, 4, QTableWidgetItem(schedule.teacher.name if schedule.teacher else "-"))
            time_str = f"{schedule.start_time.strftime('%m-%d %H:%M')} - {schedule.end_time.strftime('%H:%M')}"
            self.schedule_table.setItem(row, 5, QTableWidgetItem(time_str))
            students_str = f"{schedule.current_students}/{schedule.max_students}"
            self.schedule_table.setItem(row, 6, QTableWidgetItem(students_str))

            progress_text = "-"
            if progress:
                status_text = progress["progress_status"]
                pct = progress["progress_value"]
                review_flag = " ✍" if progress.get("has_lesson_review") else ""
                progress_text = f"{status_text} ({pct:.0f}%){review_flag}"
            self.schedule_table.setItem(row, 7, QTableWidgetItem(progress_text))
            self.schedule_table.setItem(row, 8, QTableWidgetItem(SCHEDULE_STATUS_LABELS.get(schedule.status, schedule.status)))

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
            self.progress_status_label.setText("-")
            self.progress_bar.setValue(0)
            self.progress_count_label.setText("")
            self.breakdown_label.setText("")
            self.review_hint_label.setText("")
            return

        self.detail_labels["course_name"].setText(schedule.course_name)
        self.detail_labels["course_type"].setText(schedule.course_type or "-")
        self.detail_labels["room"].setText(schedule.room.name if schedule.room else "-")
        self.detail_labels["teacher"].setText(schedule.teacher.name if schedule.teacher else "-")
        time_str = f"{schedule.start_time.strftime('%Y-%m-%d %H:%M')} - {schedule.end_time.strftime('%H:%M')}"
        self.detail_labels["time"].setText(time_str)
        self.detail_labels["students"].setText(f"{schedule.current_students}/{schedule.max_students}")
        self.detail_labels["status"].setText(SCHEDULE_STATUS_LABELS.get(schedule.status, schedule.status))
        self.detail_labels["notes"].setText(schedule.notes or "-")

        progress = self._progress_cache.get(schedule.id) or self.scheduler.get_schedule_progress(schedule.id)
        if progress:
            self._progress_cache[schedule.id] = progress
            self.progress_status_label.setText(progress["progress_status"])
            self.progress_bar.setValue(int(progress["progress_value"]))
            if progress["progress_status"] == "全部取消":
                self.progress_count_label.setText(f"全部取消 ({progress['cancelled_count']}人)")
                self.progress_bar.setStyleSheet("QProgressBar::chunk { background: #F44336; }")
            elif progress["progress_status"] == "全部完成":
                self.progress_count_label.setText(f"{progress['completed_count']}/{progress['active_students']} 已完成")
                self.progress_bar.setStyleSheet("QProgressBar::chunk { background: #4CAF50; }")
            else:
                self.progress_count_label.setText(f"{progress['completed_count']}/{progress['active_students']} 已完成")
                self.progress_bar.setStyleSheet("")
            breakdown_parts = []
            if progress["confirmed_count"]:
                breakdown_parts.append(f"已确认{progress['confirmed_count']}人")
            if progress["checked_in_count"]:
                breakdown_parts.append(f"已签到{progress['checked_in_count']}人")
            if progress["completed_count"]:
                breakdown_parts.append(f"已完成{progress['completed_count']}人")
            if progress["pending_count"]:
                breakdown_parts.append(f"待确认{progress['pending_count']}人")
            if progress["cancelled_count"]:
                breakdown_parts.append(f"取消{progress['cancelled_count']}人")
            self.breakdown_label.setText("，".join(breakdown_parts) if breakdown_parts else "暂无报名")

            if progress.get("has_lesson_review"):
                reviewed = progress.get("reviewed_at")
                reviewed_text = reviewed.strftime("%m-%d %H:%M") if reviewed else ""
                self.review_hint_label.setText(f"✍ 已填写课后记录（{reviewed_text}）")
            else:
                self.review_hint_label.setText("")
        else:
            self.progress_status_label.setText("-")
            self.progress_bar.setValue(0)
            self.progress_bar.setStyleSheet("")
            self.progress_count_label.setText("")
            self.breakdown_label.setText("")
            self.review_hint_label.setText("")

    def _load_enrollments(self):
        self.enrollment_list.clear()
        schedule = self._get_selected_schedule()
        if not schedule:
            self.current_enrollments = []
            return

        self.current_enrollments = self.scheduler.get_enrollments(schedule_id=schedule.id)
        for enroll in self.current_enrollments:
            student = self.scheduler.db.get_by_id(Student, enroll.student_id)
            status_label = ENROLLMENT_STATUS_LABELS.get(enroll.status, enroll.status)
            time_parts = []
            if enroll.enroll_time:
                time_parts.append(f"报名:{enroll.enroll_time.strftime('%H:%M')}")
            if enroll.confirm_time:
                time_parts.append(f"确认:{enroll.confirm_time.strftime('%H:%M')}")
            if enroll.checkin_time:
                time_parts.append(f"签到:{enroll.checkin_time.strftime('%H:%M')}")
            if enroll.complete_time:
                time_parts.append(f"完成:{enroll.complete_time.strftime('%H:%M')}")
            time_str = " ".join(time_parts) if time_parts else ""
            name = student.name if student else "未知"
            text = f"[{status_label}] {name} - {time_str}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, enroll.id)
            self.enrollment_list.addItem(item)

        self._update_enrollment_buttons()

    def _update_enrollment_buttons(self):
        enroll_id = self._get_selected_enrollment()
        self.confirm_btn.setEnabled(False)
        self.checkin_btn.setEnabled(False)
        self.complete_btn.setEnabled(False)

        if not enroll_id:
            return

        for enroll in self.current_enrollments:
            if enroll.id == enroll_id:
                status = enroll.status
                self.confirm_btn.setEnabled(status == "pending")
                self.checkin_btn.setEnabled(status == "confirmed")
                self.complete_btn.setEnabled(status == "checked_in")
                can_cancel = status in ["pending", "confirmed", "checked_in"]
                self.cancel_enroll_btn.setEnabled(can_cancel)
                break

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
            self._trigger_callback()
            QMessageBox.information(self, "成功", "操作成功")

    def _get_selected_enrollment(self):
        item = self.enrollment_list.currentItem()
        if item:
            return item.data(Qt.UserRole)
        return None

    def _trigger_callback(self):
        if self._after_enrollment_change_callback:
            try:
                self._after_enrollment_change_callback()
            except Exception as e:
                print(f"Callback error: {e}")

    def confirm_enrollment(self):
        enroll_id = self._get_selected_enrollment()
        if not enroll_id:
            QMessageBox.warning(self, "提示", "请先选择要确认的报名记录")
            return
        try:
            result = self.scheduler.confirm_enrollment(enroll_id)
            if result:
                self.load_data()
                self._trigger_callback()
                QMessageBox.information(self, "成功", "已确认报名")
            else:
                QMessageBox.warning(self, "失败", "确认失败")
        except ValueError as e:
            QMessageBox.warning(self, "操作无效", str(e))

    def checkin_student(self):
        enroll_id = self._get_selected_enrollment()
        if not enroll_id:
            QMessageBox.warning(self, "提示", "请先选择要签到的报名记录")
            return
        try:
            result = self.scheduler.checkin_student(enroll_id)
            if result:
                self.load_data()
                self._trigger_callback()
                QMessageBox.information(self, "成功", "签到成功")
            else:
                QMessageBox.warning(self, "失败", "签到失败")
        except ValueError as e:
            QMessageBox.warning(self, "操作无效", str(e))

    def complete_enrollment(self):
        enroll_id = self._get_selected_enrollment()
        if not enroll_id:
            QMessageBox.warning(self, "提示", "请先选择要完成的报名记录")
            return
        try:
            result = self.scheduler.complete_enrollment(enroll_id)
            if result:
                self.load_data()
                self._trigger_callback()
                QMessageBox.information(self, "成功", "已标记完成")
            else:
                QMessageBox.warning(self, "失败", "操作失败")
        except ValueError as e:
            QMessageBox.warning(self, "操作无效", str(e))

    def cancel_enrollment(self):
        enroll_id = self._get_selected_enrollment()
        if not enroll_id:
            QMessageBox.warning(self, "提示", "请先选择要取消的报名记录")
            return

        enroll = self.scheduler.get_enrollment_by_id(enroll_id)
        schedule_id = enroll.schedule_id if enroll else None
        schedule_name = ""
        if schedule_id:
            s = self.scheduler.get_schedule_by_id(schedule_id)
            if s:
                schedule_name = s.course_name

        reply = QMessageBox.question(self, "确认",
            "确定要取消该报名吗？\n\n"
            "取消后名额将自动释放给候补学员，\n"
            "系统会按优先级通知下一位候补。")
        if reply == QMessageBox.Yes:
            try:
                result = self.scheduler.cancel_enrollment(enroll_id)
                if result:
                    self.load_data()
                    self._trigger_callback()

                    notify_result = self.scheduler._last_cancel_notify_result
                    if notify_result and notify_result.get("count", 0) > 0:
                        count = notify_result["count"]
                        names = notify_result.get("student_names", [])
                        source_label = NOTIFY_SOURCE_LABELS.get(notify_result.get("source", ""), "取消释放")
                        msg = f"已释放名额。实际通知 {count} 名候补学员：\n\n"
                        msg += "\n".join([f"  • {n}" for n in names])
                        msg += f"\n\n补位来源：{source_label}"
                        QMessageBox.information(self, "补位通知已发出", msg)
                    else:
                        QMessageBox.information(self, "成功",
                            "已取消报名，名额已释放。\n\n暂无等待中的候补学员。")
            except ValueError as e:
                QMessageBox.warning(self, "操作无效", str(e))

    def open_lesson_review(self):
        schedule = self._get_selected_schedule()
        if not schedule:
            QMessageBox.warning(self, "提示", "请先选择课程")
            return

        if schedule.start_time > datetime.now():
            reply = QMessageBox.question(self, "提示", "该课程尚未开始，确定要填写课后记录吗？")
            if reply != QMessageBox.Yes:
                return

        progress = self.scheduler.get_schedule_progress(schedule.id)
        review_data = None
        if progress:
            review_data = {
                "lesson_content": progress.get("lesson_content"),
                "teacher_review": progress.get("teacher_review"),
                "next_homework": progress.get("next_homework"),
                "suggested_pieces": progress.get("suggested_pieces")
            }

        dialog = LessonReviewDialog(self, review_data)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            result = self.scheduler.save_lesson_review(
                schedule.id,
                lesson_content=data["lesson_content"],
                teacher_review=data["teacher_review"],
                next_homework=data["next_homework"],
                suggested_pieces=data["suggested_pieces"]
            )
            if result:
                self.load_data()
                self._trigger_callback()
                QMessageBox.information(self, "成功", "课后记录已保存")
            else:
                QMessageBox.warning(self, "失败", "保存失败")
