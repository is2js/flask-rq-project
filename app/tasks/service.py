import random
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
from app.models.tasks import ScheduledTask, ScheduledTaskInstance
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

        self.model = ScheduledTask
        self.instance_model = ScheduledTaskInstance

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
            # id=str(random.randint(1, 10)) #
        )

        # 작업 상태 확인
        # print(job.id)
        # print(job.to_dict())
        # d5f50af6-9a69-4c59-b55d-525e970966ca
        # {'created_at': '2023-06-01T14:34:35.279039Z', '
        # 'data': b'x\x9ck`\x9d\xaa\xcd\x00\x01\x1a=\xf2\x89\x05\x05z%\x89\xc5\xd9\xc5zE\xc5\xc5\xf1i\xa9%\xc9\x19\xa9Ez`:\x1e(2\xc5/vJ\xed\x94\x92)z\x00\xab\xb5\x12}',
        # 'success_callback_name': '', 'failure_callback_name': '', 'started_at': '', 'ended_at': '', 'last_heartbeat': '', 'worker_name': '', 'origin': 'low',
        # 'description': 'app.tasks.rss_fetcher.fetch_rss()', 'timeout': 600, 'result_ttl': 7200,
        # 'meta': b'\x80\x05\x95\x12\x00\x00\x00\x00\x00\x00\x00}\x94\x8c\x08interval\x94M\x10\x0es.'}
        # None
        # Job not found
        # jobs = self.asyncScheduler.get_jobs(with_times=True)

        # print(list(jobs))

        # [
        # (Job('514d4e70-2eaf-4389-86cd-c0cacb02d230', enqueued_at=None), datetime.datetime(2023, 6, 1, 15, 14, 29)),
        # (Job('9ed6dda9-943d-4024-9a62-7f99ee9f71a6', enqueued_at=None), datetime.datetime(2023, 6, 1, 15, 14, 29)),
        # (Job('e3f3b00c-7ac3-4d82-9aed-597990584e56', enqueued_at=None), datetime.datetime(2023, 6, 1, 15, 14, 29))]
        # def serialize_date(dt):
        #     if dt is None:
        #         return None
        #     import arrow
        #     return arrow.get(dt).to('UTC').datetime.isoformat()
        #
        # def serialize_job(job, scheduled_for=None):
        #     # print("serialize_job")
        #     return dict(
        #         id=job.id,
        #         created_at=serialize_date(job.created_at),
        #         enqueued_at=serialize_date(job.enqueued_at),
        #         scheduled_for=serialize_date(scheduled_for) if scheduled_for else None,
        #         ended_at=serialize_date(job.ended_at),
        #         origin=job.origin,
        #         result=job._result,
        #         exc_info=job.exc_info,
        #         description=job.description
        #     )
        #
        # # print(jobs)
        # jobs = [serialize_job(job, scheduled_for=scheduled_for) for (job, scheduled_for) in jobs]
        # print(jobs)
        # [{'id': '319dc315-a201-43c6-9e15-da8a35acc925', 'created_at': '2023-06-01T15:39:02.153783+00:00', 'enqueued_at': None, 'scheduled_for': '2023-06-01T15:39:02+00:00', 'ended_at': None, 'origin': 'low', 'result': None, 'exc_info': None, 'description': "builtins.print('scheduler work...1')"}, {'id': 'aed73d55-864a-484a-82fb-ffd7c56c2e90', 'created_at': '2023-06-01T15:38:35.915472+00:00', 'enqueued_at': '2023-06-01T15:38:39.132166+00:00', 'scheduled_for': '2023-06-01T15:39:09+00:00', 'ended_at': '2023-06-01T15:38:45.560742+00:00', 'origin': 'low', 'result': None, 'exc_info': None, 'description': "builtins.print('scheduler work...2')"}, {'id': '0c5673ab-8073-434e-b722-a41de77ea50c', 'created_at': '2023-06-01T15:38:35.920479+00:00', 'enqueued_at': '2023-06-01T15:38:39.129816+00:00', 'scheduled_for': '2023-06-01T16:38:39+00:00', 'ended_at': '2023-06-01T15:38:45.545068+00:00', 'origin': 'low', 'result': None, 'exc_info': None, 'description': 'app.tasks.rss_fetcher.fetch_rss()'}]
        #  [{'id': '319dc315-a201-43c6-9e15-da8a35acc925', 'created_at': '2023-06-01T15:39:02.153783+00:00', 'enqueued_at': None, 'scheduled_for': '2023-06-01T15:39:02+00:00', 'ended_at': None, 'origin': 'low', 'result': None, 'exc_info': None, 'description': "builtins.print('scheduler work...1')"}, {'id': '845db7b2-7691-45da-aab6-dfd64b853549', 'created_at': '2023-06-01T15:39:02.159722+00:00', 'enqueued_at': None, 'scheduled_for': '2023-06-01T15:39:02+00:00', 'ended_at': None, 'origin': 'low', 'result': None, 'exc_info': None, 'description': "builtins.print('scheduler work...2')"}, {'id': '0c5673ab-8073-434e-b722-a41de77ea50c', 'created_at': '2023-06-01T15:38:35.920479+00:00', 'enqueued_at': '2023-06-01T15:38:39.129816+00:00', 'scheduled_for': '2023-06-01T16:38:39+00:00', 'ended_at': '2023-06-01T15:38:45.545068+00:00', 'origin': 'low', 'result': None, 'exc_info': None, 'description': 'app.tasks.rss_fetcher.fetch_rss()'}]
        #  [{'id': '319dc315-a201-43c6-9e15-da8a35acc925',
        #  'created_at': '2023-06-01T15:39:02.153783+00:00',
        #  'enqueued_at': None,
        #  'scheduled_for': '2023-06-01T15:39:02+00:00',
        #  'ended_at': None,
        #  'origin': 'low',
        #  'result': None,
        #  'exc_info': None,
        #  'description': "builtins.print('scheduler work...1')"},
        #  {
        #  'id': 'c6715cf9-a08a-4e45-a405-d3729e8c7729',
        #  'created_at': '2023-06-01T15:39:02.165492+00:00',
        #  'enqueued_at': None,
        #  'scheduled_for': '2023-06-01T15:39:02+00:00',
        #  'ended_at': None,
        #  'origin': 'low',
        #  'result': None,
        #  'exc_info': None,
        #  'description':
        #  'app.tasks.rss_fetcher.fetch_rss()'
        #  }]

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
        return job

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
        return job

    def exists_in_redis(self, job_dict):
        redis_jobs = self.asyncScheduler.get_jobs()  # generator -> 순회하기 전에 쓰면 안됌.

        for redis_job in redis_jobs:
            if self.is_same(job_dict, redis_job):
                self.logger.info(
                    f"{redis_job.description} with {redis_job.args} {redis_job.kwargs} is already scheduled.")

                return redis_job

        return False

    def cancel_schedule(self, existed_schedule):
        existed_schedule.cancel()
        existed_schedule.delete()
        self.logger.info(f"cancel schedule {existed_schedule.description}")

    # def register_schedules2(self, job_dict_list):
    #     # job dict in redis 이미 존재자면, continue
    #     # job dict가 존재하지 않으면, schedule + model get-status running  or  create
    #     # *job dict에 없는 redis job -> cancel + model status death
    #     for job_dict in job_dict_list:
    #         try:
    #             # 이미 존재하는 작업인지 확인하고, 존재하는 job이면 cancel+delete까지 해주기
    #             # => 이미 존재하면 continue + 존재하지 않을 땐, 부모DB get_or_create 후 등록
    #             # => 존재하지 않았는데 get을 해봣을 때 'running'상태 && 같은 'name'으로 남아있다면? -> death처리..?
    #             existed_schedule = self.exists_in_redis(job_dict)
    #             if existed_schedule:
    #                 # self.cancel_schedule(existed_schedule)
    #                 continue
    #
    #             # name
    #             # description
    #             # status -> default 'running'  -> death는 ... exists에 안걸리지만, DB에 get_or_create()시 name && running 상태로 존재할 때..
    #             #        -> args가 다른 runnning 중인 schedule or  이제 안쓰는 schedule -> 이제 안스는 schedule만 death처리 해야한다.
    #             # type -> 'schedule' or 'cron'
    #             # scheduled_for -> 등록 후 나옴. -> 자식입장에서 update해줘야함. -> nullable=True로 주자 -> 현재입력 X
    #             # args, kwargs
    #             if 'scheduled_time' in job_dict:
    #                 self.schedule(**job_dict)
    #                 try:
    #                     self.model.get_or_create(**{
    #                         'type': 'schedule',
    #                         'name': job_dict.get('task_func').__name__,
    #                         'description': job_dict.get('description'),
    #                         'args': job_dict.get('args'),
    #                         'kwargs': job_dict.get('kwargs'),
    #                     })
    #                 except Exception as e:
    #                     self.logger.error(f'{str(e)}', exc_info=True)
    #
    #             elif 'cron_string' in job_dict:
    #                 self.cron(**job_dict)
    #                 try:
    #                     self.model.get_or_create(**{
    #                         'type': 'cron',
    #                         'name': job_dict.get('task_func').__name__,
    #                         'description': job_dict.get('description'),
    #                         'args': job_dict.get('args'),
    #                         'kwargs': job_dict.get('kwargs'),
    #                     })
    #                 except Exception as e:
    #                     self.logger.error(f'{str(e)}', exc_info=True)
    #             else:
    #                 ...
    #
    #         except Exception as e:
    #             self.logger.error(f'Schedule register Error: {str(e)}', exc_info=True)
    #     # 그 전에 job_dict <-> redis sync를 맞춰야한다.
    #     self.sync_redis_and_db()  # redis sync <-> db model
    def is_same(self, job_dict, redis_job):
        return job_dict['task_func'].__name__ in redis_job.description and \
            job_dict['args'] == redis_job.args and \
            job_dict['kwargs'] == redis_job.kwargs

    def register_schedules(self, job_dict_list):
        # 1) job_dict <-> redis sync
        self.sync_redis_and_model_by(job_dict_list)


    def sync_redis_and_model_by(self, job_dict_list):
        # generator라서 list로 뽑아놓고 재활용되게 한다.
        redis_scheduled_tasks = list(self.asyncScheduler.get_jobs())

        # 1) redis에만 잇는 job들을 cancel + db에서는 status='death'처리
        self.process_no_use_jobs(job_dict_list, redis_scheduled_tasks)

        # 2) job_dict_list에만 있는 new_job들은
        #  -> shedule() or cron()으로 넣고 + 받은 job의 id로  model get_or_create(기존데이터라면 status='running'처리, job_id + type 업뎃)
        self.process_new_jobs(job_dict_list, redis_scheduled_tasks)

    def process_new_jobs(self, job_dict_list, redis_scheduled_tasks):
        new_job_dict_list = self.get_unique_job_dict(job_dict_list, redis_scheduled_tasks)
        for new_job_dict in new_job_dict_list:
            if 'scheduled_time' in new_job_dict:
                try:
                    job = self.schedule(**new_job_dict)
                    self.model.get_or_create(**{
                        'job_id': job.id,
                        'type': 'schedule',
                        'name': new_job_dict.get('task_func').__name__,
                        'description': new_job_dict.get('description'),
                        'args': new_job_dict.get('args'),
                        'kwargs': new_job_dict.get('kwargs'),
                    })
                except Exception as e:
                    self.logger.error(f'{str(e)}', exc_info=True)

            elif 'cron_string' in new_job_dict:
                try:
                    job = self.cron(**new_job_dict)
                    self.model.get_or_create(**{
                        'job_id': job.id,
                        'type': 'cron',
                        'name': new_job_dict.get('task_func').__name__,
                        'description': new_job_dict.get('description'),
                        'args': new_job_dict.get('args'),
                        'kwargs': new_job_dict.get('kwargs'),
                    })
                except Exception as e:
                    self.logger.error(f'{str(e)}', exc_info=True)
            else:
                ...

    def process_no_use_jobs(self, job_dict_list, redis_scheduled_tasks):
        no_use_redis_jobs = self.get_unique_redis_schedule(job_dict_list, redis_scheduled_tasks)
        for no_use_redis_job in no_use_redis_jobs:

            # cancel task
            self.cancel_schedule(no_use_redis_job)

            # db model status to 'death'
            no_use_scheduled_task = self.model.query.filter_by(job_id=no_use_redis_job.id).first()
            if no_use_scheduled_task:
                no_use_scheduled_task.update(status='death')

    def get_unique_redis_schedule(self, job_dict_list, redis_scheduled_tasks):
        unique_redis_tasks = []
        for redis_job in redis_scheduled_tasks:
            for job_dict in job_dict_list:
                if self.is_same(job_dict, redis_job):
                    break
            else:
                unique_redis_tasks.append(redis_job)

        return unique_redis_tasks

    def get_unique_job_dict(self, job_dict_list, redis_scheduled_tasks):
        unique_job_dicts = []
        for job_dict in job_dict_list:
            for redis_job in redis_scheduled_tasks:
                if self.is_same(job_dict, redis_job):
                    break
            else:
                unique_job_dicts.append(job_dict)

        return unique_job_dicts

    def sync_redis_and_db(self):
        # 앞에서 삭제될 것은 삭제된 상태라 다시 뽑는다
        redis_jobs = list(self.asyncScheduler.get_jobs())  # generator
        db_jobs = self.model.get_list()
        # job_dict와 형식을 맞추기 위해 serialize -> job_dict에는 func자체가 있어서 .__name__까지 해야하므로 일치는 불가능

        for db_job in db_jobs:
            for redis_task in redis_jobs:
                # redis에 있으면 넘어가고
                # => redis에 있으면서, 'death'면 running처리까지 하고 넘어가기?
                # => running만 가지고 오면 안된다.
                self.logger.info(f'db_task: {db_job}'
                                 f'redis_task: {redis_task}')
                if db_job.name in redis_task.description and \
                        db_job.args == redis_task.args and \
                        db_job.kwargs == redis_task.kwargs:
                    self.logger.info(f'redis에 존재하는 db_task입니다.')
                    self.logger.info(f'db_task.status: {db_job.status}')
                    if db_job.status == 'death':
                        db_job.update(status='running')
                        self.logger.info(f'db_task.status: {db_job.status}')
                    break
            # 없으면 death처리
            else:
                self.logger.info(f'redis에 없는 db_task입니다.')
                self.logger.info(f'db_task.status: {db_job.status}')
                db_job.update(status='death')
                self.logger.info(f'db_task.status: {db_job.status}')
