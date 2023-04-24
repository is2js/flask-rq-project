import os
from urllib import request
from bs4 import BeautifulSoup


from rq import get_current_job

from app.email import send_mail
from app.models import Task
from app import app


def _set_task_progress(progress):
    job = get_current_job()
    # 1) 현재의 잡이 존재할때만, progress를 매긴다.
    if job:
        job.meta['progress'] = progress
        job.save_meta()

        ## Task에는 progress가 100일때, complete를 true로 줘야한다
        task = Task.query.get(job.get_id())
        # 특정user의 task가된다면, task의 부모user에 notification으로 알려준다.
        # task.user.add_notification('task_progress', {'task_id': job.get_id(),'progress': progress})
        # progress를 입력하는 순간에, Task데이터에도 해당 progress를 입력한다?
        # class Notification(db.Model):
        #     id = db.Column(db.Integer, primary_key=True)
        #     name = db.Column(db.String(128), index=True)
        #     user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
        #     timestamp = db.Column(db.Float, index=True, default=time)
        #     payload_json = db.Column(db.Text)
        #
        #     def get_data(self):
        #         return json.loads(str(self.payload_json))

        # class User(UserMixin, db.Model):
        #     # ...
        #
        #     def add_notification(self, name, data):
        #         self.notifications.filter_by(name=name).delete()
        #         n = Notification(name=name, payload_json=json.dumps(data), user=self)
        #         db.session.add(n)
        #         return n

        if progress >= 100:
            task.update(status='finished')


def count_words(url):
    print(f'Count words at {url}')
    start = time.time()

    r = request.urlopen(url)  # byte파일들 -> .read() 후 .decode() 필요

    soup = BeautifulSoup(r.read().decode(), "lxml")

    # 1) p태그를 찾아서 .text를 해온 뒤, 단어들처럼 공백으로 연결
    paragraphs = " ".join([p.text for p in soup.find_all("p")])
    # 2) dict에 단어 세기 -> 공백으로 모든 것을 쪼개서 단어로 세기
    word_count = dict()
    for i in paragraphs.split():
        if not i in word_count:
            word_count[i] = 1
        else:
            word_count[i] += 1

    end = time.time()

    time_elapsed = end - start

    print(word_count)
    print(f'Total words: {len(word_count)}')
    print(f'Time elapsed: {time_elapsed}')

    return len(word_count)


#### CREATE IMAGE SET ####
from PIL import Image
import time


def create_image_set(image_dir, image_name):
    start = time.time()

    # 각 최소 px 사이즈를 미리 정해놓는다.
    size_map = dict(
        thumbnail=(35, 35),
        small=(540, 540),
        medium=(768, 768),
        large=(992, 992),
        xl=(1200, 1200),
        xxl=(1400, 1400),
    )

    # file -> image객체를 만든다.
    image = Image.open(os.path.join(image_dir, image_name))

    # 각 save 전 이름 뒤에 "-size"를 적어줘야하기 때문에 ext(확장자)이름을 미리 빼놓는다.
    # image_ext = image_name.split('.')[-1]
    # -> image_ext에는 .png처럼 dot이 맨앞에 포함되어있다.
    image_name, image_ext = os.path.splitext(image_name)

    # 각 image객체를 사이즈별ㄹ .copy()부터 한 뒤, .thumbnail()메서드로 resize 후 .save()까지 한다.
    # thumbnail_image = image.copy()
    # thumbnail_image.thumbnail(size_map['thumbnail'], Image.LANCZOS)  # replace함수
    # thumbnail_image.save(f'{os.path.join(image_dir, image_name)}-thumbnail.{image_ext}',
    #                      optimize=True, quality=95)

    for size_name, size in size_map.items():
        copied_image = image.copy()
        copied_image.thumbnail(size, Image.LANCZOS)  # replace함수
        copied_image.save(f'{os.path.join(image_dir, image_name)}-{size_name}{image_ext}',
                          optimize=True, quality=95)

    end = time.time()

    time_elapsed = end - start

    print(f'Task complete in: {time_elapsed}')

    return True


def example(seconds):
    # task method는 내부에서 rq의 get_current_job()메서드를 이용하여 정의하면 queue에서 작동한다.
    job = get_current_job()

    print('Starting task')
    for i in range(seconds):
        # 1초마다 현재 job의 meta정보(dict)에 progress 정보를 직접 입력한다
        # - 입력한 정보는 connection에 시리얼라이즈 해서 저장해줘야한다.
        job.meta['progress'] = 100.0 * i / seconds
        job.save_meta()

        print(i)
        time.sleep(1)

    # job이 끝나는 시점에는 100으로 입력해준다.(현재 0초부터시작하므로)
    job.meta['progress'] = 100
    job.save_meta()
    print('Task completed')


### send_mail
def send_new_task_mail(email_data):
    """
    email_data는 dict로  attach_img_data와 sync=True만, 각 task마다 직접 지정해주기
    {
        'subject' : '', # 제목
        'recipients' : [], # 받을사람 list
        'template_name' : 'static/template/xxxx', # 메일에 보낼 템플릿 지정
        '템플릿에 쓸 변수' : 데이터, # 템플릿 {{ }} 필요한 변수 ex> 'task': Task(id='123', name='123', description='123'),
        'attachments' : [('posts.json', 'application/json',
                              json.dumps({'posts': data}, indent=4))], # 첨부파일 지정
    }
    """
    # try progress를 0으로 시작하고, finally에 100으로 지정한다.
    # -> 1) 현재의 job을 읽어서 meta에 progress를 넣고
    # -> 2) job_id에 해당하는 Task데이터를 가져와, 100이 넘으면 task.complete를 true로 바꿔준다.
    app.app_context().push()
    try:
        _set_task_progress(0)

        # 첨부될 이미지 지정만 task에서 한다. 그외에는 email_data에 정의되어 있다.
        with app.open_resource(f'static/image/email/rq_project.png', 'rb') as f:
            attach_img_data = f.read()

        _set_task_progress(50)

        send_mail(**email_data, attach_img_data=attach_img_data, sync=True)

        _set_task_progress(80)
    except:
        raise
    finally:
        _set_task_progress(100)


def send_async_mail(email_data):
    """
    email_data는 dict로  attach_img_data와 sync=True만, 각 task마다 직접 지정해주기
    {
        'subject' : '', # 제목
        'recipients' : [], # 받을사람 list
        'template_name' : 'static/template/xxxx', # 메일에 보낼 템플릿 지정
        '템플릿에 쓸 변수' : 데이터, # 템플릿 {{ }} 필요한 변수 ex> 'task': Task(id='123', name='123', description='123'),
        'attachments' : [('posts.json', 'application/json',
                              json.dumps({'posts': data}, indent=4))], # 첨부파일 지정
    }
    """
    app.app_context().push()
    try:
        _set_task_progress(0)
        with app.open_resource(f'static/image/email/rq_project.png', 'rb') as f:
            attach_img_data = f.read()
        _set_task_progress(50)

        send_mail(**email_data, attach_img_data=attach_img_data, sync=True)
        _set_task_progress(80)
    except:
        raise
    finally:
        _set_task_progress(100)