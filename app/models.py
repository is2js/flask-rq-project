import json
from datetime import datetime
from time import time

import redis.exceptions
import rq
from sqlalchemy import types, desc, asc
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
            return self
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
    status = db.Column(db.Enum(*statuses, name='status'), default='queued', index=True)

    log = db.Column(db.Text)

    result = db.Column(Json, nullable=True)
    # Notification을 위한 추가
    username = db.Column(db.String(6), index=True)

    def __repr__(self):
        return f'<Task {self.id} {self.name}>'
    @classmethod
    def create(cls, _session, name, description):

        task = cls(name=name, description=description, username=_session.get('username'))
        return task.save()

    @classmethod
    def get_list_of(cls, _session):
        return cls.query.filter(
            cls.username == _session.get('username'),
        ).all()

    @classmethod
    def get_finished_list_of(cls, _session, limit=None):
        query = cls.query.filter(
            cls.username == _session.get('username'),
            cls.status == 'finished'
        ).order_by(desc(cls.updated_at))

        if limit:
            query = query.limit(limit)

        return query.all()

    @classmethod
    def get_unfinished_list_of(cls, _session, limit=None):
        query = cls.query.filter(
            cls.username == _session.get('username'),
            cls.status != 'finished'
        ).order_by(asc(cls.created_at))

        if limit:
            query = query.limit(limit)

        return query.all()

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

    def __repr__(self):
        return '<Message {}>'.format(self.body)

    @classmethod
    def new_messages_of(cls, _session):
        recipient = _session.get('username')
        # datetime시 None이면 안되서 기본값도 준다.
        last_message_read_time = _session.get('last_message_read_time') or datetime(1900, 1, 1)

        return cls.query.filter_by(recipient=recipient) \
            .filter(cls.created_at > last_message_read_time) \
            .count()

    @classmethod
    def get_messages_of(cls, _session):
        recipient = _session.get('username')

        return cls.query.filter_by(recipient=recipient) \
            .order_by(desc(cls.created_at)).all()

    @classmethod
    def create(cls, _session, body):
        # 1. 알림처리보다 먼저, 현재 Message를 생성하여, -> 알림의 payload에 반영되게 한다.
        message = cls(recipient=_session.get('username'), body=body)
        message.save()

        # 2. 알림을 현재model에 맞는 name + 맞는 payload로 생성한다.
        n = Notification.create(_session, name='unread_message_count', payload=dict(data=cls.new_messages_of(_session)))

        return message


class Notification(BaseModel):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    username = db.Column(db.String(6), index=True)
    timestamp = db.Column(db.Float, index=True, default=time)
    payload = db.Column(Json)

    @classmethod
    def create(cls, _session, name, payload):
        # 1. 현재사용자(in_session-username)의 알림 중
        #    - name='unread_message_count' 에 해당하는 카테고리의 알림을 삭제하고
        Notification.query.filter_by(name=name, username=_session.get('username')).delete()
        # 2. 알림의 내용인 payload에 현재 새정보를 data key에 담아 저장하여 새 알림으로 대체한다
        notification = Notification(
            name=name,
            username=_session.get('username'),
            payload=payload
        )
        return notification.save()

    @classmethod
    def get_list_of(cls, _session, since=0.0):
        return Notification.query.filter(
            Notification.username == _session.get('username'),
            Notification.timestamp > since
        ).order_by(asc(Notification.timestamp)).all()
