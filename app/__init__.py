from datetime import timedelta, datetime

import jinja_partials
from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
from flask import Flask, request, Response, stream_with_context

from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

from app.config import Config
from .extentions import docs, sse

from .templates.filters import remain_from_now

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


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    jinja_partials.register_extensions(app)

    from .extentions import mail
    mail.init_app(app)

    from .models import Task, Notification, Message, Source, SourceCategory
    Base.metadata.create_all(bind=engine)

    # from app import views
    from app.views import main_bp, rss_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(rss_bp)

    # dashboard
    import rq_dashboard
    import rq_scheduler_dashboard
    app.register_blueprint(rq_dashboard.blueprint, url_prefix="/rqdashboard")
    app.register_blueprint(rq_scheduler_dashboard.blueprint, url_prefix="/rqschedulerdashboard")

    # sse route
    @app.route('/sse')
    def sse_connect():
        channel = request.args.get('channel')
        # print("channel>>>", channel)

        return Response(
            stream_with_context(sse.stream(channel=channel)),
            mimetype="text/event-stream",
            headers={
                'Cache-Control': 'no-cache',
                'Transfer-Encoding': 'chunked',
            })

    @app.route('/sse_test/<channel>')
    def sse_test(channel):
        sse.publish(f'feed__{channel}Added', channel=channel)
        return 'success'


    # scehduler task
    from app import tasks
    tasks.init_app(app)

    # apispec  초기화
    # - docs객체에 route정보들 다 입력된 상태에서 init
    docs.init_app(app)
    app.config.update({
        'APISPEC_SPEC': APISpec(
            title='chat',  # [swagger-ui] 제목
            version='v1',  # [swagger-ui] 버전
            openapi_version='2.0',  # swagger 자체 버전
            plugins=[MarshmallowPlugin()]
        ),
        'APISPEC_SWAGGER_URL': '/swagger/'  # swagger 자체 정보 url
    })

    # cors.init_app(app)

    @app.shell_context_processor
    def make_shell_context():
        from .tasks import send_async_mail
        from .tasks.service import TaskService, SchedulerService

        return dict(
            # queue=queue,
            session=session,
            Task=Task,
            Message=Message,
            Notification=Notification,
            datetime=datetime,
            timedelta=timedelta,
            TaskService=TaskService,
            SchedulerService=SchedulerService,
        )

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        session.remove()

    app.jinja_env.filters["remain_from_now"] = remain_from_now

    return app
