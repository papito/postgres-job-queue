import asyncio
import os
from typing import Optional

from quart import Quart, request

import jobq.service
from jobq.constants import Const
from jobq.logger import logger
from jobq.models.job import Job
from jobq.transaction import write_transaction


class JobWorker:
    app: Quart
    worker_id: int
    _stop_flag: bool
    stopped: bool
    polling_interval = int(os.environ.get(Const.Config.POLLING_INTERVAL, 5))
    sound_off_every_cycles = 100

    def __init__(self, worker_id, app: Quart):
        self._stop_flag = False
        self.worker_id = worker_id
        self.stopped = True
        self.app = app

    def request_stop(self):
        logger.info(f"Telling worker #{self.worker_id} to stop")
        self._stop_flag = True

    async def run(self):
        logger.info(f"Starting worker #{self.worker_id}")
        self.stopped = False

        cycles = 0

        while not self._stop_flag:
            cycles = cycles + 1
            if cycles >= self.sound_off_every_cycles:
                logger.info(f"WORKER {self.worker_id} is still in the fight!")
                cycles = 0

            await asyncio.sleep(self.polling_interval)

            if self._stop_flag:
                continue

            # A little unorthodox to use a test method, but it's just a wrapper that sets
            # the boring defaults to create request context (we need access to Quart.g - global
            # request context - so store connection info in)
            async with self.app.test_request_context("/job_worker"):
                setattr(request, "index", self.worker_id)
                await self.pull_and_execute()

        self.stopped = True
        logger.info(f"Worker {self.worker_id} is done")

    async def pull_and_execute(self) -> Optional[Job]:
        try:
            return await self._pull_and_execute()
        except Exception as ex:
            logger.exception(str(ex))

        return None

    @write_transaction
    async def _pull_and_execute(self) -> Optional[Job]:
        job: Optional[Job] = None
        try:
            job = await jobq.service.job.get_one_ripe_job()
        except Exception as ex:
            logger.error("Failed to pull a job from queue")
            logger.exception(str(ex))

        if not job:
            logger.info(f"No jobs on worker [{self.worker_id}]")
            return None

        logger.info(f"We have a JOB TO DO of type [{job.job_type}]")

        try:
            logger.info("About to rumble")
            await jobq.service.job_execution.execute(job)
            job.completed = True
            logger.info("Job succeeded")
        except Exception as ex:
            logger.warn("Job did not succeed")
            logger.exception(str(ex))

        # if the job did not succeed, reschedule a retry if any, and bail
        try:
            if not job.completed:
                job.tries = job.tries + 1
                if job.tries < job.max_retries + 1:
                    logger.info(f"Scheduling retry {job.tries + 1}")
                    job.update_for_next_retry()
                    await jobq.service.job.save(job)
        except Exception as ex:
            logger.exception(str(ex))

        return job
