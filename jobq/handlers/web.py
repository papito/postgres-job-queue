import datetime
import random
import traceback
import uuid

from quart import Blueprint, redirect, render_template, render_template_string, url_for

import jobq.service
from jobq.logger import logger
from jobq.models.job import Job, JobType
from jobq.transaction import read_transaction, write_transaction

web = Blueprint(
    "web",
    __name__,
    static_folder="assets",
    template_folder="templates",
)


@web.errorhandler(Exception)
async def handle_unknown_exception(ex: Exception) -> tuple[str, int]:
    logger.exception(str(ex))
    msg = "".join(traceback.format_exception(type(ex), value=ex, tb=ex.__traceback__))
    logger.critical(msg)

    return await render_template_string(f"{ex.__class__.__name__}: {str(ex)}"), 500


@web.route("/favicon.ico")
async def favicon():
    return redirect(url_for("static", filename="images/favicon.ico"), code=302)


@web.get("/")
@read_transaction
async def index():
    jobs: list[Job] = await jobq.service.job_db.get_all_jobs()
    workers = jobq.service.job_worker.workers

    now = datetime.datetime.utcnow()
    return await render_template("index.html", jobs=jobs, workers=workers, time=now.strftime("%H:%M:%S"))


@web.get("/create")
@write_transaction
async def create():
    job_type: JobType = random.choice([JobType.JOB_TYPE_1, JobType.JOB_TYPE_2])

    job: Job = Job(
        job_type=job_type,
        # The arbitrary argument must be unique because the schema does not allow the same job
        # type with the same arguments.
        # This restriction of course can be removed by deleting the index
        arguments={
            "arbitrary_arg_1": str(uuid.uuid4()),
        },
    ).runs_in(minutes=random.choice([1, 2, 3]))

    await jobq.service.job_db.save(job)

    return redirect(url_for("web.index"))
