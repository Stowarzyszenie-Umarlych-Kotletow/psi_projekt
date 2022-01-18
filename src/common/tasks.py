import asyncio
import threading
from typing import Coroutine


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

def coro_in_background(coroutine: Coroutine, loop: asyncio.AbstractEventLoop):
    """
    Runs a given coroutine in the background (using the specified loop)
    """
    return in_background(asyncio.run_coroutine_threadsafe(coroutine, loop))


def loop_worker(loop):
    asyncio.set_event_loop(loop)
    asyncio.get_event_loop().run_forever()

def new_loop() -> asyncio.AbstractEventLoop:
    """
    Creates a new asyncio event loop
    """
    loop = asyncio.new_event_loop()
    t = threading.Thread(target=loop_worker, args=(loop,), daemon=True)
    t.start()
    return loop