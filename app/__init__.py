from datetime import timedelta
from pathlib import Path

from flask import Flask
import redis
from flask_mail import Mail
from rq import Queue
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

from app.config import Config


# r = redis.Redis(host='redis', port=6379)  # docker상에서 service명으로 host를 사용
r = redis.Redis.from_url(Config.REDIS_URL)
queue = Queue(connection=r)

app = Flask(__name__)
app.config.from_object(Config)

mail = Mail(app)

# engine = create_engine("sqlite:///db.sqlite", pool_size=1, max_overflow=0) # default 5, 10
engine = create_engine(Config.DATABASE_URL, **Config.SQLALCHEMY_POOL_OPTIONS)

session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base = declarative_base()
Base.query = session.query_property()
# sqlite migrate 오류시 발생할 수 있는 버그 픽스
naming_convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

Base.metadata = MetaData(naming_convention=naming_convention)

from .models import *

Base.metadata.create_all(bind=engine)

from app import views
from app import tasks


@app.shell_context_processor
def make_shell_context():
    from .tasks import send_async_mail
    from .tasks.service import TaskService
    return dict(
        queue=queue,
        session=session,
        Task=Task,
        Message=Message,
        Notification=Notification,
        datetime=datetime,
        timedelta=timedelta
    )


@app.teardown_appcontext
def shutdown_session(exception=None):
    session.remove()
