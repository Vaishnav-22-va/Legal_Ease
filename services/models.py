from decimal import Decimal
from django.db import models
from django.urls import NoReverseMatch, reverse
from django.utils.text import slugify
from django.core.validators import MinValueValidator
from django.conf import settings
import os
from partner.models import Customer


# -----------------------------
# Service Category
# -----------------------------
class ServiceCategory(models.Model):
    name = models.CharField(max_length=255)
    icon_class = models.CharField(max_length=100, blank=True, null=True,
                                  help_text="Font Awesome/BoxIcon class for icon display")
    order = models.PositiveIntegerField(default=0, help_text="Defines order in navbar")
    slug = models.SlugField(max_length=255, blank=True, null=True, help_text="Optional category slug")

    class Meta:
        ordering = ['order', 'name']
        indexes = [models.Index(fields=['order'])]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:255]
        super().save(*args, **kwargs)


# -----------------------------
# Service
# -----------------------------
class Service(models.Model):
    category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE,
                                 related_name="services", null=True, blank=True)
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    icon_class = models.CharField(max_length=100, blank=True, null=True)
    page_url = models.CharField(max_length=255, blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    short_description = models.TextField(blank=True, default="")
    long_description = models.TextField(blank=True, default="")
    icon = models.ImageField(upload_to="service_icons/", blank=True, null=True)
    hero_image = models.ImageField(upload_to="service_hero/", blank=True, null=True)
    is_active = models.BooleanField(default=True, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    AVAIL_CHOICES = [('both', 'Both'), ('user', 'User only'), ('partner', 'Partner only')]
    available_for = models.CharField(max_length=10, choices=AVAIL_CHOICES, default='both')
    price_user = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'),
                                     validators=[MinValueValidator(Decimal('0.00'))])
    price_partner_default = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'),
                                                validators=[MinValueValidator(Decimal('0.00'))])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    

    class Meta:
        ordering = ['order', 'title']
        indexes = [models.Index(fields=['slug']), models.Index(fields=['is_active'])]

    def __str__(self):
        category_label = self.category.name if self.category else "Uncategorized"
        return f"{category_label} - {self.title}"

    def _generate_unique_slug(self, base):
        slug_base = slugify(base)[:240]
        slug = slug_base
        counter = 1
        qs = Service.objects.all()
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        while qs.filter(slug=slug).exists():
            slug = f"{slug_base}-{counter}"
            counter += 1
        return slug

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._generate_unique_slug(self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        if self.page_url:
            return self.page_url
        try:
            return reverse('services:info', kwargs={'slug': self.slug})
        except NoReverseMatch:
            return '#'

    def get_price_for_user(self):
        return self.price_user

    def get_default_partner_price(self):
        return self.price_partner_default
    


    
class DynamicServiceField(models.Model):
    FIELD_TYPE_CHOICES = [
        ('text', 'Text Input'),
        ('textarea', 'Text Area'),
        ('number', 'Number Input'),
        # Add other field types here as needed
    ]
    
    service = models.ForeignKey(
        'Service', 
        on_delete=models.CASCADE, 
        related_name="dynamic_fields"
    )
    name = models.CharField(
        max_length=255, 
        help_text="Internal name for the field (e.g., 'pan_number')"
    )
    label = models.CharField(
        max_length=255, 
        help_text="User-facing label (e.g., 'PAN Number')"
    )
    field_type = models.CharField(
        max_length=20, 
        choices=FIELD_TYPE_CHOICES, 
        default='text'
    )
    is_mandatory = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.label} ({self.field_type}) for {self.service.title}"
    
# -----------------------------
# Required Document
# -----------------------------
class RequiredDocument(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="required_documents")
    name = models.CharField(max_length=255, help_text="Name of the document (e.g., Passport, ID Card)")
    description = models.TextField(blank=True, help_text="Optional: further details or requirements for the document.")
    is_mandatory = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
    

# Model for Notes
class ServiceNote(models.Model):
    service = models.ForeignKey(
        'Service',
        on_delete=models.CASCADE,
        related_name="notes"  # Use a clear related_name
    )
    title = models.CharField(max_length=255)
    content = models.TextField(
        help_text="The content of the note. You can use basic HTML like <b> for bold."
    )
    order = models.PositiveIntegerField(default=0, help_text="Order in which the notes will appear.")

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Note for {self.service.title}: {self.title}"


# -----------------------------
# Service Order
# -----------------------------
def invoice_upload_path(instance, filename):
    """
    Returns the path to upload invoices for this order.
    Example: service_invoices/order_10/invoice_order_10.pdf
    """
    return os.path.join("service_invoices", f"order_{instance.pk}", filename)


class ServiceOrder(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="service_orders"
    )
    service = models.ForeignKey(
        Service, 
        on_delete=models.CASCADE, 
        related_name="orders"
    )

    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    additional_info = models.TextField(blank=True)

    invoice = models.FileField(upload_to=invoice_upload_path, blank=True, null=True)
    returned_document = models.FileField(upload_to='returned_docs/', blank=True, null=True)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)

    remarks = models.TextField(
        blank=True,
        help_text="Admin remarks for the returned document or order completion."
    )

    # ✅ Payment Status (payment gateway)
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    payment_status = models.CharField(
        max_length=20, 
        choices=PAYMENT_STATUS_CHOICES, 
        default='paid'
    )

    PAYMENT_METHOD_CHOICES = [
        ('not_paid', 'Not Paid'),
        ('wallet', 'Wallet'),
        ('gateway', 'Payment Gateway'),
    ]
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='not_paid'
    )

    # ✅ Order Progress (workflow of the service itself)
    ORDER_PROGRESS_CHOICES = [
        ('placed', 'Order Placed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    progress_status = models.CharField(
        max_length=20,
        choices=ORDER_PROGRESS_CHOICES,
        default='placed'
    )

    price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    external_order_id = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        help_text="Reference from payment gateway (e.g. Razorpay order_xxx)"
    )

    class Meta:
        indexes = [
            models.Index(fields=['payment_status']),
            models.Index(fields=['progress_status']),
            models.Index(fields=['created_at'])
        ]
        ordering = ['-created_at']

    def __str__(self):
        service_name = self.service.title if self.service else "No Service"
        return f"Order #{self.pk} - {service_name} by {self.user.email}"


class DynamicFieldResponse(models.Model):
    """ Stores the user's response for a specific dynamic field in an order. """
    order = models.ForeignKey(
        ServiceOrder, 
        on_delete=models.CASCADE, 
        related_name="dynamic_field_responses"  # <-- THIS IS THE KEY
    )
    field = models.ForeignKey(
        DynamicServiceField, 
        on_delete=models.CASCADE,
        help_text="The dynamic field (question) this response is for."
    )
    value = models.TextField(
        blank=True,
        help_text="The user's submitted value for the field."
    )

    class Meta:
        # Ensure a user can't provide multiple answers for the same field in one order
        unique_together = ('order', 'field')
        ordering = ['field__id']

    def __str__(self):
        return f"Response for '{self.field.label}' in Order #{self.order.pk}"
    

# -----------------------------
# Order Document (NEW MODEL)
# -----------------------------
def order_document_upload_path(instance, filename):
    """ Defines the upload path for user-submitted documents. """
    return f"service_orders/order_{instance.order.pk}/{filename}"


class OrderDocument(models.Model):
    """ Stores a single document uploaded by a user for a specific order. """
    order = models.ForeignKey(ServiceOrder, on_delete=models.CASCADE, related_name="uploaded_documents")
    document_name = models.CharField(max_length=255, help_text="The name of the document requirement, e.g., 'Passport'")
    file = models.FileField(upload_to=order_document_upload_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.document_name} for Order #{self.order.pk}"
