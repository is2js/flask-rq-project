from flask import session
from rq import Retry
from .word_counter import count_words
from .image_uploader import create_image_set
from .mail_sender import send_async_mail

from app import queue
from app.models import Task
from redis.exceptions import RedisError


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
            func=task_func, # task메서드
            args=args, # task메서드 인자1
            kwargs=kwargs, # task메서드 인자2
            job_id=str(task.id),  # enqueue(job)용
            timeout=timeout,
            retry=Retry(max=3, interval=5) # 일시적 네트워크 장애 오류 최대 3번 도전
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




