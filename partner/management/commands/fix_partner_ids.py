# partners/management/commands/fix_partner_ids.py

from django.core.management.base import BaseCommand
from django.db import transaction
from partner.models import Partner
from partner.utils import generate_partner_id

class Command(BaseCommand):
    help = 'Finds all Partner objects without a partner_id and generates one for them.'

    @transaction.atomic
    def handle(self, *args, **options):
        # Find all partners where the ID is null or an empty string
        partners_to_fix = Partner.objects.filter(partner_id__isnull=True) | Partner.objects.filter(partner_id='')
        
        if not partners_to_fix.exists():
            self.stdout.write(self.style.SUCCESS("No partners needed fixing. All have IDs."))
            return

        self.stdout.write(f"Found {partners_to_fix.count()} partners to fix...")

        fixed_count = 0
        for partner in partners_to_fix:
            try:
                # Generate a new ID using the utility function and save the partner
                partner.partner_id = generate_partner_id()
                partner.save()
                fixed_count += 1
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Could not fix partner {partner.id} ({partner.business_name}): {e}"))
        
        self.stdout.write(self.style.SUCCESS(f"Successfully fixed {fixed_count} partners."))

