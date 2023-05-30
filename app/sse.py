import json
from typing import Optional


class ServerSentEventMessage:
    def __init__(
            self,
            event,
            data: str = None,
            id: Optional[int] = None,
            retry: Optional[int] = None,
    ) -> None:
        self.event = event
        self.data = data
        self.id = id
        self.retry = retry

    def encode(self) -> bytes:
        """
        Listener to Front(json['data'] to String message)

        listener들이 받은 json message 중에서 'data'부분만 골라서 받아 -> front전달용 string message를 만든다.

        for pubsub_message in pubsub.listen():
            msg_dict = json.loads(pubsub_message['data'])
            yield ServerSentEventMessage(**msg_dict).encode()
        """
        # 나는 event가 필수지만, message에서는 data는 필수다. 없으면 None으로 채워보내자.
        message = f"event: {self.event}"
        message += f"\ndata: {self.data}"
        if self.id is not None:
            message = f"{message}\nid: {self.id}"
        if self.retry is not None:
            message = f"{message}\nretry: {self.retry}"
        message = f"{message}\n\n"
        # return message.encode('utf-8')
        return message

    def to_json(self):
        """
        Publisher to Listener(json to String message)

        알림을 생성하는 publish시, listener들에게 보낼 때 string으로 dump해서 보낸다.

        message = ServerSentEventMessage(event, data=data, id=id, retry=retry)
        return self.redis.publish(channel=channel, message=message.to_json())
        """
        # data가 string이 아닐 땐, json dumps
        if not isinstance(self.data, str):
            self.data = json.dumps(self.data)

        d = {"data": self.data}
        if self.event:
            d["event"] = self.event
        if self.id:
            d["id"] = self.id
        if self.retry:
            d["retry"] = self.retry
        return json.dumps(d)


class ServerSentEventService:
    def __init__(self, redis) -> None:
        if not redis:
            raise ValueError(f'redis 객체를 입력해주세요.')
        self.redis = redis

    def message_generator(self, channel='sse'):
        """
        stream에서 작동하며 queryParam으로 온 channel에 대하여
        구독을 설정하고 -> yield로 대기하면서 무한으로 뿌려준다.
        publish시 json dump된 string메세지 -> listen으로  data만 꺼내서
         -> 'data'만 load된 json message -> encode된 stirng message -> front전달

         1) 첫 연결시 -> pubsub_message['type'] == 'subscribe' => 직접 event: \ndata: 에  'type'과 'data'= 1 을 전달
         2) sse.publish()를 사용하는 경우 -> pubsub_message['type'] == 'message' => data를 json으로 넣었음.
        """
        # 옵션을 주면, listener들이 type == 'message'를 확인안해도 된다. subscribe생략됨.
        # pubsub = self.redis.pubsub(ignore_subscribe_messages=True)
        pubsub = self.redis.pubsub()
        pubsub.subscribe(channel)

        try:
            for pubsub_message in pubsub.listen():
                if pubsub_message['type'] == 'message':
                    msg_dict = json.loads(pubsub_message['data'])
                    yield ServerSentEventMessage(**msg_dict).encode()
                else:
                    # {'type': 'subscribe', 'pattern': None, 'channel': b'youtube', 'data': 1}
                    # pubsub_message['type'] == 'subscribe':
                    yield 'event: %s\ndata: %s\n\n' % (pubsub_message['type'], pubsub_message['data'])
        finally:
            try:
                pubsub.unsubscribe(channel)
            except ConnectionError:
                pass

    def stream(self, channel='sse'):
        """
        route에서 querystring으로 channel을 받아 구독하고 메세지를 받도록 설정한다.

        route에서는 stream(channel=)로 설정되어 받는 메세지를
        flask framework에 맞는 Response + 필요시 stream_with_context까지 설정해서 반환해야한다

        return Response(
            stream_with_context(sse.stream(channel=channel)),
            mimetype="text/event-stream",
            headers={
                'Cache-Control': 'no-cache',
                'Transfer-Encoding': 'chunked',
            })
            
        """
        # yield하면 에러
        return self.message_generator(channel=channel)

    def publish(self, event, data=None, id=None, retry=None, channel='sse'):
        """
        특정 채널에 대해, 알림을 생성하여 -> stream()이 받아서 방출해준다.

        sse.publish('chat__messageAdded', channel='chat_channel')
        """

        message = ServerSentEventMessage(event, data=data, id=id, retry=retry)
        return self.redis.publish(channel=channel, message=message.to_json())
