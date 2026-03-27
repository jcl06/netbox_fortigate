from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from django.contrib.auth.mixins import PermissionRequiredMixin
from netbox.views.generic import ObjectView
from utilities.permissions import get_permission_for_model

from ..forms.request import RequestForm, FirewallRequestFormSet
from ..models.request import Request



class RequestEditView(View):
    queryset = Request.objects.all()
    template_name = "netbox_fortigate/request_form.html"

    def get_object(self, pk):
        if pk is None:
            return None
        return get_object_or_404(self.queryset, pk=pk)

    def get(self, request, pk=None):
        instance = self.get_object(pk)

        perm = get_permission_for_model(Request, "change" if instance else "add")
        if not request.user.has_perm(perm):
            raise PermissionDenied()

        form = RequestForm(instance=instance)
        formset = FirewallRequestFormSet(instance=instance, prefix="firewall_rules")

        return render(
            request,
            self.template_name,
            {
                "object": instance or Request(),
                "form": form,
                "formset": formset,
                "return_url": request.path,
                "title": "Edit Request" if instance else "Add Request",
                "columns": [
                    {"name": "Source"},
                    {"name": "Destination"},
                    {"name": "Protocol"},
                    {"name": "Ports"},
                    {"name": "Username"},
                    {"name": "Delete", "width": "80px"},
                ],
                "formset_context_name": "Firewall Rules",
            },
        )

    def post(self, request, pk=None):
        instance = self.get_object(pk)

        perm = get_permission_for_model(Request, "change" if instance else "add")
        if not request.user.has_perm(perm):
            raise PermissionDenied()

        form = RequestForm(request.POST, instance=instance)
        formset = FirewallRequestFormSet(
            request.POST,
            instance=instance,
            prefix="firewall_rules",
        )

        if form.is_valid() and formset.is_valid():
            obj = form.save(commit=False)

            if not obj.requester_id:
                obj.requester = request.user

            obj.save()
            form.save_m2m()

            formset.instance = obj
            formset.save()

            messages.success(request, "Request saved successfully.")
            return redirect("plugins:fortigate:request_edit", pk=obj.pk)

        return render(
            request,
            self.template_name,
            {
                "object": instance or Request(),
                "form": form,
                "formset": formset,
                "return_url": request.path,
                "title": "Edit Request" if instance else "Add Request",
                "columns": [
                    {"name": "Source"},
                    {"name": "Destination"},
                    {"name": "Protocol"},
                    {"name": "Ports"},
                    {"name": "Username"},
                    {"name": "Delete", "width": "80px"},
                ],
                "formset_context_name": "Firewall Rules",
            },
        )

class RequestDetailView(PermissionRequiredMixin, ObjectView):
    queryset = Request.objects.all()
    permission_required = "your_plugin_name.view_request"
    template_name = "your_plugin_name/request.html"