from datetime import timedelta, datetime

from flask import Flask


from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

from app.config import Config

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

    from .extentions import mail
    mail.init_app(app)

    from .models import Task, Notification, Message, Source, SourceCategory
    Base.metadata.create_all(bind=engine)

    # from app import views
    from app.views import main_bp
    app.register_blueprint(main_bp)

    # dashboard
    import rq_dashboard
    import rq_scheduler_dashboard
    app.register_blueprint(rq_dashboard.blueprint, url_prefix="/rqdashboard")
    app.register_blueprint(rq_scheduler_dashboard.blueprint, url_prefix="/rqschedulerdashboard")

    # scehduler task
    from app import tasks
    tasks.init_app(app)

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