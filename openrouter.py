# Parsing the OCR-ed text to GPT oss model using OpenRouter API to get accurate values
# CHANGE THE API KEY BELOW IF NOT USING ENV VAR [NEEDS ATTENTION]

import os
import requests
import json

API_KEY = os.environ.get("OPENROUTER_API_KEY", "INSERTKEYHERE")

SYSTEM_PROMPT = """
You are an expert receipt information extraction system.
Extract structured data from OCR text. Categorize the receipt based on merchant name and items.
Return ONLY valid JSON with this schema:
{
  "merchant": string,
  "date": string or null,
  "items": [{"name": string, "price": float}],
  "tax": float or null,
  "total": float or null,
  "category": string or null
}
Rules:
- Do NOT hallucinate merchant, date, total, or tax
- For items: include ALL items visible in the text even if price is unclear
- If item price is missing, estimate from subtotal minus known item prices
- If only subtotal is known and multiple items have no price, split evenly
- Last resort: set price to 0.0 rather than omitting the item
- Prices must be numbers only
- Pick category from: Dining, Groceries, Transport, Health, Entertainment, Utilities, Education, Shopping, Travel, Others
"""

CATEGORIES = "Dining Groceries Transport Health Entertainment Utilities Education Shopping Travel Others"


def call_openrouter(ocr_text, save_debug_json=True, debug_path="response.json"):
    """
    Send OCR text to OpenRouter and return a parsed receipt dict.
    Returns (receipt_dict, error_message). error_message is None on success.
    """
    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "openai/gpt-oss-120b:free",
            "messages": [{
                "role": "user",
                "content": SYSTEM_PROMPT + "\n\n" + ocr_text + "\n\nCategories: " + CATEGORIES,
            }],
            "reasoning": {"enabled": True},
        },
    )

    data = response.json()

    if save_debug_json:
        with open(debug_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    try:
        content_str = data["choices"][0]["message"]["content"]
        receipt = json.loads(content_str)
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        return None, f"OpenRouter response parsing failed: {e}"

    if not receipt.get("merchant"):
        receipt["merchant"] = "Unknown"

    return receipt, None


if __name__ == "__main__":
    # Manual test — only runs when executing this file directly, not on import
    from Text_cleaning import ocr_entries
    test_text = "\n".join(e["text"] for e in ocr_entries)
    receipt, error = call_openrouter(test_text)
    print(error or json.dumps(receipt, indent=2))
