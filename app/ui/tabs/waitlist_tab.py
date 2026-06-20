from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QComboBox, QMessageBox, QHeaderView,
    QDialog, QFormLayout, QLineEdit, QSpinBox, QGroupBox,
    QAbstractItemView, QSplitter, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt
from app.database.models import Waitlist


class WaitlistTab(QWidget):
    def __init__(self, waitlist_service, scheduler):
        super().__init__()
        self.waitlist = waitlist_service
        self.scheduler = scheduler
        self.current_waitlist = []
        self._init_ui()
        self.load_data()

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
        self.status_combo.addItems(["waiting", "notified", "enrolled", "expired", "declined", "cancelled"])
        self.status_combo.setCurrentText("waiting")
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

        splitter = QSplitter(Qt.Horizontal)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        self.waitlist_table = QTableWidget()
        self.waitlist_table.setColumnCount(8)
        self.waitlist_table.setHorizontalHeaderLabels([
            "ID", "队列位置", "优先级", "学员", "课程", "状态", "通知时间", "创建时间"
        ])
        self.waitlist_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.waitlist_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.waitlist_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.waitlist_table.itemSelectionChanged.connect(self.on_waitlist_selected)
        left_layout.addWidget(self.waitlist_table, 1)

        splitter.addWidget(left_panel)

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
        for key in ["total", "waiting", "enrolled", "expired_declined"]:
            label = QLabel("0")
            self.stats_labels[key] = label
            stats_layout.addRow(QLabel(f"{key}:"), label)
        right_layout.addWidget(stats_group)

        right_layout.addStretch()

        splitter.addWidget(right_panel)
        splitter.setSizes([800, 400])

        layout.addWidget(splitter, 1)

    def load_data(self):
        self._load_filters()

        schedule_id = self.schedule_combo.currentData()
        status = self.status_combo.currentText()

        self.current_waitlist = self.waitlist.get_waitlist(
            schedule_id=schedule_id,
            status=status
        )

        self.waitlist_table.setRowCount(len(self.current_waitlist))
        for row, entry in enumerate(self.current_waitlist):
            self.waitlist_table.setItem(row, 0, QTableWidgetItem(str(entry.id)))
            self.waitlist_table.setItem(row, 1, QTableWidgetItem(str(entry.queue_position)))
            self.waitlist_table.setItem(row, 2, QTableWidgetItem(str(entry.priority_score)))
            student = self.scheduler.db.get_by_id(type(entry.student), entry.student_id)
            self.waitlist_table.setItem(row, 3, QTableWidgetItem(student.name if student else "-"))
            schedule = self.scheduler.db.get_by_id(type(entry.schedule), entry.schedule_id)
            self.waitlist_table.setItem(row, 4, QTableWidgetItem(schedule.course_name if schedule else "-"))
            self.waitlist_table.setItem(row, 5, QTableWidgetItem(entry.status))
            notified = entry.notified_time.strftime("%m-%d %H:%M") if entry.notified_time else "-"
            self.waitlist_table.setItem(row, 6, QTableWidgetItem(notified))
            self.waitlist_table.setItem(row, 7, QTableWidgetItem(entry.created_at.strftime("%m-%d %H:%M")))

        self._update_stats()

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

        notified = self.waitlist.process_waitlist_for_schedule(schedule_id)
        if notified:
            QMessageBox.information(self, "成功", f"已通知 {len(notified)} 名候补学员")
            self.load_data()
        else:
            QMessageBox.information(self, "提示", "没有可以补位的名额或没有候补学员")

    def check_expired(self):
        expired = self.waitlist.check_expired_notifications()
        if expired:
            QMessageBox.information(self, "完成", f"处理了 {len(expired)} 个过期通知")
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

        result = self.waitlist.confirm_waitlist_enrollment(entry.id)
        if result:
            QMessageBox.information(self, "成功", "候补学员已成功报名")
            self.load_data()
        else:
            QMessageBox.warning(self, "失败", "确认失败，可能名额已被占用或通知已过期")

    def decline_offer(self):
        entry = self._get_selected_entry()
        if not entry:
            QMessageBox.warning(self, "提示", "请先选择候补记录")
            return

        reply = QMessageBox.question(self, "确认", "确定要拒绝该补位邀请吗？")
        if reply == QMessageBox.Yes:
            if self.waitlist.decline_waitlist_offer(entry.id):
                QMessageBox.information(self, "成功", "已拒绝")
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
