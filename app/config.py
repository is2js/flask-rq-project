import os
from pathlib import Path

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY') or 'secret_key'

    BASE_FOLDER = Path(__file__).resolve().parent # BASE_FOLDER:  /app/app
    UPLOAD_FOLDER = BASE_FOLDER.joinpath('static/image/upload') # UPLOAD_FOLDER:  /static/image/upload

    REDIS_URL = f"redis://{os.getenv('REDIS_HOST')}:{os.getenv('REDIS_PORT')}" # redis://redis:6379

    MAIL_SERVER = os.getenv('MAIL_SERVER')
    MAIL_PORT = os.getenv('MAIL_PORT')
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS')
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')

    SERVER_NAME = os.getenv('SERVER_NAME')