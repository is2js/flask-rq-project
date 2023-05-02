- 참고: https://github1s.com/staugur/IncetOps/blob/81d73e45c758d8e16c90d91666b138363553b68c/src/libs/base.py

### cancel_task 수정
1. 현재는 Task모델에서 cancel_task메서드가 있고 `rq_job.cancel()`을 했었는데, 실제로 process가 종료되지 않았다.
   - **send_stop_job_command()를 import해와서 대신하면된다.**
   ```python
    def cancel_rq_job(self):
        try:
            rq_job = rq.job.Job.fetch(str(self.id), connection=r)
            # 1) 완료되거나 실패한 job인 경우는 취소 False -> 외부에서 취소할 수 없다고 알려준다. by flash
            if rq_job.is_finished or rq_job.is_failed:
                return False
            # 2) 대기 or 진행중인 task
            # rq_job.cancel()
            send_stop_job_command(self.redis, rq_job.get_id())
            rq_job.delete()
            self.update(
                failed=True,
                status='canceled',  # finished가 아닌 canceled로 저장
            )
            return True
        except (redis.exceptions.RedisError, rq.exceptions.NoSuchJobError):
            return False
   ```
### Service기반으로 변경하기

1. `rq-scheduler` 설치
   - pip freeze > re~
   - **docker image제거후 재 빌드** or `--no-cache`옵션으로 `docker-compose build`  + `app app-worker`
   ```dockerfile
   docker-compose build --no-cache app app-worker
   ```
2. tasks패키지에 `service.py`를 만들어서 `TaskBase`를 cls를 만든다.
   - 기본적으로 timeout과 함께 -> redis -> queue -> scheduler순으로 생성자에서 생성한다.
   - task_logger를 고정적으로 박아둔다.
    ```python
   class TaskBase(object):
       def __init__(self, queue_name):
           self.timeout = 2
           self.redis = redis.from_url(Config.REDIS_URL)
           self.asyncQueue = Queue(name=queue_name, connection=self.redis)
           self.asyncScheduler = Scheduler(queue=self.asyncQueue, connection=self.redis, interval=1)
           self.logger = task_logger
    ```
   
4. **Base기반의 `TaskService` cls를 만들고, tasks/init.py에 있던 `enqueue_task`를 옮겨준다
   - **데코레이터는 개별 task메서드에 적용해야하므로 일단 둔다.**
   - enqueue_task는 flask session에 의존적으로 현재 사용자 정보를 받아가는 중이다.
   - flask기반(session, mail)이므로 view에서 수정해서 test해야한다(shell X)
   - `self.model`에 Task를 넣어주고, enqueue시 self.model.create()로 데이터를 생성하게 한다
   ```python
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
   ```
   
3. send-mail view에서 서비스로 대체해서 테스트한다
   ```python
   @app.route('/send-mail', methods=['GET', 'POST'])
   def send_mail():
       #...
       if request.method == 'POST':
          #...
           try:
               # enqueue_task(send_async_mail, email_data, description=f'{template_name}을 이용하여 메일 전송')
               s = TaskService()
               s.enqueue_task(send_async_mail, email_data, description=f'{template_name}을 이용하여 메일 전송')
   
               flash(f'[{recipient}]에게 [{template_name} ]템플릿 메일을 전송하였습니다.', 'success')
           except Exception as e:
               logger.error(str(e))
               flash(f'[{recipient}]에게 [{template_name} ]템플릿 메일을 전송을 실패하였습니다', 'danger')
   
           return redirect(url_for('send_mail'))
   ```
   
### cancel()메서드를 Task모델 -> TaskService로 옮기기
1. cance_task를 TaskService로 이동
   ```python
    def cancel_task(self, task_id):
        try:
            rq_job = job.Job.fetch(str(task_id), connection=self.redis)
            # 1) 완료되거나 실패한 job인 경우는 취소 False -> 외부에서 취소할 수 없다고 알려준다. by flash
            if rq_job.is_finished or rq_job.is_failed:
                return False
            # 2) 대기 or 진행중인 task
            rq_job.cancel()
            rq_job.delete()

            task = self.model.query.get(int(task_id))
            task.update(
                failed=True,
                status='canceled',  # finished가 아닌 canceled로 저장
            )
            return task
        except (RedisError, NoSuchJobError):
            return False
   ```
   
2. views에서 post용 취소route 수정
   ```python
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
   ```
### TimerTask 모델 생성 및 처리하기
