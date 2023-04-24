import os
import secrets

from flask import request, render_template, flash, session, redirect, url_for
from sqlalchemy import desc

from app import app
from app import r
from app import queue
from app.tasks import count_words, create_image_set
from app.models import Task


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
    task = Task(id=rq_job.get_id(), name=name, description=description)
    task.save()
    return 'launch_task'


@app.route('/task/<name>')
def get_task(name):
    # task = Task.query.filter_by(name=name, status=False).first()
    task = Task.query.filter(
        Task.name == name,
        Task.status.in_(['queued', 'running'])
    ).first()
    print(task)
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
        if template_name == 'email/tasks':
            email_data['subject'] = 'rq프로젝트 완료된 최근 5개 Tasks 정보입니다.'
            # 템플릿별 필요변수
            # email_data['tasks'] = Task.query.order_by(desc(Task.updated_at)).limit(5).all()
            email_data['tasks'] = Task.query.filter(
                Task.status == 'finished'
            ).order_by(desc(Task.updated_at)).limit(5).all()
        elif template_name == 'email/welcome':
            email_data['subject'] = '안녕하세요 rq프로젝트 서비스 소개입니다.'
            # 템플릿별 필요변수
        elif template_name == 'email/tasks_in_progress':
            email_data['subject'] = 'rq프로젝트 진행 중인 Tasks 정보입니다.'
            # 템플릿별 필요변수
            # email_data['tasks'] = Task.query.filter_by(complete=False).all()
            email_data['tasks'] = Task.query.filter(
                Task.status.in_(['queued', 'running'])
            ).all()

        #### enqueue + Task데이터 저장
        try:
            rq_job = queue.enqueue('app.tasks.' + 'send_async_mail', email_data)
            task = Task(id=rq_job.get_id(), name='send_mail', description=f'{template_name}으로 메일 전송')
            task.save()

            flash(f'[{recipient}]에게 [{template_name} ]템플릿 메일을 전송하였습니다.', 'succes')
        except:
            flash(f'[{recipient}]에게 [{template_name} ]템플릿 메일을 전송을 실패하였습니다', 'danger')

        return redirect(url_for('send_mail'))

    return render_template('send_mail.html', **cache)
