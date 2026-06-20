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
            "status": ["pending", "confirmed", "checked_in"]
        })
        if existing_enroll:
            raise ValueError("该学生已报名此课程")

        def query(session):
            current_count = session.query(Waitlist).filter(
                and_(Waitlist.schedule_id == schedule_id, Waitlist.status == "waiting")
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
                and_(Waitlist.schedule_id == schedule_id, Waitlist.status == "waiting")
            ).order_by(Waitlist.priority_score.desc(), Waitlist.created_at).all()

            for idx, entry in enumerate(waiting, 1):
                entry.queue_position = idx
                session.add(entry)

            session.commit()
        return self.db.execute_query(query)

    def get_waitlist(self, schedule_id=None, student_id=None, status=None):
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

        def query(session):
            q = session.query(Waitlist)
            if schedule_id:
                q = q.filter(Waitlist.schedule_id == schedule_id)
            if student_id:
                q = q.filter(Waitlist.student_id == student_id)
            if status:
                if isinstance(status, list):
                    q = q.filter(Waitlist.status.in_(status))
                else:
                    q = q.filter(Waitlist.status == status)
            return q.order_by(Waitlist.queue_position).all()
        return self.db.execute_query(query)

    def get_notified_with_remaining(self, schedule_id=None):
        waitlist_confirm_minutes = self.settings.get("waitlist_confirm_minutes", 30)
        now = datetime.now()

        def query(session):
            q = session.query(Waitlist).filter(Waitlist.status == "notified")
            if schedule_id:
                q = q.filter(Waitlist.schedule_id == schedule_id)
            results = q.order_by(Waitlist.notified_time).all()

            entries = []
            for entry in results:
                deadline = entry.confirm_deadline or (entry.notified_time + timedelta(minutes=waitlist_confirm_minutes) if entry.notified_time else None)
                remaining = max(0, (deadline - now).total_seconds()) if deadline else 0
                entries.append({
                    "entry": entry,
                    "remaining_seconds": remaining,
                    "deadline": deadline,
                    "is_expired": remaining <= 0
                })
            return entries
        return self.db.execute_query(query)

    def process_waitlist_for_schedule(self, schedule_id, notify_source="manual"):
        schedule = self.db.get_by_id(Schedule, schedule_id)
        if not schedule:
            return []

        if schedule.current_students >= schedule.max_students:
            return []

        waitlist_confirm_minutes = self.settings.get("waitlist_confirm_minutes", 30)
        notified = []

        def query(session):
            effective_available = self._get_effective_available_slots(schedule_id, session)
            if effective_available <= 0:
                return []

            waiting_list = session.query(Waitlist).filter(
                and_(Waitlist.schedule_id == schedule_id, Waitlist.status == "waiting")
            ).order_by(Waitlist.priority_score.desc(), Waitlist.created_at).limit(effective_available).all()

            now = datetime.now()
            for entry in waiting_list:
                entry.status = "notified"
                entry.notify_source = notify_source
                entry.notified_time = now
                entry.confirm_deadline = now + timedelta(minutes=waitlist_confirm_minutes)
                session.add(entry)
                notified.append(entry)

            session.commit()
            return notified
        return self.db.execute_query(query)

    def _get_effective_available_slots(self, schedule_id, session):
        schedule = session.query(Schedule).filter(Schedule.id == schedule_id).first()
        if not schedule:
            return 0

        notified_count = session.query(Waitlist).filter(
            and_(Waitlist.schedule_id == schedule_id, Waitlist.status == "notified")
        ).count()

        effective_available = schedule.max_students - schedule.current_students - notified_count
        return max(0, effective_available)

    def confirm_waitlist_enrollment(self, waitlist_id):
        waitlist = self.db.get_by_id(Waitlist, waitlist_id)
        if not waitlist or waitlist.status != "notified":
            return None

        now = datetime.now()
        if waitlist.confirm_deadline and now > waitlist.confirm_deadline:
            waitlist.status = "expired"
            waitlist.expired_time = now
            self.db.update(waitlist)
            self.auto_notify_next(waitlist.schedule_id, notify_source="expired_release")
            return None

        schedule = self.db.get_by_id(Schedule, waitlist.schedule_id)
        if not schedule or schedule.current_students >= schedule.max_students:
            waitlist.status = "expired"
            waitlist.expired_time = now
            self.db.update(waitlist)
            self.auto_notify_next(waitlist.schedule_id, notify_source="expired_release")
            return None

        try:
            enrollment = self.scheduler.enroll_student(waitlist.schedule_id, waitlist.student_id)
            waitlist.status = "enrolled"
            waitlist.enrolled_time = now
            self.db.update(waitlist)
            self._reorder_queue(waitlist.schedule_id)
            self.auto_notify_next(waitlist.schedule_id)
            return enrollment
        except ValueError:
            return None

    def decline_waitlist_offer(self, waitlist_id):
        waitlist = self.db.get_by_id(Waitlist, waitlist_id)
        if waitlist:
            waitlist.status = "declined"
            self.db.update(waitlist)
            self._reorder_queue(waitlist.schedule_id)
            self.auto_notify_next(waitlist.schedule_id)
            return True
        return False

    def auto_notify_next(self, schedule_id, notify_source="cancel_release"):
        schedule = self.db.get_by_id(Schedule, schedule_id)
        if not schedule or schedule.current_students >= schedule.max_students:
            return []

        waitlist_confirm_minutes = self.settings.get("waitlist_confirm_minutes", 30)
        notified = []

        def query(session):
            effective_available = self._get_effective_available_slots(schedule_id, session)
            if effective_available <= 0:
                return []

            waiting = session.query(Waitlist).filter(
                and_(Waitlist.schedule_id == schedule_id, Waitlist.status == "waiting")
            ).order_by(Waitlist.priority_score.desc(), Waitlist.created_at).limit(effective_available).all()

            now = datetime.now()
            for entry in waiting:
                entry.status = "notified"
                entry.notify_source = notify_source
                entry.notified_time = now
                entry.confirm_deadline = now + timedelta(minutes=waitlist_confirm_minutes)
                session.add(entry)
                notified.append(entry)

            session.commit()
            return notified
        return self.db.execute_query(query)

    def check_expired_notifications(self):
        now = datetime.now()
        waitlist_confirm_minutes = self.settings.get("waitlist_confirm_minutes", 30)

        def query(session):
            expired = session.query(Waitlist).filter(
                and_(Waitlist.status == "notified", Waitlist.confirm_deadline < now)
            ).all()

            affected_schedule_ids = set()
            for entry in expired:
                entry.status = "expired"
                entry.expired_time = now
                session.add(entry)
                affected_schedule_ids.add(entry.schedule_id)

            session.commit()

            for sid in affected_schedule_ids:
                self.auto_notify_next(sid, notify_source="expired_release")

            return list(expired)
        return self.db.execute_query(query)

    def notify_with_result(self, schedule_id, notify_source="manual"):
        result = self.process_waitlist_for_schedule(schedule_id, notify_source=notify_source)
        student_names = []
        from app.database.models import Student as StuModel
        for entry in result:
            s = self.scheduler.db.get_by_id(StuModel, entry.student_id)
            if s:
                student_names.append(s.name)
        return {
            "schedule_id": schedule_id,
            "source": notify_source,
            "count": len(result),
            "entries": result,
            "student_names": student_names
        }

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
            notified = session.query(Waitlist).filter(
                and_(Waitlist.schedule_id == schedule_id, Waitlist.status == "notified")
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
                "notified": notified,
                "enrolled": enrolled,
                "expired_declined": expired
            }
        return self.db.execute_query(query)
