from datetime import datetime, timedelta

from flask import session
from rq import Retry

from .rss_fetcher import fetch_rss
from .service import SchedulerService
from .word_counter import count_words
from .image_uploader import create_image_set
from .mail_sender import send_async_mail

from app.extentions import queue
from app.models import Task
from redis.exceptions import RedisError

from ..utils import logger


def enqueue_task(
        task_func,  # Task메서드용 1
        *args,  # Task메서드용 2
        description=None,  # DB + task용
        timeout=300,  # enqueue용 (수행기다려주는 최대 시간(초))-> 5분지나면, TimeoutException  예외발생 후, 다른 task하러 간다
        **kwargs,  # Task메서드용 3
):
    if not description:
        raise ValueError('Description required to start background job')

    # 1) Task부터 생성하고, queue의 job_id를 Task.id로 배정하여, enqueue실패시도 반영되게 한다
    # -> 들어온 task_func의 .__name__을 name으로 저장한다
    # task = Task(name=task_func.__name__, description=description)
    # task.save()  # save후에는 자동으로  id가 배정되어있다.
    task = Task.create(session, name=task_func.__name__, description=description)

    # 2) enqueue대신 enqueue_call()을 사용하여 예약을 더 부드럽게 한다.
    # -> time_out 도 제공함
    try:
        queue.enqueue_call(
            func=task_func,  # task메서드
            args=args,  # task메서드 인자1
            kwargs=kwargs,  # task메서드 인자2
            job_id=str(task.id),  # enqueue(job)용
            timeout=timeout,
            retry=Retry(max=3, interval=5)  # 일시적 네트워크 장애 오류 최대 3번 도전
        )
    #### enqueue시 try/except는 (Redis에러, 최대시도에러) 만 잡고, task메서드 내부에러는 못잡는다.
    except RedisError as e:
        # 3) enqueue가 실패하면 Task의 failed 칼럼을 True / status를 finished로 채워준다
        task.update(
            failed=True,
            status='finished',
            log=f'Could not connect to Redis: ' + str(e)
        )
    except Exception as e:
        # 4) enqueue가 Retry실패 등으로 Redis외 에러가 발생해도 DB에 기록
        task.update(
            failed=True,
            status='finished',
            log=f'Error: ' + str(e)
        )

    # 5) 현재 task 데이터를 반환해준다.
    return task


def init_app(app):
    # 지금부터, 몇분 간격으로 (+ 몇번을) 반복해서 실행
    schedule_jobs = [
        dict(
            scheduled_time=datetime.now(),
            task_func=print, args=['scheduler work...1'], kwargs={},
            description='test',
            interval=timedelta(seconds=30), #repeat=4,
            timeout=timedelta(minutes=10),
        ),
        dict(
            scheduled_time=datetime.now(),
            task_func=print, args=['scheduler work...2'], kwargs={},
            description='test',
            interval=timedelta(seconds=30),
            # repeat=5, 횟수
            timeout=timedelta(minutes=10),
        ),
        # rss_fetch -> cron으로 이동

        dict(
            scheduled_time=datetime.now(),
            task_func=fetch_rss, args=[], kwargs={},
            description='fetch_rss',
            interval=timedelta(minutes=60),
            # repeat=5, # 횟수
            timeout=timedelta(minutes=10),
        ),
    ]

    # FutureWarning: Version 0.22.0+ of crontab will use datetime.utcnow() and
    # datetime.utcfromtimestamp() instead of datetime.now() and datetime.fromtimestamp() as was previous.
    cron_jobs = [
        # dict(
        #     cron_string="33 23 * * *",
        #     task_func=print, args=['cron job 1'], kwargs={},
        #     description='test',
        #     timeout=timedelta(minutes=10),
        # ),
        # 3시간마다 rss 패치
    #     dict(
    #         cron_string="0 */3 * * *",  # 분|시|(매달)일|월|(매주)요일(1=월요일)
    #         task_func=fetch_rss, args=[], kwargs={},
    #         description='fetch_rss',
    #         timeout=timedelta(minutes=5),
    #     ),
    ]

    scheduler_service = SchedulerService()

    # for job in schedule_jobs:
    for job in schedule_jobs + cron_jobs:
        try:
            # 이미 존재하는 작업인지 확인하고, 존재하는 job이면 cancel+delete까지 해주기
            existed_schedule = scheduler_service.exists(job)
            if existed_schedule:
                scheduler_service.cancel_schedule(existed_schedule)

            if 'scheduled_time' in job:
                scheduler_service.schedule(
                    **job
                )
            elif 'cron_string' in job:
                scheduler_service.cron(
                    **job
                )
            else:
                ...

        except Exception as e:
            logger.error(f'Schedule register Error: {str(e)}', exc_info=True)