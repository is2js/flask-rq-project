### Task 모델 변경하기
- 참고: https://github1s.com/staugur/IncetOps/blob/81d73e45c758d8e16c90d91666b138363553b68c/misc/incetops.sql#L39-L63
- 
1. 일단 status에 `reserved` 상태를 추가해야할 것이다.
   - enqueue_task 래핑메서드에선 `queued`를 status로 메겼지만, 
   - **추가될 schedule_task 래핑메서드에선 `reserved`로 시작하게 한다**
2. nullable로 작업수행예정시간 `reserved_at` 칼럼을 추가하자.
   ```python
   class Task(BaseModel):
       __tablename__ = 'tasks'
   
       statuses = ['queued', 'running', 'canceled', 'finished', 'reserved']
   
       # ...
   
       # timer의 수행시간
       scheduled_at = db.Column(db.DateTime, nullable=True)
   
    @classmethod
    def create(cls, _session, name, description, status='queued'):

        task = cls(name=name, description=description, username=_session.get('username'), status=status)
        return task.save()
   
   @classmethod
   def get_reserved_list_of(cls, _session, limit=None):
       query = cls.query.filter(
           cls.username == _session.get('username'),
           cls.status == 'reserved'
       ).order_by(asc(cls.scheduled_at))

       if limit:
           query = query.limit(limit)

       return query.all()
   
   def to_dict(self):
    return {
        'reserved_at': self.reserved_at
    }
   ```
   

### wraaping전에 scheduled_time 검증 추가하기
- 내부에 raise ValueError('텍스트')로 내서 -> 외부의 try except에서 지정해서 flash로 반환한다
   ```python
     try:
         is_scheduled = request.form.get('is_scheduled')
         if not is_scheduled:
             s = TaskService()
             s.enqueue_task(send_async_mail, email_data, description=f'{template_name}을 이용하여 메일 전송')
             flash(f'[{recipient}]에게 [{template_name} ]템플릿 메일을 전송하였습니다.', 'success')
         else:
             # high queue를 사용
             s = TaskService(queue_name='high')
             try:
                 scheduled_time_str = request.form.get('scheduled_time')
                 scheduled_time = datetime.strptime(scheduled_time_str, '%Y-%m-%d %H:%M:%S')
                 scheduled_time = scheduled_time + timedelta(minutes=2)
                 # scheduled_timestamp = scheduled_time.timestamp()
             except Exception as e:
                 s.logger.debug(f'시간 형식이 올바르지 않습니다.')
                 raise ValueError(f'시간 형식이 올바르지 않습니다.')
   
             # 시간 검증하기 ( 예약시간은, 등록시점보다 3분 보다 더 뒤에)
             if scheduled_time - datetime.now() < timedelta(minutes=1):
                 s.logger.debug(f'현재보다 {1}분이내의 예약은 불가능합니다.')
                 raise ValueError(f'현재보다 {1}분이내의 예약은 불가능합니다.')
             job = s.asyncQueue.enqueue_at(
                 scheduled_time,  # datetime
                 print,  # func
                 "abcdef",  # func - args
                 # description='asdf',  # func - kwargs
             )
             # s.logger.info(f"job in ScheduledJobRegistry(queue=queue): {job in registry}")
             s.logger.debug(f"job.to_dict(): {job.to_dict()}")
             s.logger.debug(f"job in s.asyncQueue.scheduled_job_registry : {job in s.asyncQueue.scheduled_job_registry}")
   
             flash(f'[{recipient}]에게 [{template_name} ]템플릿 메일 전송을 예약({scheduled_time_str})하였습니다.', 'success')
   
     except ValueError as e:
         flash(f'{str(e)}', 'danger')
   
     except Exception:
         flash(f'[{recipient}]에게 [{template_name} ]템플릿 메일을 전송을 실패하였습니다.', 'danger')
   
     return redirect(url_for('send_mail'))
   ```


### 검증을 포함 DB와 연계되는 래핑메서드 reserve_task 만들기
1. views.py상에서 전체 코드를 method로 묶고, parameter 추출하기
   - datetime은 이미 변경되고 나서 들어오며, 시간 검증만 method내부에서 하기
   - enqueue_task 참고하기
   - print 대신 `task_func` 등으로 반영되게 하기
   - **task_func용 args는 함수인자에서 `*args`로 받고, 내부에서 `args`로 입력해주기**
   - 추가로 받을 kwargs(description=,timeout=)은 미리 주고, 나머지 키워드는 `**kwargs`로 받고, 내부에서 `kwargs(dict) or **kwargs 그대로 키워드 입력`으로 메서드 인자로 사용
   ```python
   def reserve_task(
           s, scheduled_time, task_func, *args,
           description=None, timeout=None,
           **kwargs
   ):
       if scheduled_time - datetime.now() < timedelta(minutes=1):
           s.logger.debug(f'현재보다 {1}분이내의 예약은 불가능합니다.')
           raise ValueError(f'현재보다 {1}분이내의 예약은 불가능합니다.')
   
       if not description:
           s.logger.debug(f'Description required to start background job')
           raise ValueError('Description required to start background job')
   
       s.logger.info(f'schedule task start...')
       job = s.asyncQueue.enqueue_at(
           scheduled_time,  # datetime
           task_func,  # func
           *args,  # func - args ( not tuple )
           **kwargs, # func - kwargs (not dict)
           timeout=timeout,
           retry=Retry(max=3, interval=5)  # 일시적 네트워크 장애 오류시 5분간격으로 최대 3번 도전
       )
       s.logger.debug(f"job.to_dict(): {job.to_dict()}")
       s.logger.debug(f"job in s.asyncQueue.scheduled_job_registry : {job in s.asyncQueue.scheduled_job_registry}")
      
       s.logger.info(f'reserve task complete...')
   ```
   
2. 해당 메서드를 app/tasks/service.py로 이동(move)
3. def reserve_task를 tab을 눌러 TaskService cls내부 self 메서드로 이동
   - s객체의 파라미터를 `self`로 변경
4. views.py에서 TaskServic의 객체로 s.reserve_task() 호출하도록 하고 테스트
   ```python
   # str -> datetime 변환
   # - 시간을 입력안한 경우의 예외처리는, 여기서 format이 안맞아서 전송 실패한다.
   scheduled_time_str = request.form.get('scheduled_time', None)
   try:
       scheduled_time = datetime.strptime(scheduled_time_str, '%Y-%m-%d %H:%M:%S')
       scheduled_time = scheduled_time + timedelta(minutes=2)
       # scheduled_timestamp = scheduled_time.timestamp()
   except Exception as e:
       logger.debug(f'시간 형식이 올바르지 않습니다.')
       raise ValueError(f'시간 형식이 올바르지 않습니다.')
   # high queue를 사용
   s = TaskService(queue_name='high')
   s.reserve_task(scheduled_time, print, 'abcde', description='설명')
   flash(f'[{recipient}]에게 [{template_name} ]템플릿 메일 전송을 예약({str(scheduled_time)})하였습니다.', 'success')
   ```
   
### enqueue_task와 비교하여 DB반영하기
1. 래핑메서드에서 Task데이터를 생성하면서 description 키워드를 사용하며, 특별히 default status인 queued가 아닌 `scheduled`로 생성한다
2. enqueue_at시 keyword `job_id=`로 생성된 task.id를 반영한다
3. 