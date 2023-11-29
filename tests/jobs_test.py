import datetime
import importlib
import importlib.resources
import os
import unittest
from typing import Optional
from unittest.mock import patch

import asyncpg  # type: ignore
import psycopg2
import pytest
import quart
from asyncpg import Connection
from asyncpg.transaction import Transaction  # type: ignore
from freezegun import freeze_time
from quart import Quart

import jobq.service
from jobq import create_app, db
from jobq.constants import Const
from jobq.job_worker import JobWorker
from jobq.models.job import Job, JobType


@pytest.mark.asyncio
class JobsTest(unittest.IsolatedAsyncioTestCase):
    conn: Connection
    transaction: Transaction

    @classmethod
    def setUpClass(cls) -> None:
        conn = psycopg2.connect(
            database=os.environ.get(Const.Config.DB.DB_NAME),
            user=os.environ.get(Const.Config.DB.DB_USER),
            password=os.environ.get(Const.Config.DB.DB_PASSWORD),
            host=os.environ.get(Const.Config.DB.DB_HOST),
            port=os.environ.get(Const.Config.DB.DB_PORT),
        )
        sql = importlib.resources.files("jobq").joinpath("schema.sql").read_text()
        with conn.cursor() as cur:
            cur.execute("".join(sql))  # type: ignore
            conn.commit()
        conn.close()

    async def asyncSetUp(self) -> None:
        self.app: Quart = create_app()
        self.client = self.app.test_client()

        self.ctx: quart.ctx.AppContext = self.app.app_context()
        await self.ctx.push()

        self.conn = await asyncpg.connect(
            database=os.environ.get(Const.Config.DB.DB_NAME),
            user=os.environ.get(Const.Config.DB.DB_USER),
            password=os.environ.get(Const.Config.DB.DB_PASSWORD),
            host=os.environ.get(Const.Config.DB.DB_HOST),
            port=os.environ.get(Const.Config.DB.DB_PORT),
            server_settings={"jit": "off"},
        )

        db.connection_manager.set_connection(self.conn)

        self.transaction = self.conn.transaction()
        await self.transaction.start()

    async def asyncTearDown(self) -> None:
        await self.transaction.rollback()
        await self.conn.close()
        await self.ctx.pop()

    async def test_save_and_fetch_immediate_job(self):
        job: Job = Job(
            job_type=JobType.JOB_TYPE_1,
            arguments={"int_arg": 1, "str_arg": "string", "bool_arg": True},
        )

        await jobq.service.job_db.save(job)
        saved_job: Optional[Job] = await jobq.service.job_db.get_one_ripe_job()
        assert saved_job

        assert saved_job.job_type == job.job_type
        assert saved_job.arguments["int_arg"] == job.arguments["int_arg"]
        assert saved_job.arguments["str_arg"] == job.arguments["str_arg"]
        assert saved_job.arguments["bool_arg"] == job.arguments["bool_arg"]

    async def test_save_and_fetch_immediate_and_future_jobs(self):
        immediate_job: Job = Job(
            job_type=JobType.JOB_TYPE_1,
            arguments={"int_arg": 1, "str_arg": "string", "bool_arg": True},
        )

        job: Job = Job(
            job_type=JobType.JOB_TYPE_2,
            arguments={"int_arg": 2, "str_arg": "string", "bool_arg": True},
        ).runs_in(hours=4)

        far_later_job: Job = Job(
            job_type=JobType.JOB_TYPE_2,
            arguments={"int_arg": 3, "str_arg": "string", "bool_arg": True},
        ).runs_in(hours=8)

        now = datetime.datetime.now()
        saved_immediate_job: Job = await jobq.service.job_db.save(immediate_job)
        saved_job: Job = await jobq.service.job_db.save(job)
        saved_later_job: Job = await jobq.service.job_db.save(far_later_job)

        pulled_job: Optional[Job] = await jobq.service.job_db.get_one_ripe_job()
        assert pulled_job
        # this should be the immediate job
        assert pulled_job.id == saved_immediate_job.id

        # no jobs for now
        pulled_job = await jobq.service.job_db.get_one_ripe_job()
        assert not pulled_job

        # jump to the FUTURE
        with freeze_time(now + datetime.timedelta(hours=2)):
            pulled_job = await jobq.service.job_db.get_one_ripe_job()
            assert not pulled_job

        with freeze_time(now + datetime.timedelta(hours=5, minutes=5)):
            pulled_job = await jobq.service.job_db.get_one_ripe_job()
            assert pulled_job
            assert pulled_job.id == saved_job.id

        with freeze_time(now + datetime.timedelta(hours=20, minutes=5)):
            pulled_job = await jobq.service.job_db.get_one_ripe_job()
            assert pulled_job
            assert pulled_job.id == saved_later_job.id

    async def test_default_max_retries(self):
        job: Job = Job(
            job_type=JobType.JOB_TYPE_2,
            base_retry_minutes=0,
        )

        await jobq.service.job_db.save(job)

        worker = JobWorker(worker_id=0, app=self.app)

        with patch("jobq.service.job_execution.execute", side_effect=AssertionError("LOL")):
            for try_num in range(0, Const.Jobs.MAX_RETRIES + 1):
                processed_job: Optional[Job] = await worker.pull_and_execute()
                assert processed_job
                assert processed_job.tries == try_num + 1

        # no more retries left - the job should be no longer in the queue
        processed_job = await worker.pull_and_execute()
        assert not processed_job

    async def test_custom_max_retries(self):
        custom_max_retries = 2

        job: Job = Job(
            job_type=JobType.JOB_TYPE_2,
            max_retries=custom_max_retries,
            base_retry_minutes=0,
        )

        await jobq.service.job_db.save(job)

        worker = JobWorker(worker_id=0, app=self.app)

        with patch("jobq.service.job_execution.execute", side_effect=AssertionError("LOL")):
            processed_job: Optional[Job] = await worker.pull_and_execute()
            assert processed_job
            assert processed_job.tries == 1

            for retry_num in range(1, custom_max_retries + 1):
                processed_job = await worker.pull_and_execute()
                assert processed_job
                assert processed_job.tries == retry_num + 1

        # no more retries left - the job should be no longer in the queue
        processed_job = await worker.pull_and_execute()
        assert not processed_job

    async def test_no_retries(self):
        job: Job = Job(
            job_type=JobType.JOB_TYPE_1,
            max_retries=0,
        )

        await jobq.service.job_db.save(job)

        worker = JobWorker(worker_id=0, app=self.app)

        with patch("jobq.service.job_execution.execute", side_effect=AssertionError("LOL")):
            await worker.pull_and_execute()

        # job should be no longer in queue
        processed_job: Optional[Job] = await worker.pull_and_execute()
        assert not processed_job

    async def test_one_retry(self):
        job: Job = Job(
            job_type=JobType.JOB_TYPE_2,
            base_retry_minutes=0,
        )

        await jobq.service.job_db.save(job)

        worker = JobWorker(worker_id=0, app=self.app)

        with patch("jobq.service.job_execution.execute", side_effect=AssertionError("LOL")):
            await worker.pull_and_execute()

        processed_job: Optional[Job] = await worker.pull_and_execute()
        assert processed_job
        assert processed_job.completed

        pulled_job: Optional[Job] = await worker.pull_and_execute()
        # job should be no longer in queue
        assert not pulled_job

    async def test_retry_delays(self):
        job: Job = Job(
            job_type=JobType.JOB_TYPE_1,
            base_retry_minutes=20,
            max_retries=3,
        )

        await jobq.service.job_db.save(job)

        now = datetime.datetime.now()
        worker = JobWorker(worker_id=0, app=self.app)

        #
        # The succession should 20 minutes, 80 minutes, 180 minutes
        #
        with patch("jobq.service.job_execution.execute", side_effect=RuntimeError("LOL")):
            # FIRST TRY
            processed_job: Optional[Job] = await worker.pull_and_execute()
            assert processed_job
            assert not processed_job.completed

            # # job is on delay - should not process
            processed_job = await worker.pull_and_execute()
            assert not processed_job

            # FIRST RETRY
            with freeze_time(now + datetime.timedelta(minutes=20 + 2)):
                processed_job = await worker.pull_and_execute()
                assert processed_job

            with freeze_time(now + datetime.timedelta(minutes=70)):  # from first try
                # not ripe yet
                processed_job = await worker.pull_and_execute()
                assert not processed_job

            # SECOND RETRY
            with freeze_time(now + datetime.timedelta(minutes=20 + 80 + 2)):
                processed_job = await worker.pull_and_execute()
                assert processed_job
            with freeze_time(now + datetime.timedelta(minutes=20 + 80 + 10)):  # from first try
                # not ripe yet
                processed_job = await worker.pull_and_execute()
                assert not processed_job

            # THIRD RETRY
            with freeze_time(now + datetime.timedelta(minutes=20 + 80 + 180 + 2)):  # from first try
                processed_job = await worker.pull_and_execute()
                assert processed_job

                # no more retries left
                processed_job = await worker.pull_and_execute()
                assert not processed_job

    async def test_duplicate_job_is_silently_ignored(self):
        job1: Job = Job(
            job_type=JobType.JOB_TYPE_2,
            arguments={"int_arg": 1, "str_arg": "string", "bool_arg": True},
        )

        job2: Job = Job(
            job_type=JobType.JOB_TYPE_1,
            arguments={"int_arg": 1, "str_arg": "string", "bool_arg": True},
        ).runs_in(hours=4)

        await jobq.service.job_db.save(job1)
        await jobq.service.job_db.save(job2)
