import asyncio
import logging
import os
from typing import Optional

from quart import Quart, request
from siftlog import SiftLog  # type: ignore

import jobq.service
from jobq.constants import Const
from jobq.models.job import Job
from jobq.transaction import write_transaction


class JobWorker:
    app: Quart
    worker_id: int
    logger: SiftLog
    _stop_flag: bool
    stopped: bool
    polling_interval = int(os.environ.get(Const.Config.POLLING_INTERVAL, 5))
    # after each X sleep cycles, the worker will squak
    sound_off_every_cycles = 100

    def __init__(self, worker_id, app: Quart):
        self._stop_flag = False
        self.worker_id = worker_id
        self.stopped = True
        self.app = app

        core_logger = logging.getLogger(Const.LOG_NAME)

        # A worker has its own log instance as it has persistent properties to be logged (worker id)
        self.logger = SiftLog(
            core_logger,
            worker_id=f"#{self.worker_id}",
        )

    def request_stop(self):
        self.logger.info("Telling worker to stop")
        self._stop_flag = True

    async def run(self):
        self.logger.info("Starting worker")
        self.stopped = False

        sound_off_cycles = 0

        while not self._stop_flag:
            sound_off_cycles = sound_off_cycles + 1
            if sound_off_cycles >= self.sound_off_every_cycles:
                self.logger.info("Worker is still in the fight!")
                sound_off_cycles = 0

            await asyncio.sleep(self.polling_interval)

            if self._stop_flag:
                continue

            # A little unorthodox to use a test method, but it's just a wrapper that sets
            # the boring defaults to create request context (we need access to Quart.g - global
            # request context - to store connection info in)
            async with self.app.test_request_context("/job_worker"):
                setattr(request, "index", self.worker_id)
                await self.pull_and_execute()

        self.stopped = True
        self.logger.info("Worker is done")

    async def pull_and_execute(self) -> Optional[Job]:
        try:
            return await self._pull_and_execute()
        except Exception as ex:
            # important to swallow all exceptions so the worker does not exit
            self.logger.exception(str(ex))

        return None

    @write_transaction
    async def _pull_and_execute(self) -> Optional[Job]:
        job: Optional[Job] = None

        try:
            job = await jobq.service.job_db.get_one_ripe_job()
        except Exception as ex:
            self.logger.error("Failed to pull a job from queue")
            self.logger.exception(str(ex))

        if not job:
            self.logger.info("No ripe jobs for worker :(")
            return None

        self.logger.info(f"We have a JOB TO DO of type [{job.job_type}]")

        try:
            await jobq.service.job_execution.execute(job)
            job.completed = True
            self.logger.info("Job succeeded")
        except Exception as ex:
            self.logger.warn("Job did not succeed")
            self.logger.exception(str(ex))

        # if the job did not succeed, reschedule a retry if any, and bail
        try:
            if not job.completed:
                job.tries = job.tries + 1
                if job.tries < job.max_retries + 1:
                    self.logger.info(f"Scheduling retry {job.tries + 1}")
                    job.update_for_next_retry()
                    await jobq.service.job_db.save(job)
        except Exception as ex:
            self.logger.exception(str(ex))

        return job
