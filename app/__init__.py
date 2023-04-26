from pathlib import Path

from flask import Flask
import redis
from flask_mail import Mail
from rq import Queue
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

from app.config import Config

# r = redis.Redis(host='redis', port=6379)  # docker상에서 service명으로 host를 사용
r = redis.Redis.from_url(Config.REDIS_URL)
queue = Queue(connection=r)

app = Flask(__name__)
app.config.from_object(Config)

mail = Mail(app)

engine = create_engine("sqlite:///db.sqlite", pool_size=1, max_overflow=0) # default 5, 10
session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base = declarative_base()
Base.query = session.query_property()


from .models import *
Base.metadata.create_all(bind=engine)


from app import views
from app import tasks


@app.shell_context_processor
def make_shell_context():
    return dict(
        queue=queue,
        session=session,
        Task=Task,
        Message=Message,
        Notification=Notification,
    )


@app.teardown_appcontext
def shutdown_session(exception=None):
    session.remove()