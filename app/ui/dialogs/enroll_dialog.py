from PySide6.QtWidgets import (
    QDialog, QFormLayout, QComboBox, QDialogButtonBox, QMessageBox,
    QLabel, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QPushButton, QGroupBox
)
from PySide6.QtCore import Qt


class EnrollDialog(QDialog):
    def __init__(self, scheduler, recommender, waitlist, schedule, parent=None):
        super().__init__(parent)
        self.scheduler = scheduler
        self.recommender = recommender
        self.waitlist = waitlist
        self.schedule = schedule
        self.setWindowTitle("学员报名")
        self.resize(800, 600)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        info_group = QGroupBox("课程信息")
        info_layout = QFormLayout(info_group)
        info_layout.addRow(QLabel("课程:"), QLabel(self.schedule.course_name))
        info_layout.addRow(QLabel("老师:"), QLabel(self.schedule.teacher.name if self.schedule.teacher else "-"))
        info_layout.addRow(QLabel("时间:"), QLabel(
            f"{self.schedule.start_time.strftime('%Y-%m-%d %H:%M')} - {self.schedule.end_time.strftime('%H:%M')}"
        ))
        info_layout.addRow(QLabel("名额:"), QLabel(
            f"{self.schedule.current_students}/{self.schedule.max_students}"
        ))
        layout.addWidget(info_group)

        if self.schedule.current_students >= self.schedule.max_students:
            layout.addWidget(QLabel("⚠️ 课程已满，学员将加入候补队列"))

        tab_layout = QHBoxLayout()

        left_panel = QVBoxLayout()
        left_panel.addWidget(QLabel("选择学员:"))

        self.student_combo = QComboBox()
        for student in self.scheduler.get_all_students("active"):
            self.student_combo.addItem(student.name, student.id)
        left_panel.addWidget(self.student_combo)

        recommend_btn = QPushButton("智能推荐老师")
        recommend_btn.clicked.connect(self.show_recommendations)
        left_panel.addWidget(recommend_btn)

        enroll_btn = QPushButton("直接报名")
        enroll_btn.clicked.connect(self.do_enroll)
        left_panel.addWidget(enroll_btn)

        waitlist_btn = QPushButton("加入候补")
        waitlist_btn.clicked.connect(self.do_waitlist)
        left_panel.addWidget(waitlist_btn)

        left_panel.addStretch()
        tab_layout.addLayout(left_panel, 1)

        right_panel = QVBoxLayout()
        right_panel.addWidget(QLabel("推荐结果:"))

        self.recommend_table = QTableWidget()
        self.recommend_table.setColumnCount(5)
        self.recommend_table.setHorizontalHeaderLabels(["排名", "老师", "匹配度", "曲风", "级别"])
        self.recommend_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.recommend_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.recommend_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        right_panel.addWidget(self.recommend_table, 1)

        tab_layout.addLayout(right_panel, 2)
        layout.addLayout(tab_layout, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def show_recommendations(self):
        student_id = self.student_combo.currentData()
        if not student_id:
            QMessageBox.warning(self, "提示", "请先选择学员")
            return

        try:
            recommendations = self.recommender.recommend_teachers(
                student_id, schedule_id=self.schedule.id, top_n=5
            )

            self.recommend_table.setRowCount(len(recommendations))
            for row, rec in enumerate(recommendations):
                self.recommend_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
                self.recommend_table.setItem(row, 1, QTableWidgetItem(rec["teacher"].name))
                self.recommend_table.setItem(row, 2, QTableWidgetItem(f"{rec['total_score']:.2%}"))
                self.recommend_table.setItem(row, 3, QTableWidgetItem(f"{rec['style_score']:.0%}"))
                self.recommend_table.setItem(row, 4, QTableWidgetItem(f"{rec['level_score']:.0%}"))

            if recommendations:
                QMessageBox.information(
                    self, "推荐完成",
                    f"已为学员推荐 {len(recommendations)} 位老师\n\n"
                    f"最佳匹配: {recommendations[0]['teacher'].name} "
                    f"(匹配度 {recommendations[0]['total_score']:.2%})"
                )
        except ValueError as e:
            QMessageBox.warning(self, "错误", str(e))

    def do_enroll(self):
        student_id = self.student_combo.currentData()
        if not student_id:
            QMessageBox.warning(self, "提示", "请先选择学员")
            return

        if self.schedule.current_students >= self.schedule.max_students:
            reply = QMessageBox.question(
                self, "课程已满",
                "课程已满，是否将学员加入候补队列？"
            )
            if reply == QMessageBox.Yes:
                self.do_waitlist()
            return

        try:
            self.scheduler.enroll_student(self.schedule.id, student_id)
            QMessageBox.information(self, "成功", "报名成功")
            super().accept()
        except ValueError as e:
            QMessageBox.warning(self, "错误", str(e))

    def do_waitlist(self):
        student_id = self.student_combo.currentData()
        if not student_id:
            QMessageBox.warning(self, "提示", "请先选择学员")
            return

        try:
            self.waitlist.add_to_waitlist(self.schedule.id, student_id)
            QMessageBox.information(self, "成功", "已加入候补队列")
            super().accept()
        except ValueError as e:
            QMessageBox.warning(self, "错误", str(e))
