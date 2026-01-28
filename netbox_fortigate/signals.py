from __future__ import annotations

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from core.choices import JobStatusChoices

from .jobs import FortiGateRunner, compute_next_run
from .models import FortiGateScheduler


def _delete_pending_jobs(schedule: FortiGateScheduler) -> None:
    """
    Remove any enqueued/scheduled jobs that haven't started yet for this schedule.
    """
    FortiGateRunner.get_jobs(instance=schedule).filter(
        status__in=JobStatusChoices.ENQUEUED_STATE_CHOICES
    ).delete()


@receiver(post_save, sender=FortiGateScheduler)
def sync_schedule_job(sender, instance: FortiGateScheduler, created: bool, **kwargs):
    """
    Keep a single scheduled Job aligned with the schedule record.

    - enabled=True: ensure a job is scheduled at the next matching time
    - enabled=False: remove pending jobs
    """
    # Always clear pending jobs first if we’re toggling/altering schedule parameters
    _delete_pending_jobs(instance)

    if not instance.enabled:
        return

    next_dt = compute_next_run(instance).dt

    # Schedule ONE future run at the calculated time.
    # The runner itself will schedule the *next* run when it finishes.
    FortiGateRunner.enqueue_once(
        instance=instance,
        schedule_at=next_dt,
        interval=None,  # IMPORTANT: cron-like scheduling uses schedule_at, not interval
        schedule_id=instance.pk,
    )


@receiver(post_delete, sender=FortiGateScheduler)
def cleanup_schedule_jobs(sender, instance: FortiGateScheduler, **kwargs):
    _delete_pending_jobs(instance)
