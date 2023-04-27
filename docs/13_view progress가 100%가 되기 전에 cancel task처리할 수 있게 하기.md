1. **view의 progress alert 창에 `id`를 부여한 `cancel`  취소a태그를 추가한다.**
   - 100%가 되는 close button과 달리, 보이다가 -> 100%가 되면 사라지는 a태그를 작성한다.
   ```html
    <div class="alert alert-info fade show mt-3" role="alert">
        {{ task.description }}...
        <span id="{{ task.id }}-progress">{{ task.progress }}</span>%
        <button id="{{ task.id }}-progress-close" type="button" class="close" style="visibility: hidden"
                data-dismiss="alert" aria-label="Close">
            <span aria-hidden="true">&times;</span>
        </button>
        <a id="{{ task.id }}-progress-cancel" href="{{ url_for('cancel_task', task_id=task.id) }}"
           class="text-danger font-weight-bold"
           style="visibility: visible">
            <small>취소</small>
        </a>
    </div>
    ```
2. notificatios.js에 cancel id를 찾아 100%가 되면 안보이게 한다.
    ```js
    function set_task_progress(task_id, progress) {
        $('#' + task_id + '-progress').text(progress);
        $('#' + task_id + '-progress-close').css('visibility', progress === 100 ? 'visible' : 'hidden');
        $('#' + task_id + '-progress-cancel').css('visibility', progress === 100 ? 'hidden' : 'visible');
    }
    ```

3. **cancel_task route를 작성한다.**
   - **path로 들어오는 task_id로 직접 rq.job.Job.fetch()하는게 아니라 `Task모델의 self method부터 가져와서 Task모델과 연동`되게 할 것이다.**
   - 또한, cancel_task 호출이 `이미 종료되거나 실패한 job에 대한 호출`이어서 `취소실패`할 수 도 있기 때문에 결과를 받아서 분기처리한다
   ```python
    @app.route('/task_cancel/<task_id>')
    def cancel_task(task_id):
        # 어차피 db와 연계되어야하기 때문에, job만 불러와 취소가 아니라, Task를 불러와 메서드로 처리한다.
    
        # job = rq.job.Job.fetch('my_job_id', connection=redis)
        # job.cancel()
        # job.get_status()  # Job status is CANCELED
        task = Task.query.get(int(task_id))
        result = task.cancel_rq_job()
        if result:
            flash(f'Task#{task.id} {task.name}가 취소되었습니다.', 'success')
        else:
            flash(f'Task#{task.id} {task.name}가 이미 완료된 상태라 취소에 실패했습니다.', 'danger')
    
        # 나중에는 직접으로 돌아가도록 수정
        return redirect(url_for('send_mail'))
    ```
4. Task모델의 self method로부터 -> job을 fetch해서 정보를 판단한다
   - **이 때, job이 이미 끝난 상황이거나 실패한 job이면 return False로 취소도 실패되었다고 알려준다**
   - rob을 cancel() 후 delete()까지 따로 해줘야 job이 삭제된다.
   - **@background_task에서 돌아가는 try: result=f()후 task데이터 업뎃이 f()에 중단되어 바로 finally로 가 Notification만 수정**하기 때문에
   - **직접 취소되는 task에 대해 task데이터를 `failed+status='canceled'`업뎃을 여기서 해준다.**
    ```python
    class Task(BaseModel):
        __tablename__ = 'tasks'
        def cancel_rq_job(self):
            try:
                rq_job = rq.job.Job.fetch(str(self.id), connection=r)
                # 1) 완료되거나 실패한 job인 경우는 취소 False -> 외부에서 취소할 수 없다고 알려준다. by flash
                if rq_job.is_finished or rq_job.is_failed:
                    return False
                # 2) 대기 or 진행중인 task
                rq_job.cancel()
                rq_job.delete()
                
                # Task데이터를 완료되신 canceled로 업뎃하기
                # - @background_task의 try코드에서 수행후 result로 Task 'finished'업뎃하는 코드는 실행 안되고 중단 되고
                # - 바로 finally로 가서 set_task_progress(100)으로 Notification을 완료상태로 만든다.
                # -> 그래서 'finished'처리가 실행안되고, 중단된 대신 'canceled' 처리를 직접해줘야한다
                self.update(
                    failed=True,
                    status='canceled', # finished가 아닌 canceled로 저장
                )
                return True
            except (redis.exceptions.RedisError, rq.exceptions.NoSuchJobError):
                return False
    ```

5. **Task모델은 상태의 종류에 'canceled'를 추가하고, 진행중인 task 검색에서 != 'finished'가 아니라 in_('queued', 'running')으로 바꿔줘야한다**
    ```python
    class Task(BaseModel):
        __tablename__ = 'tasks'
        
        #...
        statuses = ['queued', 'running', 'canceled', 'finished']
        #...
        
        @classmethod
        def get_unfinished_list_of(cls, _session, limit=None):
            query = cls.query.filter(
                cls.username == _session.get('username'),
                # cls.status != 'finished'
                cls.status.in_(['queued', 'running'])
            ).order_by(asc(cls.created_at))
    
            if limit:
                query = query.limit(limit)
    
            return query.all()
    ```

- background_task에서 result를 못내고 종료된다.
  - chatgpt에 의하면 job.cancel()이 되면 `try속 result = f()는 result를 받지 못하고 중단`된 이후 바로 `finally`로 가서 Notification을 finished상태로 만든다.
     - 그럼 progress 100을 채우면서 finished된 notification알림은 검색되지 않는다.
  - 그렇다면 Notification외 try내부에 result = f()이후의 `task를 finished + result로 업뎃`하는 코드만 cancel_task에서 처리해주면 된다.

  