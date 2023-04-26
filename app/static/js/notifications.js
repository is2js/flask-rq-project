function set_message_count(n) {
    $('#message_count').text(n);
    $('#message_count').css('visibility', n ? 'visible' : 'hidden');
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
                    if (notifications[i].name == 'unread_message_count')
                        set_message_count(notifications[i].data);
                    since = notifications[i].timestamp;
                    console.log('since >> ', since);
                    console.log('notifications[i] >> ', notifications[i]);
                }
            }
        );
    }, 10000);
});