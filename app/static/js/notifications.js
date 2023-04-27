function set_message_count(n) {
    $('#message_count').text(n);
    $('#message_count').css('visibility', n ? 'visible' : 'hidden');
}

function set_task_progress(task_id, progress) {
    $('#' + task_id + '-progress').text(progress);
    $('#' + task_id + '-progress-close').css('visibility', progress === 100 ? 'visible' : 'hidden');
}

/* Function updating unread messages count */
/* $(function(){});은 자동실행되며, 내부에서 10초에 한번씩 자동 호출된다.  */
$(function () {
    var since = 0; // since 0으로 시작해서 달고갔다가, 응답받은 timestamp에 의해 업뎃
    var url = "/notifications"
    setInterval(function () {
        // $.ajax("{{ url_for('notifications') }}?since=" + since).done(
        $.ajax(url + "?since=" + since).done(
            function (notifications) {
                for (var i = 0; i < notifications.length; i++) {
                    // if (notifications[i].name == 'unread_message_count')
                    switch (notifications[i].name) {
                        case 'unread_message_count':
                            set_message_count(notifications[i].data);
                            break;
                        case 'task_progress':
                            // set_task_progress(notifications[i].task_id, notifications[i].progress);
                            set_task_progress(notifications[i].data.task_id, notifications[i].data.progress);
                            break;
                    }
                    since = notifications[i].timestamp;
                }
            }
        );
    }, 5000);
});