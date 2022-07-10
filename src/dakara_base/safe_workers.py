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
import platform
import signal
import sys
from functools import wraps
from queue import Empty, Queue
from threading import Event, Thread, Timer

from dakara_base.exceptions import DakaraError

logger = logging.getLogger(__name__)


def safe(fun):
    """Decorator to make the function safe.

    Any exception is caught and put in the error queue. This sets the stop
    event as well.

    The decorated function must be a method of a BaseSafeThread or a BaseWorker
    class (or inherited).
    """

    @wraps(fun)
    def call(self, *args, **kwargs):
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
    screen but passed to the main thread.

    This class is abstract and must be inherited with either `theading.Thread`
    or `threading.Timer`.

    Attributes:
        stop (threading.Event): Stop event that notify to stop the entire
            program when set.
        errors (queue.Queue): Error queue to communicate the exception to the
            main thread.

    Args:
        stop (threading.Event): Stop event that notify to stop the entire
            program when set.
        errors (queue.Queue): Error queue to communicate the exception to the
            main thread.
    """

    def __init__(self, stop, errors, *args, **kwargs):
        # check arguments are valid
        assert isinstance(stop, Event), "Stop argument must be of type Event"
        assert isinstance(errors, Queue), "Errors argument must be of type Queue"

        # assign stop event and error queue
        self.stop = stop
        self.errors = errors

        # specific initialization
        super().__init__(*args, **kwargs)

    @safe
    def run(self):
        """Method to run as a thread safely."""
        return super().run()


class SafeThread(BaseSafeThread, Thread):
    """Thread executed within a Worker.

    The thread is connected to the stop event and the errors queue. In case of
    failure from the threaded function, the stop event is set and the exception
    is put in the error queue. The thread closes immediatlely.

    This mechanism allows to completely stop the execution of the program if an
    exception has been raised in a sub-thread. The excetpion is not shown on
    screen but passed to the main thread.

    Attributes:
        stop (threading.Event): Stop event that notify to stop the entire
            program when set.
        errors (queue.Queue): Error queue to communicate the exception to the
            main thread.

    Args:
        stop (threading.Event): Stop event that notify to stop the entire
            program when set.
        errors (queue.Queue): Error queue to communicate the exception to the
            main thread.

    Consult the help of `threading.Thread` for more information.
    """

    pass


class SafeTimer(BaseSafeThread, Timer):
    """Timer thread executed within a Workes.

    The timer thread is connected to the stop event and the errors queue. In
    case of failure from the threaded function, the stop event is set and the
    exception is put in the error queue. The timer thread closes immediatlely.

    This mechanism allows to completely stop the execution of the program if an
    exception has been raised in a timer sub-thread. The excetpion is not shown
    on screen but passed to the main thread.

    Attributes:
        stop (threading.Event): Stop event that notify to stop the entire
            program when set.
        errors (queue.Queue): Error queue to communicate the exception to the
            main thread.

    Args:
        stop (threading.Event): Stop event that notify to stop the entire
            program when set.
        errors (queue.Queue): Error queue to communicate the exception to the
            main thread.

    Consult the help of `threading.timer` for more information.
    """

    pass


class BaseWorker:
    """Base worker class.

    The base worker is bound to a stop event which when triggered will stop the
    program. It also has an errors queue to communicate errors to the main
    thread.

    It behaves like a context manager that returns itself on enter and triggers
    the stop event on exit.

    New threads should be created with the `create_thread` method and new
    thread timers with the `create_timer` method.

    Attributes:
        stop (threading.Event): Stop event that notify to stop the entire
            program when set.
        errors (queue.Queue): Error queue to communicate the exception to the
            main thread.

    Args:
        stop (threading.Event): Stop event that notify to stop the entire
            program when set.
        errors (queue.Queue): Error queue to communicate the exception to the
            main thread.

    Raises:
        AssertionError: If the `stop` or `errors` arguments are not
            respectivily Event and Queue.
    """

    def __init__(self, stop, errors):
        # associate the stop event
        assert isinstance(stop, Event), "Stop attribute must be of type Event"
        self.stop = stop

        # associate the errors queue
        assert isinstance(errors, Queue), "Errors attribute must be of type Queue"
        self.errors = errors

    def init_worker(self):
        """Custom init method stub."""
        pass

    def __enter__(self):
        """Simple context manager enter.

        Just call the custom enter method and returns the instance.
        """
        # call custom enter
        self.enter_worker()

        return self

    def enter_worker(self):
        """Custom enter method stub."""
        pass

    def __exit__(self, *args, **kwargs):
        """Simple context manager exit..

        Just triggers the stop event.
        """
        # notify the stop event
        self.stop.set()

    def exit_worker(self, *args, **kwargs):
        """Custom exit method stub."""
        pass

    def create_thread(self, *args, **kwargs):
        """Helper to easily create a SafeThread object..

        Args:
            See `threading.Thread`.

        Returns:
            SafeThread: Secured thread instance.
        """
        return SafeThread(self.stop, self.errors, *args, **kwargs)

    def create_timer(self, *args, **kwargs):
        """Helper to easily create a SafeTimer object..

        Args:
            See `threading.Timer`.

        Returns:
            SafeTimer: Secured timer thread instance.
        """
        return SafeTimer(self.stop, self.errors, *args, **kwargs)


class Worker(BaseWorker):
    """Worker class.

    The worker is bound to a stop event which when triggered will stop the
    program. It also has an errors queue to communicate errors to the main
    thread.

    It behaves like a context manager that returns itself on enter and triggers
    the stop event on exit.

    New threads should be created with the `create_thread` method and new
    thread timers with the `create_timer` method.

    Extra actions for context manager enter and exit should be put in the
    `enter_worker` and `exit_worker` methods.

    Initialization must be performed through the `init_worker` method. The
    initialization assigns the mandatory stop event and errors queue to the
    instance and calls the custom init method.

    Attributes:
        stop (threading.Event): Stop event that notify to stop the entire
            program when set.
        errors (queue.Queue): Error queue to communicate the exception to the
            main thread.

    Args:
        stop (threading.Event): Stop event that notify to stop the entire
            program when set.
        errors (queue.Queue): Error queue to communicate the exception to the
            main thread.
    """

    def __init__(self, stop, errors, *args, **kwargs):
        super().__init__(stop, errors)

        # call custom init
        self.init_worker(*args, **kwargs)

    def __exit__(self, *args, **kwargs):
        """Simple context manager exit.

        Just triggers the stop event and call the custom exit method.
        """
        super().__exit__()

        logger.debug("Exiting worker method (%s)", self.__class__.__name__)

        # call custom exit
        self.exit_worker(*args, **kwargs)

        logger.debug("Exited worker method (%s)", self.__class__.__name__)


class WorkerSafeTimer(BaseWorker):
    """Worker class with safe timer.

    The worker class with safe timer is bound to a stop event which when
    triggered will stop the program. It also has an errors queue to communicate
    errors to the main thread.

    It contains a timer thread `timer` connected to a dummy function which must
    be redefined. New thread timers should be created with the `create_timer`
    method.

    It behaves like a context manager that gives itself on enter. On exit, it
    cancels and ends its timer thread and also triggers the stop event.

    Extra actions for context manager enter and exit should be put in the
    `enter_worker` and `exit_worker` methods.

    Initialization must be performed through the `init_worker` method.  The
    initialization assigns its own timer thread to the instance and makes it
    target a dummy method.

    Attributes:
        stop (threading.Event): Stop event that notify to stop the entire
            program when set.
        errors (queue.Queue): Error queue to communicate the exception to the
            main thread.
        timer (SafeTimer): Timer thread that must be redefined.

    Args:
        stop (threading.Event): Stop event that notify to stop the entire
            program when set.
        errors (queue.Queue): Error queue to communicate the exception to the
            main thread.
    """

    def __init__(self, stop, errors, *args, **kwargs):
        super().__init__(stop, errors)

        # create timer for itself
        def redefine_me():
            """Dummy function that should not be used."""
            raise UnredefinedTimerError(
                "You must redefine the timer of a WorkerSafeTimer"
            )

        self.timer = self.create_timer(0, redefine_me)

        # perform other custom actions
        self.init_worker(*args, **kwargs)

    def __exit__(self, *args, **kwargs):
        """Worker context manager exit.

        Cancels and close the timer thread. It calls the custom context manager
        exit method.

        The stop event has already been triggered.
        """
        super().__exit__(*args, **kwargs)

        # exit now if the timer is not running
        if not self.timer.is_alive():
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


class WorkerSafeThread(BaseWorker):
    """Worker class with safe thread.

    The worker class with safe thread is bound to a stop event which when
    triggered will stop the program. It also has an errors queue to communicate
    errors to the main thread.

    It contains a thread `thread` connected to a dummy function which must de
    redefined. New threads should be created with the `create_thread` method.

    The instance is a context manager that gives itself on enter. On exit, it
    ends its own thread and also triggers the stop event.

    Extra actions for context manager enter and exit should be put in the
    `enter_worker` and `exit_worker` methods.

    Initialisation must be performed through the `init_worker` method. The
    initialization assigns its own thread to the instance and makes it target a
    dummy method.

    If a method `run_main` is defined, it will be called in the main thread. It
    takes the stop event end the errors queue as arguments.

    Attributes:
        stop (threading.Event): Stop event that notify to stop the entire
            program when set.
        errors (queue.Queue): Error queue to communicate the exception to the
            main thread.
        thread (SafeThread): Thread bound to the `run` method.

    Args:
        stop (threading.Event): Stop event that notify to stop the entire
            program when set.
        errors (queue.Queue): Error queue to communicate the exception to the
            main thread.
    """

    def __init__(self, stop, errors, *args, **kwargs):
        super().__init__(stop, errors)

        # create thread for itself
        def redefine_me():
            """Dummy function that should not be used."""
            raise UnredefinedThreadError(
                "You must redefine the thread of a WorkerSafeThread"
            )

        self.thread = self.create_thread(target=redefine_me)

        # perform other custom actions
        self.init_worker(*args, **kwargs)

    def __exit__(self, *args, **kwargs):
        """Worker context manager exit.

        Closes the thread. It calls the custom context manager exit method.

        The stop event has already been triggered.
        """
        super().__exit__(*args, **kwargs)

        # exit now if the thread is not running
        if not self.thread.is_alive():
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


class Runner:
    """Runner class.

    The runner creates the stop event and errors queue. It is designed to
    execute the thread of a `WorkerSafeThread` instance until an error occurs
    or an user interruption pops out (Ctrl+C).

    The initialization creates the stop event and the errors queue and calls
    the custom init method.

    Attributes:
        stop (threading.Event): Stop event that notify to stop the execution of
            the thread.
        errors (queue.Queue): Error queue to communicate the exception of the
            thread.
    """

    ERROR_TIMEOUT = 5

    def __init__(self, *args, **kwargs):
        # create stop event
        self.stop = Event()

        # create errors queue
        self.errors = Queue()

        # extra actions
        self.init_runner(*args, **kwargs)

    def init_runner(self, *args, **kwargs):
        """Custom initialization stub."""
        pass

    def run_safe(self, worker_class, args=None, kwargs=None, run_main=None):
        """Execute a WorkerSafeThread instance thread.

        The thread is executed and the method waits for the stop event to be
        set or a user interruption to be triggered (Ctrl+C).

        Args:
            worker_class (WorkerSafeThread): Worker class with safe thread.
                Note you have to pass a custom class based on
                `WorkerSafeThread`.
            args (list): Positional arguments passed to the worker class constructor.
            kwargs (dict): Named arguments passed to the worker class constructor.
            run_main (function): Function to execute in the main thread. It
                must accept the stop event and be blocking as long as the event
                is not set.
        """
        if args is None:
            args = ()

        if kwargs is None:
            kwargs = {}

        # register user interruption
        def on_sigint(signal_number, frame):
            logger.debug(f"Receiving signal {signal_number} to close")
            self.errors.put(None)
            self.stop.set()

        signal.signal(signal.SIGINT, on_sigint)

        # create worker thread
        with worker_class(self.stop, self.errors, *args, **kwargs) as worker:
            logger.debug("Create worker thread")
            worker.thread.start()

            if run_main is not None:
                # if a function is provided, run it
                # it must ruturn when the stop event is set
                run_main(self.stop, self.errors)

            elif hasattr(worker, "run_main"):
                # if the worker has a function to run, run it
                # it must ruturn when the stop event is set
                worker.run_main()

            else:
                wait(self.stop)

        # get the error from the error queue
        # a delay of 5 seconds is accorded for the error to be retrieved
        try:
            reason = self.errors.get(timeout=self.ERROR_TIMEOUT)

        # if there is no error in the error queue, raise a general error
        # this case is very unlikely to happen and is not tested
        except Empty as empty_error:
            raise EmptyErrorsQueueError("Unknown error happened") from empty_error

        # if there is no error, this is a normal interruption
        if reason is None:
            logger.debug("User stop caught")
            return

        _, error, traceback = reason
        logger.debug("Internal error caught")
        error.with_traceback(traceback)
        raise error


def wait(stop, interval=0.5):
    """Wait for stop event to be set.

    We have to use a specific code for Windows because the Ctrl+C event will
    not be handled during `self.stop.wait()`. This method is blocking for
    Windows, not for Linux, which is due to the way Ctrl+C is differently
    handled by the two OSs. For Windows, a quick and dirty solution consists
    in polling the `self.stop.wait()` with a timeout argument, so the call is
    non-permanently blocking.

    See also:
        https://mail.python.org/pipermail/python-dev/2017-August/148800.html
        https://stackoverflow.com/a/51954792/4584444

    Args:
        stop (threading.Event): Stop event.
        interval (float): For Windows only, interval between two
            attempts to wait for the stop event.
    """
    logger.debug("Waiting for stop event")

    if platform.system() == "Windows":
        while not stop.is_set():
            stop.wait(interval)

        return

    # otherwise just wait for the program to stop
    stop.wait()


class UnredefinedTimerError(DakaraError):
    """Unredefined timer error.

    Error raised if the default timer of the `WorkerSafeTimer` class has not
    been redefined.
    """


class UnredefinedThreadError(DakaraError):
    """Unredefined thread error.

    Error raised if the default thread of the `WorkerSafeTimer` class has not
    been redefined.
    """


class EmptyErrorsQueueError(RuntimeError):
    """No error caught error.

    Error raised if the safe workers mechanism stops for an error, but there is
    no error. This error is completely unexpected and hence does not inherit
    from DakaraError.
    """
