from django.core.management.base import BaseCommand, CommandError
from netbox_fortigate.models import Fortigate
from netbox_fortigate.utils.inventory import update_routing_table
import json
import os

class Command(BaseCommand):
    help = 'Import FortiGate routing table from a JSON file'

    def add_arguments(self, parser):
        parser.add_argument('--device', required=True, help='Name or ID of the FortiGate device')
        parser.add_argument('--file', required=True, help='Path to the JSON file containing routes')

    def handle(self, *args, **options):
        device_ident = options['device']
        file_path = options['file']

        # Lookup the Fortigate model instance
        try:
            if device_ident.isdigit():
                fg = Fortigate.objects.get(id=int(device_ident))
            else:
                fg = Fortigate.objects.get(device__name=device_ident)
        except Fortigate.DoesNotExist:
            raise CommandError(f"Fortigate device '{device_ident}' not found.")

        # Load JSON file
        if not os.path.exists(file_path):
            raise CommandError(f"File not found: {file_path}")

        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
        except Exception as e:
            raise CommandError(f"Failed to parse JSON file: {str(e)}")

        self.stdout.write(f"Importing routing table for {fg.device.name} from {file_path}...")
        
        try:
            status = update_routing_table(device=fg, data=data)
            if status[0]:
                self.stdout.write(self.style.SUCCESS(f"Successfully imported routing table! Status: {status[1]}"))
            else:
                self.stdout.write(self.style.ERROR(f"Failed to import routing table: {status[1]}"))
        except Exception as e:
            raise CommandError(f"An error occurred during import: {str(e)}")
