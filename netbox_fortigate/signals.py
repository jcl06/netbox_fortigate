from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.db.models.signals import m2m_changed

from core.choices import JobStatusChoices

from .models import *
from .choices import ScheduleModeChoices
from .jobs import compute_next_run
from .registry import RUNNER_REGISTRY, get_runner




MONITORED_MODELS = [
    Interfaces, 
    Zone, 
    Address, 
    AddressGroup, 
    Services, 
    ServiceGroup, 
    User, 
    AuthenticationServer,
    VIP, 
    VIPGroup,     
    ScheduleOnetime, 
    ScheduleRecurring,
    ScheduleGroup,
]

import threading

def _delete_pending(schedule: Scheduler) -> None:
    """
    Delete all queued/scheduled jobs for this schedule across ALL registered runners.
    """
    for runner in RUNNER_REGISTRY.values():
        runner.get_jobs(instance=schedule).filter(
            status__in=JobStatusChoices.ENQUEUED_STATE_CHOICES
        ).delete()


@receiver(post_save, sender=Scheduler)
def sync_jobs(sender, instance: Scheduler, **kwargs):
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


@receiver(post_delete, sender=Scheduler)
def cleanup_jobs(sender, instance: Scheduler, **kwargs):
    _delete_pending(instance)




# Create a thread-local object to hold the context
_thread_locals = threading.local()

def set_m2m_validation_context(validation_required):
    _thread_locals.validation_required = validation_required

def get_m2m_validation_context():
    return getattr(_thread_locals, 'validation_required', True)


@receiver(m2m_changed)
def validate_devices_on_m2m_change(sender, instance, action, reverse, model, pk_set, **kwargs):
    if instance.__class__ not in MONITORED_MODELS + [Policy]:
        return  # Skip if instance is not in monitored models
    # Check if we are supposed to validate (e.g., from the admin or form context)
    if get_m2m_validation_context() and action in ['pre_add', 'pre_set']:
        for pk in pk_set:
            # Get the object being added by primary key
            new_object = model.objects.get(pk=pk)
            
            # Check if the device matches
            if new_object.fortigate != instance.fortigate:
                raise ValidationError(f"The device of object {new_object} must match the instance's device ({instance.fortigate}).")
            

@receiver(post_delete)
def delete_related_object(sender, instance, **kwargs):
    if sender not in MONITORED_MODELS:
        return
    content_type = ContentType.objects.get_for_model(sender)
    Object.objects.filter(fortigate=instance.fortigate, object_type=content_type, object_id=instance.pk).delete()


@receiver(post_save)
def create_or_update_related_object(sender, instance, **kwargs):
    if sender not in MONITORED_MODELS:
        if sender == Fortigate:
            cascade_decommissioned(instance)
        return
    content_type = ContentType.objects.get_for_model(sender)
    obj, created = Object.objects.get_or_create(fortigate=instance.fortigate, object_type=content_type, object_id=instance.pk)
    
    if not created:
        obj.save()


def cascade_decommissioned(instance, visited=None):
    if visited is None:
        visited = set()

        # Prevent circular references
    if instance in visited:
        return
    visited.add(instance)

    for field in instance._meta.get_fields():
        if field.is_relation and field.auto_created and not field.concrete:
            related_manager = getattr(instance, field.get_accessor_name(), None)
            if related_manager:
                related_objects = related_manager.all()
                model_name = field.related_model.__name__.lower()

                if related_objects and model_name != "fortigateobject":
                    for item in related_objects:
                        if not item.is_decommissioned:
                            updated_time = timezone.localtime()
                            item.updated_time = updated_time
                            change = f"{updated_time.strftime('%Y-%b-%d %H:%m')}: Changing status from Decommissioned to Active"
                            item.is_decommissioned = True;
                            item.save()

                # Recurse into related objects
                for related_object in related_objects:
                    cascade_decommissioned(related_object, visited)