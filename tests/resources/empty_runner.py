from dakara_base.safe_workers import Runner, WorkerSafeThread


class MyWorker(WorkerSafeThread):
    def init_worker(self):
        self.thread = self.create_thread(target=self.run_thread)

    def run_thread(self):
        print("starting worker")
        self.stop.wait()
        print("ending worker")


class MyRunner(Runner):
    def run(self):
        print("starting runner")
        self.run_safe(MyWorker)
        print("ending runner")


if __name__ == "__main__":
    runner = MyRunner()
    runner.run()
