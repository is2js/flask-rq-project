import time

import redis
from flask import Flask, request
from rq import Queue

app = Flask(__name__)

r = redis.Redis(host='redis', port=6379)
q = Queue(connection=r)

def background_task(n):

    delay = 2

    print('Task running')
    print(f'Simulating {delay} seconds delay')

    time.sleep(delay)

    print(len(n))
    print('Task complete')

    return len(n)

@app.route('/task')
def add_task():  # put application's code here
    if request.args.get('n'):
        job = q.enqueue(background_task, request.args.get('n'))
        q_len = len(q)
        # http://localhost:8000/task?n=kk
        # Task b31f35f8-0c9b-4239-89d7-6a5b56454fae added to queue at 2023-04-18 04:27:21.490604. 2 tasks in the queue
        return f'Task {job.id} added to queue at {job.enqueued_at}. {q_len} tasks in the queue'

    return 'No value for n'


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000)
