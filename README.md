# netbox_fortigate

NetBox 4.1.3 plugin skeleton.

## Install (dev)
1. Install the plugin (editable):
   - `pip install -e .`
2. Add to `netbox/configuration.py`:
   - `PLUGINS = ["netbox_fortigate"]`
3. Restart NetBox.

## Verify
- Navigate to `/plugins/fortigate/`
- You should see “netbox_fortigate: OK …”
- Sidebar should show:
  - Fortigate
  - Fortigate Requests
