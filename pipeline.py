import json
import os
import requests
import sqlite3
from datetime import datetime

REPO = r"C:\Users\user\Desktop\AccuTrack-Visual-Expense-Intelligence-Dashboard"
DB_PATH = os.path.join(REPO, "receipts.db")

# ─────────────────────────────────────────
# STEP 1: OCR — read Text_cleaning.py output
# ─────────────────────────────────────────
def run_ocr(image_path):
    """Run OCR dengan preprocessing yang lebih baik"""
    
    # ✅ GUNA PREPROCESS.PY
    from preprocess import document_unwarping, document_preprocess
    
    # Step 1: Unwarp
    unwarped = document_unwarping([image_path])
    if not unwarped:
        return None, "❌ Unwarping failed"
    
    # Step 2: Preprocess (upscale, grayscale, threshold, morphology)
    preprocessed = document_preprocess(unwarped)
    if not preprocessed:
        return None, "❌ Preprocessing failed"
    
    # Step 3: OCR
    from preprocess import document_OCR
    json_paths = document_OCR(preprocessed)
    
    if not json_paths:
        return None, "❌ OCR failed"
    
    # Step 4: Baca OCR result dari JSON
    with open(json_paths[0], 'r', encoding='utf-8') as f:
        ocr_result = json.load(f)
    
    texts = ocr_result.get("rec_texts", [])
    ocr_text = "\n".join(texts)
    
    # Blur detection (optional)
    import cv2
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
    blur_warning = None
    if blur_score < 100:
        blur_warning = f"⚠️ Image quality low (blur: {blur_score:.1f})"
    
    return ocr_text, blur_warning

# ─────────────────────────────────────────
# STEP 2: LLM Parsing via OpenRouter
# ─────────────────────────────────────────
def parse_with_llm(ocr_text):
    """Send OCR text to OpenRouter LLM, return structured receipt dict"""

    # Read API key from openrouter.py config
    with open(os.path.join(REPO, "openrouter.py"), "r") as f:
        content = f.read()
    import re
    match = re.search(r'Bearer (sk-or-[^\'"]+)', content)
    if not match:
        return None, "❌ OpenRouter API key not found in openrouter.py"
    api_key = match.group(1)

    categories = "Dining Groceries Transport Health Entertainment Utilities Education Shopping Travel Others"

    system_prompt = """
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
- Do NOT hallucinate values
- If missing, return null
- Use only provided text
- Prices must be numbers only
- Pick category from: Dining, Groceries, Transport, Health, Entertainment, Utilities, Education, Shopping, Travel, Others
"""

    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "openai/gpt-oss-120b:free",
            "messages": [{"role": "user", "content": system_prompt + "\n\n" + ocr_text + "\n\nCategories: " + categories}],
            "reasoning": {"enabled": True}
        }
    )

    data = response.json()

    # Save response.json for debugging
    with open(os.path.join(REPO, "response.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    content_str = data["choices"][0]["message"]["content"]
    receipt = json.loads(content_str)
    
    # Ensure the response has a merchant field; if not, set it to "Unknown"
    if "merchant" not in receipt or receipt["merchant"] is None:
        receipt["merchant"] = "Unknown"
    
    return receipt, None


# ─────────────────────────────────────────
# STEP 3: Save to Database
# ─────────────────────────────────────────
def save_to_db(receipt, image_path=None):
    """Save structured receipt to SQLite database"""
    from db_manager import init_db, save_receipt
    init_db()

    # Prepare data
    receipt["missing_fields"] = []
    if not receipt.get("total"):
        receipt["missing_fields"].append("total")
    if not receipt.get("tax"):
        receipt["missing_fields"].append("tax")
    if not receipt.get("date"):
        receipt["missing_fields"].append("date")

    receipt["raw_ocr_text"] = receipt.get("raw_ocr_text", "")
    if "items" in receipt and isinstance(receipt["items"], list):
        receipt["items"] = json.dumps(receipt["items"])

    # Use today's date if missing
    if not receipt.get("date"):
        receipt["date"] = datetime.now().strftime("%Y-%m-%d")

    # Ensure numeric fields have defaults if null
    if receipt.get("total") is None:
        receipt["total"] = 0.0
    if receipt.get("tax") is None:
        receipt["tax"] = 0.0

    receipt_id = save_receipt(receipt, image_path)
    return receipt_id


# ─────────────────────────────────────────
# STEP 4: Format reply message for Telegram
# ─────────────────────────────────────────
def format_reply(receipt, receipt_id, blur_warning=None):
    """Format extracted receipt data as a clean Telegram message"""

    items = receipt.get("items", [])
    if isinstance(items, str):
        items = json.loads(items)

    items_text = ""
    for item in items:
        items_text += f"  • {item['name']}: RM {item['price']:.2f}\n"

    warnings = ""
    missing = receipt.get("missing_fields", [])
    if blur_warning:
        warnings += f"\n{blur_warning}"
    if "tax" in missing:
        warnings += "\n⚠️ SST field not found on this receipt."
    if "total" in missing:
        warnings += "\n⚠️ Total amount could not be detected. Please verify manually."

    reply = f"""✅ Receipt #{receipt_id} saved!

📋 *EXPENSE RECORD*
🏪 Merchant : {receipt.get('merchant', 'Unknown')}
📅 Date     : {receipt.get('date', 'Unknown')}
🏷️ Category : {receipt.get('category') or 'Others'}
💰 Total    : RM {receipt.get('total', 0):.2f}
🧾 SST/Tax  : RM {receipt.get('tax', 0) or 0:.2f}

🛒 *Items:*
{items_text}
{warnings}
"""
    return reply


# ─────────────────────────────────────────
# FULL PIPELINE
# ─────────────────────────────────────────
def process_receipt(image_path):
    """
    Full pipeline: image → OCR → LLM → DB → formatted reply
    Returns (reply_text, error_message)
    """
    print(f"[AccuTrack] Processing: {image_path}")

    # Step 1: OCR
    ocr_text, blur_warning = run_ocr(image_path)
    if ocr_text is None:
        return None, blur_warning

    print(f"[AccuTrack] OCR complete. Text length: {len(ocr_text)}")

    # Step 2: LLM Parse
    receipt, error = parse_with_llm(ocr_text)
    if receipt is None:
        return None, error

    print(f"[AccuTrack] LLM parsed. Merchant: {receipt.get('merchant')}")

    # Step 3: Save to DB
    receipt_id = save_to_db(receipt, image_path)
    print(f"[AccuTrack] Saved to DB. ID: {receipt_id}")

    # Step 4: Format reply
    reply = format_reply(receipt, receipt_id, blur_warning)
    
    # Clean the string of any emoji characters that cause CP1252 issues
    import re
    reply = re.sub(r'[^\x00-\x7F]+', '', reply)
    print(reply)

    return reply, None


# ─────────────────────────────────────────
# TEST
# ─────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if "--image" in sys.argv:
        idx = sys.argv.index("--image")
        if idx + 1 < len(sys.argv):
            image_path = sys.argv[idx + 1].strip('"').strip("'")

            # Resolve media:// or telegram:file/ URIs to actual file path
            if image_path.startswith("media://"):
                filename = image_path.replace("media://", "")
                image_path = os.path.join(r"C:\Users\user\.openclaw\media\inbound", filename)

            elif image_path.startswith("telegram:file/"):
                filename = image_path.split("/")[-1]
                image_path = os.path.join(r"C:\Users\user\.openclaw\media\inbound", filename)

            # If still not found, use most recent file in inbound folder
            if not os.path.exists(image_path):
                inbound = r"C:\Users\user\.openclaw\media\inbound"
                files = [os.path.join(inbound, f) for f in os.listdir(inbound)
                         if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                if files:
                    image_path = max(files, key=os.path.getmtime)
                    print(f"[AccuTrack] Using most recent image: {image_path}")
                else:
                    print("❌ No images found in inbound folder.")
                    sys.exit(1)

            reply, error = process_receipt(image_path)
            if error:
                print(f"❌ Error: {error}")
            else:
                print(reply)
        else:
            print("❌ No image path provided after --image")

    elif "--dashboard" in sys.argv:
        from db_manager import get_spending_summary_by_category, get_gross_total
        summary = get_spending_summary_by_category()
        total = get_gross_total()
        print(f"📊 *SPENDING DASHBOARD*\n")
        print(f"💰 Total Spent: RM {total:.2f}\n")
        print("📂 *By Category:*")
        for cat, amt in summary.items():
            print(f"  • {cat}: RM {amt:.2f}")

    else:
        print("❌ Usage: python pipeline.py --image <path>")
