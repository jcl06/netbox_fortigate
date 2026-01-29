from __future__ import annotations

from typing import Type

from django.core.exceptions import ValidationError
from netbox.jobs import JobRunner

from .choices import JobTypeChoices
from .jobs import FortiGateInventoryPullRunner, FortiGateRequestRunner


RUNNER_REGISTRY: dict[str, Type[JobRunner]] = {
    JobTypeChoices.INVENTORY_PULL: FortiGateInventoryPullRunner,
    JobTypeChoices.IMPLEMENT_REQUEST: FortiGateRequestRunner,
}


def get_runner(job_type: str) -> Type[JobRunner]:
    try:
        return RUNNER_REGISTRY[job_type]
    except KeyError as exc:
        raise ValidationError({"job_type": f"No runner registered for job_type={job_type!r}"}) from exc
