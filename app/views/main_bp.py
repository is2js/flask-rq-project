import os
import secrets
import string
import random
import time
from datetime import datetime, timedelta

import markdown2 as markdown2
from flask import request, render_template, flash, session, redirect, url_for, jsonify, Blueprint, current_app as app
from sqlalchemy import asc
from app.extentions import queue
from app.rss_sources import get_current_services, URLService, YoutubeService, BlogService
from app.tasks import count_words, create_image_set, send_async_mail
from app.models import Task, Message, Notification, SourceCategory, Feed
from app.tasks.service import TaskService
from app.utils import logger

main_bp = Blueprint('main', __name__)


def is_htmx_request():
    return 'HX-Request' in request.headers


# route 작성
@main_bp.route('/')
def index():
    # feeds = []
    # for service in get_current_services():
    #     feeds += service.get_feeds()
    #
    # # 통합feeds를 published 정순으로 정렬
    # feeds.sort(key=lambda feed: feed.published)
    # if is_htmx_request:
    #     feeds = URLService().get_feeds(page=2)
    # return f"'HX-Request' in request.headers: {'HX-Request' in request.headers}"
    # return render_template('main/components/feed-list-elements.html', feeds=feeds)

    page = request.args.get('page', 1, type=int)

    if is_htmx_request():
        # feeds = URLService().get_feeds(page=2)
        # return render_template('main/components/feed-list-elements.html', feeds=feeds)
        # feeds = URLService().get_feeds(page=page)
        # time.sleep(0.5)
        # return render_template('main/components/feed-list-elements.html', feeds=feeds, page=page)
        pagination = URLService().get_feeds(page=page)
        time.sleep(0.2)
        return render_template('main/components/feed-list-elements.html',
                               feeds=pagination.items,
                               page=pagination.page,
                               has_next=pagination.has_next
                               )

    # feeds = URLService().get_feeds(page=1)
    # return render_template('main/index.html', feeds=feeds)
    # feeds = URLService().get_feeds(page=page)
    # return render_template('main/index.html', feeds=feeds, page=page)

    pagination = URLService().get_feeds(page=page)

    categories = SourceCategory.get_source_config_active_list()
    # [<app.models.sources.SourceCategory object at 0x7f5de54aa580>, <app.models.sources.SourceCategory object at 0x7f5de54aa5e0>, <app.models.sources.SourceCategory object at 0x7f5de54aa190>]

    return render_template('main/index.html',
                           feeds=pagination.items,
                           page=pagination.page,
                           has_next=pagination.has_next,
                           categories=categories
                           )


@main_bp.route('/feed/<slug>')
def feed_single(slug):

    feed = Feed.get_by_slug(slug)

    categories = SourceCategory.get_source_config_active_list()

    category_name = feed.source.source_category.name.lower() # 비교를 위하 소문자로
    if category_name == 'youtube':
        service = YoutubeService()
    elif category_name == 'blog':
        service = BlogService()
    elif category_name == 'url':
        service = URLService()
    else:
        raise ValueError(f'Invalid category name : {category_name}')

    related_feeds = service.get_feeds()[:5] # 기본 10개 가져오는데 5개만

    return render_template('main/single.html',
                           feed=feed,
                           categories=categories,
                           related_feeds=related_feeds,
                           )


@main_bp.route('/category/<name>')
def feeds_by_category(name):
    category_name = name.lower()  # 비교를 위하 소문자로

    if category_name == 'youtube':
        service = YoutubeService()
    elif category_name == 'blog':
        service = BlogService()
    elif category_name == 'url':
        service = URLService()
    else:
        raise ValueError(f'Invalid category name : {category_name}')

    page = request.args.get('page', 1, type=int)

    if is_htmx_request():
        pagination = service.get_feeds(page=page)
        time.sleep(0.2)
        return render_template('main/components/feed-list-elements-category.html',
                               feeds=pagination.items,
                               page=pagination.page,
                               has_next=pagination.has_next,
                               category_name=name
                               )

    pagination = service.get_feeds(page=page)

    # content_right - category-cloud + footer
    categories = SourceCategory.get_source_config_active_list()
    categories = categories

    return render_template('main/category.html',
                           feeds=pagination.items,
                           page=pagination.page,
                           has_next=pagination.has_next,
                           categories=categories,
                           category_name=name,
                           )


@main_bp.route('/word-counter', methods=['GET', 'POST'])
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


@main_bp.route('/upload-image', methods=['GET', 'POST'])
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


@main_bp.route('/image/<image_dir_name>/<image_file_name>')
def view_image(image_dir_name, image_file_name):
    return render_template('view_image.html', image_dir_name=image_dir_name, image_file_name=image_file_name)


@main_bp.route('/launch-task/<name>/<args>/<description>')
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


@main_bp.route('/task/<name>')
def get_task(name):
    # task = Task.query.filter_by(name=name, status=False).first()
    task = Task.query.filter(
        Task.name == name,
        Task.status.in_(['queued', 'running'])
    ).first()
    return 'get_task'


@main_bp.route('/tasks-in-progress')
def tasks_in_progress():
    tasks = Task.query.filter(
        Task.status.in_(['queued', 'running'])
    ).all()
    print(tasks)
    return 'tasks_in_progress'


#### TEST
@main_bp.route('/send-new-task-mail')
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


@main_bp.route('/send-mail', methods=['GET', 'POST'])
def send_mail():
    # session을 통해 캐슁된 데이터가 있으면, GET화면에서 같이 가지고 간다.
    cache = {
        'recipient': session.get('recipient', ''),
        'template_name': session.get('template_name', ''),
    }

    if request.method == 'POST':
        # return str(request.form.to_dict())
        # {'recipient': 'tingstyle1@gmail.com', 'template_name': 'email/welcome',
        # 1) 'scheduled_time': ''
        # 2) 'is_scheduled': '1', 'scheduled_time': '2023-05-03 18:21:32'

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

            #### is_scheduled 여부에 따라, timer task인지 일반 task인지 구분한다
            # 1) 'scheduled_time': ''
            # 2) 'is_scheduled': '1', 'scheduled_time': '2023-05-03 18:21:32'
            is_scheduled = request.form.get('is_scheduled')
            if not is_scheduled:
                s = TaskService()
                s.enqueue_task(send_async_mail, email_data, description=f'{template_name}을 이용하여 메일 전송')
                flash(f'[{recipient}]에게 [{template_name} ]템플릿 메일을 전송하였습니다.', 'success')
            else:
                # str -> datetime 변환
                # - 시간을 입력안한 경우의 예외처리는, 여기서 format이 안맞아서 전송 실패한다.
                scheduled_time_str = request.form.get('scheduled_time', None)
                try:
                    scheduled_time = datetime.strptime(scheduled_time_str, '%Y-%m-%d %H:%M:%S')
                    scheduled_time = scheduled_time + timedelta(minutes=1)
                    # scheduled_timestamp = scheduled_time.timestamp()
                except Exception as e:
                    logger.debug(f'시간 형식이 올바르지 않습니다.')
                    raise ValueError(f'시간 형식이 올바르지 않습니다.')

                # high queue를 사용
                s = TaskService(queue_name='high')
                # s.reserve_task(scheduled_time, print, 'abcde', description='설명')
                s.reserve_task(scheduled_time, send_async_mail, email_data, description=f'{template_name}을 이용하여 메일 전송')

                flash(f'[{recipient}]에게 [{template_name} ]템플릿 메일 전송을 예약({str(scheduled_time)})하였습니다.', 'success')

        except ValueError as e:
            logger.error(str(e))
            flash(f'{str(e)}', 'danger')

        except Exception as e:
            logger.error(str(e))
            flash(f'[{recipient}]에게 [{template_name} ]템플릿 메일을 전송을 실패하였습니다.', 'danger')

        return redirect(url_for('main.send_mail'))

    return render_template('send_mail.html', **cache)


# task 취소
@main_bp.route('/task_cancel/<task_id>')
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
    return redirect(url_for('main.send_mail'))


@main_bp.route('/task_reserve/<task_id>')
def cancel_reserve(task_id):
    s = TaskService('high')
    task = s.cancel_reserve(task_id)

    if task:
        flash(f'예약 Task#{task.id} {task.name}가 취소되었습니다.', 'success')
    else:
        flash(f'예약 Task의 취소에 실패했습니다.', 'danger')

    # 나중에는 직접으로 돌아가도록 수정
    return redirect(url_for('main.send_mail'))


# 미들웨어 함수
@main_bp.before_request
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


@main_bp.route('/change_username')
def change_username():
    # 해당username의 저장된 데이터 Message를 삭제한다.
    Message.query.filter_by(recipient=session.get('username')).delete()

    #### 여러개를 조회할 경우 .delete()가 안먹히고, count만 반환된다.
    # -> 순회하면서 삭제하도록 변경
    # targets = Notification.query.filter(
    targets = Notification.query.filter_by(
        username=session.get('username')
        # Notification.query.filter_by(
        # Notification.username.like(f"{session['username']}%"),
    ).all()
    for t in targets:
        t.delete()

    # 처리할 거 다하고 session.clear()를 써도 된다.
    session.clear()

    # return redirect(url_for('main.send_mail'))
    # return redirect(request.url) # 이것은 change_user로 redict
    # 처리후 이전페이지 redirect는 request.referrer를 쓰면 된다.
    return redirect(request.referrer)


@main_bp.route('/messages')
def messages():
    # 1. 마지막 읽은 시간 update -> new_message가 0으로 뽑힐 것이다.
    session['last_message_read_time'] = datetime.now()

    # 1-2.  noticiation초기화 추가 -> notification의 'unread_message_count'의 payload {'data': n ===> 0 }으로 업뎃시켜줘야한다.
    # => Notification create() 내부에선 기존 데이터를 삭제하고, 생성하게 된다.
    Notification.create(username=session.get('username'), name='unread_message_count', data=0)

    # 2. 현재 session username으로 메세지 검색
    messages = Message.get_messages_of(session)

    return render_template('messages.html', messages=messages)


@main_bp.route('/notifications')
def notifications():
    since = request.args.get('since', 0.0, type=float)

    notifications = Notification.query.filter(
        Notification.username == session['username'],
        # Notification.username.like(f"{session['username']}%"),
        Notification.created_at > since
    ).order_by(asc(Notification.created_at)).all()

    # return jsonify([{
    #     'name': n.name,
    #     'data': n.payload['data'],
    #     'timestamp': n.timestamp
    # } for n in notifications])

    # logger.debug([ n.to_dict() for n in notifications])

    return jsonify([n.to_dict() for n in notifications])


@main_bp.route('/rss', methods=['GET', 'POST'])
def rss():
    current_services = get_current_services()

    markdown_text = ''
    for service in current_services:
        markdown_text += service.render()

    markdown_html = markdown2.markdown(markdown_text)

    return render_template('rss.html', markdown_html=markdown_html)
