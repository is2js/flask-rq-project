import redis
import rq
from flask import session
from redis.exceptions import RedisError
from rq import Queue, Retry
from rq.command import send_stop_job_command
from rq.exceptions import NoSuchJobError
from rq_scheduler import Scheduler

from app.models import Task
from app.config import Config
from app.utils import task_logger


class TaskBase(object):
    def __init__(self, queue_name):
        self.timeout = 2
        self.redis = redis.from_url(Config.REDIS_URL)
        self.asyncQueue = Queue(name=queue_name, connection=self.redis)
        self.asyncScheduler = Scheduler(queue=self.asyncQueue, connection=self.redis, interval=1)
        self.logger = task_logger


# Task의 종류: Task, TimerTask, ScheduledTask마다
# service를 만들어, 전용 enqueue, 전용 model list 등을 처리한다?
class TaskService(TaskBase):
    """
    enqueue_task시 Task모델에 의존해서 사용된다.
    """

    def __init__(self, queue_name='default'):
        super().__init__(queue_name=queue_name)
        self.model = Task

    def enqueue_task(self,
                     task_func,  # Task메서드용 1
                     *args,  # Task메서드용 2
                     description=None,  # DB + task용
                     timeout=300,  # enqueue용 (수행기다려주는 최대 시간(초))-> 5분지나면, TimeoutException  예외발생 후, 다른 task하러 간다
                     **kwargs,  # Task메서드용 3
                     ):
        """
        s = TaskService()
        s.enqueue_task(send_async_mail, email_data, description=f'{template_name}을 이용하여 메일 전송')
        """
        if not description:
            raise ValueError('Description required to start background job')

        # 1) Task부터 생성하고, queue의 job_id를 Task.id로 배정하여, enqueue실패시도 반영되게 한다
        # -> 들어온 task_func의 .__name__을 name으로 저장한다
        # task = Task(name=task_func.__name__, description=description)
        # task.save()  # save후에는 자동으로  id가 배정되어있다.
        task = self.model.create(session, name=task_func.__name__, description=description)
        self.logger.info(f'start task...{task.name}')

        # 2) enqueue대신 enqueue_call()을 사용하여 예약을 더 부드럽게 한다.
        # -> time_out 도 제공함
        try:
            self.asyncQueue.enqueue_call(
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
            self.logger.error(str(e), exc_info=True)
            task.update(
                failed=True,
                status='finished',
                log=f'Could not connect to Redis: ' + str(e)
            )
        except Exception as e:
            self.logger.error(str(e), exc_info=True)
            # 4) enqueue가 Retry실패 등으로 Redis외 에러가 발생해도 DB에 기록
            task.update(
                failed=True,
                status='finished',
                log=f'Error: ' + str(e)
            )

        # 5) 현재 task 데이터를 반환해준다.
        self.logger.info(f'complete task...{task.name}')
        return task

    def cancel_task(self, task_id):
        try:
            rq_job = rq.job.Job.fetch(str(task_id), connection=self.redis)
            # 1) 완료되거나 실패한 job인 경우는 취소 False -> 외부에서 취소할 수 없다고 알려준다. by flash
            if rq_job.is_finished or rq_job.is_failed:
                self.logger.info(f'cancel task fail because already done')
                return False
            # 2) 대기 or 진행중인 task
            # rq_job.cancel()
            send_stop_job_command(self.redis, rq_job.get_id())
            rq_job.delete()

            task = self.model.query.get(int(task_id))
            task.update(
                failed=True,
                status='canceled',  # finished가 아닌 canceled로 저장
            )
            return task
        except (RedisError, NoSuchJobError):
            return False
