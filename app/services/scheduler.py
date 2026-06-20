from datetime import datetime, timedelta
from sqlalchemy import and_, or_
from app.database.models import Room, Teacher, Student, Schedule, Enrollment, Archive, MusicPiece, RecommendationLog, Waitlist
from app.config.settings import AppSettings


class SchedulerService:
    VALID_TRANSITIONS = {
        "pending": ["confirmed", "cancelled"],
        "confirmed": ["checked_in", "cancelled"],
        "checked_in": ["completed", "cancelled"],
        "completed": [],
        "cancelled": [],
        "released": []
    }

    STATUS_LABELS = {
        "pending": "待确认",
        "confirmed": "已确认",
        "checked_in": "已签到",
        "completed": "已完成",
        "cancelled": "已取消",
        "released": "已释放"
    }

    def __init__(self, db_manager):
        self.db = db_manager
        self.settings = AppSettings()
        self._on_release_callback = None

    def set_release_callback(self, callback):
        self._on_release_callback = callback

    def add_room(self, name, location=None, capacity=1, equipment=None, status="active"):
        room = Room(name=name, location=location, capacity=capacity, equipment=equipment, status=status)
        return self.db.add(room)

    def update_room(self, room_id, **kwargs):
        room = self.db.get_by_id(Room, room_id)
        if room:
            for key, value in kwargs.items():
                if hasattr(room, key):
                    setattr(room, key, value)
            return self.db.update(room)
        return None

    def delete_room(self, room_id):
        room = self.db.get_by_id(Room, room_id)
        if room:
            self.db.delete(room)
            return True
        return False

    def get_all_rooms(self, status=None):
        filters = {}
        if status:
            filters["status"] = status
        return self.db.query(Room, filters=filters, order_by=Room.name)

    def add_teacher(self, name, phone=None, gender=None, age=None, level=None, styles=None,
                   rating=5.0, experience_years=0, certificate=None, bio=None, status="active"):
        teacher = Teacher(name=name, phone=phone, gender=gender, age=age, level=level,
                         styles=styles, rating=rating, experience_years=experience_years,
                         certificate=certificate, bio=bio, status=status)
        return self.db.add(teacher)

    def update_teacher(self, teacher_id, **kwargs):
        teacher = self.db.get_by_id(Teacher, teacher_id)
        if teacher:
            for key, value in kwargs.items():
                if hasattr(teacher, key):
                    setattr(teacher, key, value)
            return self.db.update(teacher)
        return None

    def delete_teacher(self, teacher_id):
        teacher = self.db.get_by_id(Teacher, teacher_id)
        if teacher:
            self.db.delete(teacher)
            return True
        return False

    def get_all_teachers(self, status=None):
        filters = {}
        if status:
            filters["status"] = status
        return self.db.query(Teacher, filters=filters, order_by=Teacher.name)

    def add_student(self, name, phone=None, gender=None, age=None, level=None,
                   preferred_style=None, learning_goal=None, exam_level=None, status="active"):
        student = Student(name=name, phone=phone, gender=gender, age=age, level=level,
                         preferred_style=preferred_style, learning_goal=learning_goal,
                         exam_level=exam_level, status=status)
        return self.db.add(student)

    def update_student(self, student_id, **kwargs):
        student = self.db.get_by_id(Student, student_id)
        if student:
            for key, value in kwargs.items():
                if hasattr(student, key):
                    setattr(student, key, value)
            return self.db.update(student)
        return None

    def delete_student(self, student_id):
        student = self.db.get_by_id(Student, student_id)
        if student:
            self.db.delete(student)
            return True
        return False

    def get_all_students(self, status=None):
        filters = {}
        if status:
            filters["status"] = status
        return self.db.query(Student, filters=filters, order_by=Student.name)

    def add_music_piece(self, name, composer=None, style=None, difficulty_level=None,
                         exam_category=None, exam_level=None, duration_minutes=None, description=None):
        piece = MusicPiece(name=name, composer=composer, style=style,
                          difficulty_level=difficulty_level, exam_category=exam_category,
                          exam_level=exam_level, duration_minutes=duration_minutes,
                          description=description)
        return self.db.add(piece)

    def update_music_piece(self, piece_id, **kwargs):
        piece = self.db.get_by_id(MusicPiece, piece_id)
        if piece:
            for key, value in kwargs.items():
                if hasattr(piece, key):
                    setattr(piece, key, value)
            return self.db.update(piece)
        return None

    def delete_music_piece(self, piece_id):
        piece = self.db.get_by_id(MusicPiece, piece_id)
        if piece:
            self.db.delete(piece)
            return True
        return False

    def get_all_music_pieces(self):
        return self.db.query(MusicPiece, order_by=MusicPiece.name)

    def check_room_availability(self, room_id, start_time, end_time, exclude_schedule_id=None):
        def query(session):
            q = session.query(Schedule).filter(
                and_(Schedule.room_id == room_id,
                     Schedule.status.in_(["scheduled", "in_progress"]),
                     and_(Schedule.start_time < end_time, Schedule.end_time > start_time))
            )
            if exclude_schedule_id:
                q = q.filter(Schedule.id != exclude_schedule_id)
            return q.first() is None
        return self.db.execute_query(query)

    def check_teacher_availability(self, teacher_id, start_time, end_time, exclude_schedule_id=None):
        def query(session):
            q = session.query(Schedule).filter(
                and_(Schedule.teacher_id == teacher_id,
                     Schedule.status.in_(["scheduled", "in_progress"]),
                     and_(Schedule.start_time < end_time, Schedule.end_time > start_time))
            )
            if exclude_schedule_id:
                q = q.filter(Schedule.id != exclude_schedule_id)
            return q.first() is None
        return self.db.execute_query(query)

    def add_schedule(self, room_id, teacher_id, course_name, course_type, start_time, end_time,
                    max_students=1, notes=None):
        if not self.check_room_availability(room_id, start_time, end_time):
            raise ValueError("琴室在该时间段已被占用")
        if not self.check_teacher_availability(teacher_id, start_time, end_time):
            raise ValueError("老师在该时间段已被占用")
        schedule = Schedule(room_id=room_id, teacher_id=teacher_id, course_name=course_name,
                          course_type=course_type, start_time=start_time, end_time=end_time,
                          max_students=max_students, current_students=0, status="scheduled", notes=notes)
        return self.db.add(schedule)

    def update_schedule(self, schedule_id, **kwargs):
        schedule = self.db.get_by_id(Schedule, schedule_id)
        if schedule:
            room_id = kwargs.get("room_id", schedule.room_id)
            teacher_id = kwargs.get("teacher_id", schedule.teacher_id)
            start_time = kwargs.get("start_time", schedule.start_time)
            end_time = kwargs.get("end_time", schedule.end_time)
            if room_id != schedule.room_id or start_time != schedule.start_time or end_time != schedule.end_time:
                if not self.check_room_availability(room_id, start_time, end_time, schedule_id):
                    raise ValueError("琴室在该时间段已被占用")
            if teacher_id != schedule.teacher_id or start_time != schedule.start_time or end_time != schedule.end_time:
                if not self.check_teacher_availability(teacher_id, start_time, end_time, schedule_id):
                    raise ValueError("老师在该时间段已被占用")
            for key, value in kwargs.items():
                if hasattr(schedule, key):
                    setattr(schedule, key, value)
            return self.db.update(schedule)
        return None

    def delete_schedule(self, schedule_id):
        schedule = self.db.get_by_id(Schedule, schedule_id)
        if schedule:
            self.db.delete(schedule)
            return True
        return False

    def get_schedules(self, start_date=None, end_date=None, status=None, room_id=None, teacher_id=None):
        def query(session):
            q = session.query(Schedule)
            if start_date:
                q = q.filter(Schedule.start_time >= start_date)
            if end_date:
                q = q.filter(Schedule.end_time <= end_date)
            if status:
                q = q.filter(Schedule.status == status)
            if room_id:
                q = q.filter(Schedule.room_id == room_id)
            if teacher_id:
                q = q.filter(Schedule.teacher_id == teacher_id)
            return q.order_by(Schedule.start_time).all()
        return self.db.execute_query(query)

    def get_schedule_by_id(self, schedule_id):
        return self.db.get_by_id(Schedule, schedule_id)

    def enroll_student(self, schedule_id, student_id):
        def query(session):
            schedule = session.query(Schedule).filter(Schedule.id == schedule_id).first()
            if not schedule:
                raise ValueError("课程不存在")
            if schedule.current_students >= schedule.max_students:
                raise ValueError("课程已满，无法报名")
            existing = session.query(Enrollment).filter(
                Enrollment.schedule_id == schedule_id,
                Enrollment.student_id == student_id,
                Enrollment.status.in_(["pending", "confirmed", "checked_in"])
            ).first()
            if existing:
                raise ValueError("该学生已报名此课程")
            enrollment = Enrollment(schedule_id=schedule_id, student_id=student_id, status="pending")
            session.add(enrollment)
            schedule.current_students += 1
            session.add(schedule)
            session.commit()
            session.refresh(enrollment)
            return enrollment
        return self.db.execute_query(query)

    def transition_enrollment(self, enrollment_id, new_status):
        enrollment = self.db.get_by_id(Enrollment, enrollment_id)
        if not enrollment:
            raise ValueError("报名记录不存在")
        current = enrollment.status
        if new_status not in self.VALID_TRANSITIONS.get(current, []):
            label = self.STATUS_LABELS.get(current, current)
            target = self.STATUS_LABELS.get(new_status, new_status)
            raise ValueError(f"无法从「{label}」转到「{target}」")
        now = datetime.now()
        enrollment.status = new_status
        if new_status == "confirmed":
            enrollment.confirm_time = now
        elif new_status == "checked_in":
            enrollment.checkin_time = now
        elif new_status == "completed":
            enrollment.complete_time = now
        elif new_status == "cancelled":
            enrollment.cancel_time = now
            schedule = self.db.get_by_id(Schedule, enrollment.schedule_id)
            if schedule and schedule.current_students > 0:
                schedule.current_students -= 1
                self.db.update(schedule)
        return self.db.update(enrollment)

    def confirm_enrollment(self, enrollment_id):
        return self.transition_enrollment(enrollment_id, "confirmed")

    def checkin_student(self, enrollment_id):
        return self.transition_enrollment(enrollment_id, "checked_in")

    def complete_enrollment(self, enrollment_id):
        return self.transition_enrollment(enrollment_id, "completed")

    def cancel_enrollment(self, enrollment_id):
        return self.transition_enrollment(enrollment_id, "cancelled")

    def get_enrollment_by_id(self, enrollment_id):
        return self.db.get_by_id(Enrollment, enrollment_id)

    def get_enrollments(self, schedule_id=None, student_id=None, status=None):
        filters = {}
        if schedule_id:
            filters["schedule_id"] = schedule_id
        if student_id:
            filters["student_id"] = student_id
        if status:
            if isinstance(status, list):
                filters["status"] = status
            else:
                filters["status"] = status
        return self.db.query(Enrollment, filters=filters)

    def check_and_release_overdue(self):
        auto_release_minutes = self.settings.get("auto_release_minutes", 15)
        now = datetime.now()
        threshold = now - timedelta(minutes=auto_release_minutes)

        def query(session):
            overdue = session.query(Enrollment).filter(
                and_(Enrollment.status == "pending",
                     Enrollment.enroll_time < threshold,
                     Enrollment.confirm_time.is_(None))
            ).all()

            released_schedule_ids = []
            for enrollment in overdue:
                enrollment.status = "released"
                enrollment.cancel_time = now
                schedule = session.query(Schedule).filter(Schedule.id == enrollment.schedule_id).first()
                if schedule and schedule.current_students > 0:
                    schedule.current_students -= 1
                    session.add(schedule)
                released_schedule_ids.append(enrollment.schedule_id)
                session.add(enrollment)

            session.commit()
            return released_schedule_ids
        released_schedule_ids = self.db.execute_query(query)

        if released_schedule_ids and self._on_release_callback:
            for sid in set(released_schedule_ids):
                try:
                    self._on_release_callback(sid)
                except Exception:
                    pass

        return released_schedule_ids

    def archive_completed_courses(self):
        now = datetime.now()

        def query(session):
            completed = session.query(Schedule).filter(
                and_(Schedule.end_time < now,
                     Schedule.status.in_(["scheduled", "in_progress"]))
            ).all()

            count = 0
            for schedule in completed:
                enrollments = session.query(Enrollment).filter(
                    Enrollment.schedule_id == schedule.id
                ).all()

                for enrollment in enrollments:
                    teacher = session.query(Teacher).filter(Teacher.id == schedule.teacher_id).first()
                    student = session.query(Student).filter(Student.id == enrollment.student_id).first()

                    rec_log = session.query(RecommendationLog).filter(
                        and_(RecommendationLog.student_id == enrollment.student_id,
                             RecommendationLog.teacher_id == schedule.teacher_id)
                    ).order_by(RecommendationLog.created_at.desc()).first()

                    archive = Archive(
                        schedule_id=schedule.id,
                        student_id=enrollment.student_id,
                        teacher_id=schedule.teacher_id,
                        room_id=schedule.room_id,
                        course_name=schedule.course_name,
                        course_type=schedule.course_type,
                        course_date=schedule.start_time,
                        actual_start=schedule.start_time,
                        actual_end=schedule.end_time,
                        student_name=student.name if student else "",
                        teacher_name=teacher.name if teacher else "",
                        room_name=schedule.room.name if schedule.room else "",
                        teacher_style=teacher.styles if teacher else "",
                        student_style=student.preferred_style if student else "",
                        student_level=student.level if student else "",
                        student_exam_level=student.exam_level if student else "",
                        status=enrollment.status,
                        match_score=rec_log.total_score if rec_log else None,
                        style_score=rec_log.style_score if rec_log else None,
                        rating_score=rec_log.rating_score if rec_log else None,
                        level_score=rec_log.level_score if rec_log else None,
                        availability_score=rec_log.availability_score if rec_log else None,
                        experience_score=rec_log.experience_score if rec_log else None,
                        notes=enrollment.notes
                    )
                    session.add(archive)
                    count += 1

                schedule.status = "completed"
                session.add(schedule)

            session.commit()
            return count
        return self.db.execute_query(query)
