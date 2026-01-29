from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.exceptions import ValidationError

from core.choices import JobStatusChoices

from .models import FortiGateScheduler
from .choices import ScheduleModeChoices
from .jobs import compute_next_run
from .registry import RUNNER_REGISTRY, get_runner


def _delete_pending(schedule: FortiGateScheduler) -> None:
    """
    Delete all queued/scheduled jobs for this schedule across ALL registered runners.
    """
    for runner in RUNNER_REGISTRY.values():
        runner.get_jobs(instance=schedule).filter(
            status__in=JobStatusChoices.ENQUEUED_STATE_CHOICES
        ).delete()


@receiver(post_save, sender=FortiGateScheduler)
def sync_jobs(sender, instance: FortiGateScheduler, **kwargs):
    _delete_pending(instance)

    if not instance.enabled:
        return

    runner = get_runner(instance.job_type)

    if instance.schedule_mode == ScheduleModeChoices.INTERVAL:
        if not instance.interval_minutes or instance.interval_minutes < 1:
            raise ValidationError({"interval_minutes": "Interval must be >= 1 minute."})

        runner.enqueue_once(
            instance=instance,
            name=runner.name,
            schedule_at=None,
            interval=instance.interval_minutes,
            schedule_id=instance.pk,
            data={
                "trigger": "scheduler",
                "schedule_id": instance.pk,
                "schedule_name": instance.name,
                "job_type": instance.job_type,
            },
        )
        return

    if instance.schedule_mode == ScheduleModeChoices.CRON:
        next_dt = compute_next_run(instance).dt
        runner.enqueue_once(
            instance=instance,
            name=runner.name,
            schedule_at=next_dt,
            interval=None,
            schedule_id=instance.pk,
            data={
                "trigger": "scheduler",
                "schedule_id": instance.pk,
                "schedule_name": instance.name,
                "job_type": instance.job_type,
            },
        )
        return

    raise ValidationError({"schedule_mode": f"Unsupported mode: {instance.schedule_mode!r}"})


@receiver(post_delete, sender=FortiGateScheduler)
def cleanup_jobs(sender, instance: FortiGateScheduler, **kwargs):
    _delete_pending(instance)
