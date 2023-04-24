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
