from django.db import models

# Create your models here.

#Internal Product Catelog that RFQ items will match against. This is a simple example and can be expanded with more fields as needed.
class CatalogItem(models.Model):
    sku = models.CharField(max_length=50, unique=True)
    description = models.TextField()

    manufacturer = models.CharField(max_length=255, blank=True)
    category = models.CharField(max_length=255, blank=True)

    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sku} - {self.description}"