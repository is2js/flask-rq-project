import os
import secrets
import string
import random
from datetime import datetime

from flask import request, render_template, flash, session, redirect, url_for, jsonify
from sqlalchemy import desc, asc

from app import app
from app import r
from app import queue
from app.tasks import count_words, create_image_set, enqueue_task, send_async_mail
from app.models import Task, Message, Notification
from app.tasks.service import TaskService
from app.utils import logger


# route 작성
@app.route('/')
def index():
    return "Hello world222"


@app.route('/word-counter', methods=['GET', 'POST'])
def word_counter():
    # 1. q.jobs로 현재의 queue의 jobs를 가져올 수 있다. -> jinja에 사용한다
    # - viewㅇ선 job.args / job.id / job.status / job.created_at.strftime() / job.enqueued_at.strftime() 을 사용한다
    jobs = queue.jobs
    # 2. 있을때만 채워지는 message는 None으로 초기화 -> if문에서 채우기 전략
    message = None
    # 3. get form이 날라오는 것은 request.method == 'POST'로 잡는게 아니라
    #    if request.args:로 잡는다
    if request.args:
        url = request.args.get('url')

        task = queue.enqueue(count_words, url)
        # 넣어주고 난 뒤 의 queue속 jobs
        jobs = queue.jobs
        # q 속 전체 task의 갯수?
        q_len = len(queue)
        # message에는 넣은 Task에 대한 정보를 넣어준다.
        message = f'Task queued at {task.enqueued_at.strftime("%a %d %b %Y %H:%M:%S")}. {q_len} jobs queued'

    return render_template('word_counter.html', message=message, jobs=jobs)


@app.route('/upload-image', methods=['GET', 'POST'])
def upload_image():
    view_url = None

    if request.method == 'POST':
        # form이 넘어오면 처리한다.
        image = request.files['image']
        # 개별 디렉토리이름은 secrets 패키지로 익명으로 만든다.
        image_dir_name = secrets.token_hex(16)

        # 폴더 만들기 -> 여러 경로의 폴더를 이어서 만들 땐, os.makedirs( , exist_ok=True)로 한다
        image_dir_path = app.config['UPLOAD_FOLDER'].joinpath(image_dir_name)
        if not os.path.exists(image_dir_path):
            # os.mkdir(image_dir_path)
            os.makedirs(image_dir_path, exist_ok=True)

        # 파일객체(image)를 일단 local에 save한다.
        image.save(os.path.join(image_dir_path, image.filename))

        # queue에 폴더와 파일이름을 따로 넣어준다.
        queue.enqueue(create_image_set, image_dir_path, image.filename)

        # queue에 넘겼으면, flash를 띄워서 마무리한다
        flash('Image uploaded and sent for resizing', 'success')

        # view_url에는 확장자를 뺀 이미지 name만 들어가게 해야한다.
        image_file_name, image_ext = os.path.splitext(image.filename)
        view_url = f'/image/{image_dir_name}/{image_file_name}'

    return render_template('upload_image.html', view_url=view_url)


@app.route('/image/<image_dir_name>/<image_file_name>')
def view_image(image_dir_name, image_file_name):
    return render_template('view_image.html', image_dir_name=image_dir_name, image_file_name=image_file_name)


@app.route('/launch-task/<name>/<args>/<description>')
def launch_task(name, args, description):
    # 1) 특정 task를 인자를 넣어 enqueue한다
    # -> enqueue해야 fetch로 받아올 job의 id를 받아온다.
    rq_job = queue.enqueue('app.tasks.' + name, args)
    # 2) 해당 task를 설명을 넣어 db데이터를 생성한다
    #
    # task = Task(id=rq_job.get_id(), name=name, description=description)
    # task.save()
    task = Task.create(session, name, description)
    return 'launch_task'


@app.route('/task/<name>')
def get_task(name):
    # task = Task.query.filter_by(name=name, status=False).first()
    task = Task.query.filter(
        Task.name == name,
        Task.status.in_(['queued', 'running'])
    ).first()
    return 'get_task'


@app.route('/tasks-in-progress')
def tasks_in_progress():
    tasks = Task.query.filter(
        Task.status.in_(['queued', 'running'])
    ).all()
    print(tasks)
    return 'tasks_in_progress'


#### TEST
@app.route('/send-new-task-mail')
def send_new_task_mail():
    # queue에 넣어야 id가 발급되는데, enqueue시 Task의 정보가 필요함.
    task = Task(name='form.name', description='form.desc')

    # form으로 넘어올 임시 데이터
    email_data = {
        'subject': f'[Task]{task.name} 이 등록되었습니다.',  # 제목
        'recipients': ['tingstyle1@gmail.com'],  # 받을사람 list
        'template_name': 'email/new_task',  # 메일에 보낼 템플릿 지정
        'task': task,  # 템플릿 사용 변수
    }

    # 1) queue에 넣고
    rq_job = queue.enqueue('app.tasks.' + 'send_new_task_mail', email_data)
    # 2) job_id로 task를 만든다.
    task.id = rq_job.get_id()
    task.save()

    return "success"


@app.route('/send-mail', methods=['GET', 'POST'])
def send_mail():
    # session을 통해 캐슁된 데이터가 있으면, GET화면에서 같이 가지고 간다.
    cache = {
        'recipient': session.get('recipient', ''),
        'template_name': session.get('template_name', ''),
    }

    if request.method == 'POST':
        # POST로 form입력을 받으면, 꺼낼 때 session에 caching도 동시에 한다
        recipient = session['recipient'] = request.form['recipient']
        template_name = session['template_name'] = request.form['template_name']

        email_data = dict()
        email_data['recipients'] = [recipient]
        email_data['template_name'] = template_name
        file = request.files['attachment']
        if file:
            # 첨부파일은 attachments의 tuple list로 보내야한다.
            email_data['attachments'] = [(file.filename, file.mimetype, file.read())]

        ### TEMPLATE 종류에 따라 다르게 호출
        if template_name == 'email/welcome':
            email_data['subject'] = '안녕하세요 rq프로젝트 서비스 소개입니다.'
            # 템플릿별 필요변수 -> X
        elif template_name == 'email/tasks_finished':
            email_data['subject'] = 'rq프로젝트 완료된 최근 5개 Tasks 정보입니다.'
            # 템플릿별 필요변수
            # email_data['tasks'] = Task.query.order_by(desc(Task.updated_at)).limit(5).all()
            # email_data['tasks'] = Task.query.filter(
            #     Task.status == 'finished'
            # ).order_by(desc(Task.updated_at)).limit(5).all()
            email_data['tasks'] = Task.get_finished_list_of(session, limit=5)
        elif template_name == 'email/tasks_in_progress':
            email_data['subject'] = 'rq프로젝트 진행 중인 Tasks 정보입니다.'
            # 템플릿별 필요변수
            # email_data['tasks'] = Task.query.filter_by(complete=False).all()
            # email_data['tasks'] = Task.query.filter(
            #     Task.status.in_(['queued', 'running'])
            # ).all()
            email_data['tasks'] = Task.get_unfinished_list_of(session, limit=None)

        elif template_name == 'email/tasks':
            email_data['subject'] = 'rq프로젝트 전체 Tasks 정보입니다.'
            # 템플릿별 필요변수
            email_data['tasks'] = Task.get_list_of(session)

        #### enqueue + Task데이터 저장 -> wrapper로 한번에
        try:
            # rq_job = queue.enqueue('app.tasks.' + 'send_async_mail', email_data)
            # task = Task(id=rq_job.get_id(), name='send_mail', description=f'{template_name}으로 메일 전송')
            # task.save()

            # enqueue_task(send_async_mail, email_data, description=f'{template_name}을 이용하여 메일 전송')
            s = TaskService()
            s.enqueue_task(send_async_mail, email_data, description=f'{template_name}을 이용하여 메일 전송')

            flash(f'[{recipient}]에게 [{template_name} ]템플릿 메일을 전송하였습니다.', 'success')
        except Exception as e:
            logger.error(str(e))
            flash(f'[{recipient}]에게 [{template_name} ]템플릿 메일을 전송을 실패하였습니다', 'danger')

        return redirect(url_for('send_mail'))

    return render_template('send_mail.html', **cache)

# task 취소
@app.route('/task_cancel/<task_id>')
def cancel_task(task_id):
    # 어차피 db와 연계되어야하기 때문에, job만 불러와 취소가 아니라, Task를 불러와 메서드로 처리한다.

    # task = Task.query.get(int(task_id))
    # result = task.cancel_rq_job()
    # if result:
    s = TaskService()
    task = s.cancel_task(task_id)


    if task:
        flash(f'Task#{task.id} {task.name}가 취소되었습니다.', 'success')
    else:
        flash(f'Task가 이미 완료된 상태라 취소에 실패했습니다.', 'danger')

    # 나중에는 직접으로 돌아가도록 수정
    return redirect(url_for('send_mail'))



# 미들웨어 함수
@app.before_request
def before_request():
    # 2. 쿼리스트링에 지정된 username이 있다면, 그녀석으로 username사용
    if request.args.get('username'):
        session['username'] = request.args.get('username')

    # 1. session에 username이 없을 경우, 랜덤하게 만들어서 박아주기
    # -> session에 넣으면 따로 객체를 안넘겨줘도 template에서 {{session.username}}을 사용할 수 있다.
    if not session.get('username'):
        username = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))
        session['username'] = username

    # 3. 해당 username의 새 메세지의 갯수
    session['new_messages'] = Message.new_messages_of(session)

    # 4. 해당 username의 진행중인 task
    # session['tasks_in_progress'] = [ task.to_dict() for task in Task.get_list_of(session)]
    session['tasks_in_progress'] = [task.to_dict() for task in Task.get_unfinished_list_of(session)]


@app.route('/change_username')
def change_username():
    # 해당username의 저장된 데이터 Message를 삭제한다.
    Message.query.filter_by(recipient=session.get('username')).delete()

    #### 여러개를 조회할 경우 .delete()가 안먹히고, count만 반환된다.
    # -> 순회하면서 삭제하도록 변경
    targets = Notification.query.filter(
        # Notification.query.filter_by(
        # username=session.get('username')
        Notification.username.like(f"{session['username']}%"),
    ).all()
    for t in targets:
        t.delete()

    # 처리할 거 다하고 session.clear()를 써도 된다.
    session.clear()

    return redirect(url_for('send_mail'))


@app.route('/messages')
def messages():
    # 1. 마지막 읽은 시간 update -> new_message가 0으로 뽑힐 것이다.
    session['last_message_read_time'] = datetime.now()

    # 1-2.  noticiation초기화 추가 -> notification의 'unread_message_count'의 payload {'data': n ===> 0 }으로 업뎃시켜줘야한다.
    # => Notification create() 내부에선 기존 데이터를 삭제하고, 생성하게 된다.
    Notification.create(username=session.get('username'), name='unread_message_count', data=0)

    # 2. 현재 session username으로 메세지 검색
    messages = Message.get_messages_of(session)

    return render_template('messages.html', messages=messages)


@app.route('/notifications')
def notifications():
    since = request.args.get('since', 0.0, type=float)

    notifications = Notification.query.filter(
        # Notification.username == session['username'],
        Notification.username.like(f"{session['username']}%"),
        Notification.created_at > since
    ).order_by(asc(Notification.created_at)).all()

    return jsonify([{
        'name': n.name,
        'data': n.payload['data'],
        'timestamp': n.timestamp
    } for n in notifications])


