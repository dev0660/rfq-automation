import json
from rapidfuzz import fuzz
from openai import OpenAI
from django.conf import settings
from catalog.models import CatalogItem


# Reuse a single client instance so request configuration stays centralized
# and we avoid re-instantiating the SDK on every match operation.
client = OpenAI(api_key=settings.OPENAI_API_KEY)


# Strict response schema for model output.
# This keeps the LLM constrained to a predictable contract so downstream
# matching logic does not have to defensively handle freeform text.
MATCH_SCHEMA = {
    "name": "catalog_match_result",
    "schema": {
        "type": "object",
        "properties": {
            "selected_sku": {"type": ["string", "null"]},
            "confidence": {"type": "number"},
            "reason": {"type": "string"},
            "needs_review": {"type": "boolean"}
        },
        "required": ["selected_sku", "confidence", "reason", "needs_review"],
        "additionalProperties": False
    },
    "strict": True
}


def get_candidate_catalog_items(raw_description: str, limit: int = 8):
    # Build a small shortlist locally before calling the LLM.
    # This keeps token usage bounded and gives the model a narrower,
    # more relevant decision set instead of the full catalog.
    candidates = []

    # Restrict fields loaded from the database to reduce ORM overhead.
    # The hard cap of 500 is a simple guardrail for now, but this should
    # eventually be replaced by a more scalable retrieval strategy if the
    # catalog grows materially.
    for item in CatalogItem.objects.filter(is_active=True).only("id", "sku", "description")[:500]:
        # Use fuzzy token sorting so word order differences in RFQ text
        # do not overly penalize otherwise similar descriptions.
        score = fuzz.token_sort_ratio(raw_description.lower(), item.description.lower())
        candidates.append({
            "id": item.id,
            "sku": item.sku,
            "description": item.description,
            "score": score,
        })

    # Return only the strongest local candidates for LLM reranking.
    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates[:limit]


def choose_best_match_with_openai(raw_description: str, candidates: list[dict]) -> dict:
    # Fail closed when retrieval produced no options.
    # Returning a reviewable non-match is safer than forcing a bad selection.
    if not candidates:
        return {
            "selected_sku": None,
            "confidence": 0,
            "reason": "No candidate catalog items available.",
            "needs_review": True,
        }

    # Flatten candidate data into a compact text block for model evaluation.
    # Include the local fuzzy score so the model can use it as a signal,
    # but not as the sole source of truth.
    candidate_text = "\n".join(
        [
            f"{idx+1}. SKU: {c['sku']} | Description: {c['description']} | LocalScore: {c['score']}"
            for idx, c in enumerate(candidates)
        ]
    )

    # Use the model as a semantic reranker over a pre-filtered candidate set.
    # The prompt explicitly biases toward abstaining when the match is weak,
    # which is usually the correct behavior in quote workflows.
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {
                "role": "developer",
                "content": (
                    "You match industrial RFQ product descriptions to an internal catalog. "
                    "Be conservative. If the match is weak or ambiguous, mark needs_review true."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"RFQ item:\n{raw_description}\n\n"
                    f"Candidate catalog items:\n{candidate_text}"
                ),
            },
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": MATCH_SCHEMA["name"],
                "schema": MATCH_SCHEMA["schema"],
                "strict": MATCH_SCHEMA["strict"],
            }
        },
    )

    # Parse structured model output into a Python dict for downstream use.
    return json.loads(response.output_text)


def match_catalog_item(raw_description: str):
    # Step 1: retrieve a small candidate pool using fast local fuzzy matching.
    candidates = get_candidate_catalog_items(raw_description)

    # Step 2: semantically rerank the shortlisted candidates with the LLM.
    result = choose_best_match_with_openai(raw_description, candidates)

    selected_sku = result.get("selected_sku")
    matched_item = None

    # Resolve the model-selected SKU back to the actual ORM object so the
    # caller gets a real catalog instance instead of only model output.
    if selected_sku:
        matched_item = CatalogItem.objects.filter(sku=selected_sku).first()

    # Return both the final decision and the supporting candidate set.
    # Keeping candidates in the response is useful for debugging, auditability,
    # and future reviewer workflows in the UI/admin layer.
    return {
        "matched_item": matched_item,
        "match_score": result.get("confidence", 0),
        "match_method": "openai",
        "match_reason": result.get("reason", ""),
        "needs_review": result.get("needs_review", True),
        "candidates": candidates,
    }