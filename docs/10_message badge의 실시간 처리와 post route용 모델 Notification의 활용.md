- 참고 github: https://github1s.com/amirine/flask-project/blob/main/app/templates/base.html

### Dynamic badge만들기
1. span badge에 `id`를 부여한다
   - 또한 new_message가 0일 때는 `style="visibility: {%%}"`를 visible/hidden을 걸어 안보이게 한다
   ```html
   <a href="{{ url_for('messages') }}">
   Message
   <span id="message_count"
   class="badge"
   style="visibility: {% if session.new_messages %}visible{% else %}hidden {% endif %};"
   >   {{ session.new_messages }}</span>
   
   </a>
   ```
   

2. jquery를 통해서, badge의 text/css를 동적으로 주입한다
   - bootstrap4에서 css와 jquery+js를 같이 가져온다.
   - js는 body의 끝부분에  위치시킨다.
   1. **static/js/`notification.js`**를 생성하고 function을 작성한다
      ```js
      function set_message_count(n) {
          $('#message_count').text(n);
          $('#message_count').css('visibility', n ? 'visible' : 'hidden');
      }
      ```
   2. send_mail.html의 body끝부분에 해당 js를 import한다
      ```html
      <script type="text/javascript" src="{{ url_for('static', filename='js/notifications.js') }}"></script>
      ```
      
3. **name별 notification를 반환해주는 post전용 route를 생성한다**
   - 