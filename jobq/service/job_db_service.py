import datetime
import json
import re
from typing import Optional

from asyncpg import Connection  # type: ignore
from quart import has_request_context, request

from jobq.db import db
from jobq.logger import logger
from jobq.models.job import Job
from jobq.transaction import read_transaction, write_transaction


class JobDbService:
    """
    Data access layer for raw Squeel
    """

    @staticmethod
    async def execute_with_result(stmt: str, *args) -> Optional[dict]:
        conn: Connection = db.connection_manager.get_connection()
        log_stmt = re.sub(" +", " ", stmt.replace("\n", "")[0:80])

        if has_request_context():
            worker_id = getattr(request, "index", 0)
            logger.info(f"Worker #{worker_id} executing [{log_stmt}...]")
        else:
            # not executed in a worker
            logger.info(f"Executing [{log_stmt}...]")

        results = await conn.fetch(stmt, *args)

        if not results:
            return None

        assert len(results) < 2
        result: dict = results[0]
        return dict(result)

    @staticmethod
    async def execute_with_results(stmt, *args) -> list[dict]:
        conn: Connection = db.connection_manager.get_connection()
        log_stmt = re.sub(" +", " ", stmt.replace("\n", "")[0:80])

        if has_request_context():
            worker_id = getattr(request, "index", 0)
            logger.info(f"Worker #{worker_id} executing [{log_stmt}...]")
        else:
            # not executed in a worker
            logger.info(f"Executing [{log_stmt}...]")

        results = await conn.fetch(stmt, *args)
        return [dict(x) for x in results]

    @write_transaction
    async def save(self, obj: Job) -> Job:
        res = await self.execute_with_result(
            """
           INSERT INTO job (job_type, arguments, ripe_at, tries, max_retries, base_retry_minutes)
                VALUES ($1, $2, $3, $4, $5, $6)
           ON CONFLICT (unique_signature)
         DO UPDATE SET job_type = $1
             RETURNING id::text
            """,
            obj.job_type,
            json.dumps(obj.arguments),
            obj.ripe_at,
            obj.tries,
            obj.max_retries,
            obj.base_retry_minutes,
        )
        assert res

        job: Job = Job.model_validate(obj)
        job.id = res["id"]

        logger.info(f"Job SCHEDULED. {job}")

        return job

    @write_transaction
    async def get_one_ripe_job(self) -> Optional[Job]:
        result = await self.execute_with_result(
            """
            DELETE FROM job
                  WHERE id = (
                             SELECT id FROM job
                              WHERE ripe_at IS NULL OR $1 >= ripe_at
                         FOR UPDATE
                        SKIP LOCKED LIMIT 1
                  )
              RETURNING *, id::text
            """,
            datetime.datetime.now(),
        )

        if not result:
            return None

        return Job.from_db(result)

    @read_transaction
    async def get_all_jobs(self) -> list[Job]:
        results = await self.execute_with_results("SELECT *, id::text FROM job")

        jobs: list[Job] = []
        for result in results:
            jobs.append(Job.from_db(result))

        return jobs
