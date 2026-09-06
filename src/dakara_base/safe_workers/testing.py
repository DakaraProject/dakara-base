"""Module for testing functions related to safe workers.

The helper `assert_worker_no_errors` checks if a worker does not have errors:

>>> from dakara_base.safe_workers import WorkerSafeThread
>>> from threading import Event
>>> from queue import Queue
>>> worker = WorkerSafeThread(Event(), Queue())
>>> assert_worker_no_errors(worker)
>>> def error_function():
...     raise Exception("error message")
>>> worker.set_thread(target=error_function)
>>> worker.thread.start()
>>> worker.thread.join()
>>> assert_worker_no_errors(worker)
Traceback (most recent call last):
    ...
AssertionError: Worker WorkerSafeThread(...) is in failed state:
0: Exception: error message
  File ...
"""

from traceback import format_tb

from dakara_base.safe_workers import BaseWorker


def assert_worker_no_errors(worker: BaseWorker) -> None:
    """Assert that a worker is not in failed state, otherwise raise an
    exception containing all the error messages of the captured exceptions..

    Args:
        worker: Instance of the worker.

    Raises:
        AssertionError: If the worker is in failed state. The error message
            contains all the errors of the worker.
    """
    if worker.errors.empty():
        return

    errors = [worker.errors.get() for _ in range(worker.errors.qsize())]
    message_bits = [(e[0].__name__, e[1], "\n".join(format_tb(e[2]))) for e in errors]
    message = "\n".join(
        f"{i}: {name}: {msg}\n{stack}"
        for i, (name, msg, stack) in enumerate(message_bits)
    )

    raise AssertionError(f"Worker {worker} is in failed state:\n{message}")
