# Parsing the OCR-ed text to GPT oss model using open router API key to get accurate value
#LINE 39 --->CHANGE THE API KEY [NEEDS ATTENTION]

import requests
import json

from Text_cleaning import ocr_entries

ocr_text = "\n".join([e["text"] for e in ocr_entries])
category = ["Dining", "Groceries", "Transport", "Health", "Entertainment", "Utilities","Education", "Other"] 
category = " ".join(category)

SYSTEM_PROMPT = """
You are an expert receipt information extraction system.

Extract structured data from OCR text. Categorize the receipt based on merchant name and items. 
Use the following schema for output:

Return ONLY valid JSON.

Schema:
  "merchant": string,
  "date": string or null,
  "items": [{"name": string, "price": float}],
  "tax": float or null,
  "total": float or null,
  "category": string or null

Rules:
- Do NOT hallucinate values
- If missing, return null
- Use only provided text
- Prices must be numbers only
"""

# First API call with reasoning
response = requests.post(
  url="https://openrouter.ai/api/v1/chat/completions",
  headers={
    "Authorization": "Bearer <INSERT API KEY FROM OPENROUTER HERE>",
    "Content-Type": "application/json",
  },
  data=json.dumps({
    "model": "openai/gpt-oss-120b:free",
    "messages": [
        {
          "role": "user",
          "content": SYSTEM_PROMPT + "\n\n" + ocr_text + category
  }],
    "reasoning": {"enabled": True}
  })
)
print("Successfully called OpenRouter API. Response:")
print(response.json())

#create response.json file
with open("response.json", "w", encoding="utf-8") as f:
    json.dump(response.json(), f, indent=2)     

# # Extract the assistant message with reasoning_details
# response = response.json()
# response = response['choices'][0]['message']

# # Preserve the assistant message with reasoning_details
# messages = [
#   {"role": "user", "content": "How many r's are in the word 'strawberry'?"},
#   {
#     "role": "assistant",
#     "content": response.get('content'),
#     "reasoning_details": response.get('reasoning_details')  # Pass back unmodified
#   },
#   {"role": "user", "content": "Are you sure? Think carefully."}
# ]

# # Second API call - model continues reasoning from where it left off
# response2 = requests.post(
#   url="https://openrouter.ai/api/v1/chat/completions",
#   data=json.dumps({
#     "model": "openai/gpt-oss-120b:free",
#     "messages": messages,  # Includes preserved reasoning_details
#     "reasoning": {"enabled": True}
#   })
# )