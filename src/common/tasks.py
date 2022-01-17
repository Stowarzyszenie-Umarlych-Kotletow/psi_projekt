import asyncio
import threading


tasks_lock = threading.Lock()
tasks = []

def in_background(future: asyncio.Future):
    def task_finished(own_future):
        with tasks_lock:
            tasks.remove(own_future)
    with tasks_lock:
        tasks.append(future)
        future.add_done_callback(task_finished)
    return future
    

def loop_worker(loop):
    asyncio.set_event_loop(loop)
    asyncio.get_event_loop().run_forever()

def new_loop() -> asyncio.AbstractEventLoop:
    loop = asyncio.new_event_loop()
    t = threading.Thread(target=loop_worker, args=(loop,), daemon=True)
    t.start()
    return loop