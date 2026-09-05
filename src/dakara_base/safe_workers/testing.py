from traceback import format_tb

from dakara_base.safe_workers import BaseWorker


def assert_worker_no_errors(worker: BaseWorker) -> None:
    """Assert that a worker is not in failed state, otherwise raise an
    exception containing all its errors.

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
