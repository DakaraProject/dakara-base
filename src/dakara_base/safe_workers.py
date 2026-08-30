"""Safe workers helper module.

This module provides some classes to facilitate the manipulaton of threads.
Especially, it guarantees that a failure in a thread will be notified in the
entire program.

Among them, the `SafeThread` and `SafeTimer` classes allow to retrieve
exceptions raised on the threaded/timed function. The `Worker` class can create
`SafeThread`s/`SafeTimer`s associated to itself. The `WorkerSafeThread` and
`WorkerSafeTimer` classes are context managers that ensure to close their
`SafeThread` or `SafeTimer` when exited. The `Runner` class can run the thread
of a `WorkerSafeThread` class untill internal error or user interrupt (Ctrl+C).

A main concept of this module is that a Python Event object is shared among the
instances of the classes of this module. This event is reffered as the stop
event, as it can be used to stop the program. A Python Queue object is also
shared among the different instances and allows to retreive exceptions raised
in sub-threads by the main one.

>>> from threading import Event
>>> from queue import Queue
>>> stop = Event()
>>> errors = Queue()
>>> worker = Worker(stop, errors)
>>> worker_with_thread = WorkerSafeThread(stop, errors)
>>> worker_with_timer = WorkerSafeTimer(stop, errors)
>>> worker.stop.set()
>>> worker_with_thread.stop.is_set()
True
"""

import logging
import sys
from dataclasses import dataclass, field
from functools import wraps
from queue import Empty, Queue
from threading import Event, Thread, Timer
from typing import Any, Callable, ClassVar, Type

if sys.version_info >= (3, 11):
    from typing import Self

else:
    from typing import Any

    Self = Any  # type: ignore


logger = logging.getLogger(__name__)


def safe(fun: Callable) -> Callable:
    """Decorator to make the function safe.

    Any exception is caught and put in the error queue. This sets the stop
    event as well.

    The decorated function must be a method of a BaseSafeThread or a BaseWorker
    class (or inherited).
    """

    @wraps(fun)
    def call(self, *args, **kwargs) -> Any:
        # check the target's class is a safe thread or a safe worker
        assert isinstance(self, (BaseSafeThread, BaseWorker)), (
            "The class '{}' of method '{}' is not a "
            "BaseSafeThread or a BaseWorker".format(
                self.__class__.__name__, fun.__name__
            )
        )

        # try to run the target
        try:
            return fun(self, *args, **kwargs)

        # if an error occurs, put it in the error queue and notify the stop
        # event
        except BaseException:
            self.errors.put_nowait(sys.exc_info())
            self.stop.set()

    return call


class BaseSafeThread:
    """Base class for thread executed within a Worker.

    The thread is connected to the stop event and the errors queue. In case of
    failure from the threaded function, the stop event is set and the exception
    is put in the error queue. The thread closes immediatlely.

    This mechanism allows to completely stop the execution of the program if an
    exception has been raised in a sub-thread. The excetpion is not shown on
    screen but passed to the main thread through the errors queue.

    This class is abstract and must be inherited with either `theading.Thread`
    or `threading.Timer`.
    """

    def __init__(self, stop: Event, errors: Queue, *args, **kwargs) -> None:
        # assign stop event and error queue
        self.stop: Event = stop
        """Stop event that notify to stop the entire program when set."""

        self.errors: Queue = errors
        """Error queue to communicate the exception to the main thread."""

        # specific initialization
        super().__init__(*args, **kwargs)


class SafeThread(BaseSafeThread, Thread):
    """Thread executed within a Worker."""

    @safe
    def run(self) -> Any:
        """Method to run as a thread safely."""
        return super().run()


class SafeTimer(BaseSafeThread, Timer):
    """Timer thread executed within a Worker."""

    @safe
    def run(self) -> Any:
        """Method to run as a thread safely."""
        return super().run()


@dataclass
class BaseWorker:
    """Base worker class.

    The base worker is bound to a stop event which when triggered will stop the
    program. It also has an errors queue to communicate errors to the main
    thread.

    It behaves like a context manager that returns itself on enter and triggers
    the stop event on exit.

    New threads should be created with the `create_thread` method and new
    thread timers with the `create_timer` method.

    Extra actions for initialization should be put in the `init_worker` method.

    Extra actions for context manager enter and exit should be put in the
    `enter_worker` and `exit_worker` methods.
    """

    stop: Event
    """Stop event that notify to stop the entire program when set."""

    errors: Queue
    """Error queue to communicate the exception to the main thread."""

    def __post_init__(self) -> None:
        # extra actions
        self.init_worker()

    def init_worker(self) -> None:
        """Custom init method stub.

        This method is always called when initializing a class instance.
        """

    def __enter__(self) -> Self:
        """Simple context manager enter.

        Just call the custom enter method and returns the instance.
        """
        # call custom enter
        self.enter_worker()

        return self

    def enter_worker(self) -> None:
        """Custom enter method stub."""

    def __exit__(self, *args, **kwargs) -> None:
        """Simple context manager exit.

        Just triggers the stop event.
        """
        # notify the stop event
        self.stop.set()

    def exit_worker(self, *args, **kwargs) -> None:
        """Custom exit method stub."""

    def create_thread(self, *args, **kwargs) -> SafeThread:
        """Helper to easily create a `SafeThread` object.

        Args:
            See `threading.Thread`.

        Returns:
            Secured thread instance.
        """
        return SafeThread(self.stop, self.errors, *args, **kwargs)

    def create_timer(self, *args, **kwargs) -> SafeTimer:
        """Helper to easily create a `SafeTimer` object.

        Args:
            See `threading.Timer`.

        Returns:
            Secured timer thread instance.
        """
        return SafeTimer(self.stop, self.errors, *args, **kwargs)


@dataclass
class Worker(BaseWorker):
    """Worker class."""

    def __exit__(self, *args, **kwargs) -> None:
        """Simple context manager exit.

        Just triggers the stop event and call the custom exit method.
        """
        super().__exit__()

        logger.debug("Exiting worker method (%s)", self.__class__.__name__)

        # call custom exit
        self.exit_worker(*args, **kwargs)

        logger.debug("Exited worker method (%s)", self.__class__.__name__)


@dataclass
class WorkerSafeTimer(BaseWorker):
    """Worker class with safe timer."""

    timer: SafeTimer | None = field(init=False, default=None)
    """Timer thread that must be defined before use."""

    def set_timer(self, *args, **kwargs) -> None:
        """Set a timer.

        Args:
            See `BaseWorker.create_timer`.
        """
        self.timer = self.create_timer(*args, **kwargs)

    def __exit__(self, *args, **kwargs) -> None:
        """Worker context manager exit.

        Cancels and close the timer thread. It calls the custom context manager
        exit method.

        The stop event has already been triggered.
        """
        super().__exit__(*args, **kwargs)

        # exit now if the timer is not running or not set
        if self.timer is None or not self.timer.is_alive():
            return

        logger.debug(
            "Closing worker safe timer thread '%s' (%s)",
            self.timer.name,
            self.__class__.__name__,
        )

        # custom exit
        self.exit_worker(*args, **kwargs)

        # cancel the timer, if the timer was waiting
        self.timer.cancel()

        # wait for termination, if the timer was running
        self.timer.join()

        logger.debug(
            "Closed worker safe timer thread '%s' (%s)",
            self.timer.name,
            self.__class__.__name__,
        )


@dataclass
class WorkerSafeThread(BaseWorker):
    """Worker class with safe thread.
    Extra actions for context manager enter and exit should be put in the
    `enter_worker` and `exit_worker` methods.
    """

    thread: SafeThread | None = field(init=False, default=None)
    """Thread that must be defined before use."""

    def set_thread(self, *args, **kwargs) -> None:
        """Set a thread.

        Args:
            See `BaseWorker.create_thread`.
        """
        self.thread = self.create_thread(*args, **kwargs)

    def __exit__(self, *args, **kwargs) -> None:
        """Worker context manager exit.

        Closes the thread. It calls the custom context manager exit method.

        The stop event has already been triggered.
        """
        super().__exit__(*args, **kwargs)

        # exit now if the thread is not running
        if self.thread is None or not self.thread.is_alive():
            return

        logger.debug(
            "Closing worker safe thread '%s' (%s)",
            self.thread.name,
            self.__class__.__name__,
        )

        # custom exit action
        self.exit_worker(*args, **kwargs)

        # wait for termination
        self.thread.join()

        logger.debug(
            "Closed worker safe thread '%s' (%s)",
            self.thread.name,
            self.__class__.__name__,
        )


@dataclass
class Runner:
    """Runner class.

    The runner creates the stop event and errors queue. It is designed to
    execute the thread of a `WorkerSafeThread` instance until an error occurs
    or a user interruption pops out (Ctrl+C).

    Extra actions for initialization should be put in the
    `init_runner` method.
    """

    POLLING_INTERVAL: ClassVar[float] = 0.5
    """For Windows only, interval between two attempts to wait for the stop
    event.
    """

    stop: Event = field(default_factory=Event)
    """Stop event that notify to stop the execution of the thread."""

    errors: Queue = field(default_factory=Queue)
    """Error queue to communicate the exception of the thread."""

    def __post_init__(self) -> None:
        # extra actions
        self.init_runner()

    def init_runner(self) -> None:
        """Custom initialization stub."""

    def run_safe(self, worker_class: Type[WorkerSafeThread], *args, **kwargs) -> None:
        """Execute a WorkerSafeThread instance thread.

        The thread is executed and the method waits for the stop event to be
        set or a user interruption to be triggered (Ctrl+C).

        Args:
            worker_class: Worker class with safe thread. Note you have to pass
                a custom class based on `WorkerSafeThread`.
            Other arguments are passed to `worker_class`.
        """
        try:
            # create worker thread
            with worker_class(self.stop, self.errors, *args, **kwargs) as worker:

                logger.debug("Create worker thread")
                assert worker.thread is not None
                worker.thread.start()

                # wait for stop event
                logger.debug("Waiting for stop event")

                # We have to use a different code for Windows because the
                # Ctrl+C event will not be handled during `self.stop.wait()`.
                # This method is blocking for Windows, not for Linux, which is
                # due to the way Ctrl+C is differently handled by the two OSs.
                # For Windows, a quick and dirty solution consists in polling
                # the `self.stop.wait()` with a timeout argument, so the call
                # is non-permanently blocking.
                # More resources on this:
                # https://mail.python.org/pipermail/python-dev/2017-August/148800.html
                # https://stackoverflow.com/a/51954792/4584444
                if sys.platform.startswith("win"):
                    while not self.stop.is_set():
                        self.stop.wait(self.POLLING_INTERVAL)

                else:
                    self.stop.wait()

        # stop on Ctrl+C
        except KeyboardInterrupt:
            logger.debug("User stop caught")
            self.stop.set()

        # stop on error
        else:
            logger.debug("Internal error caught")

            # get the error from the error queue and re-raise it
            # a delay of 5 seconds is accorded for the error to be retrieved
            try:
                _, error, traceback = self.errors.get(timeout=5)
                error.with_traceback(traceback)
                raise error

            # if there is no error in the error queue, raise a general error
            # this case is very unlikely to happen and is not tested
            except Empty as empty_error:
                raise NoErrorCaughtError("Unknown error happened") from empty_error


class NoErrorCaughtError(RuntimeError):
    """No error caught error.

    Error raised if the safe workers mechanism stops for an error, but there is
    no error. This error is completely unexpected and hence does not inherit
    from DakaraError.
    """
