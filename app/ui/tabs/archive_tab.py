from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QComboBox, QDateEdit, QMessageBox, QHeaderView,
    QGroupBox, QFormLayout, QAbstractItemView, QSplitter, QTabWidget,
    QProgressBar
)
from PySide6.QtCore import Qt, QDate
from datetime import datetime
from app.database.models import Archive, MusicPiece, Student, Teacher


ENROLLMENT_STATUS_LABELS = {
    "pending": "待确认",
    "confirmed": "已确认",
    "checked_in": "已签到",
    "completed": "已完成",
    "cancelled": "已取消",
    "released": "已释放"
}


class ArchiveTab(QWidget):
    def __init__(self, scheduler, recommender=None):
        super().__init__()
        self.scheduler = scheduler
        self.recommender = recommender
        self.current_archives = []
        self.current_pieces = []
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

        splitter.addWidget(detail_group)
        splitter.setSizes([700, 500])

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
        from app.database.models import Archive
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

            return q.order_by(Archive.course_date.desc()).all()

        self.current_archives = self.scheduler.db.execute_query(query)

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
