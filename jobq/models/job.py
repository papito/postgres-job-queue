import datetime
from enum import Enum
from json import loads
from typing import Optional, Type

from pydantic import BaseModel

from jobq.constants import Const


class JobType(Enum):
    JOB_TYPE_1 = "JOB_TYPE_1"
    JOB_TYPE_2 = "JOB_TYPE_2"


class Job(BaseModel):
    id: Optional[str]
    job_type: JobType
    tries: int = 0
    max_retries: int = Const.Jobs.MAX_RETRIES
    base_retry_minutes: int = Const.Jobs.BASE_RETRY_MINUTES
    ripe_at: Optional[datetime.datetime]
    arguments: dict[str, int | str | bool] = {}
    completed: bool = False

    class Config:
        populate_by_name = True  # to allow value assignment by snake AND camelCase
        use_enum_values = True  # to use enum_instance.value during serialization to JSON and dict

    @classmethod
    def from_db(cls: Type["Job"], db_data: dict) -> "Job":
        db_data["arguments"] = loads(db_data["arguments"])
        return Job.model_validate(db_data)

    def update_for_next_retry(self) -> None:
        next_retry_minutes = self.base_retry_minutes * pow(self.tries, 2)
        self.ripe_at = datetime.datetime.now() + datetime.timedelta(minutes=next_retry_minutes)

    def runs_in(self, minutes: int = 0, hours: int = 0) -> "Job":
        if self.ripe_at:
            raise RuntimeError(f"Job ripe_at time is already set at: {self.ripe_at}")

        if minutes + hours == 0:
            raise RuntimeError("Need minutes, hours, or both")

        self.ripe_at = datetime.datetime.now() + datetime.timedelta(minutes=minutes, hours=hours)
        return self

    def __str__(self):
        return (
            f"Job: {self.id}. Type: {self.job_type}. "
            f"Ripe at {self.ripe_at}. "
            f"Tries: {self.max_retries}, starting in {self.base_retry_minutes} minutes. "
            f"Arguments: {self.arguments}"
        )
