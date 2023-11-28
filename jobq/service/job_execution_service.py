from jobq.logger import logger
from jobq.models.job import Job, JobType


class JobExecutionService:
    @staticmethod
    async def execute(job: Job):
        match job.job_type:
            case JobType.JOB_TYPE_1.value:
                logger.info("Executing code for JOB TYPE 1")
            case JobType.JOB_TYPE_2.value:
                logger.info("Executing code for JOB TYPE 2")
            case _:
                logger.error(f"Route for job type {job.job_type} not found")
