import datetime
from django.db import transaction

def generate_customer_id():
    """
    Generates a unique B2C Customer ID in the format CUS-YYYY-NNNNN.
    e.g., CUS-2025-00001
    """
    from .models import CustomUser # Or whatever your user model is named

    current_year = datetime.date.today().year
    prefix = f"CUS-{current_year}"

    with transaction.atomic():
        # Filter for B2C users only if you have a way to distinguish them (e.g., user_type field)
        last_user = CustomUser.objects.select_for_update().filter(customer_id__startswith=prefix).order_by('customer_id').last()

        if last_user and last_user.customer_id:
            last_sequence = int(last_user.customer_id.split('-')[-1])
            new_sequence = last_sequence + 1
        else:
            new_sequence = 1

    return f"{prefix}-{new_sequence:05d}"

# accounts/utils.py

from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings

def send_otp_email(email, otp, context="Profile Update"):
    """
    Sends an OTP email using a styled HTML template.
    """
    # Prepare the email context to be passed to the template
    template_context = {
        'otp': otp,
        'context': context,
    }
    
    # Render the HTML template
    html_content = render_to_string('accounts/otp_profile_update.html', template_context)
    
    subject = f"Your OTP for {context} - LegalMunshi"
    from_email = settings.DEFAULT_FROM_EMAIL
    
    # Create the EmailMessage object
    msg = EmailMessage(
        subject,
        html_content,  # Use the rendered HTML content
        from_email,
        [email]
    )
    
    # Set the content type to HTML
    msg.content_subtype = "html"
    
    try:
        msg.send()
        print(f"OTP email sent to {email} successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")