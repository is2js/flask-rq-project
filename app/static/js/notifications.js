function set_message_count(n) {
    $('#message_count').text(n);
    $('#message_count').css('visibility', n ? 'visible' : 'hidden');
}

function set_task_progress(task_id, progress) {
    $('#' + task_id + '-progress').text(progress);
    $('#' + task_id + '-progress-close').css('visibility', progress === 100 ? 'visible' : 'hidden');
    $('#' + task_id + '-progress-cancel').css('visibility', progress === 100 ? 'hidden' : 'visible');
}

function set_task_remain(task_id, task_reserved_at) {
    $('#' + task_id + '-remain').text(task_reserved_at);
    $('#' + task_id + '-reserve-close').css('visibility', task_reserved_at === ' 남음' ? 'visible' : 'hidden');
    $('#' + task_id + '-reserve-cancel').css('visibility', task_reserved_at === ' 남음' ? 'hidden' : 'visible');
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
                console.log("notifications", notifications)
                for (var i = 0; i < notifications.length; i++) {
                    // console.log(notifications[i].data)
                    // if (notifications[i].name == 'unread_message_count')
                    switch (notifications[i].name) {

                        case 'unread_message_count':
                            set_message_count(notifications[i].data);
                            break;
                        case 'task_progress':
                            // set_task_progress(notifications[i].data.task_id, notifications[i].data.progress);
                            // task_progress인 경우, data에는 list(array)가 들어오므로 -> 순회하면서 처리한다
                            notifications[i].data.forEach(function (task, index, array) {
                                // console.log(task, index, array);
                                set_task_progress(task.task_id, task.progress);
                            });
                            break;
                        case 'task_reserve':
                            notifications[i].data.forEach(function (task, index, array) {
                                console.log(task.task_id, task.reserved_at)
                                set_task_remain(task.task_id, task.reserved_at);
                            });
                            break;
                    }
                    since = notifications[i].timestamp;
                }
            }
        );
    }, 5000);
});