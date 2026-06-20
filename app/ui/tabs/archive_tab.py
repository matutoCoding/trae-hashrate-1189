from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QComboBox, QDateEdit, QMessageBox, QHeaderView,
    QGroupBox, QFormLayout, QAbstractItemView, QSplitter, QTabWidget,
    QProgressBar, QFrame, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, QDate
from datetime import datetime
from app.database.models import Archive, MusicPiece


ENROLLMENT_STATUS_LABELS = {
    "pending": "待确认",
    "confirmed": "已确认",
    "checked_in": "已签到",
    "completed": "已完成",
    "cancelled": "已取消",
    "released": "已释放"
}


class ClickableStatCard(QFrame):
    def __init__(self, title, data_dict, filter_key, filter_value, parent_tab):
        super().__init__()
        self.filter_key = filter_key
        self.filter_value = filter_value
        self.parent_tab = parent_tab

        self.setFrameStyle(QFrame.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                background: white;
            }
            QFrame:hover {
                border: 1px solid #1976D2;
                background: #F5F9FF;
            }
        """)
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(12, 10, 12, 10)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #333;")
        layout.addWidget(title_label)

        total = data_dict.get("total", 0)
        completed = data_dict.get("completed", 0)
        cancelled = data_dict.get("cancelled", 0)
        completion_rate = (completed / total * 100) if total > 0 else 0
        cancel_rate = (cancelled / total * 100) if total > 0 else 0

        total_label = QLabel(f"共 {total} 节")
        total_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(total_label)

        stats_row = QHBoxLayout()

        completed_box = QVBoxLayout()
        comp_num = QLabel(f"{completion_rate:.0f}%")
        comp_num.setStyleSheet("font-size: 18px; font-weight: bold; color: #4CAF50;")
        comp_num.setAlignment(Qt.AlignCenter)
        comp_text = QLabel("完成率")
        comp_text.setStyleSheet("font-size: 11px; color: #4CAF50;")
        comp_text.setAlignment(Qt.AlignCenter)
        completed_box.addWidget(comp_num)
        completed_box.addWidget(comp_text)
        stats_row.addLayout(completed_box)

        cancelled_box = QVBoxLayout()
        canc_num = QLabel(f"{cancel_rate:.0f}%")
        canc_num.setStyleSheet("font-size: 18px; font-weight: bold; color: #F44336;")
        canc_num.setAlignment(Qt.AlignCenter)
        canc_text = QLabel("取消率")
        canc_text.setStyleSheet("font-size: 11px; color: #F44336;")
        canc_text.setAlignment(Qt.AlignCenter)
        cancelled_box.addWidget(canc_num)
        cancelled_box.addWidget(canc_text)
        stats_row.addLayout(cancelled_box)

        layout.addLayout(stats_row)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.parent_tab.apply_analytics_filter(self.filter_key, self.filter_value)
        super().mousePressEvent(event)


class ArchiveTab(QWidget):
    def __init__(self, scheduler, recommender=None):
        super().__init__()
        self.scheduler = scheduler
        self.recommender = recommender
        self.current_archives = []
        self.current_pieces = []
        self._active_filters = {}
        self._init_ui()
        self.load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        self.tabs = QTabWidget()

        archive_tab = QWidget()
        archive_layout = QVBoxLayout(archive_tab)
        self._init_archive_ui(archive_layout)
        self.tabs.addTab(archive_tab, "历史归档")

        music_tab = QWidget()
        music_layout = QVBoxLayout(music_tab)
        self._init_music_ui(music_layout)
        self.tabs.addTab(music_tab, "考级曲库")

        layout.addWidget(self.tabs)

    def _init_archive_ui(self, layout):
        stats_group = QGroupBox("筛选统计")
        stats_layout = QHBoxLayout(stats_group)

        self.stats_widgets = {}
        stat_configs = [
            ("total_count", "总记录", "0"),
            ("avg_score", "平均匹配分", "-"),
            ("completed_count", "已完成", "0"),
            ("cancelled_count", "已取消", "0"),
            ("pending_count", "待确认/已签到", "0")
        ]

        for i, (key, label, default) in enumerate(stat_configs):
            if i > 0:
                line = QFrame()
                line.setFrameShape(QFrame.VLine)
                line.setFrameShadow(QFrame.Sunken)
                stats_layout.addWidget(line)

            box = QVBoxLayout()
            value_label = QLabel(default)
            value_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #1976D2;")
            value_label.setAlignment(Qt.AlignCenter)
            name_label = QLabel(label)
            name_label.setAlignment(Qt.AlignCenter)
            box.addWidget(value_label)
            box.addWidget(name_label)
            stats_layout.addLayout(box)
            self.stats_widgets[key] = value_label

        layout.addWidget(stats_group)

        analytics_group = QGroupBox("运营分析（点击卡片查看详情）")
        analytics_layout = QHBoxLayout(analytics_group)

        self.clear_filter_btn = QPushButton("清除分析筛选")
        self.clear_filter_btn.clicked.connect(self.clear_analytics_filter)
        self.clear_filter_btn.setEnabled(False)
        self.clear_filter_btn.setStyleSheet("background: #FFEBEE;")
        analytics_layout.addWidget(self.clear_filter_btn)

        self.active_filter_label = QLabel("")
        self.active_filter_label.setStyleSheet("color: #1976D2; font-weight: bold;")
        analytics_layout.addWidget(self.active_filter_label, 1)

        layout.addWidget(analytics_group)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(180)
        analytics_cards_widget = QWidget()
        self.analytics_cards_layout = QHBoxLayout(analytics_cards_widget)
        self.analytics_cards_layout.setSpacing(10)
        self.analytics_cards_layout.addStretch()
        scroll_area.setWidget(analytics_cards_widget)
        layout.addWidget(scroll_area)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("日期范围:"))

        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addDays(-90))
        self.start_date.setCalendarPopup(True)
        filter_layout.addWidget(self.start_date)

        filter_layout.addWidget(QLabel("至"))

        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate().addDays(30))
        self.end_date.setCalendarPopup(True)
        filter_layout.addWidget(self.end_date)

        filter_layout.addWidget(QLabel("学员:"))
        self.student_combo = QComboBox()
        self.student_combo.addItem("全部", None)
        filter_layout.addWidget(self.student_combo)

        filter_layout.addWidget(QLabel("老师:"))
        self.teacher_combo = QComboBox()
        self.teacher_combo.addItem("全部", None)
        filter_layout.addWidget(self.teacher_combo)

        filter_layout.addWidget(QLabel("曲风:"))
        self.style_combo = QComboBox()
        self.style_combo.addItem("全部", None)
        filter_layout.addWidget(self.style_combo)

        filter_layout.addWidget(QLabel("考级级别:"))
        self.exam_level_combo = QComboBox()
        self.exam_level_combo.addItems(["全部", "一级", "二级", "三级", "四级", "五级", "六级", "七级", "八级", "九级", "十级"])
        filter_layout.addWidget(self.exam_level_combo)

        self.search_btn = QPushButton("查询")
        self.search_btn.clicked.connect(self.load_archives)
        filter_layout.addWidget(self.search_btn)

        filter_layout.addStretch()

        self.archive_btn = QPushButton("立即归档")
        self.archive_btn.clicked.connect(self.do_archive)
        filter_layout.addWidget(self.archive_btn)

        layout.addLayout(filter_layout)

        splitter = QSplitter(Qt.Horizontal)

        self.archive_table = QTableWidget()
        self.archive_table.setColumnCount(9)
        self.archive_table.setHorizontalHeaderLabels([
            "ID", "课程名称", "学员", "老师", "日期", "状态", "匹配分", "学员曲风", "考级级别"
        ])
        self.archive_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.archive_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.archive_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.archive_table.itemSelectionChanged.connect(self._on_archive_selected)
        splitter.addWidget(self.archive_table)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        detail_group = QGroupBox("归档详情")
        detail_layout = QFormLayout(detail_group)
        self.archive_detail_labels = {}

        detail_fields = [
            ("course_name", "课程名称"), ("course_type", "课程类型"),
            ("student_name", "学员"), ("teacher_name", "老师"), ("room_name", "琴室"),
            ("course_date", "上课日期"), ("status", "上课状态"),
            ("student_style", "学员曲风"), ("teacher_style", "老师曲风"),
            ("student_level", "学员级别"), ("student_exam_level", "考级级别"),
            ("match_score", "综合匹配分")
        ]
        for key, label_text in detail_fields:
            label = QLabel("-")
            label.setWordWrap(True)
            self.archive_detail_labels[key] = label
            detail_layout.addRow(QLabel(f"{label_text}:"), label)

        score_group = QGroupBox("推荐评分明细")
        score_layout = QFormLayout(score_group)
        self.score_bars = {}
        score_items = [
            ("style_score", "曲风匹配"), ("rating_score", "老师评分"),
            ("level_score", "级别匹配"), ("availability_score", "时间可用"),
            ("experience_score", "教学经验")
        ]
        for key, label_text in score_items:
            row = QHBoxLayout()
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setTextVisible(True)
            val_label = QLabel("-")
            self.score_bars[key] = (val_label, bar)
            row.addWidget(val_label)
            row.addWidget(bar, 1)
            score_layout.addRow(QLabel(f"{label_text}:"), row)

        detail_layout.addRow(score_group)

        right_layout.addWidget(detail_group)

        timeline_group = QGroupBox("报名过程")
        timeline_layout = QFormLayout(timeline_group)
        self.timeline_labels = {}
        timeline_items = [
            ("enroll_time", "报名时间"),
            ("confirm_time", "确认时间"),
            ("checkin_time", "签到时间"),
            ("complete_time", "完成时间"),
            ("cancel_time", "取消/释放时间")
        ]
        for key, label_text in timeline_items:
            label = QLabel("-")
            self.timeline_labels[key] = label
            timeline_layout.addRow(QLabel(f"{label_text}:"), label)

        right_layout.addWidget(timeline_group)

        review_group = QGroupBox("课后复盘记录")
        review_layout = QFormLayout(review_group)
        self.review_labels = {}
        review_items = [
            ("lesson_content", "学习内容"),
            ("teacher_review", "老师点评"),
            ("next_homework", "下次作业"),
            ("suggested_pieces", "建议曲目")
        ]
        for key, label_text in review_items:
            label = QLabel("-")
            label.setWordWrap(True)
            label.setStyleSheet("color: #333;")
            self.review_labels[key] = label
            review_layout.addRow(QLabel(f"{label_text}:"), label)

        right_layout.addWidget(review_group)

        music_group = QGroupBox("推荐学习曲目")
        music_layout = QVBoxLayout(music_group)
        self.recommended_music_list = QTableWidget()
        self.recommended_music_list.setColumnCount(4)
        self.recommended_music_list.setHorizontalHeaderLabels(["曲目名称", "作曲家", "难度", "级别"])
        self.recommended_music_list.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.recommended_music_list.setEditTriggers(QAbstractItemView.NoEditTriggers)
        music_layout.addWidget(self.recommended_music_list)
        right_layout.addWidget(music_group, 1)

        splitter.addWidget(right_panel)
        splitter.setSizes([600, 600])

        layout.addWidget(splitter, 1)

    def _init_music_ui(self, layout):
        btn_layout = QHBoxLayout()
        self.add_piece_btn = QPushButton("添加曲目")
        self.add_piece_btn.clicked.connect(self.add_music_piece)
        btn_layout.addWidget(self.add_piece_btn)

        self.edit_piece_btn = QPushButton("编辑")
        self.edit_piece_btn.clicked.connect(self.edit_music_piece)
        btn_layout.addWidget(self.edit_piece_btn)

        self.delete_piece_btn = QPushButton("删除")
        self.delete_piece_btn.clicked.connect(self.delete_music_piece)
        btn_layout.addWidget(self.delete_piece_btn)

        btn_layout.addStretch()

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("考级类别:"))
        self.exam_combo = QComboBox()
        self.exam_combo.addItems(["全部", "中央音乐学院", "中国音乐学院", "上海音乐学院", "中国音乐家协会"])
        filter_layout.addWidget(self.exam_combo)

        filter_layout.addWidget(QLabel("级别:"))
        self.level_combo = QComboBox()
        self.level_combo.addItems(["全部", "一级", "二级", "三级", "四级", "五级", "六级", "七级", "八级", "九级", "十级"])
        filter_layout.addWidget(self.level_combo)

        self.search_piece_btn = QPushButton("查询")
        self.search_piece_btn.clicked.connect(self.load_music_pieces)
        filter_layout.addWidget(self.search_piece_btn)

        top_layout = QVBoxLayout()
        top_layout.addLayout(btn_layout)
        top_layout.addLayout(filter_layout)
        layout.addLayout(top_layout)

        splitter = QSplitter(Qt.Horizontal)

        self.piece_table = QTableWidget()
        self.piece_table.setColumnCount(7)
        self.piece_table.setHorizontalHeaderLabels([
            "ID", "曲目名称", "作曲家", "风格", "难度", "考级类别", "级别"
        ])
        self.piece_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.piece_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.piece_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        splitter.addWidget(self.piece_table)

        detail_group = QGroupBox("曲目详情")
        detail_layout = QFormLayout(detail_group)
        self.piece_detail_labels = {}
        for key, label_text in [("name", "曲目名称"), ("composer", "作曲家"), ("style", "风格"), ("difficulty_level", "难度"), ("exam_category", "考级类别"), ("exam_level", "级别"), ("duration_minutes", "时长"), ("description", "简介")]:
            label = QLabel("-")
            label.setWordWrap(True)
            self.piece_detail_labels[key] = label
            detail_layout.addRow(QLabel(f"{label_text}:"), label)
        splitter.addWidget(detail_group)
        splitter.setSizes([700, 500])

        layout.addWidget(splitter, 1)

        self.piece_table.itemSelectionChanged.connect(self._on_piece_selected)

    def load_data(self):
        self._load_archive_filters()
        self.load_archives()
        self.load_music_pieces()

    def _load_archive_filters(self):
        current_student = self.student_combo.currentData()
        current_teacher = self.teacher_combo.currentData()

        self.student_combo.clear()
        self.student_combo.addItem("全部", None)
        for s in self.scheduler.get_all_students():
            self.student_combo.addItem(s.name, s.id)

        self.teacher_combo.clear()
        self.teacher_combo.addItem("全部", None)
        for t in self.scheduler.get_all_teachers():
            self.teacher_combo.addItem(t.name, t.id)

        self.style_combo.clear()
        self.style_combo.addItem("全部", None)
        all_styles = set()
        for t in self.scheduler.get_all_teachers():
            if t.styles:
                for s in t.styles.split(","):
                    s = s.strip()
                    if s:
                        all_styles.add(s)
        for s in sorted(all_styles):
            self.style_combo.addItem(s, s)

        if current_student:
            idx = self.student_combo.findData(current_student)
            if idx >= 0:
                self.student_combo.setCurrentIndex(idx)
        if current_teacher:
            idx = self.teacher_combo.findData(current_teacher)
            if idx >= 0:
                self.teacher_combo.setCurrentIndex(idx)

    def load_archives(self):
        start_dt = datetime.combine(self.start_date.date().toPython(), datetime.min.time())
        end_dt = datetime.combine(self.end_date.date().toPython(), datetime.max.time())

        style_filter = self.style_combo.currentData()
        exam_level_filter = self.exam_level_combo.currentText()

        def query(session):
            q = session.query(Archive).filter(
                Archive.course_date >= start_dt,
                Archive.course_date <= end_dt
            )

            student_id = self.student_combo.currentData()
            if student_id:
                q = q.filter(Archive.student_id == student_id)

            teacher_id = self.teacher_combo.currentData()
            if teacher_id:
                q = q.filter(Archive.teacher_id == teacher_id)

            if style_filter:
                q = q.filter(Archive.teacher_style.contains(style_filter))

            if exam_level_filter != "全部":
                q = q.filter(Archive.student_exam_level == exam_level_filter)

            if self._active_filters:
                for key, value in self._active_filters.items():
                    if key == "teacher_name":
                        q = q.filter(Archive.teacher_name == value)
                    elif key == "course_type":
                        q = q.filter(Archive.course_type == value)
                    elif key == "student_level":
                        q = q.filter(Archive.student_level == value)

            return q.order_by(Archive.course_date.desc()).all()

        self.current_archives = self.scheduler.db.execute_query(query)

        self._update_statistics()
        self._update_analytics_cards()

        self.archive_table.setRowCount(len(self.current_archives))
        for row, archive in enumerate(self.current_archives):
            self.archive_table.setItem(row, 0, QTableWidgetItem(str(archive.id)))
            self.archive_table.setItem(row, 1, QTableWidgetItem(archive.course_name or "-"))
            self.archive_table.setItem(row, 2, QTableWidgetItem(archive.student_name or "-"))
            self.archive_table.setItem(row, 3, QTableWidgetItem(archive.teacher_name or "-"))
            self.archive_table.setItem(row, 4, QTableWidgetItem(archive.course_date.strftime("%Y-%m-%d %H:%M") if archive.course_date else "-"))
            status_label = ENROLLMENT_STATUS_LABELS.get(archive.status, archive.status or "-")
            self.archive_table.setItem(row, 5, QTableWidgetItem(status_label))
            score = f"{archive.match_score:.2%}" if archive.match_score else "-"
            self.archive_table.setItem(row, 6, QTableWidgetItem(score))
            self.archive_table.setItem(row, 7, QTableWidgetItem(archive.student_style or "-"))
            self.archive_table.setItem(row, 8, QTableWidgetItem(archive.student_exam_level or "-"))

    def _update_statistics(self):
        archives = self.current_archives
        total = len(archives)
        self.stats_widgets["total_count"].setText(str(total))

        if total > 0:
            scores = [a.match_score for a in archives if a.match_score is not None]
            if scores:
                avg = sum(scores) / len(scores)
                self.stats_widgets["avg_score"].setText(f"{avg:.2%}")
            else:
                self.stats_widgets["avg_score"].setText("-")

            completed = len([a for a in archives if a.status == "completed"])
            cancelled = len([a for a in archives if a.status in ["cancelled", "released"]])
            pending = len([a for a in archives if a.status in ["pending", "confirmed", "checked_in"]])
            self.stats_widgets["completed_count"].setText(str(completed))
            self.stats_widgets["cancelled_count"].setText(str(cancelled))
            self.stats_widgets["pending_count"].setText(str(pending))
        else:
            self.stats_widgets["avg_score"].setText("-")
            self.stats_widgets["completed_count"].setText("0")
            self.stats_widgets["cancelled_count"].setText("0")
            self.stats_widgets["pending_count"].setText("0")

    def _update_analytics_cards(self):
        while self.analytics_cards_layout.count() > 1:
            item = self.analytics_cards_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        archives = self.current_archives

        teacher_stats = {}
        type_stats = {}
        level_stats = {}

        for a in archives:
            key_t = a.teacher_name or "未知"
            if key_t not in teacher_stats:
                teacher_stats[key_t] = {"total": 0, "completed": 0, "cancelled": 0}
            teacher_stats[key_t]["total"] += 1
            if a.status == "completed":
                teacher_stats[key_t]["completed"] += 1
            if a.status in ["cancelled", "released"]:
                teacher_stats[key_t]["cancelled"] += 1

            key_ct = a.course_type or "未分类"
            if key_ct not in type_stats:
                type_stats[key_ct] = {"total": 0, "completed": 0, "cancelled": 0}
            type_stats[key_ct]["total"] += 1
            if a.status == "completed":
                type_stats[key_ct]["completed"] += 1
            if a.status in ["cancelled", "released"]:
                type_stats[key_ct]["cancelled"] += 1

            key_lv = a.student_level or "未知"
            if key_lv not in level_stats:
                level_stats[key_lv] = {"total": 0, "completed": 0, "cancelled": 0}
            level_stats[key_lv]["total"] += 1
            if a.status == "completed":
                level_stats[key_lv]["completed"] += 1
            if a.status in ["cancelled", "released"]:
                level_stats[key_lv]["cancelled"] += 1

        if teacher_stats:
            teacher_group = QGroupBox("按老师")
            teacher_layout = QHBoxLayout(teacher_group)
            sorted_t = sorted(teacher_stats.items(), key=lambda x: -x[1]["total"])
            for name, data in sorted_t[:6]:
                card = ClickableStatCard(name, data, "teacher_name", name, self)
                card.setMinimumWidth(140)
                teacher_layout.addWidget(card)
            self.analytics_cards_layout.insertWidget(0, teacher_group)

        if type_stats:
            type_group = QGroupBox("按课程类型")
            type_layout = QHBoxLayout(type_group)
            sorted_ct = sorted(type_stats.items(), key=lambda x: -x[1]["total"])
            for name, data in sorted_ct[:4]:
                card = ClickableStatCard(name, data, "course_type", name, self)
                card.setMinimumWidth(140)
                type_layout.addWidget(card)
            self.analytics_cards_layout.insertWidget(1, type_group)

        if level_stats:
            level_group = QGroupBox("按学员级别")
            level_layout = QHBoxLayout(level_group)
            level_order = ["入门", "初级", "中级", "高级", "专业"]
            sorted_lv = sorted(level_stats.items(), key=lambda x: (level_order.index(x[0]) if x[0] in level_order else 99))
            for name, data in sorted_lv[:6]:
                card = ClickableStatCard(name, data, "student_level", name, self)
                card.setMinimumWidth(140)
                level_layout.addWidget(card)
            self.analytics_cards_layout.insertWidget(2, level_group)

    def apply_analytics_filter(self, filter_key, filter_value):
        self._active_filters = {filter_key: filter_value}
        self.clear_filter_btn.setEnabled(True)
        self.active_filter_label.setText(f"当前筛选：{self._filter_label(filter_key)} = {filter_value}")
        self.load_archives()

    def clear_analytics_filter(self):
        self._active_filters = {}
        self.clear_filter_btn.setEnabled(False)
        self.active_filter_label.setText("")
        self.load_archives()

    def _filter_label(self, key):
        mapping = {
            "teacher_name": "老师",
            "course_type": "课程类型",
            "student_level": "学员级别"
        }
        return mapping.get(key, key)

    def _on_archive_selected(self):
        current_row = self.archive_table.currentRow()
        if current_row < 0 or current_row >= len(self.current_archives):
            return

        archive = self.current_archives[current_row]

        self.archive_detail_labels["course_name"].setText(archive.course_name or "-")
        self.archive_detail_labels["course_type"].setText(archive.course_type or "-")
        self.archive_detail_labels["student_name"].setText(archive.student_name or "-")
        self.archive_detail_labels["teacher_name"].setText(archive.teacher_name or "-")
        self.archive_detail_labels["room_name"].setText(archive.room_name or "-")
        self.archive_detail_labels["course_date"].setText(archive.course_date.strftime("%Y-%m-%d %H:%M") if archive.course_date else "-")
        status_label = ENROLLMENT_STATUS_LABELS.get(archive.status, archive.status or "-")
        self.archive_detail_labels["status"].setText(status_label)
        self.archive_detail_labels["student_style"].setText(archive.student_style or "-")
        self.archive_detail_labels["teacher_style"].setText(archive.teacher_style or "-")
        self.archive_detail_labels["student_level"].setText(archive.student_level or "-")
        self.archive_detail_labels["student_exam_level"].setText(archive.student_exam_level or "-")
        self.archive_detail_labels["match_score"].setText(f"{archive.match_score:.2%}" if archive.match_score else "-")

        for key in ["style_score", "rating_score", "level_score", "availability_score", "experience_score"]:
            val = getattr(archive, key, None)
            val_label, bar = self.score_bars[key]
            if val is not None:
                val_label.setText(f"{val:.2%}")
                bar.setValue(int(val * 100))
            else:
                val_label.setText("-")
                bar.setValue(0)

        for key, field in [("enroll_time", archive.enroll_time),
                          ("confirm_time", archive.confirm_time),
                          ("checkin_time", archive.checkin_time),
                          ("complete_time", archive.complete_time),
                          ("cancel_time", archive.cancel_time)]:
            self.timeline_labels[key].setText(field.strftime("%Y-%m-%d %H:%M:%S") if field else "-")

        for key in ["lesson_content", "teacher_review", "next_homework", "suggested_pieces"]:
            val = getattr(archive, key, None)
            self.review_labels[key].setText(val or "（暂无记录）")

        self._load_recommended_music(archive)

    def _load_recommended_music(self, archive):
        self.recommended_music_list.setRowCount(0)

        student_style = archive.student_style or ""
        student_level = archive.student_level or ""
        student_exam_level = archive.student_exam_level or ""

        all_pieces = self.scheduler.get_all_music_pieces()

        matched = []
        for piece in all_pieces:
            score = 0
            if student_style and piece.style:
                style_list = [s.strip() for s in student_style.split(",")]
                if piece.style in style_list:
                    score += 50
                elif any(s in piece.style for s in style_list):
                    score += 30

            if student_level and piece.difficulty_level:
                level_order = ["入门", "初级", "中级", "高级", "专业"]
                try:
                    si = level_order.index(student_level)
                    pi = level_order.index(piece.difficulty_level)
                    if abs(si - pi) <= 1:
                        score += 30
                except ValueError:
                    pass

            if student_exam_level and piece.exam_level:
                if piece.exam_level == student_exam_level:
                    score += 20

            if archive.suggested_pieces:
                if piece.name in archive.suggested_pieces:
                    score += 100

            if score > 0:
                matched.append((piece, score))

        matched.sort(key=lambda x: x[1], reverse=True)

        self.recommended_music_list.setRowCount(len(matched[:10]))
        for row, (piece, score) in enumerate(matched[:10]):
            name = piece.name
            if score >= 100:
                name += " ★推荐"
            self.recommended_music_list.setItem(row, 0, QTableWidgetItem(name))
            self.recommended_music_list.setItem(row, 1, QTableWidgetItem(piece.composer or "-"))
            self.recommended_music_list.setItem(row, 2, QTableWidgetItem(piece.difficulty_level or "-"))
            self.recommended_music_list.setItem(row, 3, QTableWidgetItem(piece.exam_level or "-"))

    def do_archive(self):
        count = self.scheduler.archive_completed_courses()
        if isinstance(count, int):
            msg = f"已归档 {count} 条课程记录"
        else:
            msg = f"已归档 {len(count)} 条课程记录"
        QMessageBox.information(self, "完成", msg)
        self.load_archives()

    def load_music_pieces(self):
        all_pieces = self.scheduler.get_all_music_pieces()

        exam_filter = self.exam_combo.currentText()
        level_filter = self.level_combo.currentText()

        filtered = []
        for piece in all_pieces:
            if exam_filter != "全部" and piece.exam_category != exam_filter:
                continue
            if level_filter != "全部" and piece.exam_level != level_filter:
                continue
            filtered.append(piece)

        self.current_pieces = filtered

        self.piece_table.setRowCount(len(self.current_pieces))
        for row, piece in enumerate(self.current_pieces):
            self.piece_table.setItem(row, 0, QTableWidgetItem(str(piece.id)))
            self.piece_table.setItem(row, 1, QTableWidgetItem(piece.name))
            self.piece_table.setItem(row, 2, QTableWidgetItem(piece.composer or "-"))
            self.piece_table.setItem(row, 3, QTableWidgetItem(piece.style or "-"))
            self.piece_table.setItem(row, 4, QTableWidgetItem(piece.difficulty_level or "-"))
            self.piece_table.setItem(row, 5, QTableWidgetItem(piece.exam_category or "-"))
            self.piece_table.setItem(row, 6, QTableWidgetItem(piece.exam_level or "-"))

    def _get_selected_piece(self):
        current_row = self.piece_table.currentRow()
        if current_row >= 0 and current_row < len(self.current_pieces):
            return self.current_pieces[current_row]
        return None

    def _on_piece_selected(self):
        piece = self._get_selected_piece()
        if not piece:
            for label in self.piece_detail_labels.values():
                label.setText("-")
            return

        self.piece_detail_labels["name"].setText(piece.name)
        self.piece_detail_labels["composer"].setText(piece.composer or "-")
        self.piece_detail_labels["style"].setText(piece.style or "-")
        self.piece_detail_labels["difficulty_level"].setText(piece.difficulty_level or "-")
        self.piece_detail_labels["exam_category"].setText(piece.exam_category or "-")
        self.piece_detail_labels["exam_level"].setText(piece.exam_level or "-")
        self.piece_detail_labels["duration_minutes"].setText(f"{piece.duration_minutes} 分钟" if piece.duration_minutes else "-")
        self.piece_detail_labels["description"].setText(piece.description or "-")

    def add_music_piece(self):
        from app.ui.dialogs.music_piece_dialog import MusicPieceDialog
        dialog = MusicPieceDialog(self.scheduler, self)
        if dialog.exec() == 1:
            self.load_music_pieces()
            QMessageBox.information(self, "成功", "曲目添加成功")

    def edit_music_piece(self):
        piece = self._get_selected_piece()
        if not piece:
            QMessageBox.warning(self, "提示", "请先选择要编辑的曲目")
            return

        from app.ui.dialogs.music_piece_dialog import MusicPieceDialog
        dialog = MusicPieceDialog(self.scheduler, self, piece)
        if dialog.exec() == 1:
            self.load_music_pieces()
            QMessageBox.information(self, "成功", "曲目更新成功")

    def delete_music_piece(self):
        piece = self._get_selected_piece()
        if not piece:
            QMessageBox.warning(self, "提示", "请先选择要删除的曲目")
            return

        reply = QMessageBox.question(self, "确认", f"确定要删除曲目「{piece.name}」吗？")
        if reply == QMessageBox.Yes:
            if self.scheduler.delete_music_piece(piece.id):
                self.load_music_pieces()
                QMessageBox.information(self, "成功", "删除成功")
