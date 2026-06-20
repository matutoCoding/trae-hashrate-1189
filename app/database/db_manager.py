from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, joinedload, selectinload
from pathlib import Path
from .models import Base


class DatabaseManager:
    def __init__(self, db_path=None):
        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = Path(__file__).parent.parent.parent / "data" / "data.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(f"sqlite:///{self.db_path}", echo=False)
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
            expire_on_commit=False
        )

    def init_db(self):
        Base.metadata.create_all(bind=self.engine)

    def get_session(self):
        return self.SessionLocal()

    def _eager_load(self, query, model_class):
        from .models import Schedule, Enrollment, Waitlist, Student, Teacher, Room

        if model_class == Schedule:
            query = query.options(
                joinedload(Schedule.room),
                joinedload(Schedule.teacher),
                selectinload(Schedule.enrollments),
                selectinload(Schedule.waitlist_entries)
            )
        elif model_class == Enrollment:
            query = query.options(
                joinedload(Enrollment.student),
                joinedload(Enrollment.schedule)
            )
        elif model_class == Waitlist:
            query = query.options(
                joinedload(Waitlist.student),
                joinedload(Waitlist.schedule)
            )
        return query

    def add(self, obj):
        session = self.get_session()
        try:
            session.add(obj)
            session.commit()
            session.refresh(obj)
            return obj
        finally:
            session.close()

    def update(self, obj):
        session = self.get_session()
        try:
            session.merge(obj)
            session.commit()
            return obj
        finally:
            session.close()

    def delete(self, obj):
        session = self.get_session()
        try:
            session.delete(obj)
            session.commit()
        finally:
            session.close()

    def query(self, model_class, filters=None, order_by=None, limit=None):
        session = self.get_session()
        try:
            query = session.query(model_class)
            query = self._eager_load(query, model_class)
            if filters:
                for key, value in filters.items():
                    if isinstance(value, list):
                        query = query.filter(getattr(model_class, key).in_(value))
                    else:
                        query = query.filter(getattr(model_class, key) == value)
            if order_by:
                query = query.order_by(order_by)
            if limit:
                query = query.limit(limit)
            return query.all()
        finally:
            session.close()

    def get_by_id(self, model_class, obj_id):
        session = self.get_session()
        try:
            query = session.query(model_class).filter(model_class.id == obj_id)
            query = self._eager_load(query, model_class)
            return query.first()
        finally:
            session.close()

    def execute_query(self, query_func):
        session = self.get_session()
        try:
            result = query_func(session)
            session.commit()
            return result
        finally:
            session.close()
