import json
from datetime import datetime
from functools import wraps
import sqlalchemy as db
from sqlalchemy.ext import mutable
from sqlalchemy.orm import declared_attr

from app import session, Base
from app.templates.filters import remain_from_now
from app.utils.loggers import db_logger


def transaction(f):
    """ Decorator for database (session) transactions."""

    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            value = f(*args, **kwargs)
            session.commit()
            return value
        except Exception as e:
            db_logger.error(f'{str(e)}', exc_info=True)
            session.rollback()
            raise

    return wrapper


class BaseModel(Base):
    __abstract__ = True
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()

    created_at = db.Column(db.DateTime(timezone=True), nullable=True, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=True, default=datetime.utcnow, onupdate=datetime.utcnow)


    @classmethod
    def get_or_create(cls, get_key=None, **kwargs):
        if not get_key:
            instance = cls.query.filter_by(**kwargs).first()
        else:
            instance = cls.query.filter(getattr(cls, get_key) == kwargs.get(get_key)).first()
        if instance is None:
            instance = cls(**kwargs)
            instance.save()

        return instance

    @classmethod
    @transaction
    def get_list(cls):
        items = cls.query.all()
        return items

    @transaction
    def save(self):
        session.add(self)
        return self

    @transaction
    def update(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        return self

    @transaction
    def delete(self):
        session.delete(self)
        return self

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


class Json(db.types.TypeDecorator):
    """Enables JSON storage by encoding and decoding on the fly."""
    impl = db.types.Text

    def process_bind_param(self, value, dialect):
        # Python -> SQL

        return json.dumps(value, sort_keys=True).encode('utf-8')

    def process_result_value(self, value, dialect):
        # SQL -> Python
        return json.loads(value.decode('utf-8'))


mutable.MutableDict.associate_with(Json)
