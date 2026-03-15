from django.db import transaction
from quotes.models import QuoteWorksheet, QuoteLineItem
from quotes.services.openai_parser import parse_rfq_text
from quotes.services.matcher import match_catalog_item


@transaction.atomic  # Used to ensure that the entire process is atomic - if anything fails, it will roll back the whole transaction.
def create_worksheet_from_rfq_text(rfq_text: str) -> QuoteWorksheet:
    parsed = parse_rfq_text(rfq_text)

    worksheet = QuoteWorksheet.objects.create(
        rfq_source="manual_paste",
        customer_name=parsed.get("customer_name") or "",
        customer_email=parsed.get("customer_email") or "",
        status="active",
        notes="Created from RFQ intake endpoint.",
    )

    for item in parsed.get("line_items", []):
        raw_description = item["raw_description"]
        quantity = item.get("quantity", 1)
        unit = item.get("unit") or ""

        match_result = match_catalog_item(raw_description)

        QuoteLineItem.objects.create(
            worksheet=worksheet,
            raw_description=raw_description,
            parsed_description=raw_description,
            quantity=quantity,
            unit=unit,
            matched_catalog_item=match_result["matched_item"],
            match_score=match_result["match_score"],
            match_method=match_result["match_method"],
            match_reason=match_result["match_reason"],
            needs_review=match_result["needs_review"],
        )

    return worksheet