from django.db import models

class Order(models.Model):
    # Default auto-increment ID stays
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, default="pending")

    # New field for gateway/dummy order IDs
    external_order_id = models.CharField(max_length=100, unique=True, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
