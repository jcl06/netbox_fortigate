# netbox_fortigate

A NetBox plugin that brings FortiGate firewall management, policy
automation and inventory pulling into NetBox.

The plugin models FortiGate devices and their related objects (interfaces,
zones, routing tables, addresses, services, VIPs, schedules, users, etc.),
stores firewall policies, and provides a request / scheduling workflow to
pull device inventories and implement policy changes on a recurring or
one-shot basis.

- **NetBox compatibility:** `4.1.3` – `4.5.1`
- **Python:** `>=3.10`
- **Plugin version:** `0.1.0`

## Purpose

`netbox_fortigate` turns NetBox into a **single source of truth for FortiGate
firewalls**. It bridges the gap between NetBox's inventory and the live
configuration of FortiGate devices by:

- **Discovering** the running state of each firewall (interfaces, zones,
  routing tables, addresses, services, VIPs, schedules, users, auth servers)
  and persisting it as first-class NetBox models.
- **Centralizing policy management** – firewall policies and profile groups
  are stored in NetBox, so administrators can browse, search and audit them
  alongside the rest of the network inventory.
- **Automating operations** – a built-in job runner pulls inventories on
  demand or on a schedule (cron / interval) and applies user-submitted change
  requests back to the firewalls.
- **Providing a self-service workflow** – users raise `Request`s that are
  executed by the `Scheduler`, giving operations teams a controlled,
  auditable path from request to deployment without leaving NetBox.

The result is that network engineers can model, query and drive FortiGate
firewall behavior directly from NetBox instead of juggling standalone
spreadsheets, CLI scripts or the FortiManager UI.

## Features

### Modeled objects
The plugin registers a number of NetBox models grouped by domain:

- **Firewalls**
  - `Fortigate` – the firewall device itself (linked to a NetBox `Device`).
  - `Interfaces`, `Zone`, `RoutingTable` – discovered network state.
- **Addressing**
  - `Object`, `Address`, `AddressGroup`
- **Services**
  - `Services`, `ServiceGroup`
- **VIPs**
  - `VIP`, `VIPGroup`
- **Schedules**
  - `ScheduleOnetime`, `ScheduleRecurring`, `ScheduleGroup`
- **Users / Auth**
  - `User`, `UserGroup`, `AuthenticationServer`
- **Policy & Objects**
  - `Policy`, `ProfileGroup`
- **Workflow**
  - `Request`, `FirewallRequest` – user-driven change requests.
  - `Scheduler` – cron / interval job scheduler (uses NetBox jobs).

### Automation
- **Inventory Pull** – pulls the live configuration from each enabled
  FortiGate and synchronizes the modeled objects in NetBox. Runs in a
  thread pool (`inventory_max_workers` setting) and supports per-device or
  scheduled execution (`jobs.InventoryPullRunner`).
- **Implement Request** – applies a stored `Request` to the target
  FortiGate (`jobs.RequestRunner`).
- **Check Policy** – interactive policy path viewer at
  `/plugins/fortigate/check-policy/` (`views.check_policy`).
- **Scheduler** – daily / weekly / monthly (cron) or interval scheduling,
  with automatic re-enqueueing for cron jobs.

### Integration points
- Adds a **Firewalls** menu to the NetBox navigation, plus an
  **Automation → Check Policy** group and a **Schedules** item under
  **Operations → Jobs**.
- Registers a **Fortigate** tab on every NetBox `Device`
  (`DeviceJobsTabView`) listing the jobs run for that device.
- Registers custom lookups and event rules.

## Installation

### From source (dev)
1. Install the plugin (editable):
   ```bash
   pip install -e .
   ```
2. Add it to `netbox/configuration.py`:
   ```python
   PLUGINS = ["netbox_fortigate"]
   ```
3. Run migrations and collect static files:
   ```bash
   python manage.py migrate netbox_fortigate
   python manage.py collectstatic --no-input
   ```
4. Restart NetBox (and the RQ worker / scheduler if you use them):
   ```bash
   sudo systemctl restart netbox netbox-rqworker
   ```

### Configuration
The plugin reads its settings via `utils.settings.get_plugin_default`. The
following keys are recognised (all optional):

| Setting                 | Default   | Description                                              |
|-------------------------|-----------|----------------------------------------------------------|
| `DEBUG`                 | `False`   | Verbose logging in inventory pulls.                      |
| `enable_logging`        | `False`   | Enable plugin-level request logging during jobs.         |
| `SYSTEM_USERNAME`       | `system`  | Fallback audit user for scheduled jobs without a user.   |
| `inventory_max_workers` | `10`      | Thread-pool size for parallel inventory pulls.           |

## Verification
- Navigate to `/plugins/fortigate/firewalls/` – you should see the
  Fortigates list view.
- The sidebar should expose:
  - **Firewalls** menu (Firewalls, Network, Policy & Objects groups)
  - **Operations → Jobs → Schedules**
  - **Operations → Automation → Check Policy**
- On any device detail page a **Fortigate** tab appears once a
  `Fortigate` instance is linked to it.

## License
See [LICENSE](LICENSE).
