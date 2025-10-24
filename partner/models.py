# partners/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

# This assumes you have a utils.py file with these functions
from .utils import generate_partner_id, generate_partner_customer_id 

# Get the custom user model
User = settings.AUTH_USER_MODEL



# --- Document Model ---

class DocumentType(models.Model):
    """Defines the types of documents required for signup, managed by admin."""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

# --- Plan and Subscription Models ---

class PartnerPlan(models.Model):
    """
    Defines the available partner plans and their specific rules.
    """
    class PlanType(models.TextChoices):
        LIFETIME = 'LIFETIME', 'One-Time Fee (Lifetime Access)'
        WALLET_CREDIT = 'WALLET_CREDIT', 'Wallet Credit with Validity'
        SUBSCRIPTION = 'SUBSCRIPTION', 'Time-based Subscription'

    name = models.CharField(max_length=100)
    plan_type = models.CharField(max_length=20, choices=PlanType.choices)
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="The upfront cost of the plan.")
    duration_days = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Validity in days. Leave empty for Lifetime plans."
    )
    description = models.TextField(blank=True)
    required_documents = models.ManyToManyField(DocumentType, blank=True, help_text="Select documents required for this plan.")

    def __str__(self):
        return f"{self.name} ({self.get_plan_type_display()})"

class Partner(models.Model):
    """
    The main profile for a business partner, linked to a user account.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='partner')
    business_name = models.CharField(max_length=255)
    partner_id = models.CharField(max_length=20, unique=True, blank=True, editable=False)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    # Add other partner-specific fields here

    def __str__(self):
        return f"{self.business_name} ({self.partner_id or 'No ID'})"

    def save(self, *args, **kwargs):
        from .utils import generate_partner_id
        if not self.partner_id:
            self.partner_id = generate_partner_id() 
        super().save(*args, **kwargs)

    @property
    def has_active_access(self):
        """Checks if the partner has any currently active subscription."""
        return self.subscriptions.filter(is_active=True).exists()

class PartnerDocument(models.Model):
    """Stores the documents for an approved partner."""
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name='documents')
    document_type = models.ForeignKey(DocumentType, on_delete=models.CASCADE)
    file = models.FileField(upload_to='partner_documents/')

    def __str__(self):
        return f"{self.document_type.name} for {self.partner.business_name}"
    


class PartnerSubscription(models.Model):
    """
    An instance of a partner's subscription to a specific plan, tracking their access period.
    """
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(PartnerPlan, on_delete=models.PROTECT, help_text="The plan this subscription is for.")
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True, help_text="Access expiry date. Null for lifetime plans.")
    is_active = models.BooleanField(default=True, help_text="Controls if the subscription benefits are currently active.")

    def save(self, *args, **kwargs):
        """
        Sets the end_date and credits the wallet based on the plan type upon creation.
        """
        is_new = not self.pk

        if is_new:
            # --- FIX: Calculate end_date for ANY plan that has a duration ---
            if self.plan.duration_days:
                self.end_date = self.start_date + timedelta(days=self.plan.duration_days)

            # --- FIX: Apply specific logic for Wallet Credit plans ---
            if self.plan.plan_type == PartnerPlan.PlanType.WALLET_CREDIT:
                try:
                    wallet = self.partner.wallet
                    wallet.balance += self.plan.price
                    
                    # Use the calculated end_date for the wallet balance expiry
                    wallet.balance_expires_at = self.end_date 
                    wallet.save()

                    # Create a transaction record for the credit
                    WalletTransaction.objects.create(
                        wallet=wallet,
                        transaction_type=WalletTransaction.TransactionType.INITIAL_CREDIT,
                        amount=self.plan.price,
                        details=f"Initial credit from '{self.plan.name}' plan purchase."
                    )
                except PartnerWallet.DoesNotExist:
                    # This case should ideally not happen if a wallet is created with a partner
                    pass

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.partner} on {self.plan.name}"
# --- Wallet and Transaction Models ---

class PartnerWallet(models.Model):
    """A mandatory wallet for each partner to hold their credit balance."""
    partner = models.OneToOneField(Partner, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    updated_at = models.DateTimeField(auto_now=True)
    balance_expires_at = models.DateTimeField(null=True, blank=True, help_text="The date when the current balance expires.")


    def __str__(self):
        return f"{self.partner.business_name}'s Wallet (Balance: {self.balance})"

class WalletTransaction(models.Model):
    """Logs all transactions for a partner's wallet, providing a clear audit trail."""
    class TransactionType(models.TextChoices):
        INITIAL_CREDIT = 'INITIAL_CREDIT', 'Initial Plan Credit'
        TOP_UP = 'TOP_UP', 'Wallet Top-up'
        SERVICE_PAYMENT = 'SERVICE_PAYMENT', 'Service Payment'
        REFUND = 'REFUND', 'Refund Credit'
        EXPIRY = 'EXPIRY', 'Expired Balance Reset'
        ADMIN_ADJUSTMENT = 'ADMIN_ADJUSTMENT', 'Admin Adjustment'

    wallet = models.ForeignKey(PartnerWallet, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Positive for credits, negative for debits.")
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True, help_text="e.g., Order ID, Payment ID, or a note.")

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.get_transaction_type_display()} of {self.amount} for {self.wallet.partner}"

# --- Signup and Customer Models ---

class PartnerRequest(models.Model):
    """
    Temporarily stores information from the signup form until payment is complete.
    """
    full_name = models.CharField(max_length=255)
    business_type = models.CharField(max_length=50, choices=[('individual', 'Individual'), ('partnership', 'Partnership'), ('company', 'Company')])
    business_name = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    address = models.TextField()
    phone = models.CharField(max_length=15)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128) # Stores hashed password
    selected_plan = models.ForeignKey(PartnerPlan, on_delete=models.SET_NULL, null=True)
    
    payment_status = models.CharField(max_length=20, default='pending')
    order_id = models.CharField(max_length=100, null=True, blank=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Request from {self.business_name} ({self.email})"

class PartnerRequestDocument(models.Model):
    """Stores the documents uploaded during a partner request."""
    partner_request = models.ForeignKey(PartnerRequest, on_delete=models.CASCADE, related_name='documents')
    document_type = models.ForeignKey(DocumentType, on_delete=models.CASCADE)
    file = models.FileField(upload_to='partner_documents/')

    def __str__(self):
        return f"{self.document_type.name} for {self.partner_request.business_name}"

class Customer(models.Model):
    """Represents a customer created by a partner."""
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name='customers')
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    partner_customer_id = models.CharField(max_length=50, unique=True, blank=True, editable=False)

    class Meta:
        # A customer's email should be unique for a given partner
        unique_together = ('partner', 'email')

    def __str__(self):
        return f"{self.full_name} ({self.partner_customer_id or 'No ID'})"
    
    def save(self, *args, **kwargs):
        # Import locally to prevent circular import
        from .utils import generate_partner_customer_id
        if not self.partner_customer_id:
            # FIX: Uncommented the ID generation logic
            self.partner_customer_id = generate_partner_customer_id(self.partner)
        super().save(*args, **kwargs)