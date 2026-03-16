from django.db import models
from catalog.models import CatalogItem

# Create your models here.

#Represnts one RFQ request from a customer. Each RFQ can have multiple items.
class QuoteWorksheet(models.Model):

    STATUS_CHOICES = [
        ("processing", "Processing"),
        ("needs_review", "Needs Review"),
        ("completed", "Completed"),
    ]

    RFQ_SOURCE_CHOICES = [
        ("email", "Email"),
        ("manual", "Manual"),
        ("api", "API"),
    ]

    customer_name = models.CharField(max_length=255, blank=True, null=True)
    customer_email = models.EmailField(blank=True, null=True)

    rfq_text = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="processing"
    )

    rfq_source = models.CharField(
        max_length=20,
        choices=RFQ_SOURCE_CHOICES,
        default="api"
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"RFQ {self.id} - {self.customer_name}"
    
# Represents each parsed product request inside an RFQ. Each line item can be matched to a CatalogItem and will have a match score and method for how it was matched.
class QuoteLineItem(models.Model):

    worksheet = models.ForeignKey(
        QuoteWorksheet,
        on_delete=models.CASCADE,
        related_name="line_items"
    )

    raw_description = models.TextField()

    parsed_description = models.TextField(blank=True)

    quantity = models.IntegerField(default=1)
    unit = models.CharField(max_length=50, blank=True, null=True)

    matched_catalog_item = models.ForeignKey(
        CatalogItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    match_score = models.FloatField(null=True, blank=True)

    match_method = models.CharField(max_length=50, blank=True)
    
    match_reason = models.TextField(blank=True)

    needs_review = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.raw_description} ({self.quantity})"