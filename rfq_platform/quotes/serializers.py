from rest_framework import serializers
from .models import QuoteWorksheet, QuoteLineItem

# Validates the inbound RFQ request body
class RFQIntakeSerializer(serializers.Serializer):
    # Raw RFQ text submitted to the intake endpoint
    rfq_text = serializers.CharField()

    def validate_rfq_text(self, value):
        # Prevent empty submissions
        if not value or not value.strip():
            raise serializers.ValidationError("rfq_text cannot be empty.")
        return value.strip()

# Shapes each parsed/matched line item in responses
class QuoteLineItemSerializer(serializers.ModelSerializer):
    # Convenience fields pulled from the matched catalog item
    matched_catalog_sku = serializers.CharField(
        source="matched_catalog_item.sku",
        read_only=True
    )

    matched_catalog_description = serializers.CharField(
        source="matched_catalog_item.description",
        read_only=True
    )

    class Meta:
        model = QuoteLineItem
        fields = [
            "id",
            "raw_description",
            "parsed_description",
            "quantity",
            "unit",
            "matched_catalog_item",
            "matched_catalog_sku",
            "matched_catalog_description",
            "match_score",
            "match_method",
            "needs_review",
            "created_at",
        ]

# Returns the full worksheet with nested line items
class QuoteWorksheetSerializer(serializers.ModelSerializer):
    # Nested line items for the worksheet
    line_items = QuoteLineItemSerializer(many=True, read_only=True)

    class Meta:
        model = QuoteWorksheet
        fields = [
            "id",
            "customer_name",
            "customer_email",
            "rfq_text",
            "status",
            "rfq_source",
            "notes",
            "created_at",
            "completed_at",
            "line_items",
        ]