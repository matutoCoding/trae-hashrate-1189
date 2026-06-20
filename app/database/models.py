from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    location = Column(String(200))
    capacity = Column(Integer, default=1)
    equipment = Column(Text)
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.now)

    schedules = relationship("Schedule", back_populates="room")


class Teacher(Base):
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20))
    gender = Column(String(10))
    age = Column(Integer)
    level = Column(String(50))
    styles = Column(String(200))
    rating = Column(Float, default=5.0)
    experience_years = Column(Integer, default=0)
    certificate = Column(String(200))
    bio = Column(Text)
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.now)

    schedules = relationship("Schedule", back_populates="teacher")


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20))
    gender = Column(String(10))
    age = Column(Integer)
    level = Column(String(50))
    preferred_style = Column(String(100))
    learning_goal = Column(String(200))
    exam_level = Column(String(50))
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.now)

    enrollments = relationship("Enrollment", back_populates="student")
    waitlist_entries = relationship("Waitlist", back_populates="student")


class MusicPiece(Base):
    __tablename__ = "music_pieces"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    composer = Column(String(100))
    style = Column(String(50))
    difficulty_level = Column(String(50))
    exam_category = Column(String(50))
    exam_level = Column(String(50))
    duration_minutes = Column(Integer)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.now)


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    course_name = Column(String(200), nullable=False)
    course_type = Column(String(50))
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    max_students = Column(Integer, default=1)
    current_students = Column(Integer, default=0)
    status = Column(String(20), default="scheduled")
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

    room = relationship("Room", back_populates="schedules")
    teacher = relationship("Teacher", back_populates="schedules")
    enrollments = relationship("Enrollment", back_populates="schedule")
    waitlist_entries = relationship("Waitlist", back_populates="schedule")


class Enrollment(Base):
    __tablename__ = "enrollments"

    id = Column(Integer, primary_key=True)
    schedule_id = Column(Integer, ForeignKey("schedules.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    enroll_time = Column(DateTime, default=datetime.now)
    confirm_time = Column(DateTime)
    checkin_time = Column(DateTime)
    status = Column(String(20), default="pending")
    notes = Column(Text)

    schedule = relationship("Schedule", back_populates="enrollments")
    student = relationship("Student", back_populates="enrollments")


class Waitlist(Base):
    __tablename__ = "waitlist"

    id = Column(Integer, primary_key=True)
    schedule_id = Column(Integer, ForeignKey("schedules.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    priority_score = Column(Float, default=0.0)
    queue_position = Column(Integer)
    status = Column(String(20), default="waiting")
    notified_time = Column(DateTime)
    enrolled_time = Column(DateTime)
    expired_time = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)

    schedule = relationship("Schedule", back_populates="waitlist_entries")
    student = relationship("Student", back_populates="waitlist_entries")


class Archive(Base):
    __tablename__ = "archives"

    id = Column(Integer, primary_key=True)
    schedule_id = Column(Integer)
    student_id = Column(Integer)
    teacher_id = Column(Integer)
    room_id = Column(Integer)
    course_name = Column(String(200))
    course_date = Column(DateTime)
    actual_start = Column(DateTime)
    actual_end = Column(DateTime)
    student_name = Column(String(100))
    teacher_name = Column(String(100))
    room_name = Column(String(100))
    status = Column(String(20))
    match_score = Column(Float)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.now)


class RecommendationLog(Base):
    __tablename__ = "recommendation_logs"

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    teacher_id = Column(Integer, ForeignKey("teachers.id"))
    schedule_id = Column(Integer, ForeignKey("schedules.id"))
    style_score = Column(Float)
    rating_score = Column(Float)
    level_score = Column(Float)
    availability_score = Column(Float)
    experience_score = Column(Float)
    total_score = Column(Float)
    created_at = Column(DateTime, default=datetime.now)
