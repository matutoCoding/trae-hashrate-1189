from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QTableWidget, QTableWidgetItem, QPushButton, QMessageBox,
    QFormLayout, QLineEdit, QComboBox, QSpinBox, QTextEdit,
    QDialogButtonBox, QLabel, QHeaderView, QAbstractItemView,
    QGroupBox
)
from PySide6.QtCore import Qt


class DataManageDialog(QDialog):
    def __init__(self, scheduler, parent=None):
        super().__init__(parent)
        self.scheduler = scheduler
        self.setWindowTitle("数据管理")
        self.resize(900, 600)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        tabs = QTabWidget()

        self.room_tab = self._create_room_tab()
        self.teacher_tab = self._create_teacher_tab()
        self.student_tab = self._create_student_tab()

        tabs.addTab(self.room_tab, "琴室管理")
        tabs.addTab(self.teacher_tab, "老师管理")
        tabs.addTab(self.student_tab, "学员管理")

        layout.addWidget(tabs, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.accept)
        layout.addWidget(buttons)

        self._load_rooms()
        self._load_teachers()
        self._load_students()

    def _create_room_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        btn_layout = QHBoxLayout()
        self.add_room_btn = QPushButton("添加琴室")
        self.add_room_btn.clicked.connect(self.add_room)
        btn_layout.addWidget(self.add_room_btn)

        self.edit_room_btn = QPushButton("编辑")
        self.edit_room_btn.clicked.connect(self.edit_room)
        btn_layout.addWidget(self.edit_room_btn)

        self.delete_room_btn = QPushButton("删除")
        self.delete_room_btn.clicked.connect(self.delete_room)
        btn_layout.addWidget(self.delete_room_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.room_table = QTableWidget()
        self.room_table.setColumnCount(5)
        self.room_table.setHorizontalHeaderLabels(["ID", "名称", "位置", "容量", "状态"])
        self.room_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.room_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.room_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.room_table, 1)

        return widget

    def _create_teacher_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        btn_layout = QHBoxLayout()
        self.add_teacher_btn = QPushButton("添加老师")
        self.add_teacher_btn.clicked.connect(self.add_teacher)
        btn_layout.addWidget(self.add_teacher_btn)

        self.edit_teacher_btn = QPushButton("编辑")
        self.edit_teacher_btn.clicked.connect(self.edit_teacher)
        btn_layout.addWidget(self.edit_teacher_btn)

        self.delete_teacher_btn = QPushButton("删除")
        self.delete_teacher_btn.clicked.connect(self.delete_teacher)
        btn_layout.addWidget(self.delete_teacher_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.teacher_table = QTableWidget()
        self.teacher_table.setColumnCount(8)
        self.teacher_table.setHorizontalHeaderLabels(
            ["ID", "姓名", "电话", "性别", "年龄", "级别", "评分", "状态"]
        )
        self.teacher_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.teacher_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.teacher_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.teacher_table, 1)

        return widget

    def _create_student_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        btn_layout = QHBoxLayout()
        self.add_student_btn = QPushButton("添加学员")
        self.add_student_btn.clicked.connect(self.add_student)
        btn_layout.addWidget(self.add_student_btn)

        self.edit_student_btn = QPushButton("编辑")
        self.edit_student_btn.clicked.connect(self.edit_student)
        btn_layout.addWidget(self.edit_student_btn)

        self.delete_student_btn = QPushButton("删除")
        self.delete_student_btn.clicked.connect(self.delete_student)
        btn_layout.addWidget(self.delete_student_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.student_table = QTableWidget()
        self.student_table.setColumnCount(7)
        self.student_table.setHorizontalHeaderLabels(
            ["ID", "姓名", "电话", "性别", "年龄", "级别", "状态"]
        )
        self.student_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.student_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.student_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.student_table, 1)

        return widget

    def _load_rooms(self):
        rooms = self.scheduler.get_all_rooms()
        self.room_table.setRowCount(len(rooms))
        for row, room in enumerate(rooms):
            self.room_table.setItem(row, 0, QTableWidgetItem(str(room.id)))
            self.room_table.setItem(row, 1, QTableWidgetItem(room.name))
            self.room_table.setItem(row, 2, QTableWidgetItem(room.location or "-"))
            self.room_table.setItem(row, 3, QTableWidgetItem(str(room.capacity)))
            self.room_table.setItem(row, 4, QTableWidgetItem(room.status))

    def _load_teachers(self):
        teachers = self.scheduler.get_all_teachers()
        self.teacher_table.setRowCount(len(teachers))
        for row, teacher in enumerate(teachers):
            self.teacher_table.setItem(row, 0, QTableWidgetItem(str(teacher.id)))
            self.teacher_table.setItem(row, 1, QTableWidgetItem(teacher.name))
            self.teacher_table.setItem(row, 2, QTableWidgetItem(teacher.phone or "-"))
            self.teacher_table.setItem(row, 3, QTableWidgetItem(teacher.gender or "-"))
            self.teacher_table.setItem(row, 4, QTableWidgetItem(str(teacher.age) if teacher.age else "-"))
            self.teacher_table.setItem(row, 5, QTableWidgetItem(teacher.level or "-"))
            self.teacher_table.setItem(row, 6, QTableWidgetItem(f"{teacher.rating:.1f}" if teacher.rating else "-"))
            self.teacher_table.setItem(row, 7, QTableWidgetItem(teacher.status))

    def _load_students(self):
        students = self.scheduler.get_all_students()
        self.student_table.setRowCount(len(students))
        for row, student in enumerate(students):
            self.student_table.setItem(row, 0, QTableWidgetItem(str(student.id)))
            self.student_table.setItem(row, 1, QTableWidgetItem(student.name))
            self.student_table.setItem(row, 2, QTableWidgetItem(student.phone or "-"))
            self.student_table.setItem(row, 3, QTableWidgetItem(student.gender or "-"))
            self.student_table.setItem(row, 4, QTableWidgetItem(str(student.age) if student.age else "-"))
            self.student_table.setItem(row, 5, QTableWidgetItem(student.level or "-"))
            self.student_table.setItem(row, 6, QTableWidgetItem(student.status))

    def add_room(self):
        dialog = RoomDialog(self.scheduler, self)
        if dialog.exec() == QDialog.Accepted:
            self._load_rooms()

    def edit_room(self):
        row = self.room_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请先选择琴室")
            return
        from app.database.models import Room
        room_id = int(self.room_table.item(row, 0).text())
        room = self.scheduler.db.get_by_id(Room, room_id)
        if room:
            dialog = RoomDialog(self.scheduler, self, room)
            if dialog.exec() == QDialog.Accepted:
                self._load_rooms()

    def delete_room(self):
        row = self.room_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请先选择琴室")
            return
        room_id = int(self.room_table.item(row, 0).text())
        name = self.room_table.item(row, 1).text()
        reply = QMessageBox.question(self, "确认", f"确定要删除琴室「{name}」吗？")
        if reply == QMessageBox.Yes:
            if self.scheduler.delete_room(room_id):
                self._load_rooms()
                QMessageBox.information(self, "成功", "删除成功")

    def add_teacher(self):
        dialog = TeacherDialog(self.scheduler, self)
        if dialog.exec() == QDialog.Accepted:
            self._load_teachers()

    def edit_teacher(self):
        row = self.teacher_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请先选择老师")
            return
        from app.database.models import Teacher
        teacher_id = int(self.teacher_table.item(row, 0).text())
        teacher = self.scheduler.db.get_by_id(Teacher, teacher_id)
        if teacher:
            dialog = TeacherDialog(self.scheduler, self, teacher)
            if dialog.exec() == QDialog.Accepted:
                self._load_teachers()

    def delete_teacher(self):
        row = self.teacher_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请先选择老师")
            return
        teacher_id = int(self.teacher_table.item(row, 0).text())
        name = self.teacher_table.item(row, 1).text()
        reply = QMessageBox.question(self, "确认", f"确定要删除老师「{name}」吗？")
        if reply == QMessageBox.Yes:
            if self.scheduler.delete_teacher(teacher_id):
                self._load_teachers()
                QMessageBox.information(self, "成功", "删除成功")

    def add_student(self):
        dialog = StudentDialog(self.scheduler, self)
        if dialog.exec() == QDialog.Accepted:
            self._load_students()

    def edit_student(self):
        row = self.student_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请先选择学员")
            return
        from app.database.models import Student
        student_id = int(self.student_table.item(row, 0).text())
        student = self.scheduler.db.get_by_id(Student, student_id)
        if student:
            dialog = StudentDialog(self.scheduler, self, student)
            if dialog.exec() == QDialog.Accepted:
                self._load_students()

    def delete_student(self):
        row = self.student_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请先选择学员")
            return
        student_id = int(self.student_table.item(row, 0).text())
        name = self.student_table.item(row, 1).text()
        reply = QMessageBox.question(self, "确认", f"确定要删除学员「{name}」吗？")
        if reply == QMessageBox.Yes:
            if self.scheduler.delete_student(student_id):
                self._load_students()
                QMessageBox.information(self, "成功", "删除成功")


class RoomDialog(QDialog):
    def __init__(self, scheduler, parent=None, room=None):
        super().__init__(parent)
        self.scheduler = scheduler
        self.room = room
        self.setWindowTitle("编辑琴室" if room else "添加琴室")
        self.resize(400, 350)
        self._init_ui()

    def _init_ui(self):
        layout = QFormLayout(self)

        self.name_edit = QLineEdit()
        layout.addRow(QLabel("名称:"), self.name_edit)

        self.location_edit = QLineEdit()
        layout.addRow(QLabel("位置:"), self.location_edit)

        self.capacity_spin = QSpinBox()
        self.capacity_spin.setRange(1, 20)
        self.capacity_spin.setValue(1)
        layout.addRow(QLabel("容量:"), self.capacity_spin)

        self.equipment_edit = QTextEdit()
        self.equipment_edit.setMaximumHeight(80)
        layout.addRow(QLabel("设备:"), self.equipment_edit)

        self.status_combo = QComboBox()
        self.status_combo.addItems(["active", "inactive"])
        layout.addRow(QLabel("状态:"), self.status_combo)

        if self.room:
            self.name_edit.setText(self.room.name)
            self.location_edit.setText(self.room.location or "")
            self.capacity_spin.setValue(self.room.capacity or 1)
            self.equipment_edit.setPlainText(self.room.equipment or "")
            idx = self.status_combo.findText(self.room.status)
            if idx >= 0:
                self.status_combo.setCurrentIndex(idx)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def accept(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入琴室名称")
            return

        try:
            if self.room:
                self.scheduler.update_room(
                    self.room.id,
                    name=name,
                    location=self.location_edit.text().strip() or None,
                    capacity=self.capacity_spin.value(),
                    equipment=self.equipment_edit.toPlainText().strip() or None,
                    status=self.status_combo.currentText()
                )
            else:
                self.scheduler.add_room(
                    name=name,
                    location=self.location_edit.text().strip() or None,
                    capacity=self.capacity_spin.value(),
                    equipment=self.equipment_edit.toPlainText().strip() or None,
                    status=self.status_combo.currentText()
                )
            super().accept()
        except Exception as e:
            QMessageBox.warning(self, "错误", str(e))


class TeacherDialog(QDialog):
    def __init__(self, scheduler, parent=None, teacher=None):
        super().__init__(parent)
        self.scheduler = scheduler
        self.teacher = teacher
        self.setWindowTitle("编辑老师" if teacher else "添加老师")
        self.resize(500, 550)
        self._init_ui()

    def _init_ui(self):
        layout = QFormLayout(self)

        self.name_edit = QLineEdit()
        layout.addRow(QLabel("姓名:"), self.name_edit)

        self.phone_edit = QLineEdit()
        layout.addRow(QLabel("电话:"), self.phone_edit)

        self.gender_combo = QComboBox()
        self.gender_combo.addItems(["", "男", "女"])
        layout.addRow(QLabel("性别:"), self.gender_combo)

        self.age_spin = QSpinBox()
        self.age_spin.setRange(18, 80)
        self.age_spin.setValue(30)
        layout.addRow(QLabel("年龄:"), self.age_spin)

        self.level_combo = QComboBox()
        self.level_combo.addItems(["", "入门", "初级", "中级", "高级", "专业"])
        layout.addRow(QLabel("级别:"), self.level_combo)

        self.styles_edit = QLineEdit()
        self.styles_edit.setPlaceholderText("用逗号分隔，如：传统,现代,流行")
        layout.addRow(QLabel("擅长曲风:"), self.styles_edit)

        self.rating_spin = QSpinBox()
        self.rating_spin.setRange(1, 5)
        self.rating_spin.setValue(5)
        layout.addRow(QLabel("评分:"), self.rating_spin)

        self.experience_spin = QSpinBox()
        self.experience_spin.setRange(0, 50)
        layout.addRow(QLabel("教学经验(年):"), self.experience_spin)

        self.certificate_edit = QLineEdit()
        layout.addRow(QLabel("证书:"), self.certificate_edit)

        self.bio_edit = QTextEdit()
        self.bio_edit.setMaximumHeight(80)
        layout.addRow(QLabel("简介:"), self.bio_edit)

        self.status_combo = QComboBox()
        self.status_combo.addItems(["active", "inactive"])
        layout.addRow(QLabel("状态:"), self.status_combo)

        if self.teacher:
            self.name_edit.setText(self.teacher.name)
            self.phone_edit.setText(self.teacher.phone or "")
            idx = self.gender_combo.findText(self.teacher.gender or "")
            if idx >= 0:
                self.gender_combo.setCurrentIndex(idx)
            self.age_spin.setValue(self.teacher.age or 30)
            idx = self.level_combo.findText(self.teacher.level or "")
            if idx >= 0:
                self.level_combo.setCurrentIndex(idx)
            self.styles_edit.setText(self.teacher.styles or "")
            self.rating_spin.setValue(int(self.teacher.rating) if self.teacher.rating else 5)
            self.experience_spin.setValue(self.teacher.experience_years or 0)
            self.certificate_edit.setText(self.teacher.certificate or "")
            self.bio_edit.setPlainText(self.teacher.bio or "")
            idx = self.status_combo.findText(self.teacher.status)
            if idx >= 0:
                self.status_combo.setCurrentIndex(idx)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def accept(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入姓名")
            return

        try:
            gender = self.gender_combo.currentText() or None
            level = self.level_combo.currentText() or None

            if self.teacher:
                self.scheduler.update_teacher(
                    self.teacher.id,
                    name=name,
                    phone=self.phone_edit.text().strip() or None,
                    gender=gender,
                    age=self.age_spin.value(),
                    level=level,
                    styles=self.styles_edit.text().strip() or None,
                    rating=float(self.rating_spin.value()),
                    experience_years=self.experience_spin.value(),
                    certificate=self.certificate_edit.text().strip() or None,
                    bio=self.bio_edit.toPlainText().strip() or None,
                    status=self.status_combo.currentText()
                )
            else:
                self.scheduler.add_teacher(
                    name=name,
                    phone=self.phone_edit.text().strip() or None,
                    gender=gender,
                    age=self.age_spin.value(),
                    level=level,
                    styles=self.styles_edit.text().strip() or None,
                    rating=float(self.rating_spin.value()),
                    experience_years=self.experience_spin.value(),
                    certificate=self.certificate_edit.text().strip() or None,
                    bio=self.bio_edit.toPlainText().strip() or None,
                    status=self.status_combo.currentText()
                )
            super().accept()
        except Exception as e:
            QMessageBox.warning(self, "错误", str(e))


class StudentDialog(QDialog):
    def __init__(self, scheduler, parent=None, student=None):
        super().__init__(parent)
        self.scheduler = scheduler
        self.student = student
        self.setWindowTitle("编辑学员" if student else "添加学员")
        self.resize(500, 500)
        self._init_ui()

    def _init_ui(self):
        layout = QFormLayout(self)

        self.name_edit = QLineEdit()
        layout.addRow(QLabel("姓名:"), self.name_edit)

        self.phone_edit = QLineEdit()
        layout.addRow(QLabel("电话:"), self.phone_edit)

        self.gender_combo = QComboBox()
        self.gender_combo.addItems(["", "男", "女"])
        layout.addRow(QLabel("性别:"), self.gender_combo)

        self.age_spin = QSpinBox()
        self.age_spin.setRange(3, 100)
        self.age_spin.setValue(10)
        layout.addRow(QLabel("年龄:"), self.age_spin)

        self.level_combo = QComboBox()
        self.level_combo.addItems(["", "入门", "初级", "中级", "高级", "专业"])
        layout.addRow(QLabel("级别:"), self.level_combo)

        self.style_edit = QLineEdit()
        self.style_edit.setPlaceholderText("如：传统,流行")
        layout.addRow(QLabel("偏好曲风:"), self.style_edit)

        self.goal_edit = QLineEdit()
        layout.addRow(QLabel("学习目标:"), self.goal_edit)

        self.exam_level_combo = QComboBox()
        self.exam_level_combo.addItems(["", "一级", "二级", "三级", "四级", "五级", "六级", "七级", "八级", "九级", "十级"])
        layout.addRow(QLabel("考级级别:"), self.exam_level_combo)

        self.status_combo = QComboBox()
        self.status_combo.addItems(["active", "inactive"])
        layout.addRow(QLabel("状态:"), self.status_combo)

        if self.student:
            self.name_edit.setText(self.student.name)
            self.phone_edit.setText(self.student.phone or "")
            idx = self.gender_combo.findText(self.student.gender or "")
            if idx >= 0:
                self.gender_combo.setCurrentIndex(idx)
            self.age_spin.setValue(self.student.age or 10)
            idx = self.level_combo.findText(self.student.level or "")
            if idx >= 0:
                self.level_combo.setCurrentIndex(idx)
            self.style_edit.setText(self.student.preferred_style or "")
            self.goal_edit.setText(self.student.learning_goal or "")
            idx = self.exam_level_combo.findText(self.student.exam_level or "")
            if idx >= 0:
                self.exam_level_combo.setCurrentIndex(idx)
            idx = self.status_combo.findText(self.student.status)
            if idx >= 0:
                self.status_combo.setCurrentIndex(idx)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def accept(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入姓名")
            return

        try:
            gender = self.gender_combo.currentText() or None
            level = self.level_combo.currentText() or None
            exam_level = self.exam_level_combo.currentText() or None

            if self.student:
                self.scheduler.update_student(
                    self.student.id,
                    name=name,
                    phone=self.phone_edit.text().strip() or None,
                    gender=gender,
                    age=self.age_spin.value(),
                    level=level,
                    preferred_style=self.style_edit.text().strip() or None,
                    learning_goal=self.goal_edit.text().strip() or None,
                    exam_level=exam_level,
                    status=self.status_combo.currentText()
                )
            else:
                self.scheduler.add_student(
                    name=name,
                    phone=self.phone_edit.text().strip() or None,
                    gender=gender,
                    age=self.age_spin.value(),
                    level=level,
                    preferred_style=self.style_edit.text().strip() or None,
                    learning_goal=self.goal_edit.text().strip() or None,
                    exam_level=exam_level,
                    status=self.status_combo.currentText()
                )
            super().accept()
        except Exception as e:
            QMessageBox.warning(self, "错误", str(e))
