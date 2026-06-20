from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QComboBox, QMessageBox, QHeaderView,
    QGroupBox, QFormLayout, QDoubleSpinBox, QAbstractItemView,
    QSplitter, QListWidget, QListWidgetItem, QProgressBar, QTextEdit
)
from PySide6.QtCore import Qt


class RecommendTab(QWidget):
    def __init__(self, recommender, scheduler):
        super().__init__()
        self.recommender = recommender
        self.scheduler = scheduler
        self.current_recommendations = []
        self.current_match_records = []
        self._init_ui()
        self.load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        top_layout = QHBoxLayout()

        student_group = QGroupBox("选择学员")
        student_layout = QHBoxLayout(student_group)
        student_layout.addWidget(QLabel("学员:"))
        self.student_combo = QComboBox()
        self.student_combo.setMinimumWidth(200)
        student_layout.addWidget(self.student_combo)

        self.recommend_teachers_btn = QPushButton("推荐老师")
        self.recommend_teachers_btn.clicked.connect(self.recommend_teachers)
        student_layout.addWidget(self.recommend_teachers_btn)

        self.recommend_courses_btn = QPushButton("推荐课程")
        self.recommend_courses_btn.clicked.connect(self.recommend_courses)
        student_layout.addWidget(self.recommend_courses_btn)

        top_layout.addWidget(student_group)

        weights_group = QGroupBox("权重配置")
        weights_layout = QFormLayout(weights_group)
        self.weight_spins = {}

        weight_labels = {
            "style_match": "曲风匹配:",
            "rating": "老师评分:",
            "level_match": "级别匹配:",
            "availability": "时间可用:",
            "experience": "教学经验:"
        }

        for key, label_text in weight_labels.items():
            spin = QDoubleSpinBox()
            spin.setRange(0.0, 1.0)
            spin.setSingleStep(0.05)
            spin.setDecimals(2)
            self.weight_spins[key] = spin
            weights_layout.addRow(QLabel(label_text), spin)

        btn_row = QHBoxLayout()
        self.save_weights_btn = QPushButton("保存权重")
        self.save_weights_btn.clicked.connect(self.save_weights)
        btn_row.addWidget(self.save_weights_btn)

        self.reset_weights_btn = QPushButton("重置默认")
        self.reset_weights_btn.clicked.connect(self.reset_weights)
        btn_row.addWidget(self.reset_weights_btn)

        weights_layout.addRow(btn_row)
        top_layout.addWidget(weights_group)
        top_layout.addStretch()

        layout.addLayout(top_layout)

        splitter = QSplitter(Qt.Horizontal)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        self.result_label = QLabel("推荐结果")
        self.result_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        left_layout.addWidget(self.result_label)

        self.result_table = QTableWidget()
        self.result_table.setColumnCount(8)
        self.result_table.setHorizontalHeaderLabels([
            "排名", "总分", "老师", "曲风", "评分", "级别", "可用度", "经验"
        ])
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.result_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.result_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.result_table.itemSelectionChanged.connect(self.on_recommend_selected)
        left_layout.addWidget(self.result_table, 1)

        splitter.addWidget(left_panel)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        detail_group = QGroupBox("详细评分")
        detail_layout = QFormLayout(detail_group)

        self.score_labels = {}
        score_items = [
            ("total_score", "总分"),
            ("style_score", "曲风匹配分"),
            ("rating_score", "评分得分"),
            ("level_score", "级别匹配分"),
            ("availability_score", "可用度得分"),
            ("experience_score", "经验得分")
        ]

        for key, label_text in score_items:
            row_layout = QHBoxLayout()
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setTextVisible(True)
            self.score_labels[key] = (QLabel("0.00"), bar)
            row_layout.addWidget(self.score_labels[key][0])
            row_layout.addWidget(bar, 1)
            detail_layout.addRow(QLabel(label_text + ":"), row_layout)

        right_layout.addWidget(detail_group)

        reason_group = QGroupBox("推荐原因")
        reason_layout = QVBoxLayout(reason_group)
        self.reason_label = QLabel("选择推荐结果后查看推荐原因")
        self.reason_label.setWordWrap(True)
        self.reason_label.setStyleSheet("padding: 8px; background: rgba(33,150,243,0.08); border-radius: 4px; line-height: 1.6;")
        reason_layout.addWidget(self.reason_label)

        self.save_match_btn = QPushButton("保存为撮合记录")
        self.save_match_btn.clicked.connect(self.save_as_match)
        self.save_match_btn.setEnabled(False)
        reason_layout.addWidget(self.save_match_btn)

        right_layout.addWidget(reason_group)

        info_group = QGroupBox("老师信息")
        info_layout = QFormLayout(info_group)
        self.teacher_info_labels = {}
        for key, label_text in [("name", "姓名"), ("level", "级别"), ("styles", "擅长曲风"), ("rating", "评分"), ("experience_years", "教学经验"), ("phone", "联系电话")]:
            label = QLabel("-")
            self.teacher_info_labels[key] = label
            info_layout.addRow(QLabel(f"{label_text}:"), label)
        right_layout.addWidget(info_group)

        right_layout.addStretch()

        splitter.addWidget(right_panel)
        splitter.setSizes([700, 500])

        layout.addWidget(splitter, 1)

    def load_data(self):
        self._load_students()
        self._load_weights()

    def _load_students(self):
        current_student = self.student_combo.currentData()
        self.student_combo.clear()

        students = self.scheduler.get_all_students("active")
        for student in students:
            self.student_combo.addItem(student.name, student.id)

        if current_student:
            idx = self.student_combo.findData(current_student)
            if idx >= 0:
                self.student_combo.setCurrentIndex(idx)

    def _load_weights(self):
        weights = self.recommender.get_current_weights()
        for key, value in weights.items():
            if key in self.weight_spins:
                self.weight_spins[key].setValue(value)

    def recommend_teachers(self):
        student_id = self.student_combo.currentData()
        if not student_id:
            QMessageBox.warning(self, "提示", "请先选择学员")
            return

        try:
            self.current_recommendations = self.recommender.recommend_teachers(student_id, top_n=5)
            self._display_teacher_results()
        except ValueError as e:
            QMessageBox.warning(self, "错误", str(e))

    def recommend_courses(self):
        student_id = self.student_combo.currentData()
        if not student_id:
            QMessageBox.warning(self, "提示", "请先选择学员")
            return

        try:
            self.current_recommendations = self.recommender.recommend_schedules(student_id, top_n=5)
            self._display_course_results()
        except ValueError as e:
            QMessageBox.warning(self, "错误", str(e))

    def _display_teacher_results(self):
        self.result_table.setColumnCount(8)
        self.result_table.setHorizontalHeaderLabels([
            "排名", "总分", "老师", "曲风", "评分", "级别", "可用度", "经验"
        ])

        self.result_table.setRowCount(len(self.current_recommendations))
        for row, rec in enumerate(self.current_recommendations):
            self.result_table.setItem(row, 0, QTableWidgetItem(f"{row + 1}"))
            self.result_table.setItem(row, 1, QTableWidgetItem(f"{rec['total_score']:.2%}"))
            teacher = rec["teacher"]
            self.result_table.setItem(row, 2, QTableWidgetItem(teacher.name))
            self.result_table.setItem(row, 3, QTableWidgetItem(f"{rec['style_score']:.0%}"))
            self.result_table.setItem(row, 4, QTableWidgetItem(f"{rec['rating_score']:.0%}"))
            self.result_table.setItem(row, 5, QTableWidgetItem(f"{rec['level_score']:.0%}"))
            self.result_table.setItem(row, 6, QTableWidgetItem(f"{rec['availability_score']:.0%}"))
            self.result_table.setItem(row, 7, QTableWidgetItem(f"{rec['experience_score']:.0%}"))

        self.result_label.setText(f"推荐老师 - 共 {len(self.current_recommendations)} 位")

    def _display_course_results(self):
        self.result_table.setColumnCount(7)
        self.result_table.setHorizontalHeaderLabels([
            "排名", "总分", "课程", "老师", "时间", "剩余名额", "匹配度"
        ])

        self.result_table.setRowCount(len(self.current_recommendations))
        for row, rec in enumerate(self.current_recommendations):
            self.result_table.setItem(row, 0, QTableWidgetItem(f"{row + 1}"))
            self.result_table.setItem(row, 1, QTableWidgetItem(f"{rec['total_score']:.2%}"))
            schedule = rec["schedule"]
            self.result_table.setItem(row, 2, QTableWidgetItem(schedule.course_name))
            self.result_table.setItem(row, 3, QTableWidgetItem(rec["teacher"].name))
            time_str = f"{schedule.start_time.strftime('%m-%d %H:%M')}"
            self.result_table.setItem(row, 4, QTableWidgetItem(time_str))
            slots = schedule.max_students - schedule.current_students
            self.result_table.setItem(row, 5, QTableWidgetItem(str(slots)))
            self.result_table.setItem(row, 6, QTableWidgetItem(f"{rec['total_score']:.0%}"))

        self.result_label.setText(f"推荐课程 - 共 {len(self.current_recommendations)} 门")

    def on_recommend_selected(self):
        current_row = self.result_table.currentRow()
        if current_row < 0 or current_row >= len(self.current_recommendations):
            return

        rec = self.current_recommendations[current_row]

        score_keys = ["total_score", "style_score", "rating_score", "level_score", "availability_score", "experience_score"]
        for key in score_keys:
            if key in self.score_labels and key in rec:
                value = rec[key]
                self.score_labels[key][0].setText(f"{value:.4f}")
                self.score_labels[key][1].setValue(int(value * 100))

        reason = rec.get("reason_text", "")
        self.reason_label.setText(reason if reason else "暂无推荐原因")

        teacher = rec.get("teacher")
        if teacher:
            self.teacher_info_labels["name"].setText(teacher.name or "-")
            self.teacher_info_labels["level"].setText(teacher.level or "-")
            self.teacher_info_labels["styles"].setText(teacher.styles or "-")
            self.teacher_info_labels["rating"].setText(f"{teacher.rating:.1f}" if teacher.rating else "-")
            self.teacher_info_labels["experience_years"].setText(f"{teacher.experience_years} 年" if teacher.experience_years else "-")
            self.teacher_info_labels["phone"].setText(teacher.phone or "-")

        self.save_match_btn.setEnabled(True)

    def save_as_match(self):
        current_row = self.result_table.currentRow()
        if current_row < 0 or current_row >= len(self.current_recommendations):
            return

        rec = self.current_recommendations[current_row]
        student = rec.get("student")
        teacher = rec.get("teacher")
        if not student or not teacher:
            return

        reply = QMessageBox.question(self, "确认",
            f"确定要将「{student.name}」与「{teacher.name}」的推荐保存为撮合记录吗？\n匹配度: {rec['total_score']:.2%}")
        if reply == QMessageBox.Yes:
            from app.database.models import RecommendationLog
            logs = self.recommender.get_recommendation_history(
                student_id=student.id, teacher_id=teacher.id, limit=1
            )
            if logs:
                self.recommender.save_as_match(logs[0].id)
                QMessageBox.information(self, "成功", "已保存为撮合记录")
            else:
                QMessageBox.warning(self, "提示", "未找到对应的推荐记录")

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
            QMessageBox.information(self, "成功", "权重已重置为默认值")
