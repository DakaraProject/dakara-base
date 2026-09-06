from queue import Queue
from threading import Event
from time import sleep
from unittest.mock import MagicMock

import pytest

from dakara_base.safe_workers import (
    BaseSafeThread,
    BaseWorker,
    Runner,
    SafeThread,
    SafeTimer,
    Worker,
    WorkerSafeThread,
    WorkerSafeTimer,
    safe,
)
from dakara_base.safe_workers.testing import assert_worker_no_errors


class DummyError(Exception):
    pass


def dummy_function_safe():
    return


def dummy_function_error():
    raise DummyError


class DummySafeThread(BaseSafeThread):
    @safe
    def function_safe(self):
        dummy_function_safe()

    @safe
    def function_error(self):
        dummy_function_error()


class DummySafeWorker(BaseWorker):
    @safe
    def function_safe(self):
        dummy_function_safe()

    @safe
    def function_error(self):
        dummy_function_error()


class DummyUnsafe:
    @safe
    def function_safe(self):
        dummy_function_safe()

    @safe
    def function_error(self):
        dummy_function_error()


@pytest.fixture
def dummy_safe_thread():
    return DummySafeThread(Event(), Queue())


@pytest.fixture
def dummy_safe_worker():
    return DummySafeWorker(Event(), Queue())


@pytest.fixture
def dummy_unsafe():
    return DummyUnsafe()


@pytest.fixture
def get_safe_thread():
    def fun(target):
        return SafeThread(Event(), Queue(), target=target)

    return fun


@pytest.fixture
def get_safe_timer():
    def fun(target, interval=0):
        return SafeTimer(Event(), Queue(), interval, target)

    return fun


@pytest.fixture
def worker():
    return Worker(Event(), Queue())


class DummyWorkerSafeTimer(WorkerSafeTimer):

    def function_already_dead(self):
        return

    def function_to_cancel(self):
        # call itself in loop
        self.set_timer(0.1, self.function_to_cancel)
        assert self.timer is not None
        self.timer.start()

    def function_to_join(self):
        sleep(0.1)

    def function_error(self):
        raise DummyError


@pytest.fixture
def dummy_worker_safe_timer():
    return DummyWorkerSafeTimer(Event(), Queue())


class DummyWorkerSafeThread(WorkerSafeThread):

    def function_already_dead(self):
        return

    def function_to_join(self):
        sleep(0.1)

    def function_error(self):
        raise DummyError("test error")


@pytest.fixture
def dummy_worker_safe_thread():
    return DummyWorkerSafeThread(Event(), Queue())


@pytest.fixture
def runner():
    return Runner()


class DummyWorkerSafeThreadNormal(WorkerSafeThread):

    def init_worker(self):
        self.set_thread(target=self.test)

    def test(self):
        pass


class DummyWorkerSafeThreadError(WorkerSafeThread):

    def init_worker(self):
        self.set_thread(target=self.test)

    def test(self):
        raise DummyError("test error")


class TestSafeDecorator:
    def test_safe_worker(self, dummy_safe_worker):
        """Test a safe function of a worker.

        Test that a non-error function does not trigger any error, does not set
        the stop event and does not put an error in the error queue.
        """
        # pre assertions
        assert not dummy_safe_worker.stop.is_set()
        assert_worker_no_errors(dummy_safe_worker)

        # call the method
        dummy_safe_worker.function_safe()

        # post assertions
        assert not dummy_safe_worker.stop.is_set()
        assert_worker_no_errors(dummy_safe_worker)

    def test_safe_worker_error(self, dummy_safe_worker):
        """Test an error function of a worker.

        Test that an error function does not trigger any error, sets the stop
        event and puts a DummyError in the error queue.
        """
        # pre assertions
        assert not dummy_safe_worker.stop.is_set()
        assert_worker_no_errors(dummy_safe_worker)

        # call the method
        dummy_safe_worker.function_error()

        # post assertions
        assert dummy_safe_worker.stop.is_set()
        assert not dummy_safe_worker.errors.empty()
        _, error, _ = dummy_safe_worker.errors.get()
        assert isinstance(error, DummyError)

    def test_safe_thread(self, dummy_safe_thread):
        """Test a thread.

        Test that a non-error function does not trigger any error, does not set
        the stop event and does not put an error in the error queue.
        """
        # pre assertions
        assert not dummy_safe_thread.stop.is_set()
        assert_worker_no_errors(dummy_safe_thread)

        # call the method
        dummy_safe_thread.function_safe()

        # post assertions
        assert not dummy_safe_thread.stop.is_set()
        assert_worker_no_errors(dummy_safe_thread)

    def test_safe_thread_error(self, dummy_safe_thread):
        """Test a thread with an error."""
        # pre assertions
        assert not dummy_safe_thread.stop.is_set()
        assert_worker_no_errors(dummy_safe_thread)

        # call the method
        dummy_safe_thread.function_error()

        # post assertions
        assert dummy_safe_thread.stop.is_set()
        with pytest.raises(
            AssertionError, match="Worker .* is in failed state:\n.*DummyError"
        ):
            assert_worker_no_errors(dummy_safe_thread)

    def test_unsafe(self, dummy_unsafe):
        """Test an unsafe class.

        Test that the decorator raises an error, as the class is not supported.
        """
        # call the method
        with pytest.raises(AssertionError):
            dummy_unsafe.function_safe()

    def test_unsafe_error(self, dummy_unsafe):
        """Test an unsafe class.

        Test that the decorator raises an error, as the class is not supported.
        """
        # call the method
        with pytest.raises(AssertionError):
            dummy_unsafe.function_error()


class TestSafeThread:
    def test_function_safe(self, get_safe_thread):
        """Test a safe function.

        Test that a non-error function run as a thread does not trigger any
        error, does not set the stop event and does not put an error in the
        error queue.
        """
        safe_thread = get_safe_thread(dummy_function_safe)

        # pre assertions
        assert not safe_thread.stop.is_set()
        assert_worker_no_errors(safe_thread)

        # run thread
        safe_thread.start()
        safe_thread.join()

        # post assertions
        assert not safe_thread.stop.is_set()
        assert_worker_no_errors(safe_thread)

    def test_function_error(self, get_safe_thread):
        """Test an error function.

        Test that an error function run as a thread does not trigger any error,
        sets the stop event and puts a DummyError in the error queue.
        """
        safe_thread = get_safe_thread(dummy_function_error)

        # pre assertions
        assert not safe_thread.stop.is_set()
        assert_worker_no_errors(safe_thread)

        # run thread
        safe_thread.start()
        safe_thread.join()

        # post assertions
        assert safe_thread.stop.is_set()
        assert not safe_thread.errors.empty()
        _, error, _ = safe_thread.errors.get()
        assert isinstance(error, DummyError)


class TestSafeTimer:
    def test_function_safe(self, get_safe_timer):
        """Test a safe function.

        Test that a non-error function run as a timer does not trigger any
        error, does not set the stop event and does not put an error in the
        error queue.
        """
        safe_timer = get_safe_timer(dummy_function_safe)

        # pre assertions
        assert not safe_timer.stop.is_set()
        assert_worker_no_errors(safe_timer)

        # run timer
        safe_timer.start()
        safe_timer.join()

        # post assertions
        assert not safe_timer.stop.is_set()
        assert_worker_no_errors(safe_timer)

    def test_function_error(self, get_safe_timer):
        """Test an error function.

        Test that an error function run as a timer does not trigger any error,
        sets the stop event and puts a DummyError in the error queue.
        """
        safe_timer = get_safe_timer(dummy_function_error)

        # pre assertions
        assert not safe_timer.stop.is_set()
        assert_worker_no_errors(safe_timer)

        # run timer
        safe_timer.start()
        safe_timer.join()

        # post assertions
        assert safe_timer.stop.is_set()
        assert not safe_timer.errors.empty()
        _, error, _ = safe_timer.errors.get()
        assert isinstance(error, DummyError)


class TestWorker:
    def test_run_safe(self, worker):
        """Test a safe run.

        Test that a worker used with no error does not produce any error,
        finishes with a triggered stop event and an empty error queue.
        """
        # pre assertions
        assert not worker.stop.is_set()
        assert_worker_no_errors(worker)

        # create and run worker
        with worker:
            dummy_function_safe()

        # post assertions
        assert worker.stop.is_set()
        assert_worker_no_errors(worker)

    def test_run_error(self, worker):
        """Test a run with error.

        Test that a worker used with error does produce an error, finishes with
        a triggered stop event and an empty error queue.
        """
        # pre assertions
        assert not worker.stop.is_set()
        assert_worker_no_errors(worker)

        # create and run worker
        with pytest.raises(DummyError):
            with worker:
                dummy_function_error()

        # there is no point continuing the test here

        # post assertions
        assert worker.stop.is_set()
        assert_worker_no_errors(worker)

    def test_run_thread_safe(self, worker):
        """Test a run with a safe thread.

        Test that a worker used with a non-error thread does not produce any
        error, finishes with a triggered stop event and an empty error queue.
        """
        # pre assertions
        assert not worker.stop.is_set()
        assert_worker_no_errors(worker)

        # create and run worker
        with worker:
            thread = worker.create_thread(target=dummy_function_safe)
            thread.start()
            thread.join()

        # post assertions
        assert worker.stop.is_set()
        assert_worker_no_errors(worker)

    def test_run_thread_error(self, worker):
        """Test a run with a thread with error.

        Test that a worker used with a thread with an error does not produce
        any error, finishes with a triggered stop event and a non-empty error
        queue.
        """
        # pre assertions
        assert not worker.stop.is_set()
        assert_worker_no_errors(worker)

        # create and run worker
        with worker:
            thread = worker.create_thread(target=dummy_function_error)
            thread.start()
            thread.join()

        # post assertions
        assert worker.stop.is_set()
        assert not worker.errors.empty()
        _, error, _ = worker.errors.get()
        assert isinstance(error, DummyError)


class TestWorkerSafeTimer:
    def test_run_timer_dead(self, dummy_worker_safe_timer):
        """Test to end a worker when its timer is dead.

        Test that a worker stopped with a dead timer finishes with a triggered
        stop event, an empty error queue and a still dead timer.
        """
        # pre assertions
        assert not dummy_worker_safe_timer.stop.is_set()
        assert_worker_no_errors(dummy_worker_safe_timer)

        # create and run worker
        with dummy_worker_safe_timer as worker:
            worker.set_timer(0.5, worker.function_already_dead)
            assert worker.timer is not None
            worker.timer.start()
            worker.timer.join()

        # post assertions
        assert dummy_worker_safe_timer.stop.is_set()
        assert_worker_no_errors(dummy_worker_safe_timer)
        assert not dummy_worker_safe_timer.timer.is_alive()

    def test_run_timer_cancelled(self, dummy_worker_safe_timer):
        """Test to end a deamon when its timer is waiting.

        Test that a worker stopped with a waiting timer finishes with a
        triggered stop event, an empty error queue and a dead timer.
        """
        # pre assertions
        assert not dummy_worker_safe_timer.stop.is_set()
        assert_worker_no_errors(dummy_worker_safe_timer)

        # create and run worker
        with dummy_worker_safe_timer as worker:
            worker.set_timer(0.5, worker.function_to_cancel)
            assert worker.timer is not None
            worker.timer.start()
            sleep(0.1)

        # post assertions
        assert dummy_worker_safe_timer.stop.is_set()
        assert_worker_no_errors(dummy_worker_safe_timer)
        assert not dummy_worker_safe_timer.timer.is_alive()
        assert dummy_worker_safe_timer.timer.finished.is_set()

    def test_run_timer_joined(self, dummy_worker_safe_timer):
        """Test to end a deamon when its timer is running.

        Test that a worker stopped with a running timer finishes with a
        triggered stop event, an empty error queue and a dead timer.
        """
        # pre assertions
        assert not dummy_worker_safe_timer.stop.is_set()
        assert_worker_no_errors(dummy_worker_safe_timer)

        # create and run worker
        with dummy_worker_safe_timer as worker:
            worker.set_timer(0.5, worker.function_to_join)
            assert worker.timer is not None
            worker.timer.start()
            sleep(0.1)

        # post assertions
        assert dummy_worker_safe_timer.stop.is_set()
        assert_worker_no_errors(dummy_worker_safe_timer)
        assert not dummy_worker_safe_timer.timer.is_alive()

    def test_uninitialized_timer(self, dummy_worker_safe_timer):
        """Test the timer must be initialized.

        Test that a worker with its default timer does not generate an error,
        but finishes with a triggered stop event and an non-empty error queue.
        """
        # pre assertions
        assert not dummy_worker_safe_timer.stop.is_set()
        assert_worker_no_errors(dummy_worker_safe_timer)

        # create and run worker
        with pytest.raises(AttributeError):
            with dummy_worker_safe_timer as worker:
                worker.timer.start()

        # post assertions
        assert dummy_worker_safe_timer.stop.is_set()
        assert_worker_no_errors(dummy_worker_safe_timer)

    def test_error_timer(self, dummy_worker_safe_timer):
        """Test the timer with an error callback.

        Test that a worker with its default timer does not generate an error,
        but finishes with a triggered stop event and an non-empty error queue.
        """
        # pre assertions
        assert not dummy_worker_safe_timer.stop.is_set()
        assert_worker_no_errors(dummy_worker_safe_timer)

        # create and run worker
        with dummy_worker_safe_timer as worker:
            worker.set_timer(0, worker.function_error)
            assert worker.timer is not None
            worker.timer.start()

        # post assertions
        assert dummy_worker_safe_timer.stop.is_set()
        assert not dummy_worker_safe_timer.errors.empty()
        _, error, _ = dummy_worker_safe_timer.errors.get()
        assert isinstance(error, DummyError)


class TestWorkerSafeThread:
    def test_run_thread_dead(self, dummy_worker_safe_thread):
        """Test to end a worker when its thread is dead.

        Test that a worker stopped with a dead thread finishes with a triggered
        stop event, an empty error queue and a still dead thread.
        """
        # pre assertions
        assert not dummy_worker_safe_thread.stop.is_set()
        assert_worker_no_errors(dummy_worker_safe_thread)

        # create and run worker
        with dummy_worker_safe_thread as worker:
            worker.set_thread(target=worker.function_already_dead)
            assert worker.thread is not None
            worker.thread.start()
            worker.thread.join()

        # post assertions
        assert dummy_worker_safe_thread.stop.is_set()
        assert_worker_no_errors(dummy_worker_safe_thread)
        assert not dummy_worker_safe_thread.thread.is_alive()

    def test_run_thread_joined(self, dummy_worker_safe_thread):
        """Test to end a deamon when its thread is running.

        Test that a worker stopped with a running thread finishes with a
        triggered stop event, an empty error queue and a dead thread.
        """
        # pre assertions
        assert not dummy_worker_safe_thread.stop.is_set()
        assert_worker_no_errors(dummy_worker_safe_thread)

        # create and run worker
        with dummy_worker_safe_thread as worker:
            worker.set_thread(target=worker.function_to_join)
            assert worker.thread is not None
            worker.thread.start()
            sleep(0.1)

        # post assertions
        assert dummy_worker_safe_thread.stop.is_set()
        assert_worker_no_errors(dummy_worker_safe_thread)
        assert not dummy_worker_safe_thread.thread.is_alive()

    def test_uninitialized_thread(self, dummy_worker_safe_thread):
        """Test the thread must be initialized.

        Test that a worker with its default thread does not generate an error,
        but finishes with a triggered stop event and an non-empty error queue.
        """
        # pre assertions
        assert not dummy_worker_safe_thread.stop.is_set()
        assert_worker_no_errors(dummy_worker_safe_thread)

        # create and run worker
        with pytest.raises(AttributeError):
            with dummy_worker_safe_thread as worker:
                worker.thread.start()

        # post assertions
        assert dummy_worker_safe_thread.stop.is_set()
        assert dummy_worker_safe_thread.errors.empty()

    def test_error_thread(self, dummy_worker_safe_thread):
        """Test the thread with an error.

        Test that a worker with its default thread does not generate an error,
        but finishes with a triggered stop event and an non-empty error queue.
        """
        # pre assertions
        assert not dummy_worker_safe_thread.stop.is_set()
        assert_worker_no_errors(dummy_worker_safe_thread)

        # create and run worker
        with dummy_worker_safe_thread as worker:
            worker.set_thread(target=worker.function_error)
            assert worker.thread is not None
            worker.thread.start()

        # post assertions
        assert dummy_worker_safe_thread.stop.is_set()
        assert not dummy_worker_safe_thread.errors.empty()
        _, error, _ = dummy_worker_safe_thread.errors.get()
        assert isinstance(error, DummyError)


class TestRunner:
    def test_run_safe_interrupt(self, runner):
        """Test a run with an interruption by KeyboardInterrupt exception.

        The run should end with a set stop event and an empty errors queue.
        """
        # pre assertions
        assert not runner.stop.is_set()
        assert_worker_no_errors(runner)

        # modify stop event wait method
        runner.stop.wait = MagicMock()
        runner.stop.wait.side_effect = KeyboardInterrupt

        # call the method
        runner.run_safe(DummyWorkerSafeThreadNormal)

        # post assertions
        assert runner.stop.is_set()
        assert_worker_no_errors(runner)

        # assert stop event wait method was called
        runner.stop.wait.assert_called_once()

    def test_run_safe_error(self, runner):
        """Test a run with an error.

        The run should raise a DummyError, end with a set stop event and an
        empty error queue.
        """
        # pre assertions
        assert not runner.stop.is_set()
        assert_worker_no_errors(runner)

        # call the method
        with pytest.raises(DummyError):
            runner.run_safe(DummyWorkerSafeThreadError)

        # post assertions
        assert runner.stop.is_set()
        assert_worker_no_errors(runner)


class TestAssentWorkerNoErrors:
    def test(self, dummy_safe_worker):
        """Test assert function with error"""
        dummy_safe_worker.function_safe()
        assert_worker_no_errors(dummy_safe_worker)

    def test_error(self, dummy_safe_worker):
        """Test assert function with error"""
        dummy_safe_worker.function_error()

        with pytest.raises(
            AssertionError, match="Worker .* is in failed state:\n.*DummyError"
        ):
            assert_worker_no_errors(dummy_safe_worker)
