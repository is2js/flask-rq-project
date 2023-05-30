import jinja_partials
from flask_apispec import FlaskApiSpec
from flask_mail import Mail
import redis
from rq import Queue
from .config import Config

mail = Mail()

# r = redis.Redis(host='redis', port=6379)  # docker상에서 service명으로 host를 사용
r = redis.Redis.from_url(Config.REDIS_URL)
queue = Queue(connection=r)

docs = FlaskApiSpec()

from app.sse import ServerSentEventService

sse = ServerSentEventService(r)
