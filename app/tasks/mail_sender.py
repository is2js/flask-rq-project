import time
from threading import Thread

from flask_mail import Message
from app.config import Config
from .decorators import background_task, set_task_progress

from ..extentions import mail
from flask import render_template
from app import create_app

@background_task
def send_async_mail(email_data):
    """
    email_data는 dict로  attach_img_data와 sync=True만, 각 task마다 직접 지정해주기
    {
        'subject' : '', # 제목
        'recipients' : [], # 받을사람 list
        'template_name' : 'email/welcome' or 'email/tasks' , # 메일에 보낼 템플릿 지정( templates폴더까진 자동으로 진행됨)
        '템플릿에 쓸 변수' : 데이터, # 템플릿 {{ }} 필요한 변수 ex> 'task': Task(id='123', name='123', description='123'),
        'attachments' : [('posts.json', 'application/json',
                              json.dumps({'posts': data}, indent=4))], # 첨부파일 지정
    }
    """
    # flask-mail 사용 때문에 추가
    app = create_app()
    app.app_context().push()
    ## -> 데코레이터로 이동
    # try:
    with app.open_resource(f'static/image/email/rq_project.png', 'rb') as f:
        attach_img_data = f.read()

    set_task_progress(50)

    # time.sleep(10)

    send_mail(**email_data, attach_img_data=attach_img_data, sync=True)

    result = {'result': 'success'}
    return result



def send_mail(subject, recipients, template_name,
              sender=Config.MAIL_SENDER, attach_img_data=None, attachments=None, sync=False, **kwargs):
    # 1) Message객체 생성
    msg = Message(subject=Config.MAIL_SUBJECT_PREFIX + subject, sender=sender, recipients=recipients)
    # msg.body, msg.html = text_body, html_body
    msg.body = render_template(template_name + '.txt', **kwargs)
    msg.html = render_template(template_name + '.html', **kwargs)

    # 2) [로고 이미지] inline 첨부 및 img태그로 변환
    if attach_img_data:
        msg.attach(
            filename="image.png",
            content_type="image/png",
            data=attach_img_data,
            disposition='inline',
            headers=[['Content-ID', '<image>']]
        )
        msg.html += '<p><img src="cid:image" height="200"></p>'

    # 3) 첨부파일이 있으면, 순회하면서 msg.attach()에 넣어준다.
    if attachments:
        for attachment in attachments:
            msg.attach(*attachment)

    # 3) 동기로 하고 싶을때만, 바로 발송한다.
    if sync:
        mail.send(msg)
    # 4) 보통 비동기로 호출되는데, Thread()로 호출해준다.
    else:
        # Thread(target=mail.send, args=(msg, )).start()
        # Thread는 app_context를 안타고 있는 상황이므로, 따로 메서드를 빼서, app_context내에서 실행되어야한다
        # -> 실행안되는 상태에선 current_app을 사용 못하므로, app객체를 init(.)에서 가져와야한다.
        Thread(target=send_thread_async_mail, args=(msg,)).start()


def send_thread_async_mail(msg):
    with app.app_context():
        mail.send(msg)
