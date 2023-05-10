import copy
import json
from datetime import datetime, date
from functools import wraps
from time import time

import redis.exceptions
import rq
from rq.command import send_stop_job_command
from sqlalchemy import types, desc, asc
from sqlalchemy.ext import mutable
from . import session, Base
from .extentions import r
import sqlalchemy as db

from .templates.filters import remain_from_now


def transaction(f):
    """ Decorator for database (session) transactions."""

    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            value = f(*args, **kwargs)
            session.commit()
            return value
        except Exception:
            session.rollback()
            raise

    return wrapper


def format_datetime(value, fmt='%Y-%m-%d %H:%M'):
    formatted = value.strftime(fmt.encode('unicode-escape').decode()).encode().decode('unicode-escape')
    return formatted


def format_date(value, fmt='%Y-%m-%d'):
    formatted = value.strftime(fmt.encode('unicode-escape').decode()).encode().decode('unicode-escape')
    return formatted


class BaseModel(Base):
    __abstract__ = True

    created_at = db.Column(db.DateTime, nullable=True, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=True, default=datetime.now, onupdate=datetime.now)

    @classmethod
    @transaction
    def get_list(cls):
        items = cls.query.all()
        # try:
        #     items = cls.query.all()
        #     session.close()
        # except Exception:
        #     session.rollback()
        #     raise
        return items

    @transaction
    def save(self):
        session.add(self)
        return self
        # try:
        #     session.add(self)
        #     session.commit()
        #     return self
        # except Exception:
        #     session.rollback()
        #     raise

    @transaction
    def update(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        return self
        # try:
        #     for key, value in kwargs.items():
        #         setattr(self, key, value)
        #     session.commit()
        #     return self
        # except Exception:
        #     session.rollback()
        #     raise

    @transaction
    def delete(self):
        session.delete(self)
        return self
        # try:
        #     session.delete(self)
        #     session.commit()
        # except Exception:
        #     session.rollback()
        #     raise

    def to_dict(self):
        data = dict()

        for col in self.__table__.columns:
            _key = col.name
            _value = getattr(self, _key)

            # {"data": [{"progress": 100, "task_id": 34}, {"progress": 100, "task_id": 35}, {"progress": 100, "task_id": 36}, {"progress": 100, "task_id": 37}, {"progress": 100, "task_id": 38}, {"progress": 100, "task_id": 39}, {"progress": 100, "task_id": 40}, {"progress": 100, "task_id": 41}, {"progress": 100, "task_id": 43}, {"progress": 100, "task_id": 42}, {"progress": 100, "task_id": 44}, {"progress": 100, "task_id": 45}, {"progress": 100, "task_id": 46}, {"progress": 100, "task_id": 47}, {"progress": 100, "task_id": 48}, {"progress": 100, "task_id": 49}]}
            if _key == 'payload':
                # 내부의 list를 가변변수로 받아 수정한 list를 재할당 예정.
                data_list = _value['data']
                for i, d in enumerate(data_list):
                    # {"progress": 100, "task_id": 34} or {"reserved_at": "2023-05-05T18:52:03", "task_id": 33}
                    task_notification = dict()
                    for k, v in d.items():
                        # reserved_at의 isoformat datetime인 경우, 'xx 남음'으로 변경
                        if k == 'reserved_at':
                            task_notification[k] = remain_from_now(datetime.fromisoformat(v))
                        else:
                            task_notification[k] = v
                    data_list[i] = task_notification
                # 'payload' 대신 'data' key에 넣음
                # _value['data'] = data_list

                # payload['data'] -> data['data']로 변경 for Notification
                data['data'] = data_list
                continue

            # 나머지 들은 그대로 할당
            data[_key] = _value

        return data


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

    statuses = ['queued', 'running', 'canceled', 'finished', 'reserved']

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

    # timer의 수행시간
    reserved_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'<Task {self.id} {self.name}>'

    @classmethod
    def create(cls, _session, name, description,
               status='queued', reserved_at=None):

        task = cls(name=name, description=description, username=_session.get('username'), status=status,
                   reserved_at=reserved_at)
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
            # cls.status != 'finished'
            # cls.status.in_(['queued', 'running'])
            cls.status.notin_(['canceled', 'finished'])
        ).order_by(asc(cls.created_at))

        if limit:
            query = query.limit(limit)

        return query.all()

    @classmethod
    def get_reserved_list_of(cls, _session, limit=None):
        query = cls.query.filter(
            cls.username == _session.get('username'),
            cls.status == 'reserved'
        ).order_by(asc(cls.scheduled_at))

        if limit:
            query = query.limit(limit)

        return query.all()

    def get_rq_job(self):
        try:
            rq_job = rq.job.Job.fetch(str(self.id), connection=r)
        except (redis.exceptions.RedisError, rq.exceptions.NoSuchJobError):
            # except redis.exceptions.RedisError:
            return None
        return rq_job

    def get_progress(self):
        job = self.get_rq_job()
        return job.meta.get('progress', 0) if job is not None \
            else 100

    # session에 객체를 넣어주기 위한 직렬화
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'failed': self.failed,
            'status': self.status,
            'log': self.log,
            'result': self.result,
            'username': self.username,
            'progress': self.get_progress(),
            'reserved_at': self.reserved_at
        }

    def cancel_rq_job(self):
        try:
            rq_job = rq.job.Job.fetch(str(self.id), connection=r)
            # 1) 완료되거나 실패한 job인 경우는 취소 False -> 외부에서 취소할 수 없다고 알려준다. by flash
            if rq_job.is_finished or rq_job.is_failed:
                return False
            # 2) 대기 or 진행중인 task
            # rq_job.cancel()
            send_stop_job_command(self.redis, rq_job.get_id())
            rq_job.delete()

            # Task데이터를 완료되신 canceled로 업뎃하기
            # - @background_task의 try코드에서 수행후 result로 Task 'finished'업뎃하는 코드는 실행 안되고 중단 되고
            # - 바로 finally로 가서 set_task_progress(100)으로 Notification을 완료상태로 만든다.
            # -> 그래서 'finished'처리가 실행안되고, 중단된 대신 'canceled' 처리를 직접해줘야한다
            self.update(
                failed=True,
                status='canceled',  # finished가 아닌 canceled로 저장
            )
            return True
        except (redis.exceptions.RedisError, rq.exceptions.NoSuchJobError):
            return False


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
        n = Notification.create(
            username=_session.get('username'),
            name='unread_message_count',
            # payload=dict(data=cls.new_messages_of(_session)),
            data=cls.new_messages_of(_session)
        )

        return message


class Notification(BaseModel):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    username = db.Column(db.String(6), index=True)
    timestamp = db.Column(db.Float, index=True, default=time)
    payload = db.Column(Json)

    @classmethod
    def create(cls, username, name, data):
        # 1. name별 username별 이미 Notification이 있으면 payload를 수정, 없으면 새로 생성한다.
        notification = Notification.query.filter_by(name=name, username=username).first()
        if notification:
            ## 수정
            # - message는 payload['data']를 덮어쓰기만 하면 되지만
            # - task는  payload['data']는 list이며, list 내부 task_dict들을 순회하면서
            #   1) data={'task_id'}와 같은 task_id를 가진 dict가 있으면 => 해당 dict를 덮어쓴다
            #   2) 같은 task_id를 가진 dict가 없다면 => payload['data']라는 list에 append해서 update한다
            ## 수정시 Json필드의 주의사항
            # - 덮어쓸 index를 찾아서, payload['data'][idx] = data 로 집어넣으면  update or commit()시 반영이 안된다 -> 무슨 수를 써도 안됨.
            # => payload라는 dict(json)전체 업뎃이 아닌  payload['data']의 list르 업뎃하는 상황이라면,
            # => 기존의 dict list인 payload['data']을 임시변수에 받아놓고 -> 업뎃한 뒤 -> payload['data]에 재할당 해주자.
            #    notification.payload['data'].append( data )  OR  notification.payload['data'] [idx] = data 는 업뎃이 안된다.

            # if name == 'task_progress' :
            if name in ['task_progress', 'task_reserve']:
                previous_list = notification.payload['data']
                for idx, task_dict in enumerate(previous_list):
                    if data['task_id'] == task_dict['task_id']:
                        # 반영은 됌.
                        # notification.update(payload=dict(data='new'))

                        # 이것도 반영됌
                        # notification.payload['data'] = 'new'
                        # session.commit()

                        # payload['data']는 달라졌으나, 반영은 안됌
                        # notification.payload['data'][idx] = data
                        # session.commit()
                        previous_list[idx] = data
                        notification.payload['data'] = previous_list
                        break
                else:
                    previous_list.append(data)
                    notification.payload['data'] = previous_list

                session.commit()
                return notification

            # elif name == 'unread_message_count':
            else:
                payload = dict(data=data)
                return notification.update(payload=payload)

        else:
            ## 생성
            # 1) 외부에서 받은 data={}를 내부적으로 payload를 dict(data=)에 넣어서 생성
            # - message -> int로 data가 들어어오면 -> dict(data= int ) 형식으로 집어넣기
            # - task_progress -> dict로 data={'task_id':, 'progress':}가 들어오면 dict(data= [  ])로 list로 감싸서 집어넣기
            # if name == 'task_progress':
            if name in ['task_progress', 'task_reserve']:
                payload = dict(data=[data])
            # elif name == 'unread_message_count':
            else:
                payload = dict(data=data)

            notification = Notification(
                name=name,
                username=username,
                payload=payload
            )
            return notification.save()

    @classmethod
    def get_list_of(cls, _session, since=0.0):
        return Notification.query.filter(
            Notification.username == _session.get('username'),
            Notification.timestamp > since
        ).order_by(asc(Notification.timestamp)).all()
