import json
import re



# from parser import ocr_entries
"""
PREPROCESSING LAYER FOR OCR TEXTS :
This layer cleans OCR text and removes noise to improve accuracy of feature extraction in the parser.
standardizes bounding boxes, and remove sensitive info (if any) before passing to the parser.
"""

#Change the path to the correct json file path [NEED YOUR ATTENTION]
jsonfile="./Dataset/061.json"
with open(jsonfile, "r", encoding="utf-8") as f:
    ocr_data = json.load(f)

texts=ocr_data.get("rec_texts", [])
boxes = ocr_data.get("rec_polys", ocr_data.get("rec_boxes", []))

ocr_entries = []
def clean_text(text):
    text = text.replace("|", "")
    text = text.replace(":", " ")
    text = text.replace("  ", " ")
    return text.strip()




def remove_noise_boxes(entries):
    """
    Filter OCR text entries to remove sensitive information (phone numbers, addresses, emails, URLs)
    and noisy phrases such as thank‑you notes or refund messages.
    Returns a list of entries that are deemed clean.
    """
    filtered_entries = []

    # Keywords for address detection
    address_keywords = [
        "jalan ", "jln ", "taman ", "tmn ", "kawasan ", "perindustrian",
        "lorong ", "bangunan ", "tingkat ", "level ", "lot ", "kampung ", "kg "
    ]
    # Keywords for contact information
    contact_keywords = [
        "tel:", "fax:", "email:", "www.", ".com", ".my",
        "tel ", "fax ", "h/p", "hp:", "phone", "website"
    ]
    # Generic thank‑you / gratitude phrases
    thank_you_keywords = [
        "thank you", "terima kasih", "please come again", "sila datang lagi",
        "thanks", "have a nice day", "tq", "t.kasih", "welcome", "jumpa lagi",
    ]
    # Additional noise phrases specific to this project
    extra_noise_phrases = [
        "goods cannot be refund",
    ]

    for item in entries:
        text = item["text"]
        text_lower = text.lower()

        # 1. Discard entries that are mainly symbols or have very low alphanumeric density
        alnum_count = sum(c.isalnum() for c in text)
        if alnum_count == 0 or (len(text) > 3 and alnum_count / len(text) < 0.3):
            continue

        # 2. Detect address / contact / thank‑you patterns (exact or fuzzy)
        is_address = any(kw in text_lower for kw in address_keywords)
        is_contact = any(kw in text_lower for kw in contact_keywords)
        is_thank_you = any(kw in text_lower for kw in thank_you_keywords)
        is_extra_noise = any(phrase in text_lower for phrase in extra_noise_phrases)

        # 3. Regex‑based detection for postcodes, phone numbers, emails and URLs
        has_postcode_pattern = bool(re.search(r"\b\d{5}\s+[a-zA-Z]+\b", text))
        has_phone_pattern = bool(re.search(r"\b0\d{1,2}[-\s]?\d{7,8}\b", text))
        has_email_pattern = bool(re.search(r"\b[\w.-]+@[\w.-]+\.[a-zA-Z]{2,}\b", text))
        has_url_pattern = bool(re.search(r"\b(?:www\.)?\S+\.(?:com|net|org|my|io)\b", text, re.IGNORECASE))

        has_tax_invoice_pattern = bool(re.search(r"\btax\s+invoice\b", text, re.IGNORECASE))

        if (is_address or is_contact or is_thank_you or is_extra_noise or
                has_postcode_pattern or has_phone_pattern or has_email_pattern or has_url_pattern or
                has_tax_invoice_pattern):
            # Skip entry containing any sensitive or noisy content
            continue

        filtered_entries.append(item)

    return filtered_entries

for text, box in zip(texts, boxes):
    # Standardize 4-point OCR polygons into [xmin, ymin, xmax, ymax]
    if isinstance(box, list) and len(box) == 4 and isinstance(box[0], list):
        xs = [point[0] for point in box]
        ys = [point[1] for point in box]
        normalized_box = [min(xs), min(ys), max(xs), max(ys)]
    else:
        normalized_box = box

    ocr_entries.append({
        "text": clean_text(text),
        "box": normalized_box
    })

ocr_entries = remove_noise_boxes(ocr_entries)
# print(ocr_entries)  # Example: check the cleaned entry for the total amount line