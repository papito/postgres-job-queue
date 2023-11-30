from jobq.logger import logger
from jobq.models.job import Job, JobType


class JobExecutionService:
    """
    A job router - connecting the job type to the actual code that runs it.
    """

    @staticmethod
    async def execute(job: Job):
        match job.job_type:
            case JobType.JOB_TYPE_1.value:
                logger.info(f"Executing code for JOB TYPE 1, job {job.id}")
            case JobType.JOB_TYPE_2.value:
                logger.info(f"Executing code for JOB TYPE 2, job {job.id}")
            case _:
                logger.error(f"Route for job type {job.job_type} not found")
