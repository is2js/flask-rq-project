- 모델 참고: https://github1s.com/spapas/django-test-rq/blob/master/tasks/models.py

### Task 메서드 정의 with @background_task, set_task_progress
1. `tasks패키지/xxx.py`로 작동시킬 모듈을 만들고
2. 내부에 `동기적인 기본 실행메서드`를 정의하고
    ```python
    def send_mail(subject, recipients, template_name,
                  sender=Config.MAIL_SENDER, attach_img_data=None, attachments=None, sync=False, **kwargs):
    # ...
    ```
3. `tasks패키지/decorators.py`에 정의된 `@background_task`데코레이터를 이용해서 동기메서드를 호출하는 `비동기메서드`를 또 구현한다
    - 비동기 메서드 내부에서는 
        1. @background_task 내부에서도 progress 0, 100를 채우는 `set_task_progress(xx)`를 내부에서 사용하며
        2. 동기메서드를 호출하고
        3. result dict를 반환한다. 
    ```python
    @background_task
    def send_async_mail(email_data):
        #...
        set_task_progress(50)
        #...
        send_mail(**email_data, attach_img_data=attach_img_data, sync=True)
        
        result = {'result': 'success'}
   
        return result
    ```
   
4. `@background_task` + `set_task_progress`는 **`현재 rq에 들어간 상태로 가정`**하여 `get_current_job()`을 통해 rq에 들어간 job의 정보를 얻을 수 잇는 상태다.
    - 이 때, 비동기메서드보다 더 외부에서 비동기메서드를 호출할 때 Task모델의 데이터가 만들어진다. `enqueue_task() 내부`
    1. get_current_job()모듈의 `.get_id()`를 이용하여 현재 rq에 들어간 job의 id를 얻은 뒤
    2. 이미 더 외부에서 호출되어 만들어진 Task모델 데이터를 filter하여 찾고, `status를 running`으로 변경해준다
    3. 또한 `set_task_progress(0)`을 호출하여 
        - get_current_job()으로 얻은 job에 meta데이터에 progress를 0으로 입력하고 저장하며
        - job_id -> task데이터 -> 현재 progress(0)으로 `Notification`데이터를 name=task_progress로 생성한다
    4. 데코레이터로서 `자신을 걸어준 비동기메서드`를 function으로 호출하여, 비동기메서드가 반환하는 result dict를 받으면, **비동기메서드의 호출이 끝난 상태**로 판단하여 
    5. 찾아놓은 Task데이터의 status를 finished로 바꾸고, result도 같이 저장한다.
        - **즉, Task의 running -> 비동기메서드호출 -> 결과 -> finished with 결과**까지를 완성한다.
        - Task의 생성은 더 외부(enqueue_task)에서 한다.
    6. 성공했든 실패했든 `finally`를 통해 `set_task_progress(100)`을 호출하여 job.meta데이터 및 Notification 100을 생성한다.
        - **즉, set_task_progress는 0과 100까지를 다 담당한다.**
        - set_task_progress의 중간수치는 @background_task를 달고 있는 비동기메서드 내부에서 직접 설정해준다.

5. 이렇게 동기 -> `비동기메서드` with @background_task데코 + set_task_progress메서드로 `정의가 완료`되었다.

### TaskService(비동기 실행, 비동기 예약실행)
- DB와의 연관관계를 정리하면
    - s.enqueue_task()시 Task 데이터 create
    - s.cancel_task()시 Task 데이터 canceled update
    - 데코레이터 @background_task에서 Task running -> finished 업데이트
- SchedulerService에서 없는 것
    - self.model + self.instance_model
    - enqueue_task처럼 실행시 Task모델 데이터(model, instance_model) 생성
        - 생성된 id로 queue에 넣어주기?!(instance?!) 
    - cancel_task처럼 취소시 Taks모델 데이터 canceled로 업데이트
    - 데코레이터 @background_task에 상응하는, Task모델 데이터 running, finishe로 업데이트 
    - `데코레이터를 적용`외에 Notification 데이터 생성 및  `set_task_progress(50)` + `result = {'result': 'success'}를 반환해줄`비동기 메서드 ?!

- 이제 비동기 메서드를 호출하는 TaskService들을 살펴보면

1. `TaskBase(timeout, redis객체, rq-Queue객체)`를 바탕으로 생성된 `TaskService`, `SchedulerService`에 정의된 메서드로 한다.

2. `TaskService`는 사용될 queue_name을 받아 해당 rq-queue를 생성한다. default로는 `default` queue_name를 사용한다.
    - 내부에서는 Task모델을 `self.model`로 가지고 있고
    - task_logger객체를 `self.logger`로 가지고 있고
    - 예약실행시, N초이상 차이날때만 예약실행이 가능하도록 `self.RESERVATION_LIMIT_SECONDS` = 30을 가지고 있다
        - 예약실행시에는 `queue_name을 high`로 사용해서 서로 다른 queue를 사용한다
    ```python
    class TaskBase(object):
        def __init__(self, queue_name):
            self.timeout = 60
            self.redis = redis.from_url(Config.REDIS_URL)
            self.asyncQueue = Queue(name=queue_name, connection=self.redis)
        #...
    class TaskService(TaskBase):
        def __init__(self, queue_name='default'):
            super().__init__(queue_name=queue_name)
            self.model = Task
            self.RESERVATION_LIMIT_SECONDS = 30
            self.logger = task_logger
    ```
3. TaskService는 일반 비동기 실행(`enqueue_task` with `default` queue-name), 예약 비동기 실행(`reserve_task` with queue-name `high`)을 할 수 있다. 
    ```python
    if not is_scheduled:
        s = TaskService()
        s.enqueue_task(send_async_mail, email_data, description=f'{template_name}을 이용하여 메일 전송')
    else:
        # high queue를 사용
        s = TaskService(queue_name='high')
        s.reserve_task(scheduled_time, send_async_mail, email_data, description=f'{template_name}을 이용하여 메일 전송')
        flash(f'[{recipient}]에게 [{template_name} ]템플릿 메일 전송을 예약({str(scheduled_time)})하였습니다.', 'success')
    ```
   
4. `s.enqueue_task()`메서느는 `비동기 task메서드` + 필요한 `args`+`kwargs를` 받고, 그외에 db에 입력할 `description`, 선택적 timeout을 받는다.
    - `description`과 함께, `사용자`(현재는session), 들어온 비동기메서드의 이름인 `task_func.__name__`,  `self.model(Task)`를 이용해 **Task 데이터를 생성한 뒤**
    - 내가 가진 `self.asyncQueue`에다가 비동기 task메서드를 넣는다.
    ```python
    class TaskService(TaskBase):
        def enqueue_task(self,
                         task_func,  # Task메서드용 1
                         *args,  # Task메서드용 2
                         description=None,  # DB + task용
                         timeout=None,  # enqueue용 (수행기다려주는 최대 시간(초))-> 5분지나면, TimeoutException  예외발생 후, 다른 task하러 간다
                         **kwargs,  # Task메서드용 3
                         ):
            if not description:
                raise ValueError('Description required to start background job')
            task = self.model.create(session, name=task_func.__name__, description=description)
            self.logger.info(f'start task...{task.name}')
            try:
    
                self.asyncQueue.enqueue_call(
                    func=task_func,  # task메서드
                    args=args,  # task메서드 인자1
                    kwargs=kwargs,  # task메서드 인자2
                    timeout=timeout if timeout else self.timeout,
                    retry=Retry(max=3, interval=5),  # 일시적 네트워크 장애 오류시 5분간격으로 최대 3번 도전
                    job_id=str(task.id),  # DB연동
                )
            self.logger.info(f'complete task...{task.name}')
            return task
    ```
   
5. enqueue_task에 대해 끝나기 전에 `cancel_task`를 할 수 있는데
    - `task_id`를 인자로 받아서, str()로 변환 후, fetch로 가져온 rq_job을 끝나지 or 취소하지 않았으면 취소한다.
    - Task데이터에 `status를 canceled`로 바꾼다.
    - **취소가 제대로 되었으면 해당 task데이터가 반환되고 아니라면 return False되어 -> 외부에서 판단할 수 있게 한다**
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
    ```python
    @main_bp.route('/task_cancel/<task_id>')
    def cancel_task(task_id):
        s = TaskService()
        task = s.cancel_task(task_id)
        if task:
            flash(f'Task#{task.id} {task.name}가 취소되었습니다.', 'success')
        else:
            flash(f'Task가 이미 완료된 상태라 취소에 실패했습니다.', 'danger')
        return redirect(url_for('main.send_mail'))
    ```
    

6. 예약 실행 s.reserve_task()의 경우, enqueue_task와 인자가 동일한 데 + `scheduled_time`만 추가된다.
    - 마찬가지로 task모델을 생성하고
    - queue에 넣는데 enqueue_call()이 아닌 enqueue_at()으로 넣는다.
    - **Notification을 `비동기 메서드가 queue에 들어간 상태`에서 호출되는 @background_task에 set_task_progress(0)호출시 하는게 아니라**
    - **예약직후부터 Notification을 받을 수 있게 `reserve_task()`에서부터 `비동기 상태로 실행되기 전 Notification`을 날려줄 수 있게 만든다.**
    ```python
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
    ```
   

7. 예약취소 cancel_reserve()는 cancel_task와 달리
    - fetch로 가져온 job의 끝났는지or실패했는지로 판단하는게 아니라
    - **아직 실행안되고 예약작업들에 등록되어있는지를 `ScheduledJobRegistry(queue=self.asyncQueue)`안에 job이 속해있는지로 확인한다.**
    - 없으면 early return으로 False를 뱉고, 예약작업들 속에 있으면 Task를 업데이트 한다.
    ```python
    def cancel_reserve(self, task_id):
        rq_job = rq.job.Job.fetch(str(task_id), connection=self.redis)
        registry = ScheduledJobRegistry(queue=self.asyncQueue)
        if rq_job not in registry:
            return False

        rq_job.cancel()
        rq_job.delete()
        task = self.model.query.get(int(task_id))
        task.update(
            failed=True,
            status='canceled',  # finished가 아닌 canceled로 저장
        )
        return task
    ```
   
### 기존 SchedulerService 분석
1. TaskService와 달리 queue_name -> `self.asyncQueue` 생성 외에 **해당 queue를 가지고 `self.asyncScheduler`도 추가로 가진다.**
    - required) `self.model 및 self.instance_model`이 존재하지 않고 할당되지 않음.
    - required) job의 상태를 파악해보지 못함.
       - rq-scheduler 패키지는 예약된 작업에 대한 자세한 정보를 기록하지 않습니다. 따라서 Job 객체에서 직접 예약된 작업의 상태 또는 예약 시간을 확인할 수 있는 메서드나 속성이 제공되지 않습니다.
    - rq-scheduler-dashboard를 참고하여 status는 running or death로 파악한다. 근데, 개별 task가 아니라 전체 scheduler 1개의 개념이다...
    ```python
    @blueprint.route('/status.json')
    @jsonify
    def scheduler_status():
        scheduler = Scheduler()
        return dict(
            running=(
                scheduler.connection.exists_in_redis(scheduler.scheduler_key) and
                not scheduler.connection.hexists(scheduler.scheduler_key, 'death')
            )
        )
    ```
    - required) scheduler개별job이 아니라 등록된 전체job를 `self.asyncScheduler`에서 얻어서 한꺼번에 get_or_create해야할 것 같다
        - scheduler의 각 job에서 얻을 수 있는 정보는 dashboard와 같이 `job_id`, `create_at`, 첨엔 같은 `scheduled_for`이다.
        - 개별 istance들이 생성될 때, 부모모델데이터로서 scheduled_for도 같이 업뎃해야할 듯??
    - 그렇다면, name로 부모데이터를 검색하고, job의 존재유무를 통해 running or death로 해야할 듯 하다
    - service내부에서 처리되도록 하기 위해, 개별 .scheduler + .cron의 list를 처리할 새로운 메서드를 만들어야할 듯하다

2. `.schedule()`과 `.cron()`
    - `self.asyncScheduler`에서 .schedule()과 .cron()을 호출한다.
    - 아직 매핑메서드로서 기능은 인자 검증밖에 안하고 있다.

3. `.exists()`는 **self.asyncScheduler에서 `.get_jobs()`의 job들을 순회하며**
    - description(모듈경로 + 모듈이름)에 `입력되는 job_dict`의 task_func의 __name__이 존재하는지
    - args, .kwargs까지 모두 일치해야 같은 schedule or cron으로 본다
    - required) 데이터 저장시 args, kwargs까지 같이 저장하여, 존재하는지검사에서도 args, kwargs까지 검사해야할 듯.
    ```python
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
    ```
   
4. `.cancel_schedule()`은 cancel+delete까지 한다.
    - required) 이제 exists하면... 취소+삭제가 아니라 건너띄도록해서 기존 것 유지되도록 해야한다?

### SchedulerService용 model(self.model + self.instance_model) 구현하기

#### 참고프로젝트 분석하기

- django 프로젝트 참고: https://github1s.com/spapas/django-test-rq/blob/master/tasks/models.py
1. 참고용 ScheduledTask, ScheduledTaskInstance
    ```python
    class ScheduledTask(models.Model):
        # A model to save information about a scheduled task
        created_on = models.DateTimeField(auto_now_add=True)
        name = models.CharField(max_length=128)
        # A scheduled task has a common job id for all its occurences
        job_id = models.CharField(max_length=128)
    
    
    class ScheduledTaskInstance(models.Model):
        # A model to save information about instances of a scheduled task
        scheduled_task = models.ForeignKey('ScheduledTask', on_delete=models.PROTECT)
        created_on = models.DateTimeField(auto_now_add=True)
        result = models.CharField(max_length=128, blank=True, null=True)
    ```
   
2. queue에 들어갈 비동기 메서드에서 get_current_job -> job.id를 얻어서  
    1. ScheduledTask(job_id=, name=) -> get_or_create
        - required) 나는 job_id + name외에 args, kwargs까지 넣어서 비교해서 get_or_create
        - required) 추가로 scheduled_for
    2.  동기메서드 작동 -> 결과물result -> ScheduledTaskInstance(Scheduled_Task = task, result=) -> create한다
        - result는 빠지고
        - ScheduledTaskInstance의 create_at ->  ScheduledTask의 직전 실행시간으로 update? + scheduler_for를 interval로 처리?
    ```python
    @job
    def scheduled_get_url_words(url):
        """
        This creates a ScheduledTask instance for each group of 
        scheduled task - each time this scheduled task is run
        a new instance of ScheduledTaskInstance will be created
        """
        job = get_current_job()
    
        task, created = ScheduledTask.objects.get_or_create(
            job_id=job.get_id(),
            name=url
        )
        response = requests.get(url)
        response_len = len(response.text)
        ScheduledTaskInstance.objects.create(
            scheduled_task=task,
            result = response_len,
        )
        return response_len
    ```
   

### db적용 및 개선사항 적용
1. tasks/init.py에서 schedule_jobs + cron_jos 순회하던 것을 service 안의 메서드로 이동
    ```python
    # app/tasks/__init__.py
    def init_app(app):
        # 지금부터, 몇분 간격으로 (+ 몇번을) 반복해서 실행
        schedule_job_dicts = [
            #...
        ]
        cron_job_dicts = [
            #...
        ]
        scheduler_service = SchedulerService()
        scheduler_service.register_schedules(cron_job_dicts + schedule_job_dicts)
    ```
2. model생성
    ```python
    class ScheduledTask(BaseModel):
        __tablename__ = 'scheduledtasks'
    
        statuses = ['running', 'death']
        types = ['schedule', 'cron']
    
        id = db.Column(db.Integer, primary_key=True)
    
        name = db.Column(db.String(128), index=True)
        description = db.Column(db.String(128))
    
        # complete = db.Column(db.Boolean, default=False)
        status = db.Column(db.Enum(*statuses, name='status'), default='running', index=True)
    
        # 추가 type + args + kwargs
        type = db.Column(db.Enum(*types, name='type'), nullable=False)
        args = db.Column(List, nullable=True)
        kwargs = db.Column(Json, nullable=True)
    
        # 인스턴스 자식의 수행시간
        # => scheduled_for -> 자식 등록 후 나옴. -> 자식입장에서 update해줘야함. -> nullable=True로 주자
        scheduled_for = db.Column(db.DateTime(timezone=True), nullable=True)
    ```

3. self.model, self.instance_model에 ScheduledTask, ScheduledTaskInstance 삽입
    - dict를 위한 Text 상속 Json 칼럼외에 
    - **list를 위한 Text 상속 `List 칼럼`도 정의**한다
    ```python
    class List(db.types.TypeDecorator):
        """Enables JSON list storage by encoding and decoding on the fly."""
        impl = db.Text
    
        # 경고로 인해 추가
        cache_ok = True
    
        def process_bind_param(self, value, dialect):
            if value is not None:
                return json.dumps(value).encode('utf-8')
    
        def process_result_value(self, value, dialect):
            if value is not None:
                return json.loads(value.decode('utf-8'))
    
    
    mutable.MutableList.associate_with(List)
    ```
    
4. TaskService처럼 enqueue_task 전에 model을 생성 -> model의 task.id를 str()해서 job의 id로 배정해줄 필요 없다
    - 왜냐면, task_model.id -> rq.Fetch(id= ) -> cancel_rq_job을 할 필요가 없기 때문이다.
    - **job_dict -> redis에 자동으로 반영되며 실시간으로 취소시키는 일은 없을 것이다.**

5. **3가지 영역이 있는데 `job_dict_list`(schedule + cron), `redis_jobs`(scheduler.get_jobs()), `Db model jobs`(ScheduledTask)**
    1. 앱 시작시, `job_dict_list <-> redis_jobs`를 먼저 sync시켜, **job_dict_list에 있는 것은 redis에 그대로두고**
        - **`redis에만 남아있는 job들`은 redis에서 `cancel`시킨다.**
        - **job_dict_list에만 존재하는 `new_job_dict`는 `schedule or cron` + `model create`까지 해줘야한다.**
            - **기존에 `같은 name, args, kwargs`로 제작된 model데이터가 있다면, 부모로서 가져와서 사용되도록 `get_or_create`로 처리되게 한다**
        
    2. 그 이후 job_dicts와 1:1매칭된 `redis_jobs` <-> `Db model jobs`를 sync시킨다.
    ```python
    def register_schedules(self, job_dict_list):
        # 1) job_dict <-> redis sync
        self.sync_redis_and_model_by(job_dict_list)

    ```
   
6. 먼저, input되는 job_dict_list <-> redis_jobs 와 비교하되, 
   - **공통으로 존재한다면 continue하면서**
   - **먼저, `취소(cancle_schedule)시켜야`할 job_dict_list에 없는 `no_use_redis_jobs`를 찾아내기 위해**
       - **`redis_jobs`를 바깥으로 한 2중 반복문을 돌아서, 안쪽 job_dict_list와 is_same(name, args, kwargs)에 안걸리는 `unique`한 것들을 찾아낸다.**
   - **다음으로 `등록(schedule or cron) with db(get_or_create)`시켜야할 `new_job_dict_list`를 찾아내기 위해**
       - **`job_dict_list`를 바깥으로 한 2중 반복문을 돌아서, 안쪽 redis_jobs와 is_same(name, args, kwargs)에 안걸리는 `unique`한 것들을 찾아낸다.**
   
   ```python
    def sync_input_and_redis(self, job_dict_list):
        # generator라서 list로 뽑아놓고 재활용되게 한다.
        redis_scheduled_tasks = list(self.asyncScheduler.get_jobs())
   
        no_use_redis_jobs = self.get_unique_redis_schedule(job_dict_list, redis_scheduled_tasks)
   
        new_job_dict_list = self.get_unique_job_dict(job_dict_list, redis_scheduled_tasks)
    ```
    - 각각은, is_same에 걸리면, break로 통과하되, 안쪽 job들에 is_same이 안걸려 else로 오는 것들을 append해서 모은다.
    ```python
    def is_same(self, job_dict, redis_job):
        return job_dict['task_func'].__name__ in redis_job.description and \
            job_dict['args'] == redis_job.args and \
            job_dict['kwargs'] == redis_job.kwargs
   
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
    ```
   

7. 이제 redis에 있는 job들은 cancel_schedule() 해준다.
    - 이 때, 해당 job들에 대한 db데이터도 `status=death`로 바꿔줘야한다.
    - 그러기 위해선 job_id를 create시부터 field에 등록해야한다.
    - 그러기 위해선 schedule(), cron()에서 job을 반환받아, 그것으로 `job.id`를 job_id필드(str)에 등록해줘야한다.
        - 일단 task에선 직업 model생성 -> 그 model.id를 job.id로 줬었는데, 이번엔 주어지는 string으로 대체
    1. model에서 job_id를 추가한다
        ```python
        class ScheduledTask(BaseModel):
            # cancel시 필요
            job_id = db.Column(db.String(36), nullable=False)
            #...
        ```
    2. **redis에만 잇어 cancel되는 job들의 id를 model에서 필터링해 death 상태로 만들어준다.**
        ```python
        def sync_redis_and_model_by(self, job_dict_list):
            # generator라서 list로 뽑아놓고 재활용되게 한다.
            redis_scheduled_tasks = list(self.asyncScheduler.get_jobs())
    
            no_use_redis_jobs = self.get_unique_redis_schedule(job_dict_list, redis_scheduled_tasks)
            for no_use_redis_job in no_use_redis_jobs:
                
                # cancel task
                self.cancel_schedule(no_use_redis_job)
                
                # db model status to 'death'
                no_use_scheduled_task = self.model.query.filter_by(job_id=no_use_redis_job.id).first()
                if no_use_scheduled_task:
                    no_use_scheduled_task.update(status='death')
        ```
    3. new_job_dict를 등록할 때, **부모개념으로서 기존에 있던 데이터를 그대로 쓰기 위해 `get_or_create`를 써야하는데**
        - **name, args, kwargs만 같으면 그대로 쓸건데, `death`상태라면 `running`으로 바꿔서 쓰고 `job_id`도 업뎃해줘야한다**
        - 참고로 type은 job정보에서 가져올 수 없어서, redis <-> job_dict비교시 is_same에 넣질 못했다.
        - **따라서 여기서도 type은 비교하지말고 가져와야한다. 그렇다면 `type`도 변경해줘야한다.**
        - 즉, 필터링은 `name, args, kwargs`로 하고, **death상태이라면 => `job_id`필수업뎃 + `type`필수없뎃 + `status`필수없뎃이다.**
        ```python
        class ScheduledTask(BaseModel):
            #...
            @classmethod
            def get_or_create(cls, **job_dict):
                instance = cls.query.filter(
                    job_dict.get('name') == getattr(cls, 'name'),
                    job_dict.get('args') == getattr(cls, 'args'),
                    job_dict.get('kwargs') == getattr(cls, 'kwargs'),
        
                ).first()
                # 기존에 없는 데이터면 생성해서 쓴다.
                if instance is None:
                    instance = cls(**job_dict)
                    instance.save()
        
                # 기존에 있는 데이터를 갖다쓴다면,
                # 'death'상태의 기존 데이터라면 ->  status='running' + 달라질 수 있는 필수 job_id for cancel / type 을 필수로 업뎃해줘야한다.
                else:
                    if instance.status == 'death':
                        instance.update(
                            status='running',
                            job_id=job_dict.get('job_id'),
                            type=job_dict.get('type')
                        )
        
                return instance
        ```
    4. 이제 new_job_dict들을 등록 + model get_or_create까지 해준다
    ```python
    def sync_redis_and_model_by(self, job_dict_list):
        # generator라서 list로 뽑아놓고 재활용되게 한다.
        redis_scheduled_tasks = list(self.asyncScheduler.get_jobs())

        # 1) redis에만 잇는 job들을 cancel + db에서는 status='death'처리
        no_use_redis_jobs = self.get_unique_redis_schedule(job_dict_list, redis_scheduled_tasks)
        for no_use_redis_job in no_use_redis_jobs:
       # 2) job_dict_list에만 있는 new_job들은
        #  -> shedule() or cron()으로 넣고 + 받은 job의 id로  model get_or_create
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
    ```
   

8. 그렇다면 알아서 sync redis <-> db까지 처리됬으니, 리팩토링만 해준다.
    ```python
    def sync_redis_and_model_by(self, job_dict_list):
        # generator라서 list로 뽑아놓고 재활용되게 한다.
        redis_scheduled_tasks = list(self.asyncScheduler.get_jobs())

        # 1) redis에만 잇는 job들을 cancel + db에서는 status='death'처리
        self.process_no_use_jobs(job_dict_list, redis_scheduled_tasks)

        # 2) job_dict_list에만 있는 new_job들은
        #  -> shedule() or cron()으로 넣고 + 받은 job의 id로  model get_or_create(기존데이터라면 status='running'처리, job_id + type 업뎃)
        self.process_new_jobs(job_dict_list, redis_scheduled_tasks)
    ```
    