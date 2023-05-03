- Timer Task 참고: https://github1s.com/staugur/IncetOps/blob/81d73e45c758d8e16c90d91666b138363553b68c/src/plugins/IncetOps/libs/service.py#L239-L240

### view
1. `jquery-datetimepicker` css 및 `moment -> jquery-datetimepicker` js를 추가한 뒤, form에 예약하기 클릭시 시간을 선택하도록 추가한다
   ```html
    <!-- 추가 스크립트 -->
    <!-- DatetimePicker CSS 파일 -->
    <link rel="stylesheet"
          href="https://cdnjs.cloudflare.com/ajax/libs/jquery-datetimepicker/2.5.20/jquery.datetimepicker.min.css">

   //
   <!-- 추가 스크립트( moment -> picker -> boostrap)   -->
   <!-- Moment JS 파일 -->
   <script src="https://cdnjs.cloudflare.com/ajax/libs/moment.js/2.29.1/moment.min.js"></script>
   <!-- DatetimePicker JS 파일 -->
   <script src="https://cdnjs.cloudflare.com/ajax/libs/jquery-datetimepicker/2.5.20/jquery.datetimepicker.full.min.js"></script>
   ```
   
   ```html
   <div class="form-group mb-3">
       <div class="form-check">
           <input class="form-check-input" type="checkbox" name="is_scheduled" value="1">
           <label class="form-check-label" for="is_scheduled">
               예약하기
           </label>
       </div>
   </div>
   <div class="form-group mb-3" id="scheduled_time_field" style="display: none;">
       <label for="scheduled_time">예약 시간 선택:</label>
       <div class="input-group date" id="datetimepicker" data-target-input="nearest">
           <input type="text" name="scheduled_time" class="form-control datetimepicker-input"
                  data-target="#datetimepicker"/>
           <div class="input-group-append" data-target="#datetimepicker"
                data-toggle="datetimepicker">
               <div class="input-group-text"><i class="fa fa-calendar"></i></div>
           </div>
       </div>
   </div>
   ```
   ```html
   <!-- 추가 스크립트 2( moment -> picker)   -->
   <!-- Moment JS 파일 -->
   <script src="https://cdnjs.cloudflare.com/ajax/libs/moment.js/2.29.1/moment.min.js"></script>
   <!-- DatetimePicker JS 파일 -->
   <script src="https://cdnjs.cloudflare.com/ajax/libs/jquery-datetimepicker/2.5.20/jquery.datetimepicker.full.min.js"></script>
   
   <script>
       $(function () {
           // datetimepicker 초기화
           $('#datetimepicker').datetimepicker({
               format: 'YYYY-MM-DD HH:mm:ss',
               sideBySide: true,
               minDate: moment(),
           });
   
           // datetimepicker에서 선택된 시간을 input창에 넣어주기
           $('#datetimepicker').on('change.datetimepicker', function (e) {
               $('input[name="scheduled_time"]').val(moment(e.date).format('YYYY-MM-DD HH:mm:ss'));
           });
   
           // is_scheduled 체크박스 이벤트 처리
           $('input[name="is_scheduled"]').change(function () {
               var is_scheduled = $(this).is(':checked');
               if (is_scheduled) {
                   $('#scheduled_time_field').show();
               } else {
                   $('#scheduled_time_field').hide();
               }
           });
   
       });
   </script>
   ```
   

### route
1. request.form.to_dict()로 어떻게 넘어오는지 확인한다.
   - **checkbox는 클릭된 상태일 때만 `value=""`의 값이 넘어오고, 체크안됬으면 key도 안넘어온다.**
   - **datetime은 문자열로 넘어온다**
   ```python
   @app.route('/send-mail', methods=['GET', 'POST'])
   def send_mail():
       # session을 통해 캐슁된 데이터가 있으면, GET화면에서 같이 가지고 간다.
       cache = {
           'recipient': session.get('recipient', ''),
           'template_name': session.get('template_name', ''),
       }
   
   
       if request.method == 'POST':
           return str(request.form.to_dict())
           # {'recipient': 'tingstyle1@gmail.com', 'template_name': 'email/welcome',
           # 1) 'scheduled_time': ''
           # 2) 'is_scheduled': '1', 'scheduled_time': '2023-05-03 18:21:32'
   ```
   
2. **check필드의 존재여부에 따라, 일반task vs timer task가 결정된다.**
   ```python
   try:
     #### is_scheduled 여부에 따라, timer task인지 일반 task인지 구분한다
      # 1) 'scheduled_time': ''
      # 2) 'is_scheduled': '1', 'scheduled_time': '2023-05-03 18:21:32'
      is_scheduled = request.form.get('is_scheduled')
      if not is_scheduled:
          # s = TaskService()
          # s.enqueue_task(send_async_mail, email_data, description=f'{template_name}을 이용하여 메일 전송')
          flash(f'[{recipient}]에게 [{template_name} ]템플릿 메일을 전송하였습니다.', 'success')
      else:
          scheduled_time_str = request.form.get('scheduled_time')
          # 시간을 입력안한 경우의 예외처리는, 여기서 format이 안맞아서 전송 실패한다.
          scheduled_time = datetime.strptime(scheduled_time_str, '%Y-%m-%d %H:%M:%S')
   
          flash(f'[{recipient}]에게 [{template_name} ]템플릿 메일 전송을 예약({scheduled_time_str})하였습니다.', 'success')
   ```
   

### Docker파일에 TZ 한국으로 설정 + rq worker queue추가 하기
- 각 Dockerfile에 설정
   ```dockerfile
   # 환경변수 설정
   ENV TZ=Asia/Seoul
   
   # 시간대 설정
   RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
   ```
- `docker-compose build --no-cache`
- terminal에서 `date`명령어로 KST 확인
   ```shell
   root@9b92e489a538:/app# date
   Wed May  3 19:35:54 KST 2023
   ```
  


2. rq worker command에  추가 queue 반영하기
    - docker-compose command에 `rq worker`(default queue생략) -> `rq worker default high low` 3개의 queue를 띄운다
    ```dockerfile
    command: bash -c "
      rq worker default high low -u 'redis://$REDIS_HOST:$REDIS_PORT' --with-scheduler
      "
    ```
    ```shell
    00:03:29 *** Listening on default, high, low...
    2023-05-03T15:03:29.505146571Z 00:03:29 Scheduler for low,default,high started with PID 8
    2023-05-03T15:03:29.505620401Z 00:03:29 Cleaning registries for queue: default
    2023-05-03T15:03:29.506650537Z 00:03:29 Cleaning registries for queue: high
    2023-05-03T15:03:29.507372223Z 00:03:29 Cleaning registries for queue: low
    ```
   

### route에서 print를 task메서드로 timer task 수행하기

1. 현재 front에서 현재시각만 datetime format으로 넘어오므로 `timedelta를 이용해서 30초`뒤에 수행하게 할 예정
2. TaskService()의 queue_name을 `high`로 주고 timer task를 수행해보자.
   - enqueue_at(datetime, )
   - enqueue_in(timedelta, )로 작동하며 **각각은 args를 인자로 안받고 연결해서 입력해야한다.**
   - **현재 queue에 예정되어있는지 확인하려면 `queue.scheduled_job_registry`에 반환된 `job`이 `in`되어있는지 확인하면 된다.**
   - db처리 포함 래핑메서드가 없는 상황이므로 service객체.queue를 사용해서 처리한다
   ```python
    is_scheduled = request.form.get('is_scheduled')
    if not is_scheduled:
        s = TaskService()
        s.enqueue_task(send_async_mail, email_data, description=f'{template_name}을 이용하여 메일 전송')
        flash(f'[{recipient}]에게 [{template_name} ]템플릿 메일을 전송하였습니다.', 'success')
    else:
        # high queue를 사용
        s = TaskService(queue_name='high')
    
        # str -> datetime 변환
        # - 시간을 입력안한 경우의 예외처리는, 여기서 format이 안맞아서 전송 실패한다.
        scheduled_time_str = request.form.get('scheduled_time')
        scheduled_time = datetime.strptime(scheduled_time_str, '%Y-%m-%d %H:%M:%S')
        scheduled_time = scheduled_time + timedelta(seconds=30)
    
        job = s.asyncQueue.enqueue_at(
            scheduled_time,  # datetime
            print,  # func
            "abcdef",  # func - args
    )
    ```
    - schedule처리가 되어있는지와 들어간 job에 대한 정보를 logger로 찍어본다
    ```python
    s.logger.info(f"job.to_dict(): {job.to_dict()}")
    s.logger.info(f"job in s.asyncQueue.scheduled_job_registry : {job in s.asyncQueue.scheduled_job_registry}")
    ```
3. front에서 예약을 누르면 **42분 35초에 예약되었다고 나온다.**
   - `[tingstyle1@gmail.com]에게 [email/welcome ]템플릿 메일 전송을 예약(2023-05-04 01:42:35)하였습니다.` 
   - logger에는 아래와 같이 찍힌다 **42분 50초에 생성됨.**
   ```shell
   job.to_dict(): {'created_at': '2023-05-03T16:42:50.793259Z', 'data': b'x\x9ck`\x9d\xaa\xcc\x00\x01\x1a=|I\xa5\x999%\x99y\xc5z\x05E\x99y%S\xfcz\xd8\x12\x93\x92SR\xd3\xa6\xb4N\xa9\x9dR2E\x0f\x00+3\x0f\x82', 'success_callback_name': '', 'failure_callback_name': '', 'started_at': '', 'ended_at': '', 'last_heartbeat': '', 'worker_name': '', 'origin': 'high', 'description': "builtins.print('abcdef')", 'timeout': 180, 'status': <JobStatus.SCHEDULED: 'scheduled'>}
   job in s.asyncQueue.scheduled_job_registry : True
   ```
   - rq worker log를 보면 **43분 05초(15초 걸림)에 수행된다.**
   ```
   01:43:05 high: builtins.print('abcdef') (c793c28e-7bf0-4dd0-a0fc-8ff533580982)
    2023-05-03T16:43:05.512647620Z abcdef
    2023-05-03T16:43:05.513797095Z 01:43:05 high: Job OK (c793c28e-7bf0-4dd0-a0fc-8ff533580982)
   ```
   - view에서 전송시간(`42:35`) vs route에서 생성시간(42:50) vs 수행시작시작(`43:05`)



### Task 모델 변경하기
1. 일단 status에 `scheduled`를 추가해야할 것이다.
   - enqueue_task 래핑메서드에선 `queued`를 status로 메겼지만, 
   - **추가될 schedule_task 래핑메서드에선 `scheduled`로 시작하게 한다**
2. 