from datetime import datetime, timedelta

import redis
import rq
from flask import session
from redis.exceptions import RedisError
from rq import Queue, Retry
from rq.command import send_stop_job_command
from rq.exceptions import NoSuchJobError
from rq.registry import ScheduledJobRegistry
from rq_scheduler import Scheduler

from app.models import Task, Notification
from app.config import Config
from app.utils import task_logger, schedule_logger, datetime_to_utc


class TaskBase(object):
    def __init__(self, queue_name):
        self.timeout = 60
        self.redis = redis.from_url(Config.REDIS_URL)
        self.asyncQueue = Queue(name=queue_name, connection=self.redis)
        # self.asyncScheduler = Scheduler(queue=self.asyncQueue, connection=self.redis)


# Task의 종류: Task, TimerTask, ScheduledTask마다
# service를 만들어, 전용 enqueue, 전용 model list 등을 처리한다?
class TaskService(TaskBase):
    """
    enqueue_task시 Task모델에 의존해서 사용된다.
    """

    def __init__(self, queue_name='default'):
        super().__init__(queue_name=queue_name)
        self.model = Task
        self.RESERVATION_LIMIT_SECONDS = 30
        self.logger = task_logger

    def enqueue_task(self,
                     task_func,  # Task메서드용 1
                     *args,  # Task메서드용 2
                     description=None,  # DB + task용
                     timeout=None,  # enqueue용 (수행기다려주는 최대 시간(초))-> 5분지나면, TimeoutException  예외발생 후, 다른 task하러 간다
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
        try:

            # 2) enqueue대신 enqueue_call()을 사용하여 예약을 더 부드럽게 한다.
            # -> time_out 도 제공함
            self.asyncQueue.enqueue_call(
                func=task_func,  # task메서드
                args=args,  # task메서드 인자1
                kwargs=kwargs,  # task메서드 인자2
                timeout=timeout if timeout else self.timeout,
                retry=Retry(max=3, interval=5),  # 일시적 네트워크 장애 오류시 5분간격으로 최대 3번 도전
                job_id=str(task.id),  # DB연동
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

    def cancel_reserve(self, task_id):
        rq_job = rq.job.Job.fetch(str(task_id), connection=self.redis)

        # self.logger.debug(f"취소 전 예약작업 여부: {rq_job in registry}")
        # 취소 전 예약작업 여부: True

        # 예약된 작업인지 확인 -> 예약작업 속에 없으면 return False
        registry = ScheduledJobRegistry(queue=self.asyncQueue)
        if rq_job not in registry:
            return False

        rq_job.cancel()
        rq_job.delete()

        # self.logger.debug(f"취소 후 예약작업 여부: {rq_job in registry}")
        # 취소 후 예약작업 여부: False

        task = self.model.query.get(int(task_id))
        task.update(
            failed=True,
            status='canceled',  # finished가 아닌 canceled로 저장
        )
        return task

    def reserve_task(
            self,
            scheduled_time: datetime, task_func, *args,
            description=None,  # timeout=None,
            **kwargs
    ):
        if scheduled_time - datetime.now() < timedelta(seconds=self.RESERVATION_LIMIT_SECONDS):
            raise ValueError(f'현재보다 {self.RESERVATION_LIMIT_SECONDS}초 이내의 예약은 불가능합니다.')

        if not description:
            raise ValueError('Description required to start background job')

        # DB 연동
        task = self.model.create(session, name=task_func.__name__, description=description,
                                 status='reserved', reserved_at=scheduled_time)
        self.logger.info(f'schedule task start...')
        try:
            # job = s.asyncQueue.enqueue_in(
            #     timedelta(seconds=1),  # timedelta
            job = self.asyncQueue.enqueue_at(
                scheduled_time,  # datetime
                task_func,  # func
                *args,  # func - args ( not tuple )
                **kwargs,  # func - kwargs (not dict)
                # timeout=timeout if timeout else self.timeout, # enquque_call에만 사용됨. 여기서 사용하면 task_func의 키워드인자로 인식되어버린다.
                retry=Retry(max=3, interval=5),  # 일시적 네트워크 장애 오류시 5분간격으로 최대 3번 도전
                job_id=str(task.id),  # DB 연동
            )
            self.logger.debug(f"job.to_dict(): {job.to_dict()}")
            self.logger.debug(
                f"job in s.asyncQueue.scheduled_job_registry : {job in self.asyncQueue.scheduled_job_registry}")

            #### 예약 전송 Notification 생성
            # - @background_task에서의 생성은 running부터 시작되는 것
            Notification.create(
                username=session.get('username'),
                name='task_reserve',
                data={
                    'task_id': task.id,
                    'reserved_at': scheduled_time.isoformat()
                }
            )

            # registry = ScheduledJobRegistry(queue=s.asyncQueue)
            # s.logger.info(f"job in ScheduledJobRegistry(queue=queue): {job in registry}")

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

        self.logger.info(f'reserve task complete...')
        return task


class SchedulerService(TaskBase):
    def __init__(self, queue_name='low'):
        super().__init__(queue_name=queue_name)
        self.asyncScheduler = Scheduler(queue=self.asyncQueue, connection=self.redis)
        self.logger = schedule_logger

        # self.model = Task
        # self.RESERVATION_LIMIT_SECONDS = 30

    def schedule(
            self,
            scheduled_time: datetime,
            task_func,
            # *args,
            args=None,
            description=None,  # timeout=None,
            interval=None,
            repeat=None,
            timeout=None,
            # **kwargs,
            kwargs=None,
    ):

        if not interval:
            raise ValueError('interval(반복주기)가 없을 수 없습니다.')

        # timedelta -> seconds로 변환 interval -> *2로 result ttl 보관
        if isinstance(interval, timedelta):
            interval = int(interval.total_seconds())
        result_ttl = interval * 2

        # timeout 변환
        if isinstance(timeout, timedelta):
            timeout = int(timeout.total_seconds())

        if not description:
            raise ValueError('Description required to schedule job')

        # DB 연동
        # task = self.model.create(session, name=task_func.__name__, description=description,
        #                          status='reserved', reserved_at=scheduled_time)
        # try:

        # job = self.asyncScheduler.schedule(
        job = self.asyncScheduler.schedule(
            datetime_to_utc(scheduled_time),  # scheduled_time=datetime.now().astimezone(utc),
            task_func,
            # args=args,
            args=args,
            # kwargs=kwargs,
            kwargs=kwargs,
            interval=interval,
            result_ttl=result_ttl,
            repeat=repeat,
            timeout=timeout,
            # id=
        )

        # self.logger.debug(f"job.to_dict(): {job.to_dict()}")
        # self.logger.debug(
        #     f"list(self.asyncScheduler.get_jobs(with_times=True)) : {list(self.asyncScheduler.get_jobs(with_times=True))}")

        #### 예약 전송 Notification 생성
        # - @background_task에서의 생성은 running부터 시작되는 것
        # Notification.create(
        #     username=session.get('username'),
        #     name='task_reserve',
        #     data={
        #         'task_id': task.id,
        #         'reserved_at': scheduled_time.isoformat()
        #     }
        # )

        # except RedisError as e:
        #     # 3) enqueue가 실패하면 Task의 failed 칼럼을 True / status를 finished로 채워준다
        #     self.logger.error(str(e), exc_info=True)
        #     task.update(
        #         failed=True,
        #         status='finished',
        #         log=f'Could not connect to Redis: ' + str(e)
        #     )
        # except Exception as e:
        #     self.logger.error(str(e), exc_info=True)
        #     # 4) enqueue가 Retry실패 등으로 Redis외 에러가 발생해도 DB에 기록
        #     task.update(
        #         failed=True,
        #         status='finished',
        #         log=f'Error: ' + str(e)
        #     )

        self.logger.info(f'Scheduled {task_func.__name__}({args}, {kwargs}) to run every {interval} seconds')
        # return task

    def cron(
            self,
            cron_string,
            task_func,
            # *args,
            args=None,
            description=None,
            timeout=None,
            result_ttl=3600,
            # **kwargs
            kwargs=None
    ):
        """
        FutureWarning: Version 0.22.0+ of crontab will use datetime.utcnow() and
        datetime.utcfromtimestamp() instead of datetime.now() and
        datetime.fromtimestamp() as was previous. This had been a bug, which will be
        remedied.
        """
        # # for test
        # scheduled_jobs = self.asyncScheduler.get_jobs()
        # for job in scheduled_jobs:
        #     self.asyncScheduler.cancel(job)

        if not description:
            raise ValueError('Description required to start cron job')

        # timeout 변환
        if isinstance(timeout, timedelta):
            timeout = int(timeout.total_seconds())

        # DB 연동
        # task = self.model.create(session, name=task_func.__name__, description=description,
        #                          status='reserved', reserved_at=scheduled_time)
        # self.logger.info(f'schedule task start...')
        # try:

        job = self.asyncScheduler.cron(
            cron_string,  # 나중에는 utc버전으로 바뀌는 듯?
            func=task_func,
            args=args,
            kwargs=kwargs,
            result_ttl=result_ttl,
            timeout=timeout,
            # id=,
            use_local_timezone=True
        )
        # self.logger.debug(f"job.to_dict(): {job.to_dict()}")
        # self.logger.debug(
        #     f"list(self.asyncScheduler.get_jobs(with_times=True)) : {list(self.asyncScheduler.get_jobs(with_times=True))}")

        #### 예약 전송 Notification 생성
        # - @background_task에서의 생성은 running부터 시작되는 것
        # Notification.create(
        #     username=session.get('username'),
        #     name='task_reserve',
        #     data={
        #         'task_id': task.id,
        #         'reserved_at': scheduled_time.isoformat()
        #     }
        # )

        # except RedisError as e:
        #     # 3) enqueue가 실패하면 Task의 failed 칼럼을 True / status를 finished로 채워준다
        #     self.logger.error(str(e), exc_info=True)
        #     task.update(
        #         failed=True,
        #         status='finished',
        #         log=f'Could not connect to Redis: ' + str(e)
        #     )
        # except Exception as e:
        #     self.logger.error(str(e), exc_info=True)
        #     # 4) enqueue가 Retry실패 등으로 Redis외 에러가 발생해도 DB에 기록
        #     task.update(
        #         failed=True,
        #         status='finished',
        #         log=f'Error: ' + str(e)
        #     )

        self.logger.info(f'Cron {task_func.__name__}({args}, {kwargs}) to run every {cron_string}')
        # return task

    def exists(self, job_dict):
        scheduled_jobs = self.asyncScheduler.get_jobs()  # generator -> 순회하기 전에 쓰면 안됌.

        for scheduled_job in scheduled_jobs:
            scheduled_func_name = scheduled_job.description
            scheduled_args = scheduled_job.args
            scheduled_kwargs = scheduled_job.kwargs
            if job_dict['task_func'].__name__ in scheduled_func_name and \
                    job_dict['args'] == scheduled_args and \
                    job_dict['kwargs'] == scheduled_kwargs:

                self.logger.info(
                    f"{scheduled_func_name} with {scheduled_args} {scheduled_kwargs} is already scheduled.")

                return scheduled_job

        return False

    def cancel_schedule(self, existed_schedule):
        self.logger.info(f"cancel schedule {existed_schedule.description}")
        existed_schedule.cancel()
        existed_schedule.delete()
