from datetime import datetime, timedelta
from sqlalchemy import and_
from app.database.models import Teacher, Student, Schedule, Enrollment, RecommendationLog
from app.config.settings import AppSettings


class RecommenderService:
    def __init__(self, db_manager):
        self.db = db_manager
        self.settings = AppSettings()
        self.level_order = ["入门", "初级", "中级", "高级", "专业"]

    def _calculate_style_score(self, student, teacher):
        if not student.preferred_style or not teacher.styles:
            return 0.5
        student_styles = [s.strip() for s in student.preferred_style.split(",")]
        teacher_styles = [s.strip() for s in teacher.styles.split(",")]
        if not student_styles or not teacher_styles:
            return 0.5
        matches = len(set(student_styles) & set(teacher_styles))
        total = len(set(student_styles))
        return min(1.0, matches / total) if total > 0 else 0.5

    def _calculate_rating_score(self, teacher):
        rating = teacher.rating or 5.0
        return min(1.0, rating / 5.0)

    def _calculate_level_score(self, student, teacher):
        if not student.level or not teacher.level:
            return 0.5
        try:
            student_idx = self.level_order.index(student.level)
            teacher_idx = self.level_order.index(teacher.level)
        except ValueError:
            return 0.5
        if teacher_idx >= student_idx:
            return 1.0
        else:
            diff = student_idx - teacher_idx
            return max(0.0, 1.0 - (diff * 0.25))

    def _calculate_availability_score(self, teacher, schedule_id=None):
        def query(session):
            now = datetime.now()
            two_weeks_later = now + timedelta(weeks=2)
            q = session.query(Schedule).filter(
                and_(Schedule.teacher_id == teacher.id,
                     Schedule.start_time >= now,
                     Schedule.start_time <= two_weeks_later,
                     Schedule.status.in_(["scheduled", "in_progress"]))
            )
            if schedule_id:
                q = q.filter(Schedule.id != schedule_id)
            scheduled_count = q.count()
            max_weekly = 20
            available_slots = max_weekly - scheduled_count
            return max(0.0, min(1.0, available_slots / max_weekly))
        return self.db.execute_query(query)

    def _calculate_experience_score(self, teacher):
        years = teacher.experience_years or 0
        return min(1.0, years / 10.0)

    def calculate_match_score(self, student, teacher, schedule_id=None):
        weights = self.settings.get_all_weights()
        style_score = self._calculate_style_score(student, teacher)
        rating_score = self._calculate_rating_score(teacher)
        level_score = self._calculate_level_score(student, teacher)
        availability_score = self._calculate_availability_score(teacher, schedule_id)
        experience_score = self._calculate_experience_score(teacher)

        total_score = (
            style_score * weights.get("style_match", 0.30) +
            rating_score * weights.get("rating", 0.25) +
            level_score * weights.get("level_match", 0.25) +
            availability_score * weights.get("availability", 0.10) +
            experience_score * weights.get("experience", 0.10)
        )

        return {
            "total_score": round(total_score, 4),
            "style_score": round(style_score, 4),
            "rating_score": round(rating_score, 4),
            "level_score": round(level_score, 4),
            "availability_score": round(availability_score, 4),
            "experience_score": round(experience_score, 4),
            "weights": weights
        }

    def generate_reason_text(self, student, teacher, scores):
        weights = scores.get("weights", {})
        parts = []

        style_w = weights.get("style_match", 0.30)
        style_contrib = scores["style_score"] * style_w
        student_styles = [s.strip() for s in (student.preferred_style or "").split(",") if s.strip()]
        teacher_styles = [s.strip() for s in (teacher.styles or "").split(",") if s.strip()]
        matched = set(student_styles) & set(teacher_styles)
        if matched:
            parts.append(f"曲风匹配({','.join(matched)})贡献{style_contrib:.2f}分(权重{style_w:.0%}x得分{scores['style_score']:.0%})")
        else:
            parts.append(f"曲风无直接匹配,贡献{style_contrib:.2f}分")

        rating_w = weights.get("rating", 0.25)
        rating_contrib = scores["rating_score"] * rating_w
        parts.append(f"评分{teacher.rating:.1f}贡献{rating_contrib:.2f}分(权重{rating_w:.0%}x得分{scores['rating_score']:.0%})")

        level_w = weights.get("level_match", 0.25)
        level_contrib = scores["level_score"] * level_w
        if scores["level_score"] >= 1.0:
            parts.append(f"级别{teacher.level}>=学员{student.level}完全匹配,贡献{level_contrib:.2f}分")
        else:
            parts.append(f"级别匹配度{scores['level_score']:.0%},贡献{level_contrib:.2f}分")

        avail_w = weights.get("availability", 0.10)
        avail_contrib = scores["availability_score"] * avail_w
        parts.append(f"可用度贡献{avail_contrib:.2f}分(权重{avail_w:.0%}x得分{scores['availability_score']:.0%})")

        exp_w = weights.get("experience", 0.10)
        exp_contrib = scores["experience_score"] * exp_w
        parts.append(f"经验{teacher.experience_years}年贡献{exp_contrib:.2f}分(权重{exp_w:.0%}x得分{scores['experience_score']:.0%})")

        return "; ".join(parts)

    def recommend_teachers(self, student_id, schedule_id=None, top_n=5):
        student = self.db.get_by_id(Student, student_id)
        if not student:
            raise ValueError("学员不存在")

        teachers = self.db.query(Teacher, filters={"status": "active"})
        results = []
        for teacher in teachers:
            scores = self.calculate_match_score(student, teacher, schedule_id)
            reason = self.generate_reason_text(student, teacher, scores)
            results.append({
                "teacher": teacher,
                "student": student,
                "reason_text": reason,
                **scores
            })

        results.sort(key=lambda x: x["total_score"], reverse=True)

        for result in results[:top_n]:
            self._log_recommendation(
                student_id=student_id,
                teacher_id=result["teacher"].id,
                schedule_id=schedule_id,
                scores=result,
                reason_text=result["reason_text"]
            )

        return results[:top_n]

    def recommend_teachers_for_schedule(self, student_id, schedule_id=None, top_n=5):
        return self.recommend_teachers(student_id, schedule_id, top_n)

    def recommend_schedules(self, student_id, top_n=5):
        student = self.db.get_by_id(Student, student_id)
        if not student:
            raise ValueError("学员不存在")

        now = datetime.now()

        def query(session):
            return session.query(Schedule).filter(
                and_(Schedule.start_time > now, Schedule.status == "scheduled")
            ).all()
        schedules = self.db.execute_query(query)

        results = []
        for schedule in schedules:
            if schedule.current_students >= schedule.max_students:
                continue
            teacher = self.db.get_by_id(Teacher, schedule.teacher_id)
            if not teacher or teacher.status != "active":
                continue
            scores = self.calculate_match_score(student, teacher, schedule.id)
            reason = self.generate_reason_text(student, teacher, scores)
            results.append({
                "schedule": schedule,
                "teacher": teacher,
                "student": student,
                "reason_text": reason,
                **scores
            })

        results.sort(key=lambda x: x["total_score"], reverse=True)
        return results[:top_n]

    def _log_recommendation(self, student_id, teacher_id, schedule_id, scores, reason_text=""):
        weights = scores.get("weights", {})
        log = RecommendationLog(
            student_id=student_id,
            teacher_id=teacher_id,
            schedule_id=schedule_id,
            style_score=scores["style_score"],
            rating_score=scores["rating_score"],
            level_score=scores["level_score"],
            availability_score=scores["availability_score"],
            experience_score=scores["experience_score"],
            total_score=scores["total_score"],
            style_weight=weights.get("style_match", 0.30),
            rating_weight=weights.get("rating", 0.25),
            level_weight=weights.get("level_match", 0.25),
            availability_weight=weights.get("availability", 0.10),
            experience_weight=weights.get("experience", 0.10),
            reason_text=reason_text
        )
        self.db.add(log)

    def save_as_match(self, log_id):
        def query(session):
            log = session.query(RecommendationLog).filter(RecommendationLog.id == log_id).first()
            if log:
                log.saved_as_match = True
                session.add(log)
                session.commit()
                return True
            return False
        return self.db.execute_query(query)

    def get_match_records(self, student_id=None, teacher_id=None, limit=50):
        def query(session):
            q = session.query(RecommendationLog).filter(RecommendationLog.saved_as_match == True)
            if student_id:
                q = q.filter(RecommendationLog.student_id == student_id)
            if teacher_id:
                q = q.filter(RecommendationLog.teacher_id == teacher_id)
            return q.order_by(RecommendationLog.created_at.desc()).limit(limit).all()
        return self.db.execute_query(query)

    def get_recommendation_history(self, student_id=None, teacher_id=None, limit=20):
        filters = {}
        if student_id:
            filters["student_id"] = student_id
        if teacher_id:
            filters["teacher_id"] = teacher_id
        from app.database.models import RecommendationLog
        return self.db.query(RecommendationLog, filters=filters,
                           order_by=RecommendationLog.created_at.desc(), limit=limit)

    def update_weights(self, new_weights):
        total = sum(new_weights.values())
        if abs(total - 1.0) > 0.01:
            raise ValueError("权重之和必须等于1.0")
        valid_keys = ["style_match", "rating", "level_match", "availability", "experience"]
        for key in new_weights:
            if key not in valid_keys:
                raise ValueError(f"无效的权重键: {key}")
            if new_weights[key] < 0 or new_weights[key] > 1:
                raise ValueError(f"权重值必须在0-1之间: {key}")
        self.settings.set_all_weights(new_weights)
        return True

    def get_current_weights(self):
        return self.settings.get_all_weights()

    def reset_weights(self):
        default_weights = {
            "style_match": 0.30,
            "rating": 0.25,
            "level_match": 0.25,
            "availability": 0.10,
            "experience": 0.10
        }
        self.settings.set_all_weights(default_weights)
        return default_weights
