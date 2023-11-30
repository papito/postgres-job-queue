import asyncio
import os

from quart import Quart

from jobq.constants import Const
from jobq.job_worker import JobWorker
from jobq.logger import logger


class JobWorkerService:
    """
    Orchestrates worker background tasks
    """

    workers: list[JobWorker] = []

    def start(self, app: Quart):
        worker_count = int(os.environ.get(Const.Config.WORKER_COUNT, 0))

        for _ in range(0, worker_count):
            worker = JobWorker(worker_id=_ + 1, app=app)
            app.add_background_task(worker.run)
            self.workers.append(worker)

        if not self.workers:
            logger.warn("NO JOBS ARE RUNNING")

    async def stop(self):
        if not self.workers:
            return

        for worker in self.workers:
            worker.request_stop()

        while not all([w.stopped for w in self.workers]):
            logger.info("Waiting for all workers to stop...")
            await asyncio.sleep(1)

        logger.info("All workers have stopped")
