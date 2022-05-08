import os
import platform
import signal
import subprocess
from importlib.resources import path
from time import sleep
from unittest import TestCase, skipIf, skipUnless

from path import Path, TempDir

import dakara_base  # noqa F401


class RunnerIntegrationTestCase(TestCase):
    IS_SUBPROCESS_SAME_ENV = (
        platform.system() != "Windows" or "SUBPROCESS_SAME_ENV_TEST" in os.environ
    )
    IS_BATCH_JOB = platform.system() == "Windows" and "BATCH_JOB_TEST" in os.environ

    @staticmethod
    def wait_output(process, line, interval=0.1):
        """Wait a process to output a line.

        Beware this method consumes the lines from the process, so they will
        not be included in `process.communicate()`.

        Args:
            process (subprocess.Popen): Process to evaluate.
            line (str): Line of text to obtain to process output.
            interval (float): Interval in seconds between two evaluations.

        Returns:
            list of str: Lines outputed by the process before the expected one
            showed up.
        """
        lines = []
        while process.poll() is None:
            sleep(interval)
            out = process.stdout.readline()
            if not out:
                continue

            lines.append(out.strip())

            if line in lines:
                return lines

    @skipUnless(
        IS_SUBPROCESS_SAME_ENV,
        "Can only be tested if subprocess environment is same as current environment",
    )
    @skipIf(IS_BATCH_JOB, "Can only be tested if script is not launched in batch job")
    def test_run_safe_signal(self):
        """Test to send an interruption signal to a runner."""
        with TempDir() as tempdir:
            with path("tests.resources", "empty_runner.py") as resource_path:
                file_path = Path(resource_path).copy(tempdir)

            process = subprocess.Popen(
                ["python", "-u", str(file_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            start_lines = self.wait_output(process, "starting worker")

            system = platform.system()
            if system == "Windows":
                process.send_signal(signal.CTRL_C_EVENT)

            else:
                process.send_signal(signal.SIGINT)

            out, _ = process.communicate()
            end_lines = out.splitlines()
            self.assertListEqual(start_lines, ["starting runner", "starting worker"])
            self.assertListEqual(end_lines, ["ending worker", "ending runner"])

            self.assertEqual(process.returncode, 0)
