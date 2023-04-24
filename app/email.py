from threading import Thread

from flask import render_template
from flask_mail import Message
from . import mail, app


def send_mail(subject, recipients, template_name,
              sender='rq프로젝트', attach_img_data=None, attachments=None, sync=False, **kwargs):
    # 1) Message객체 생성
    msg = Message(subject=subject, sender=sender, recipients=recipients)
    # msg.body, msg.html = text_body, html_body
    msg.body = render_template(template_name + '.txt', **kwargs)
    msg.html = render_template(template_name + '.html', **kwargs)

    # 2) 이미지 inline 첨부 및 img태그로 변환
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
        Thread(target=send_async_mail, args=(msg,)).start()


def send_async_mail(msg):
    with app.app_context():
        mail.send(msg)
