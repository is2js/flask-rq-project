### 참고 깃허브
- `rq-test` django지만, task의 결과를 저장 + long_task구분 + scheduledTask구분 하는 모델: 
  - blog: https://spapas.github.io/2015/01/27/async-tasks-with-django-rq/#models-py
- `OK` flask인데, TypeDecorator로 Text칼럼을 매핑해서 Json필드 + @compile로 미지원필드 대체
  - https://github.com/okpy/ok/blob/master/server/models.py
  - Job 모델 + 내부list Enum사용
  - **job처리를 데코레이터로 + transaction도**
- `busy-beaver` task에 내부클래스로 상태enum(결과저장은x)
  - https://github.com/busy-beaver-dev/busy-beaver/blob/5e3543f41f189fbe4a50d64e3d6734dc765579b4/busy_beaver/common/models.py#L30
- `xcessiv` rest ML모델 결과저장 + Text to Json필드 사용 + mutable적용하여 dict처럼 사용
  - https://github.com/reiinakano/xcessiv/blob/master/xcessiv/models.py

### [ok + beavor]tasks.py를  패키지로 변환하기
1. `app/tasks패키지 + init`을 만들면, 기존 app/tasks.py의 task메서드들이 `app.tasks.xxx`로 인식되지 않게 된다.
    - from app.tasks의 기준이 `app/tasks.py`에서 `app/tasks/__init__.py`로 바뀌기 때문이다.
    ```shell
    Traceback (most recent call last):
    2023-04-24T09:31:41.761245714Z   File "/usr/local/lib/python3.9/site-packages/flask/cli.py", line 218, in locate_app
    2023-04-24T09:31:41.761247314Z     __import__(module_name)
    2023-04-24T09:31:41.761248724Z   File "/app/manage.py", line 1, in <module>
    2023-04-24T09:31:41.761250594Z     from app import app
    2023-04-24T09:31:41.761252044Z   File "/app/app/__init__.py", line 32, in <module>
    2023-04-24T09:31:41.761253684Z     from app import views
    2023-04-24T09:31:41.761255074Z   File "/app/app/views.py", line 10, in <module>
    2023-04-24T09:31:41.761256494Z     from app.tasks import count_words, create_image_set
    2023-04-24T09:31:41.761258174Z ImportError: cannot import name 'count_words' from 'app.tasks' (/app/app/tasks/__init__.py)
    ```

2. 각각의 task메서드들을 xxx.py로 만들고, init에서 `from .xxx import method`로 쩜임포트해서 그대로 연결되게 한다.
    - 각 task의 공통메서드들을 init.py(상위모듈)에 두면 안된다. init.py는 하위모듈들을 .import할 것이기 때문에, 만약 상위모듈에 공통메서드를 두고 하위모듈이 가져다 쓰면, 정의(선언)보다 아래에서 import 해야하는데, 복잡해진다
    - 공통모듈을 commons.py를 만들어 정의하자
      - 일단 `_set_task_progress`만 공통이다.
      - **beavor에 따라 set progress코드가 조금 바뀜.**
        - 추후 [retry도 참고해서 적용](https://github1s.com/busy-beaver-dev/busy-beaver/blob/5e3543f41f189fbe4a50d64e3d6734dc765579b4/busy_beaver/toolbox/rq.py)해주기
    - `mail_sender.py` / `word_counter.py` / `upload_image.py`를 만들어 commons.py를 이용해 정의한다.
   1. `tasks/commons.py`
   ```python
    from rq import get_current_job
    
    from app.models import Task
    
    
    def set_task_progress(progress):
        job = get_current_job()
        if job:
            job.meta['progress'] = progress
            job.save_meta()
    
    
            if progress >= 100:
                task = Task.query.get(job.get_id())
                if task:
                    task.update(status='finished')
    
    ```
    2. tasks.py의 메서드들을 각 모듈로 옮긴다.
       - return에 result dict를 넣어준다. Task.result 에 저장할 수 있도록
       - send_mail모듈도 다 같이 넣어준다.
       - 이 때 Thread로 async치던 것의 이름을 바꿔준다.

3. `app/tasks/__init__.py`에 기존 task모듈들을 .import해서 기존 from app.tasks import task메서드들이 인식되게 한다
    ```python
    from .upload_image import create_image_set
    from .word_counter import count_words
    from .mail_sender import send_async_mail
    ```
   

4. test


##