### Task Model에 사용자 username 반영하고, 생성/조회 메서드 구현하기
1. Notification은 session속 username을 기준으로 가져오기 때문에, Task도 특정username에 대한 task만 골라낼 수 있어야한다
   - Message에서는 username 대신 recipient 칼럼으로 들어갔었다.
   ```python
    class Task(BaseModel):
        __tablename__ = 'tasks'
        # ...
        username = db.Column(db.String(6), index=True)
    ```
   - sqlite삭제 후 재실행하여 생성
   
2. 유저정보를 session인자를 추가해서 받아야하므로 self save -> cls creaet()로 매핑한다
   - 기존 생성 in enqueue_task
      ```python
      task = Task(name=task_func.__name__, description=description)
      task.save()
      ```
   - create(session, args) 도입
   ```python
   @classmethod
   def create(cls, _session, name, description):
       task = cls(name=name, description=description, username=_session.get('username'))
       return task.save()
   ```
3. 그동안 sessiond없이 Task() 데이터를 .save()로 저장한 code들을 수정해야한다.
   - tasks/init/enqueue_task내부에서 create(session, )으로 호출되어야하므로
      - **tasks모듈이 request에 의존적으로 되버림 -> enqueue_task는 shell에서 테스트 못하게 된다?!**
   ```python
   def enqueue_task(
           task_func,  # Task메서드용 1
           *args,  # Task메서드용 2
           description=None,  # DB + task용
           timeout=300,  # enqueue용 (수행기다려주는 최대 시간(초))-> 5분지나면, TimeoutException  예외발생 후, 다른 task하러 간다
           **kwargs,  # Task메서드용 3
       ):
       if not description:
           raise ValueError('Description required to start background job')
       task = Task.create(session, name=task_func.__name__, description=description)
   
       try:
           queue.enqueue_call(
       #...
   ```
   

4. tasks정보를 보내는 send_mail view에서 Task조회시, session을 받는 나의 task들을 가져와야한다
   - 끝난 것은 `종료(updated_at)`의 `역순(desc)으로 최근것부터` 가져오고
   - 안끝나는 것은 `생성(create_at)`을 `처음부터` 가져온다
   ```python
    @classmethod
    def get_list_of(cls, _session):
        return cls.query.filter(
            cls.username == _session.get('username'),
        ).all()

    @classmethod
    def get_finished_list_of(cls, _session, limit=None):
        query = cls.query.filter(
            cls.username == _session.get('username'),
            cls.status == 'finished'
        ).order_by(desc(cls.updated_at))
        
        if limit:
            query = query.limit(limit)
            
        return query.all()

    @classmethod
    def get_unfinished_list_of(cls, _session, limit=None):
        query = cls.query.filter(
            cls.username == _session.get('username'),
            cls.status != 'finished'
        ).order_by(asc(cls.created_at))
        
        if limit:
            query = query.limit(limit)
            
        return query.all()
   ```
   - send_mail route
   ```python
     if template_name == 'email/welcome':
         email_data['subject'] = '안녕하세요 rq프로젝트 서비스 소개입니다.'
     elif template_name == 'email/tasks':
         email_data['subject'] = 'rq프로젝트 완료된 최근 5개 Tasks 정보입니다.'
         email_data['tasks'] = Task.get_finished_list_of(session, limit=5)
     elif template_name == 'email/tasks_in_progress':
         email_data['subject'] = 'rq프로젝트 진행 중인 Tasks 정보입니다.'
         email_data['tasks'] = Task.get_unfinished_list_of(session, limit=None)
   ```
   

5. template이름을 tasks_finished로 바꾸고, 전체를 조회할 tasks 템플릿 생성

### set_task_progress에서 생성 및 업데이트 되는 Notification
#### 현재상황
1. Message의 경우
   1. 메세지.create()시 Notification name=unread_message_count + payload=새메세지갯수 생성
   2. 메세지 확인시 Notification payload default값으로 업뎃
2. Task의 경우
   1. enqueue_task()시 Task.create()
   2. Task 수행 전/후 @background_task에서 Task.update() + set_taks_progress(0 or 100)
   3. Task 수행 도중 set_task_progress(0< < 100)
      - set_task_progress시 get_current_job의 meta에 progress 저장
#### 요구사항
1. Notification 생성을 Task.create() or set_task_progress(0)에서 한다
   - **set_task_progress(n)의 n값이 변할 때마다 Notification도 변해야하므로 Message.create()와 달리 Task는 set_progress에서 해야할 듯.**
   ```python
   def set_task_progress(progress):
       job = get_current_job()
       if job:
           job.meta['progress'] = progress
           job.save_meta()
   
           Notification.create(session, name='task_progress', payload=dict(
               task_id=job.get_id(),
               progress=progress,
           ))
   ```

2. test시 Notification.create()에 필요한 session이 worker에서 작동되 http request 에러가 난다
   - 다른모델과 달리, **Notification의 create에서는 session말고 username만 받도록 변경**
   - **task들의 내부에 사용되는 Model 및 method는 `flask.session`이 사용되면 안된다.**
   ```python
    class Notification(BaseModel):
    # ...
    @classmethod
    def create(cls, username, name, payload):
        # 1. 현재사용자(in_session-username)의 알림 중
        #    - name='unread_message_count' 에 해당하는 카테고리의 알림을 삭제하고
        Notification.query.filter_by(name=name, username=username).delete()
        # 2. 알림의 내용인 payload에 현재 새정보를 data key에 담아 저장하여 새 알림으로 대체한다
        notification = Notification(
            name=name,
            username=username,
            payload=payload
        )
        return notification.save()
   ```
   - **username은 job_id -> Task -> task.username으로 찾을 수 있다.**  
   ```python
   def set_task_progress(progress):
       job = get_current_job()
       if job:
           job.meta['progress'] = progress
           job.save_meta()
   
           task = Task.query.get(job.get_id())
           Notification.create(name='task_progress', username=task.username, payload=dict(
               task_id=task.id,
               progress=progress,
           ))
   ```
   
3. task를 실행시켜보면 payload에 task_id + progress가 업뎃된다.
   - background_task에서 0, 100을 넣고
   - 각 task메서드에서 0~100 사이에 set_task_progress를 넣으면 자동으로 업뎃된다.


