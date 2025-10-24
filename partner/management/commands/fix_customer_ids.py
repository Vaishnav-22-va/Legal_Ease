# partners/management/commands/fix_customer_ids.py

from django.core.management.base import BaseCommand
from django.db import transaction
from partner.models import Customer
from partner.utils import generate_partner_customer_id

class Command(BaseCommand):
    help = 'Finds all customers without a partner_customer_id and generates one for them.'

    @transaction.atomic
    def handle(self, *args, **options):
        # Find all customers where the ID is null or an empty string
        customers_to_fix = Customer.objects.filter(partner_customer_id__isnull=True) | Customer.objects.filter(partner_customer_id='')
        
        if not customers_to_fix.exists():
            self.stdout.write(self.style.SUCCESS("No customers needed fixing. All have IDs."))
            return

        self.stdout.write(f"Found {customers_to_fix.count()} customers to fix...")

        fixed_count = 0
        for customer in customers_to_fix:
            try:
                # Generate a new ID using the existing utility function
                customer.partner_customer_id = generate_partner_customer_id(customer.partner)
                customer.save()
                fixed_count += 1
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Could not fix customer {customer.id} ({customer.full_name}): {e}"))
        
        self.stdout.write(self.style.SUCCESS(f"Successfully fixed {fixed_count} customers."))