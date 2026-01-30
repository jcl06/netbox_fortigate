from django.db.models.signals import post_migrate
from django.dispatch import receiver

from core.models import ObjectType
from django.contrib.contenttypes.models import ContentType
from extras.models import EventRule, Notification
from extras.choices import EventRuleActionChoices


@receiver(post_migrate)
def ensure_event_rule(sender, **kwargs):
    if sender.name != "netbox_fortigate":
        return

    # What object type to watch
    watched_ct = ObjectType.objects.get_by_natural_key("netbox_fortigate", "fortigatescheduler")
    notification_ct = ObjectType.objects.get_by_natural_key("extras", "notification")

    rule, created = EventRule.objects.get_or_create(
        name="FortiGate: Notify Job Scheduler",
        defaults={
            "enabled": False,
            "event_types": ["job_completed", "job_failed", "job_errored"], 
            "conditions": {
                "and": [
                    {
                    "attr": "object.data.trigger",
                    "op": "eq",
                    "value": "manual"
                    }
                ]
            },
            "action_type": "notification",  
            "action_object_type": notification_ct
        },
    )

    

    if not created:
        changed = False
        if rule.action_type != "notification":
            rule.action_type = "notification"
            changed = True
        if rule.action_object_type_id != notification_ct.pk:
            rule.action_object_type = notification_ct
            changed = True
        if rule.event_types != ["job_completed", "job_failed", "job_errored"]:
            rule.event_types = ["job_completed", "job_failed", "job_errored"]
            changed = True
        if changed:
            rule.conditions = {
                "and": [
                    {
                    "attr": "object.data.trigger",
                    "op": "eq",
                    "value": "manual"
                    }
                ]
            }
            rule.save()
            

    rule.object_types.set((watched_ct,))
