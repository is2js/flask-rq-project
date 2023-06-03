- 모델 참고: https://github1s.com/spapas/django-test-rq/blob/master/tasks/models.py

1. `ScheduledTaskInstance` 모델은 **job_id가 없다.** 각 부모의 schedule or cron시 발생되는 job만 id가 부여되고
    - **그것이 백그라운드로 실행될 때, 생성되어야한다.**
    - job_id뿐만 아니라 name도 필요없을 듯 싶은데, 부모의 name으로 생성해준다?
    - status는 일반 Task와 동일하게 주되, 생성시 ~~`queued`~~ -> 데코레이터로 `running`시작 -> `finished` `failed`까지만 존재하고
       - 예약실행의 `reserved`는 없다
    - **cascade로 삭제되기 위해서**
        1. 자식의 부모fk에 `ondelete="CASCADE"`로 부모삭제시 삭되도록 
        2. 부모의 자식relationship에 `cascade='all, delete-orphan'`를 줘서 **삭제시 같이 삭제 + 부모가 None인 고아도 자동삭제**되게 한다
    ```python
    class ScheduledTask(BaseModel):
        __tablename__ = 'scheduledtasks'
        # ...
        children = relationship('ScheduledTaskInstance', back_populates='parent', cascade='all, delete-orphan')
    
    class ScheduledTaskInstance(BaseModel):
        __tablename__ = 'scheduledtaskinstances'
    
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(128), index=True)
    
        # args, kwargs
    
    
        # 부모와의 관계
        parent_id = db.Column(db.Integer, db.ForeignKey('scheduledtasks.id', ondelete="CASCADE"))
        parent = relationship('ScheduledTask', foreign_keys=[parent_id], back_populates='children', uselist=False)
    
        # 일반 task와 공통점
        statuses = ['running', 'canceled', 'finished'] # ['queued', , 'reserved']
    
        failed = db.Column(db.Boolean, default=False)
        status = db.Column(db.Enum(*statuses, name='status'), default='queued', index=True)
        log = db.Column(db.Text)
    
        def __repr__(self):
            return f'<ScheduledTaskInstance {self.id} {self.name}>'
    ```


2. 작업메서드 `fetch_rss`를 넣어줄 때, **내부 백그라운드에서 같이 자동으로 작동할 수 있도록 @데코레이터**로 작업되어야한다.
    - enqueue_task처럼 부모객체는 생성하는데, **자식객체의 생성은 스케쥴이 작동할 때 생성되어야한다**
    - **어차피 자식생성시 부모객체를 get_or_create해야하므로 -> `부모 생성`로직도 같이 데코레이터로 넣으면 될 것 같다?**
    - **-> 안된다. 데코레이터내에서 얻은 get_current_job으로는 데이터 생성 정보가 다 없음. job_dict에만 있음.**


3. 그전에 model생성부분을 일반 TaskService의 enqueue_task처럼 `self.schedule`, `self.cron` 내부로 옮기자.
    - 실제 task_func을 scheduler에 넣어서 job을 반환받고, job.id를 이용해서 모델을 만든다.
    - 기존
    ```python
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
                    'kwargs'
    ```
    - 변경
    ```python
    for new_job_dict in new_job_dict_list:
        if 'scheduled_time' in new_job_dict:
            try:
                job = self.schedule(**new_job_dict)
    ```
    ```python
    class SchedulerService(TaskBase):
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
            #...
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
                # id= #
            )
    
            self.model.get_or_create(**{
                'job_id': job.id,
                'type': 'schedule',
                'name': task_func.__name__,
                'description': description,
                'args': args,
                'kwargs': kwargs,
            })
    ```
    - cron도 똑같이 내부로 옮겨준다

4. **이제 각 메서드가 비동기로 실행될 때 전/후에 Instance Model데이터를 생성 -> 성공 with result /실패를 담을 수 있게 데코레이터를 작성한다**
4. TaskService는 enqueue시 모델 생성 후 -> try enqueue를 해서 실패시 모델을 fail/finished 등으로 업뎃한다
    - ScheduledTaskInstance는 백그라운드에서 처리한다.
    ```python
    def scheduled_task(f):
        @wraps(f)
        def task_handler(*args, **kwargs):
            job = get_current_job()  # 부모의 job이 잡힌다.
    
            parent_task = ScheduledTask.query.filter_by(job_id=job.id).first()
            child = ScheduledTaskInstance(
                name=parent_task.name,
                parent=parent_task,
            ).save()
            try:
                f(*args, **kwargs)
    
                child.update(
                    status='finished',
                )
    
            except Exception as e:
                logger.error(str(e), exc_info=True)
                child.update(
                    failed=True,
                    status='finished',
                    log=f'Failed for: ' + str(e)
                )
            finally:
                ...
    
        return task_handler
    ```
   
6. **문제점: 자식의 실패 -> 부모의 실패와 동일하다.**
    - 비어있던 finally에서 **자식 실패/성공 여부(`failed=True or False`)에 따라 -> 부모도 status를 running/death외 그것으로 바꿔주자**
        - 부모가 running or death만 있는 상태에서
        - **자식이 failed==False(default) -> running 유지**
        - **자식이 `failed==True` -> `running -> failed`로 변경**
   ```python
    def scheduled_task(f):
        @wraps(f)
        def task_handler(*args, **kwargs):
            job = get_current_job()  # 부모의 job이 잡힌다.
    
            parent_task = ScheduledTask.query.filter_by(job_id=job.id).first()
            child_task = ScheduledTaskInstance(
                name=parent_task.name,
                parent=parent_task,
            ).save()
            try:
                f(*args, **kwargs)
    
                child_task.update(
                    status='finished',
                )
    
            except Exception as e:
                logger.error(str(e), exc_info=True)
                child_task.update(
                    failed=True,
                    status='finished',
                    log=f'Failed for: ' + str(e)
                )
            finally:
                if child_task.failed:
                    parent_task.update(status='failed')
    
        return task_handler
    ```
    - 부모의 상태값으로 `failed`도 추가한다
    ```python
    class ScheduledTask(BaseModel):
        __tablename__ = 'scheduledtasks'
    
        statuses = ['running', 'death', 'failed']
        #...
    ```
   
7. 부모 생성시 get_or_create로 기존데이터를 가져올 수 있는데
    - death시에만 가져와서 running으로 변경했으나
    - death + failed에서도 running으로 변경해서 가져오도록 하자.
        - 자식 성공여부에 따라 다시 바뀌므로 running으로 바꿔놓는게 맞다
    ```python
    class ScheduledTask(BaseModel):
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
                if instance.status == 'death' or 'failed':
                    instance.update(
                        status='running',
                        job_id=job_dict.get('job_id'),
                        type=job_dict.get('type')
                    )
    
            return instance
    ```
   

8. 다 취소하고, 새로 db가 만들어지도록 스케쥴러에 있는 queue를 cancel in 대쉬보드 -> 재실행해서 부모 및 자식 데이터가 생성되는지 확인한다.

9. scheduled_for는 삭제해야할 듯. 데코레이터는 service에 있는 asyncScheduler에 접근할 수 없어서 모른다?
10. 