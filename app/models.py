import json
from datetime import datetime

import redis.exceptions
import rq
from sqlalchemy import types, ColumnElement, desc
from sqlalchemy.ext import mutable
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.sqltypes import Text
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

    # id = db.Column(db.String(36), primary_key=True)
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(128), index=True)
    description = db.Column(db.String(128))

    # complete = db.Column(db.Boolean, default=False)
    failed = db.Column(db.Boolean, default=False)
    status = db.Column(db.Enum(*statuses, name='status'), default='queued')

    log = db.Column(db.Text)

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


class Message(BaseModel):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    # sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    recipient = db.Column(db.String(6), index=True)
    body = db.Column(db.String(140))

    # timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    def __repr__(self):
        return '<Message {}>'.format(self.body)

    @classmethod
    def new_messages_of(cls, _session):
        recipient = _session.get('username')
        # datetime시 None이면 안되서 기본값도 준다.
        last_message_read_time = _session.get('last_message_read_time') \
                                 or datetime(1900, 1, 1)

        return cls.query.filter_by(recipient=recipient)\
            .filter(cls.created_at > last_message_read_time)\
            .count()

    @classmethod
    def get_messages(cls, _session):
        recipient = _session.get('username')

        return cls.query.filter_by(recipient=recipient)\
            .order_by(desc(cls.created_at)).all()

