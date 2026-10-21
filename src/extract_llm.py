"""LLM extractor using the Anthropic API, with a structured JSON output.

Requires: pip install anthropic, and an ANTHROPIC_API_KEY environment variable.
Costs a few cents to run on the sample dataset with a small model.
"""
import json
import os

MODEL = os.environ.get("EXTRACTOR_MODEL", "claude-haiku-5-5")

PROMPT = """You extract structured details from Canadian card statement descriptors.

Return a JSON object with these keys:
- merchant: the clean business name a customer would recognise (e.g. "Tim Hortons", "Uber Eats")
- processor: the payment processor if shown, else "". Processors appear as prefixes:
  "SQ *" = Square, "TST*" = Toast, "SP *" = Shopify, "PAYPAL *" = PayPal, "GOOGLE *" = Google.
  Return the processor's name, not the prefix.
- city: city in normal capitalisation if present, else ""
- province: two-letter Canadian province code if present, else ""
- category: one of Restaurants & Cafes, Groceries, Gas, Subscriptions, Transportation,
  Pharmacy, Retail, Alcohol, Utilities, Travel, Online Shopping, Personal Care, Entertainment.
  Shopify merchants are online stores, so use Online Shopping for them.

Never guess a city or province that is not in the descriptor.

Descriptor: {raw}"""


FIELDS = ["merchant", "processor", "city", "province", "category"]
CATEGORIES = ["Restaurants & Cafes", "Groceries", "Gas", "Subscriptions", "Transportation",
              "Pharmacy", "Retail", "Alcohol", "Utilities", "Travel", "Online Shopping",
              "Personal Care", "Entertainment"]
PROCESSORS = ["", "Square", "Toast", "Shopify", "PayPal", "Google"]
# Structured outputs guarantee the reply matches this schema, so no JSON cleanup is needed.
SCHEMA = {
    "type": "object",
    "properties": {**{f: {"type": "string"} for f in FIELDS},
                   "processor": {"type": "string", "enum": PROCESSORS},
                   "category": {"type": "string", "enum": CATEGORIES}},
    "required": FIELDS,
    "additionalProperties": False,
}


def extract(raw: str) -> dict:
    import anthropic  # imported here so the rules baseline works without it

    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=MODEL, max_tokens=1024,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": PROMPT.format(raw=raw)}])
    text = next((b.text for b in msg.content if b.type == "text"), "")
    try:
        return json.loads(text)
    except json.JSONDecodeError:  # e.g. a refusal or a reply cut off at max_tokens
        return {f: "" for f in FIELDS}
