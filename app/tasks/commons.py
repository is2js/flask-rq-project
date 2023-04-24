from functools import wraps

from rq import get_current_job

from app.models import Task


def set_task_progress(progress):
    job = get_current_job()
    if job:
        job.meta['progress'] = progress
        job.save_meta()

        # if progress >= 100:
        #     task = Task.query.get(job.get_id())
        #     if task:
        #         task.update(status='finished')


## DB처리 + 예외처리까지 하는 데코레이터
def background_task(f):
    @wraps(f)
    def task_handler(*args, **kwargs):
        #### TAKS 실행시 '생성후 enqueue상태` -> `running`상태
        # 1-1) Task실행시, 해당id로 Task Db데이터부터 가져온다.
        task = Task.query.get(get_current_job().get_id())
        # 1-2) task가 실행되면, Task DB에서 running상태로 업데이트한다
        task.update(status='running')
        # 1-3) 필요시 logger 생성
        # 1-4) job에 progress 정보 넣어주기
        set_task_progress(0)

        #### TASK메서드 수행 in try/except
        # 2-1) 실패시 TASK DB데이터에 exception기록
        # => task내부 try/except는 삭제
        try:
            result = f(*args, **kwargs)

            #### TASK 정상수행 완료시 result를 TASK DB에 입력
            # - dict타입아니면, result key에 담아서 입력
            if not isinstance(result, dict):
                result = dict(result=result)

            task.update(
                status='finished',
                result=result
            )

        except Exception as e:
            task.update(
                failed=True,
                status='finished',
                log=f'Failed for: ' + str(e)
            )
        finally:
            set_task_progress(100)

    return task_handler
