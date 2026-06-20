from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QComboBox, QMessageBox, QHeaderView,
    QDialog, QFormLayout, QLineEdit, QSpinBox, QGroupBox,
    QAbstractItemView, QSplitter, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, QTimer
from datetime import datetime
from app.database.models import Waitlist, Student, Schedule


STATUS_LABELS = {
    "waiting": "等待中",
    "notified": "已通知",
    "enrolled": "已报名",
    "expired": "已过期",
    "declined": "已拒绝",
    "cancelled": "已取消"
}

SOURCE_LABELS = {
    "cancel_release": "取消释放",
    "expired_release": "过期释放",
    "manual": "手动处理"
}


class WaitlistTab(QWidget):
    def __init__(self, waitlist_service, scheduler):
        super().__init__()
        self.waitlist = waitlist_service
        self.scheduler = scheduler
        self.current_waitlist = []
        self.current_notified = []
        self._init_ui()
        self.load_data()
        self._init_refresh_timer()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("课程:"))
        self.schedule_combo = QComboBox()
        self.schedule_combo.addItem("全部", None)
        filter_layout.addWidget(self.schedule_combo)

        filter_layout.addWidget(QLabel("状态:"))
        self.status_combo = QComboBox()
        status_items = ["全部", "waiting", "notified", "enrolled", "expired", "declined", "cancelled"]
        for s in status_items:
            label = STATUS_LABELS.get(s, s)
            self.status_combo.addItem(label, s)
        self.status_combo.setCurrentIndex(1)
        filter_layout.addWidget(self.status_combo)

        self.search_btn = QPushButton("查询")
        self.search_btn.clicked.connect(self.load_data)
        filter_layout.addWidget(self.search_btn)

        filter_layout.addStretch()

        self.process_btn = QPushButton("处理补位")
        self.process_btn.clicked.connect(self.process_waitlist)
        filter_layout.addWidget(self.process_btn)

        self.check_expired_btn = QPushButton("检查过期")
        self.check_expired_btn.clicked.connect(self.check_expired)
        filter_layout.addWidget(self.check_expired_btn)

        layout.addLayout(filter_layout)

        tab_widget = QSplitter(Qt.Vertical)

        waitlist_group = QGroupBox("候补队列")
        waitlist_layout = QVBoxLayout(waitlist_group)

        self.waitlist_table = QTableWidget()
        self.waitlist_table.setColumnCount(11)
        self.waitlist_table.setHorizontalHeaderLabels([
            "ID", "队列位置", "优先级", "学员", "课程", "状态", "补位来源", "通知时间", "确认截止", "剩余时间", "创建时间"
        ])
        self.waitlist_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.waitlist_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.waitlist_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.waitlist_table.itemSelectionChanged.connect(self.on_waitlist_selected)
        waitlist_layout.addWidget(self.waitlist_table)

        tab_widget.addWidget(waitlist_group)

        notified_group = QGroupBox("已通知候补（倒计时）")
        notified_layout = QVBoxLayout(notified_group)

        self.notified_table = QTableWidget()
        self.notified_table.setColumnCount(8)
        self.notified_table.setHorizontalHeaderLabels([
            "ID", "学员", "课程", "补位来源", "通知时间", "确认截止", "剩余时间", "状态"
        ])
        self.notified_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.notified_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.notified_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        notified_layout.addWidget(self.notified_table)

        tab_widget.addWidget(notified_group)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        action_group = QGroupBox("操作")
        action_layout = QVBoxLayout(action_group)

        self.confirm_enroll_btn = QPushButton("确认报名")
        self.confirm_enroll_btn.clicked.connect(self.confirm_enrollment)
        action_layout.addWidget(self.confirm_enroll_btn)

        self.decline_btn = QPushButton("拒绝补位")
        self.decline_btn.clicked.connect(self.decline_offer)
        action_layout.addWidget(self.decline_btn)

        self.remove_btn = QPushButton("移出队列")
        self.remove_btn.clicked.connect(self.remove_from_waitlist)
        action_layout.addWidget(self.remove_btn)

        priority_layout = QHBoxLayout()
        priority_layout.addWidget(QLabel("调整优先级:"))
        self.priority_spin = QSpinBox()
        self.priority_spin.setRange(0, 100)
        priority_layout.addWidget(self.priority_spin)

        self.update_priority_btn = QPushButton("更新")
        self.update_priority_btn.clicked.connect(self.update_priority)
        priority_layout.addWidget(self.update_priority_btn)
        action_layout.addLayout(priority_layout)

        right_layout.addWidget(action_group)

        stats_group = QGroupBox("统计信息")
        stats_layout = QFormLayout(stats_group)
        self.stats_labels = {}
        stat_keys = [("total", "总记录"), ("waiting", "等待中"), ("notified", "已通知"), ("enrolled", "已报名"), ("expired_declined", "过期/拒绝")]
        for key, label_text in stat_keys:
            label = QLabel("0")
            self.stats_labels[key] = label
            stats_layout.addRow(QLabel(f"{label_text}:"), label)
        right_layout.addWidget(stats_group)

        right_layout.addStretch()

        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.addWidget(tab_widget)
        main_splitter.addWidget(right_panel)
        main_splitter.setSizes([800, 400])

        layout.addWidget(main_splitter, 1)

    def _init_refresh_timer(self):
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._refresh_notified_remaining)
        self.refresh_timer.start(30000)

    def load_data(self):
        self._load_filters()

        schedule_id = self.schedule_combo.currentData()
        status = self.status_combo.currentData()
        if status == "全部":
            status = None

        self.current_waitlist = self.waitlist.get_waitlist(
            schedule_id=schedule_id,
            status=status
        )

        self.waitlist_table.setRowCount(len(self.current_waitlist))
        for row, entry in enumerate(self.current_waitlist):
            self.waitlist_table.setItem(row, 0, QTableWidgetItem(str(entry.id)))
            self.waitlist_table.setItem(row, 1, QTableWidgetItem(str(entry.queue_position)))
            self.waitlist_table.setItem(row, 2, QTableWidgetItem(str(entry.priority_score)))
            student = self.scheduler.db.get_by_id(Student, entry.student_id)
            self.waitlist_table.setItem(row, 3, QTableWidgetItem(student.name if student else "-"))
            schedule = self.scheduler.db.get_by_id(Schedule, entry.schedule_id)
            self.waitlist_table.setItem(row, 4, QTableWidgetItem(schedule.course_name if schedule else "-"))
            self.waitlist_table.setItem(row, 5, QTableWidgetItem(STATUS_LABELS.get(entry.status, entry.status)))
            source = SOURCE_LABELS.get(entry.notify_source, "-") if entry.notify_source else "-"
            self.waitlist_table.setItem(row, 6, QTableWidgetItem(source))
            notified = entry.notified_time.strftime("%m-%d %H:%M") if entry.notified_time else "-"
            self.waitlist_table.setItem(row, 7, QTableWidgetItem(notified))
            deadline = entry.confirm_deadline.strftime("%m-%d %H:%M") if entry.confirm_deadline else "-"
            self.waitlist_table.setItem(row, 8, QTableWidgetItem(deadline))
            remaining = self._calc_remaining(entry)
            self.waitlist_table.setItem(row, 9, QTableWidgetItem(remaining))
            self.waitlist_table.setItem(row, 10, QTableWidgetItem(entry.created_at.strftime("%m-%d %H:%M")))

        self._load_notified_table()
        self._update_stats()

    def _calc_remaining(self, entry):
        if entry.status != "notified" or not entry.confirm_deadline:
            return "-"
        now = datetime.now()
        diff = (entry.confirm_deadline - now).total_seconds()
        if diff <= 0:
            return "已过期"
        minutes = int(diff // 60)
        seconds = int(diff % 60)
        return f"{minutes}分{seconds}秒"

    def _load_notified_table(self):
        self.current_notified = self.waitlist.get_notified_with_remaining()
        self.notified_table.setRowCount(len(self.current_notified))
        for row, item in enumerate(self.current_notified):
            entry = item["entry"]
            self.notified_table.setItem(row, 0, QTableWidgetItem(str(entry.id)))
            student = self.scheduler.db.get_by_id(Student, entry.student_id)
            self.notified_table.setItem(row, 1, QTableWidgetItem(student.name if student else "-"))
            schedule = self.scheduler.db.get_by_id(Schedule, entry.schedule_id)
            self.notified_table.setItem(row, 2, QTableWidgetItem(schedule.course_name if schedule else "-"))
            source = SOURCE_LABELS.get(entry.notify_source, "-") if entry.notify_source else "-"
            self.notified_table.setItem(row, 3, QTableWidgetItem(source))
            notified = entry.notified_time.strftime("%m-%d %H:%M:%S") if entry.notified_time else "-"
            self.notified_table.setItem(row, 4, QTableWidgetItem(notified))
            deadline = item["deadline"].strftime("%m-%d %H:%M:%S") if item["deadline"] else "-"
            self.notified_table.setItem(row, 5, QTableWidgetItem(deadline))
            remaining_sec = item["remaining_seconds"]
            if remaining_sec <= 0:
                remaining_text = "已过期"
            else:
                m = int(remaining_sec // 60)
                s = int(remaining_sec % 60)
                remaining_text = f"{m}分{s}秒"
            self.notified_table.setItem(row, 6, QTableWidgetItem(remaining_text))
            self.notified_table.setItem(row, 7, QTableWidgetItem("已过期" if item["is_expired"] else "待确认"))

    def _refresh_notified_remaining(self):
        self._load_notified_table()

    def _load_filters(self):
        current_schedule = self.schedule_combo.currentData()
        self.schedule_combo.clear()
        self.schedule_combo.addItem("全部", None)

        schedules = self.scheduler.get_schedules(status="scheduled")
        for s in schedules:
            text = f"{s.course_name} - {s.start_time.strftime('%m-%d %H:%M')}"
            self.schedule_combo.addItem(text, s.id)

        if current_schedule:
            idx = self.schedule_combo.findData(current_schedule)
            if idx >= 0:
                self.schedule_combo.setCurrentIndex(idx)

    def _update_stats(self):
        schedule_id = self.schedule_combo.currentData()
        if schedule_id:
            stats = self.waitlist.get_waitlist_statistics(schedule_id)
            for key, value in stats.items():
                if key in self.stats_labels:
                    self.stats_labels[key].setText(str(value))
        else:
            for label in self.stats_labels.values():
                label.setText("-")

    def on_waitlist_selected(self):
        entry = self._get_selected_entry()
        if entry:
            self.priority_spin.setValue(int(entry.priority_score))

    def _get_selected_entry(self):
        current_row = self.waitlist_table.currentRow()
        if current_row >= 0 and current_row < len(self.current_waitlist):
            return self.current_waitlist[current_row]
        return None

    def process_waitlist(self):
        schedule_id = self.schedule_combo.currentData()
        if not schedule_id:
            QMessageBox.warning(self, "提示", "请先选择课程")
            return

        result = self.waitlist.notify_with_result(schedule_id, notify_source="manual")
        count = result.get("count", 0)
        names = result.get("student_names", [])

        if count > 0:
            msg = f"已实际通知 {count} 名候补学员：\n\n"
            msg += "\n".join([f"  {i+1}. {n}" for i, n in enumerate(names)])
            msg += f"\n\n补位来源：{SOURCE_LABELS.get('manual', '手动处理')}"
            QMessageBox.information(self, "补位通知已发出", msg)
            self.load_data()
        else:
            reason_msg = "可能的原因：\n1. 暂无等待中的候补学员\n2. 没有空余名额\n3. 已有已通知待确认的学员（已算作占位）"
            QMessageBox.information(self, "暂无可通知学员",
                f"本次未发出任何补位邀请。\n\n{reason_msg}")

    def check_expired(self):
        expired = self.waitlist.check_expired_notifications()
        if expired:
            student_names = []
            for entry in expired:
                s = self.scheduler.db.get_by_id(Student, entry.student_id)
                if s:
                    student_names.append(s.name)
            msg = f"处理了 {len(expired)} 个过期通知：\n\n"
            msg += "\n".join([f"  • {n}" for n in student_names])
            msg += "\n\n系统已自动通知下一位候补学员（补位来源：过期释放）"
            QMessageBox.information(self, "处理完成", msg)
            self.load_data()
        else:
            QMessageBox.information(self, "完成", "没有过期的通知")

    def confirm_enrollment(self):
        entry = self._get_selected_entry()
        if not entry:
            QMessageBox.warning(self, "提示", "请先选择候补记录")
            return

        if entry.status != "notified":
            QMessageBox.warning(self, "提示", "只有已通知的候补记录才能确认报名")
            return

        student = self.scheduler.db.get_by_id(Student, entry.student_id)
        schedule = self.scheduler.db.get_by_id(Schedule, entry.schedule_id)
        name = student.name if student else "该学员"
        course = schedule.course_name if schedule else ""

        reply = QMessageBox.question(self, "确认",
            f"确定要确认 {name} 的补位报名吗？\n\n课程：{course}")
        if reply == QMessageBox.Yes:
            result = self.waitlist.confirm_waitlist_enrollment(entry.id)
            if result:
                QMessageBox.information(self, "成功",
                    f"{name} 已成功补位报名！\n\n课程人数已同步更新。")
                self.load_data()
            else:
                QMessageBox.warning(self, "失败",
                    "确认失败，可能名额已被占用、通知已过期或课程已满")

    def decline_offer(self):
        entry = self._get_selected_entry()
        if not entry:
            QMessageBox.warning(self, "提示", "请先选择候补记录")
            return

        student = self.scheduler.db.get_by_id(Student, entry.student_id)
        name = student.name if student else "该学员"

        reply = QMessageBox.question(self, "确认",
            f"确定要让 {name} 拒绝该补位邀请吗？\n\n"
            "拒绝后系统将自动通知下一位候补学员。")
        if reply == QMessageBox.Yes:
            if self.waitlist.decline_waitlist_offer(entry.id):
                next_result = self.waitlist.notify_with_result(entry.schedule_id, notify_source="manual")
                next_names = next_result.get("student_names", [])
                if next_names:
                    msg = f"{name} 已拒绝补位。\n\n系统已自动通知下一位候补：\n"
                    msg += "\n".join([f"  • {n}" for n in next_names])
                    QMessageBox.information(self, "成功", msg)
                else:
                    QMessageBox.information(self, "成功", f"{name} 已拒绝补位，暂无下一位候补学员。")
                self.load_data()

    def remove_from_waitlist(self):
        entry = self._get_selected_entry()
        if not entry:
            QMessageBox.warning(self, "提示", "请先选择候补记录")
            return

        reply = QMessageBox.question(self, "确认", "确定要将该学员移出候补队列吗？")
        if reply == QMessageBox.Yes:
            if self.waitlist.remove_from_waitlist(entry.id):
                QMessageBox.information(self, "成功", "已移出")
                self.load_data()

    def update_priority(self):
        entry = self._get_selected_entry()
        if not entry:
            QMessageBox.warning(self, "提示", "请先选择候补记录")
            return

        new_score = self.priority_spin.value()
        if self.waitlist.update_priority_score(entry.id, new_score):
            QMessageBox.information(self, "成功", "优先级已更新")
            self.load_data()
