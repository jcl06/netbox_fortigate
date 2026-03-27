from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.db import models
from netbox.models import NetBoxModel, ChangeLoggedModel

from ..choices import RequestTypeChoices


User = get_user_model()

__all__ = (
    'Request',
    'FirewallRequest',
)


class Request(ChangeLoggedModel, models.Model):
    title = models.CharField(max_length=100)
    request_number = models.CharField(max_length=100, editable=False)
    request_type = models.CharField(max_length=50, choices=RequestTypeChoices, default=RequestTypeChoices.CORP_ACCESS)
    requester = models.ForeignKey(User, related_name='requesters', on_delete=models.SET_NULL, null=True)
    requester_repr = models.CharField(max_length=255, blank=True, verbose_name=_("Requester"), editable=False)
    request_data = models.JSONField(default=dict, blank=True, editable=False)
    reviewer_required = models.BooleanField(default=False)
    reviewed_by = models.ForeignKey(User, related_name='reviewers', on_delete=models.SET_NULL, null=True)
    reviewed_by_repr = models.CharField(max_length=255, blank=True, verbose_name=_("Reviewer"), editable=False)
    approvers = models.ManyToManyField(User, related_name='approvers')
    approvers_repr = models.TextField(blank=True, editable=False)
    approved_by = models.ManyToManyField(User, related_name='approved_by')
    approved_by_repr = models.TextField(blank=True, editable=False)
    status = models.CharField(max_length=20, default='pending', editable=False)
    is_approved = models.BooleanField(default=False, verbose_name='approved')
    remarks = models.TextField(blank=True)
    

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return f"{self.title} - {self.id}"
    
    def save(self, *args, **kwargs):

        # Record the user's name and the object's representation as static strings
        if not self.requester_repr:
            self.requester_repr = self.requester.username
        if not self.reviewed_by_repr and self.reviewed_by:
            self.reviewed_by_repr = self.reviewed_by.username
        if not self.approvers_repr and self.approvers.all():
            approvers = []
            for user in self.approvers.all():
                approvers.append(user.username)
            self.approvers_repr = ", ".join(approvers)
        if self.approved_by.all():
            approvers = []
            for user in self.approved_by.all():
                approvers.append(user.username)
            self.approved_by_repr = ", ".join(approvers)

        if self.approvers.all() and self.approved_by.all() and not self.is_approved:
            if len(self.approvers.all()) == len(self.approved_by.all()) and self.status == 'pending approval':
                self.is_approved = True

        return super().save(*args, **kwargs)


class FirewallRequest(models.Model):
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name='firewall_rules')
    source = models.JSONField(blank=True, default=list)
    destination = models.JSONField(blank=True, default=list)
    protocol = models.CharField(
        max_length=4,
        choices=(('tcp', 'TCP'), ('udp', 'UDP'), ('icmp', 'ICMP')),
        default='tcp'
    )
    ports = models.JSONField(blank=True, default=list)
    username = models.JSONField(blank=True, default=list)

