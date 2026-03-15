# Service responsible for converting unstructured RFQ text (emails, pasted requests,
# etc.) into structured JSON that the quoting pipeline can operate on.
#
# The output of this parser feeds downstream systems such as:
# - catalog matching
# - quote worksheet creation
# - pricing / quoting workflows
#
# The OpenAI structured output API is used to enforce a deterministic schema so
# downstream services can safely rely on the output without additional parsing logic.

import json
from openai import OpenAI
from django.conf import settings


# Instantiate OpenAI client using API key from environment configuration.
# Keeping this here centralizes the LLM dependency for this service module.
client = OpenAI(api_key=settings.OPENAI_API_KEY)


# JSON schema defining the contract between the LLM parser and the backend.
#
# This schema ensures:
# - deterministic response structure
# - strict validation of required RFQ fields
# - prevention of hallucinated attributes
#
# Downstream services assume this structure when generating quote worksheets
# and matching catalog items.
RFQ_SCHEMA = {
    "name": "rfq_parse_result",
    "schema": {
        "type": "object",
        "properties": {
            # Optional customer metadata extracted from the RFQ email body
            "customer_name": {"type": ["string", "null"]},
            "customer_email": {"type": ["string", "null"]},

            # List of requested items extracted from the RFQ text
            "line_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {

                        # Raw text description of the requested item as written by the customer.
                        # This is preserved for traceability and later catalog matching.
                        "raw_description": {"type": "string"},

                        # Parsed quantity associated with the item request.
                        "quantity": {"type": "integer"},

                        # Optional unit extracted from the request (e.g., "pcs", "units", "boxes").
                        # Often null because many RFQs omit units entirely.
                        "unit": {"type": ["string", "null"]}
                    },

                    # These fields must always be returned by the parser.
                    "required": ["raw_description", "quantity", "unit"],

                    # Prevent the model from introducing additional keys.
                    "additionalProperties": False
                }
            }
        },

        # Top-level fields that must always exist in the response.
        "required": ["customer_name", "customer_email", "line_items"],

        # Enforce strict contract with downstream services.
        "additionalProperties": False
    },

    # Enforces strict adherence to the schema during generation.
    "strict": True
}


def parse_rfq_text(rfq_text: str) -> dict:
    """
    Convert raw RFQ text into structured JSON using the OpenAI structured output API.

    Responsibilities:
    - Extract customer metadata
    - Identify requested items
    - Normalize quantities and units
    - Return a schema-compliant JSON structure

    This function intentionally does NOT perform catalog matching, pricing,
    or validation against inventory. Its responsibility is purely semantic parsing.

    Returns:
        dict: Structured RFQ representation matching RFQ_SCHEMA
    """

    response = client.responses.create(
        model="gpt-4.1-mini",

        # Two-message prompt structure:
        # - developer message defines system behavior
        # - user message contains raw RFQ input
        input=[
            {
                "role": "developer",
                "content": (
                    "You extract structured RFQ data from industrial quoting requests. "
                    "Return only valid JSON matching the provided schema."
                ),
            },
            {
                "role": "user",
                "content": f"Parse this RFQ text:\n\n{rfq_text}",
            },
        ],

        # Enforce structured output generation using the defined schema
        text={
            "format": {
                "type": "json_schema",
                "name": RFQ_SCHEMA["name"],
                "schema": RFQ_SCHEMA["schema"],
                "strict": RFQ_SCHEMA["strict"],
            }
        },
    )

    # The API returns JSON as text; deserialize it into a Python dictionary
    # so downstream services can operate on the parsed RFQ data.
    return json.loads(response.output_text)