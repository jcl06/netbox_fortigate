import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import close_old_connections
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from django.contrib.auth.mixins import PermissionRequiredMixin
from netbox.views.generic import ObjectView
from utilities.permissions import get_permission_for_model

from ..forms.request import RequestForm, FirewallRequestFormSet
from ..models.request import Request, FirewallRequest
from ..utils.policy_lookups import is_connection_allowed

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Per-row path tracing (runs in worker threads)
# ---------------------------------------------------------------------------

def _trace_firewall_rule(rule):
    """
    Trace the network path for a single FirewallRequest row.

    Each row is an independent sub-request: it has its own source(s),
    destination(s), protocol, port(s), and username(s).  Every
    (src × dst × port) combination is traced through the network to
    discover which FortiGate firewalls sit in the path and whether each
    one allows or denies the traffic.

    Returns a JSON-serialisable dict with the inputs, per-combination
    traces, and a summary counter.
    """
    close_old_connections()

    result = {
        "rule_id": rule.id,
        "sources": rule.source,
        "destinations": rule.destination,
        "protocol": rule.protocol,
        "ports": rule.ports,
        "usernames": rule.username,
        "traces": [],
        "summary": {
            "total": 0,
            "allowed": 0,
            "denied": 0,
            "errors": 0,
        },
    }

    # Skip rows that have no source or destination
    if not rule.source or not rule.destination:
        return result

    # Authentication context — use first username if any are provided
    auth_type = "user" if rule.username else ""
    username = rule.username[0] if rule.username else ""

    # For ICMP there are no "ports"; the value represents icmp-type.
    # Default to [0] so we always iterate at least once.
    ports = rule.ports if rule.ports else [0]

    for src in rule.source:
        for dst in rule.destination:
            for port in ports:
                result["summary"]["total"] += 1
                icmptype = port if rule.protocol == "icmp" else None

                trace = {
                    "src": src,
                    "dst": dst,
                    "port": port,
                    "protocol": rule.protocol,
                    "username": username or None,
                    "status": "unknown",
                    "path": [],
                    "error": None,
                }

                try:
                    status = is_connection_allowed(
                        src,
                        dst,
                        rule.protocol,
                        port,
                        auth_type or None,
                        username or None,
                        icmptype,
                    )

                    if not status[0]:
                        trace["status"] = "error"
                        trace["error"] = str(status[1])
                        result["summary"]["errors"] += 1
                    else:
                        policies_map = status[1]  # {Fortigate: {status, policies, …}}
                        path_map = status[2]      # {Fortigate: {src: […], dst: […]}}

                        all_allowed = True
                        for device, info in policies_map.items():
                            path_info = path_map.get(device, {})

                            device_entry = {
                                "device": str(device),
                                "device_id": device.id,
                                "status": info["status"],
                                "policies": info["policies"],
                                "src_interfaces": [
                                    str(i) for i in info.get("source_interface", [])
                                ],
                                "dst_interfaces": [
                                    str(i) for i in path_info.get("dst", [])
                                ],
                            }
                            trace["path"].append(device_entry)

                            if info["status"] != "allow":
                                all_allowed = False

                        trace["status"] = "allowed" if all_allowed else "denied"
                        if all_allowed:
                            result["summary"]["allowed"] += 1
                        else:
                            result["summary"]["denied"] += 1

                except Exception as exc:
                    logger.exception(
                        "Error tracing rule %s: %s → %s:%s", rule.id, src, dst, port
                    )
                    trace["status"] = "error"
                    trace["error"] = str(exc)
                    result["summary"]["errors"] += 1

                result["traces"].append(trace)

    close_old_connections()
    return result


def _process_request_rules(request_obj):
    """
    Process all FirewallRequest rows for a Request **concurrently**.

    Each row is independent and gets its own result / error handling.
    Returns a list of per-row result dicts (order matches the queryset).
    """
    rules = list(request_obj.firewall_rules.all())
    if not rules:
        return []

    # Preserve original ordering; slots filled by as_completed()
    results = [None] * len(rules)

    max_workers = min(len(rules), 4)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_idx = {
            executor.submit(_trace_firewall_rule, rule): idx
            for idx, rule in enumerate(rules)
        }

        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                results[idx] = future.result()
            except Exception as exc:
                logger.exception(
                    "Unexpected error processing rule index %s", idx
                )
                results[idx] = {
                    "rule_id": rules[idx].id,
                    "error": str(exc),
                    "traces": [],
                    "summary": {
                        "total": 0,
                        "allowed": 0,
                        "denied": 0,
                        "errors": 1,
                    },
                }

    return results


def _build_summary_message(results):
    """
    Build a human-readable summary message from the per-row trace results.
    Returns (level, message) where level is 'success', 'warning', or 'error'.
    """
    total_rules = len(results)
    total_allowed = 0
    total_denied = 0
    total_errors = 0

    for r in results:
        s = r.get("summary", {})
        total_allowed += s.get("allowed", 0)
        total_denied += s.get("denied", 0)
        total_errors += s.get("errors", 0)

    if total_errors and not total_allowed and not total_denied:
        return (
            "error",
            f"Path tracing failed for all {total_rules} rule(s). "
            f"Check the logs for details.",
        )

    parts = []
    if total_allowed:
        parts.append(f"{total_allowed} allowed")
    if total_denied:
        parts.append(f"{total_denied} denied")
    if total_errors:
        parts.append(f"{total_errors} error(s)")

    detail = ", ".join(parts)
    msg = f"Request saved. Path trace results across {total_rules} rule(s): {detail}."

    if total_denied or total_errors:
        return ("warning", msg)
    return ("success", msg)


# ---------------------------------------------------------------------------
# Helper to build template context (shared between GET and POST error path)
# ---------------------------------------------------------------------------

def _form_context(request, instance, form, formset):
    return {
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
    }


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

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
            _form_context(request, instance, form, formset),
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

            # ----- Automated path tracing per row (concurrent) -----
            results = _process_request_rules(obj)

            # Persist trace results into the request's JSON field
            obj.request_data = results
            obj.save(update_fields=["request_data"])

            # Flash a summary message
            level, msg = _build_summary_message(results)
            if level == "success":
                messages.success(request, msg)
            elif level == "warning":
                messages.warning(request, msg)
            else:
                messages.error(request, msg)

            return redirect("plugins:netbox_fortigate:request_edit", pk=obj.pk)

        return render(
            request,
            self.template_name,
            _form_context(request, instance, form, formset),
        )


class RequestDetailView(PermissionRequiredMixin, ObjectView):
    queryset = Request.objects.all()
    permission_required = "netbox_fortigate.view_request"
    template_name = "netbox_fortigate/request.html"