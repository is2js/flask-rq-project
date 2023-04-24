import json
from datetime import datetime

import redis.exceptions
import rq
from sqlalchemy import types
from sqlalchemy.ext import mutable

from . import session, Base, r
import sqlalchemy as db


class BaseModel(Base):
    __abstract__ = True

    created_at = db.Column(db.DateTime, nullable=True, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=True, default=datetime.now, onupdate=datetime.now)

    @classmethod
    def get_list(cls):
        try:
            items = cls.query.all()
            session.close()
        except Exception:
            session.rollback()
            raise
        return items

    def save(self):
        try:
            session.add(self)
            session.commit()
        except Exception:
            session.rollback()
            raise

    def update(self, **kwargs):
        try:
            for key, value in kwargs.items():
                setattr(self, key, value)
            session.commit()
        except Exception:
            session.rollback()
            raise

    def delete(self):
        try:
            session.delete(self)
            session.commit()
        except Exception:
            session.rollback()
            raise


class Json(types.TypeDecorator):
    """Enables JSON storage by encoding and decoding on the fly."""
    impl = types.Text

    def process_bind_param(self, value, dialect):
        # Python -> SQL
        return json.dumps(value, sort_keys=True).encode('utf-8')

    def process_result_value(self, value, dialect):
        # SQL -> Python
        return json.loads(value.decode('utf-8'))


mutable.MutableDict.associate_with(Json)


class Task(BaseModel):
    __tablename__ = 'tasks'

    statuses = ['queued', 'running', 'finished']

    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128), index=True)
    description = db.Column(db.String(128))

    # complete = db.Column(db.Boolean, default=False)
    failed = db.Column(db.Boolean, default=False)
    status = db.Column(db.Enum(*statuses, name='status'), default='queued')

    result = db.Column(Json, nullable=True)

    def get_rq_job(self):
        try:
            rq_job = rq.job.Job.fetch(self.id, connection=r)
        # except (redis.exceptions.RedisError, rq.exceptions.NoSuchJobError):
        except redis.exceptions.RedisError:
            return None
        return rq_job

    def get_progress(self):
        job = self.get_rq_job()
        return job.meta.get('progress', 0) if job is not None \
            else 100
