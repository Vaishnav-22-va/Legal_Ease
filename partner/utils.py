# partner/utils.py

import datetime
from django.db import transaction



def generate_partner_id():
    """
    Generates a unique Partner ID in the format PRT-YYYY-NNNN.
    The sequence resets every year.
    e.g., PRT-2025-0001
    """
    from .models import Partner  # Import locally to avoid circular import issues
    
    current_year = datetime.date.today().year
    prefix = f"PRT-{current_year}"
    
    # Use a transaction to prevent race conditions
    with transaction.atomic():
        # Lock the table to ensure the sequence is correct
        last_partner = Partner.objects.select_for_update().filter(partner_id__startswith=prefix).order_by('partner_id').last()
        
        if last_partner and last_partner.partner_id:
            last_sequence = int(last_partner.partner_id.split('-')[-1])
            new_sequence = last_sequence + 1
        else:
            new_sequence = 1
            
    return f"{prefix}-{new_sequence:04d}"


def generate_partner_customer_id(partner):
    """
    Generates a unique Customer ID for a specific partner.
    The sequence is per partner.
    e.g., PC-PRT-2025-0001-001
    """
    from .models import Customer # Import locally
    
    if not partner.partner_id:
        # This can happen if the partner is being created in the same transaction
        # and their ID hasn't been saved yet. Ensure partner is saved first.
        raise ValueError("Partner must have a valid partner_id to generate a customer ID.")

    prefix = f"PC-{partner.partner_id}"
    
    with transaction.atomic():
        # Count existing customers for this specific partner
        customer_count = Customer.objects.select_for_update().filter(partner=partner).count()
        new_sequence = customer_count + 1
        
    return f"{prefix}-{new_sequence:03d}"

