from datetime import datetime, timedelta
from sqlalchemy import and_
from app.database.models import Waitlist, Schedule, Enrollment, Student
from app.config.settings import AppSettings


class WaitlistService:
    def __init__(self, db_manager, scheduler):
        self.db = db_manager
        self.scheduler = scheduler
        self.settings = AppSettings()

    def add_to_waitlist(self, schedule_id, student_id, priority_score=0.0):
        schedule = self.db.get_by_id(Schedule, schedule_id)
        if not schedule:
            raise ValueError("课程不存在")

        existing_wait = self.db.query(Waitlist, filters={
            "schedule_id": schedule_id,
            "student_id": student_id,
            "status": "waiting"
        })
        if existing_wait:
            raise ValueError("该学生已在候补队列中")

        existing_enroll = self.db.query(Enrollment, filters={
            "schedule_id": schedule_id,
            "student_id": student_id,
            "status": ["enrolled", "confirmed"]
        })
        if existing_enroll:
            raise ValueError("该学生已报名此课程")

        def query(session):
            current_count = session.query(Waitlist).filter(
                and_(
                    Waitlist.schedule_id == schedule_id,
                    Waitlist.status == "waiting"
                )
            ).count()

            waitlist_entry = Waitlist(
                schedule_id=schedule_id,
                student_id=student_id,
                priority_score=priority_score,
                queue_position=current_count + 1,
                status="waiting"
            )
            session.add(waitlist_entry)
            session.commit()
            session.refresh(waitlist_entry)
            return waitlist_entry
        return self.db.execute_query(query)

    def remove_from_waitlist(self, waitlist_id):
        waitlist = self.db.get_by_id(Waitlist, waitlist_id)
        if waitlist:
            waitlist.status = "cancelled"
            self.db.update(waitlist)
            self._reorder_queue(waitlist.schedule_id)
            return True
        return False

    def _reorder_queue(self, schedule_id):
        def query(session):
            waiting = session.query(Waitlist).filter(
                and_(
                    Waitlist.schedule_id == schedule_id,
                    Waitlist.status == "waiting"
                )
            ).order_by(Waitlist.priority_score.desc(), Waitlist.created_at).all()

            for idx, entry in enumerate(waiting, 1):
                entry.queue_position = idx
                session.add(entry)

            session.commit()
        return self.db.execute_query(query)

    def get_waitlist(self, schedule_id=None, student_id=None, status="waiting"):
        filters = {}
        if schedule_id:
            filters["schedule_id"] = schedule_id
        if student_id:
            filters["student_id"] = student_id
        if status:
            filters["status"] = status

        def query(session):
            q = session.query(Waitlist)
            if schedule_id:
                q = q.filter(Waitlist.schedule_id == schedule_id)
            if student_id:
                q = q.filter(Waitlist.student_id == student_id)
            if status:
                q = q.filter(Waitlist.status == status)
            return q.order_by(Waitlist.queue_position).all()
        return self.db.execute_query(query)

    def process_waitlist_for_schedule(self, schedule_id):
        schedule = self.db.get_by_id(Schedule, schedule_id)
        if not schedule:
            return []

        if schedule.current_students >= schedule.max_students:
            return []

        available_slots = schedule.max_students - schedule.current_students
        notified = []

        def query(session):
            waiting_list = session.query(Waitlist).filter(
                and_(
                    Waitlist.schedule_id == schedule_id,
                    Waitlist.status == "waiting"
                )
            ).order_by(Waitlist.priority_score.desc(), Waitlist.created_at).limit(available_slots).all()

            for entry in waiting_list:
                entry.status = "notified"
                entry.notified_time = datetime.now()
                session.add(entry)
                notified.append(entry)

            session.commit()
            return notified
        return self.db.execute_query(query)

    def confirm_waitlist_enrollment(self, waitlist_id):
        waitlist = self.db.get_by_id(Waitlist, waitlist_id)
        if not waitlist or waitlist.status != "notified":
            return None

        schedule = self.db.get_by_id(Schedule, waitlist.schedule_id)
        if not schedule or schedule.current_students >= schedule.max_students:
            waitlist.status = "expired"
            waitlist.expired_time = datetime.now()
            self.db.update(waitlist)
            return None

        auto_release_minutes = self.settings.get("auto_release_minutes", 15)
        if waitlist.notified_time and datetime.now() - waitlist.notified_time > timedelta(minutes=auto_release_minutes):
            waitlist.status = "expired"
            waitlist.expired_time = datetime.now()
            self.db.update(waitlist)
            self._reorder_queue(waitlist.schedule_id)
            return None

        try:
            enrollment = self.scheduler.enroll_student(waitlist.schedule_id, waitlist.student_id)
            waitlist.status = "enrolled"
            waitlist.enrolled_time = datetime.now()
            self.db.update(waitlist)
            self._reorder_queue(waitlist.schedule_id)
            return enrollment
        except ValueError:
            return None

    def decline_waitlist_offer(self, waitlist_id):
        waitlist = self.db.get_by_id(Waitlist, waitlist_id)
        if waitlist:
            waitlist.status = "declined"
            self.db.update(waitlist)
            self._reorder_queue(waitlist.schedule_id)
            return True
        return False

    def check_expired_notifications(self):
        auto_release_minutes = self.settings.get("auto_release_minutes", 15)
        now = datetime.now()
        threshold = now - timedelta(minutes=auto_release_minutes)

        def query(session):
            expired = session.query(Waitlist).filter(
                and_(
                    Waitlist.status == "notified",
                    Waitlist.notified_time < threshold
                )
            ).all()

            result = []
            for entry in expired:
                entry.status = "expired"
                entry.expired_time = now
                session.add(entry)
                result.append(entry)

            session.commit()

            for entry in result:
                waiting = session.query(Waitlist).filter(
                    and_(
                        Waitlist.schedule_id == entry.schedule_id,
                        Waitlist.status == "waiting"
                    )
                ).order_by(Waitlist.priority_score.desc(), Waitlist.created_at).limit(1).first()

                if waiting:
                    schedule = session.query(Schedule).filter(Schedule.id == entry.schedule_id).first()
                    if schedule and schedule.current_students < schedule.max_students:
                        waiting.status = "notified"
                        waiting.notified_time = now
                        session.add(waiting)

            session.commit()
            return result
        return self.db.execute_query(query)

    def update_priority_score(self, waitlist_id, score):
        waitlist = self.db.get_by_id(Waitlist, waitlist_id)
        if waitlist:
            waitlist.priority_score = score
            self.db.update(waitlist)
            self._reorder_queue(waitlist.schedule_id)
            return True
        return False

    def get_waitlist_statistics(self, schedule_id):
        def query(session):
            total = session.query(Waitlist).filter(Waitlist.schedule_id == schedule_id).count()
            waiting = session.query(Waitlist).filter(
                and_(Waitlist.schedule_id == schedule_id, Waitlist.status == "waiting")
            ).count()
            enrolled = session.query(Waitlist).filter(
                and_(Waitlist.schedule_id == schedule_id, Waitlist.status == "enrolled")
            ).count()
            expired = session.query(Waitlist).filter(
                and_(Waitlist.schedule_id == schedule_id, Waitlist.status.in_(["expired", "declined"]))
            ).count()

            return {
                "total": total,
                "waiting": waiting,
                "enrolled": enrolled,
                "expired_declined": expired
            }
        return self.db.execute_query(query)
