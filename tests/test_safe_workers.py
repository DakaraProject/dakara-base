from contextlib import contextmanager
from queue import Queue
from threading import Event, Timer
from time import sleep
from unittest import TestCase
from unittest.mock import MagicMock

from dakara_base.safe_workers import (
    BaseSafeThread,
    BaseWorker,
    Runner,
    SafeThread,
    SafeTimer,
    UnredefinedThreadError,
    UnredefinedTimerError,
    Worker,
    WorkerSafeThread,
    WorkerSafeTimer,
    safe,
)


class MyError(Exception):
    """Dummy error class."""

    pass


class BaseTestCase(TestCase):
    """Generic test case.

    It includes some dummy functions a new assertion method.
    """

    def setUp(self):
        # create stop event and errors queue
        self.stop = Event()
        self.errors = Queue()

    def function_safe(self):
        """Function that does not raise any error."""
        return

    def function_error(self):
        """Function that raises a MyError."""
        raise MyError("test error")

    @contextmanager
    def assertNotRaises(self, ExceptionClass):
        """Assert that the provided exception does not raise.

        Args:
            ExceptionClass (class): Class of the exception.
        """
        try:
            yield None

        except ExceptionClass:
            self.fail("{} raised".format(ExceptionClass.__name__))


class SafeTestCase(BaseTestCase):
    """Test the `safe` decorator."""

    def create_classes(self):
        """Create dummy classes."""

        class Base:
            @safe
            def function_safe(self2):
                self.function_safe()

            @safe
            def function_error(self2):
                self.function_error()

        class Thread(BaseSafeThread, Base):
            pass

        class Worker(BaseWorker, Base):
            pass

        class Other(Base):
            pass

        return Thread, Worker, Other

    def test_worker_function_safe(self):
        """Test a safe function of a worker.

        Test that a non-error function does not trigger any error, does not set
        the stop event and does not put an error in the error queue.
        """
        # pre assertions
        self.assertFalse(self.stop.is_set())
        self.assertTrue(self.errors.empty())

        # create instance
        _, Worker, _ = self.create_classes()
        worker = Worker(self.stop, self.errors)

        # call the method
        worker.function_safe()

        # post assertions
        self.assertFalse(self.stop.is_set())
        self.assertTrue(self.errors.empty())

    def test_worker_function_error(self):
        """Test an error function of a worker.

        Test that an error function does not trigger any error, sets the stop
        event and puts a MyError in the error queue.
        """
        # pre assertions
        self.assertFalse(self.stop.is_set())
        self.assertTrue(self.errors.empty())

        # create instance
        _, Worker, _ = self.create_classes()
        worker = Worker(self.stop, self.errors)

        # call the method
        with self.assertNotRaises(MyError):
            worker.function_error()

        # post assertions
        self.assertTrue(self.stop.is_set())
        self.assertFalse(self.errors.empty())
        _, error, _ = self.errors.get()
        self.assertIsInstance(error, MyError)

    def test_thread(self):
        """Test a thread.

        Test that a non-error function does not trigger any error, does not set
        the stop event and does not put an error in the error queue.
        """
        # pre assertions
        self.assertFalse(self.stop.is_set())
        self.assertTrue(self.errors.empty())

        # create instance
        Thread, _, _ = self.create_classes()
        thread = Thread(self.stop, self.errors)

        # call the method
        thread.function_safe()

        # post assertions
        self.assertFalse(self.stop.is_set())
        self.assertTrue(self.errors.empty())

    def test_other(self):
        """Test an other class.

        Test that the decorator raises an error, as the class is not supported.
        """
        # pre assertions
        self.assertFalse(self.stop.is_set())
        self.assertTrue(self.errors.empty())

        # create instance
        _, _, Other = self.create_classes()
        other = Other()

        # call the method
        with self.assertRaises(AssertionError):
            other.function_safe()

        # post assertions
        self.assertFalse(self.stop.is_set())
        self.assertTrue(self.errors.empty())


class SafeThreadTestCase(BaseTestCase):
    """Test the SafeThread class."""

    def create_controlled_thread(self, target):
        """Helper to create a safe thread for a target function."""
        return SafeThread(self.stop, self.errors, target=target)

    def test_function_safe(self):
        """Test a safe function.

        Test that a non-error function run as a thread does not trigger any
        error, does not set the stop event and does not put an error in the
        error queue.
        """
        # pre assertions
        self.assertFalse(self.stop.is_set())
        self.assertTrue(self.errors.empty())

        # create thread
        controlled_thread = self.create_controlled_thread(self.function_safe)

        # run thread
        controlled_thread.start()
        controlled_thread.join()

        # post assertions
        self.assertFalse(self.stop.is_set())
        self.assertTrue(self.errors.empty())

    def test_function_error(self):
        """Test an error function.

        Test that an error function run as a thread does not trigger any error,
        sets the stop event and puts a MyError in the error queue.
        """
        # pre assertions
        self.assertFalse(self.stop.is_set())
        self.assertTrue(self.errors.empty())

        # create thread
        controlled_thread = self.create_controlled_thread(self.function_error)

        # run thread
        with self.assertNotRaises(MyError):
            controlled_thread.start()
            controlled_thread.join()

        # post assertions
        self.assertTrue(self.stop.is_set())
        self.assertFalse(self.errors.empty())
        _, error, _ = self.errors.get()
        self.assertIsInstance(error, MyError)


class SafeTimerTestCase(SafeThreadTestCase):
    """Test the SafeTimer class."""

    def create_controlled_thread(self, target):
        """Helper to create a safe timer thread for a target function.

        The delay is non null (0.5 s).
        """
        return SafeTimer(self.stop, self.errors, 0.5, target)  # set a non-null delay


class WorkerTestCase(BaseTestCase):
    """Test the Worker class."""

    def test_run_safe(self):
        """Test a safe run.

        Test that a worker used with no error does not produce any error,
        finishes with a triggered stop event and an empty error queue.
        """
        # pre assertions
        self.assertFalse(self.stop.is_set())
        self.assertTrue(self.errors.empty())

        # create and run worker
        with Worker(self.stop, self.errors):
            self.function_safe()

        # post assertions
        self.assertTrue(self.stop.is_set())
        self.assertTrue(self.errors.empty())

    def test_run_error(self):
        """Test a run with error.

        Test that a worker used with error does produce an error, finishes
        with a triggered stop event and an empty error queue.
        """
        # pre assertions
        self.assertFalse(self.stop.is_set())
        self.assertTrue(self.errors.empty())

        # create and run worker
        with self.assertRaises(MyError):
            with Worker(self.stop, self.errors):
                self.function_error()

        # there is no point continuing this test from here

        # post assertions
        self.assertTrue(self.stop.is_set())
        self.assertTrue(self.errors.empty())

    def test_run_thread_safe(self):
        """Test a run with a safe thread.

        Test that a worker used with a non-error thread does not produce any
        error, finishes with a triggered stop event and an empty error queue.
        """
        # pre assertions
        self.assertFalse(self.stop.is_set())
        self.assertTrue(self.errors.empty())

        # create and run worker
        with Worker(self.stop, self.errors) as worker:
            worker.thread = worker.create_thread(target=self.function_safe)
            worker.thread.start()
            worker.thread.join()

        # post assertions
        self.assertTrue(self.stop.is_set())
        self.assertTrue(self.errors.empty())

    def test_run_thread_error(self):
        """Test a run with a thread with error.

        Test that a worker used with a thread with an error does not produce
        any error, finishes with a triggered stop event and a non-empty error
        queue.
        """
        # pre assertions
        self.assertFalse(self.stop.is_set())
        self.assertTrue(self.errors.empty())

        # create and run worker
        with self.assertNotRaises(MyError):
            with Worker(self.stop, self.errors) as worker:
                worker.thread = worker.create_thread(target=self.function_error)
                worker.thread.start()
                worker.thread.join()

        # post assertions
        self.assertTrue(self.stop.is_set())
        self.assertFalse(self.errors.empty())
        _, error, _ = self.errors.get()
        self.assertIsInstance(error, MyError)


class WorkerSafeTimerTestCase(BaseTestCase):
    """Test the WorkerSafeTimer class."""

    class WorkerSafeTimerToTest(WorkerSafeTimer):
        """Dummy worker class."""

        def function_already_dead(self):
            """Function that ends immediately."""
            return

        def function_to_cancel(self):
            """Function that calls itself in loop every second."""
            self.timer = Timer(1, self.function_to_cancel)
            self.timer.start()

        def function_to_join(self):
            """Function that waits one second."""
            sleep(1)

    def test_run_timer_dead(self):
        """Test to end a worker when its timer is dead.

        Test that a worker worker stopped with a dead timer finishes with a
        triggered stop event, an empty error queue and a still dead timer.
        """
        # pre assertions
        self.assertFalse(self.stop.is_set())
        self.assertTrue(self.errors.empty())

        # create and run worker
        with self.WorkerSafeTimerToTest(self.stop, self.errors) as worker:
            worker.timer = worker.create_timer(0, worker.function_already_dead)
            worker.timer.start()
            worker.timer.join()

        # post assertions
        self.assertTrue(self.stop.is_set())
        self.assertTrue(self.errors.empty())
        self.assertFalse(worker.timer.is_alive())

    def test_run_timer_cancelled(self):
        """Test to end a deamon when its timer is waiting.

        Test that a worker worker stopped with a waiting timer finishes with a
        triggered stop event, an empty error queue and a dead timer.
        """
        # pre assertions
        self.assertFalse(self.stop.is_set())
        self.assertTrue(self.errors.empty())

        # create and run worker
        with self.WorkerSafeTimerToTest(self.stop, self.errors) as worker:
            worker.timer = worker.create_timer(0, worker.function_to_cancel)
            worker.timer.start()
            sleep(0.5)

        # post assertions
        self.assertTrue(self.stop.is_set())
        self.assertTrue(self.errors.empty())
        self.assertFalse(worker.timer.is_alive())
        self.assertTrue(worker.timer.finished.is_set())

    def test_run_timer_joined(self):
        """Test to end a deamon when its timer is running.

        Test that a worker worker stopped with a running timer finishes with a
        triggered stop event, an empty error queue and a dead timer.
        """
        # pre assertions
        self.assertFalse(self.stop.is_set())
        self.assertTrue(self.errors.empty())

        # create and run worker
        with self.WorkerSafeTimerToTest(self.stop, self.errors) as worker:
            worker.timer = worker.create_timer(0, worker.function_to_join)
            worker.timer.start()
            sleep(0.5)

        # post assertions
        self.assertTrue(self.stop.is_set())
        self.assertTrue(self.errors.empty())
        self.assertFalse(worker.timer.is_alive())

    def test_unredifined_timer(self):
        """Test the timer must be redefined.

        Test that a worker worker with its default timer does not generate an
        error, but finishes with a triggered stop event and an non-empty error
        queue.
        """
        # pre assertions
        self.assertFalse(self.stop.is_set())
        self.assertTrue(self.errors.empty())

        # create and run worker
        with self.assertNotRaises(UnredefinedTimerError):
            with self.WorkerSafeTimerToTest(self.stop, self.errors) as worker:
                worker.timer.start()

        # post assertions
        self.assertTrue(self.stop.is_set())
        self.assertFalse(self.errors.empty())
        _, error, _ = self.errors.get()
        self.assertIsInstance(error, UnredefinedTimerError)


class WorkerSafeThreadTestCase(BaseTestCase):
    """Test the WorkerSafeThread class."""

    class WorkerSafeThreadToTest(WorkerSafeThread):
        """Dummy worker class."""

        def function_already_dead(self):
            """Function that ends immediately."""
            return

        def function_to_join(self):
            """Function that waits one second."""
            sleep(1)

    def test_run_thread_dead(self):
        """Test to end a worker when its thread is dead.

        Test that a worker worker stopped with a dead thread finishes with a
        triggered stop event, an empty error queue and a still dead thread.
        """
        # pre assertions
        self.assertFalse(self.stop.is_set())
        self.assertTrue(self.errors.empty())

        # create and run worker
        with self.WorkerSafeThreadToTest(self.stop, self.errors) as worker:
            worker.thread = worker.create_thread(target=worker.function_already_dead)
            worker.thread.start()
            worker.thread.join()

        # post assertions
        self.assertTrue(self.stop.is_set())
        self.assertTrue(self.errors.empty())
        self.assertFalse(worker.thread.is_alive())

    def test_run_thread_joined(self):
        """Test to end a deamon when its thread is running.

        Test that a worker worker stopped with a running thread finishes with a
        triggered stop event, an empty error queue and a dead thread.
        """
        # pre assertions
        self.assertFalse(self.stop.is_set())
        self.assertTrue(self.errors.empty())

        # create and run worker
        with self.WorkerSafeThreadToTest(self.stop, self.errors) as worker:
            worker.thread = worker.create_thread(target=worker.function_to_join)
            worker.thread.start()
            sleep(0.5)

        # post assertions
        self.assertTrue(self.stop.is_set())
        self.assertTrue(self.errors.empty())
        self.assertFalse(worker.thread.is_alive())

    def test_unredifined_thread(self):
        """Test the thread must be redefined.

        Test that a worker worker with its default thread does not generate an
        error, but finishes with a triggered stop event and an non-empty error
        queue.
        """
        # pre assertions
        self.assertFalse(self.stop.is_set())
        self.assertTrue(self.errors.empty())

        # create and run worker
        with self.assertNotRaises(UnredefinedThreadError):
            with self.WorkerSafeThreadToTest(self.stop, self.errors) as worker:
                worker.thread.start()

        # post assertions
        self.assertTrue(self.stop.is_set())
        self.assertFalse(self.errors.empty())
        _, error, _ = self.errors.get()
        self.assertIsInstance(error, UnredefinedThreadError)


class RunnerTestCase(BaseTestCase):
    """Test the Runner class.

    The class to test should leave because of a Ctrl+C, or because of an
    internal eror.
    """

    class WorkerNormal(Worker):
        """Dummy worker class."""

        def init_worker(self):
            self.thread = self.create_thread(target=self.test)

        def test(self):
            pass

    class WorkerError(Worker):
        """Dummy worker class that will fail."""

        def init_worker(self):
            self.thread = self.create_thread(target=self.test)

        def test(self):
            raise MyError("test error")

    def setUp(self):
        # create class to test
        self.runner = Runner()

    def test_run_safe_interrupt(self):
        """Test a run with an interruption by KeyboardInterrupt exception.

        The run should end with a set stop event and an empty errors queue.
        """
        # pre assertions
        self.assertFalse(self.runner.stop.is_set())
        self.assertTrue(self.runner.errors.empty())

        # modify stop event wait method
        self.runner.stop.wait = MagicMock()
        self.runner.stop.wait.side_effect = KeyboardInterrupt

        # call the method
        self.runner.run_safe(self.WorkerNormal)

        # post assertions
        self.assertTrue(self.runner.stop.is_set())
        self.assertTrue(self.runner.errors.empty())

        # assert stop event wait method was called
        self.runner.stop.wait.assert_called_once()

    def test_run_safe_error(self):
        """Test a run with an error.

        The run should raise a MyError, end with a set stop event and an
        empty error queue.
        """
        # pre assertions
        self.assertFalse(self.runner.stop.is_set())
        self.assertTrue(self.runner.errors.empty())

        # call the method
        with self.assertRaises(MyError):
            self.runner.run_safe(self.WorkerError)

        # post assertions
        self.assertTrue(self.runner.stop.is_set())
        self.assertTrue(self.runner.errors.empty())
