import json
from rapidfuzz import fuzz
from django.conf import settings
from catalog.models import CatalogItem

def get_candidate_catalog_items(raw_description: str, limit: int = 8):
    candidates = []

    for item in CatalogItem.objects.filter(is_active=True).only("id", "sku", "description")[:500]:
        score = fuzz.token_sort_ratio(raw_description.lower(), item.description.lower())
        candidates.append({
            "id": item.id,
            "sku": item.sku,
            "description": item.description,
            "score": score,
        })

    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates[:limit]