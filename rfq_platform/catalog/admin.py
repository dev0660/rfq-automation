from django.contrib import admin

# Register your models here.
from .models import CatalogItem


@admin.register(CatalogItem)
class CatalogItemAdmin(admin.ModelAdmin):
    # Show key catalog fields in the admin changelist view.
    list_display = (
        "sku",
        "description",
        "manufacturer",
        "category",
        "unit_price",
        "is_active",
        "created_at",
    )

    # Allow quick lookup by common product-identifying fields.
    search_fields = ("sku", "description", "manufacturer", "category")

    # Enable useful admin-side filtering for catalog maintenance.
    list_filter = ("is_active", "manufacturer", "category")

    # Keep catalog items consistently sorted by SKU.
    ordering = ("sku",)
