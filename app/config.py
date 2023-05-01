import os
from pathlib import Path


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY') or 'secret_key'

    BASE_FOLDER = Path(__file__).resolve().parent  # BASE_FOLDER:  /rq/app
    UPLOAD_FOLDER = BASE_FOLDER.joinpath('static/image/upload')  # UPLOAD_FOLDER:  /rq/app + /static/image/upload
    LOG_FOLDER = BASE_FOLDER.parent.joinpath('logs')  # LOG_FOLDER:  /rq + logs

    DATABASE_URL = os.getenv('DATABASE_URL') or 'sqlite:///db.sqlite'
    SQLALCHEMY_POOL_OPTIONS = {
        'pool_size': 3,
        'pool_recycle': 55,  # # ClearDB's idle limit is 90 seconds, so set the recycle to be under 90
        'pool_timeout': 5,
        'max_overflow': 10
    } if os.getenv('DATABASE_URL') else {
        'pool_size': 1,
        'max_overflow': 0
    }

    REDIS_URL = f"redis://{os.getenv('REDIS_HOST')}:{os.getenv('REDIS_PORT')}"  # redis://redis:6379

    MAIL_SERVER = os.getenv('MAIL_SERVER')
    MAIL_PORT = os.getenv('MAIL_PORT')
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS')
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    # CUSTOM
    MAIL_SUBJECT_PREFIX = '[RQ프로젝트] '
    MAIL_SENDER = 'RQ프로젝트 <tingstyle11@gmail.com>'

    SERVER_NAME = os.getenv('SERVER_NAME')
