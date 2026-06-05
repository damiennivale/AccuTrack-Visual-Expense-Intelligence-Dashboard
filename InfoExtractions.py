import json
import spacy
import re

nlp = spacy.load("en_core_web_sm")
#load json
jsonfile="sample1.json"
with open(jsonfile, "r", encoding="utf-8") as f:
    ocr_data = json.load(f)

texts=ocr_data.get("rec_texts", [])
boxes=ocr_data.get("rec_boxes", [])

for i in range(len(texts)):
    textboxes_dict = {text: box for text, box in zip(texts, boxes)}

# Clean text function
def clean_text(text):
    text = text.replace("|", "")
    text = text.replace(":", " ")
    text = text.replace("  ", " ")
    return text.strip()
global thold_y


def getmerchant(textboxes_dict):
    # Sort elements by ymin (box[1]) to process from the top down
    sorted_items = sorted(textboxes_dict.items(), key=lambda item: item[1][1])
    top_candidates = sorted_items[:5]

    # Explicit business indicators
    merchant_keywords = [
        "PERNIAGAAN", "SDN BHD", "BHD", "ENTERPRISE", "TRADING", "KEDAI", 
        "RESTORAN", "COMPANY", "MARKET", "SHOP", "SERVICES", "VENTURES", "RESTAURANT"]
    # extract merchant if matched merch_keywords
    for text, box in top_candidates:
        text_upper = text.upper()
        if any(kw in text_upper for kw in merchant_keywords):
            return text

    # Strategy A: Use spaCy NER to find an organization name
    for text, box in top_candidates:
        doc = nlp(text)
        for ent in doc.ents:
            if ent.label_ in ["ORG", "PERSON"]:
                return ent.text   

    return "Merchant Not Found"

def getdate(textboxes_dict):
    sorted_items = sorted(textboxes_dict.items(), key=lambda item: item[1][1])
    if not sorted_items:
        return "Date Not Found"

    merchant_name = getmerchant(textboxes_dict)
    y_threshold = 0
    
    # Find the merchant's bottom Y coordinate
    for text, box in sorted_items[:8]:
        if merchant_name != "Merchant Not Found" and merchant_name in text:
            y_threshold = max(y_threshold, box[3])
    
    if y_threshold == 0:
        y_threshold = sorted_items[0][1][3]

    date_patterns = [
        # 4-digit year patterns (highest priority)
        r"\b\d{2}/\d{2}/\d{4}\b",
        r"\b\d{2}-\d{2}-\d{4}\b",
        r"\b\d{4}-\d{2}-\d{2}\b",

        # dotted format
        r"\b\d{2}\.\d{2}\.\d{4}\b",

        # 2-digit year fallback (use carefully)
        r"\b\d{2}/\d{2}/\d{2}\b",
        r"\b\d{2}-\d{2}-\d{2}\b"
    ]

    for text, box in sorted_items:
        # skip if we're still in the merchant header region
        if box[1] <= y_threshold:
            continue

        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)

    return "Date Not Found"


def getTotal(textboxes_dict):
    # Regex to capture only the decimal digits structure (e.g., 169.78)
    NUMBER_ONLY_PATTERN = r"(\d+\.\d{2})"
    
    # Standard format regex to validate a price token (e.g., "169.78", "RM169.80")
    PRICE_PATTERN = r"^\d+\.\d{2}$|^R?M?\d+\.\d{2}$"
    
    # Target keywords for final transactional total calculations
    TOTAL_KEYWORDS = ["TOTAL SALES", "GRAND TOTAL", "ROUNDING", "TOTAL"]

    # Step 1: Sort all items from top to bottom based on ymin (box[1])
    sorted_items = sorted(textboxes_dict.items(), key=lambda item: item[1][1])
    
    # Step 2: Loop from top to bottom to find the row text that contains our total anchors
    for text, box in sorted_items:
        text_upper = text.upper()
        
        if any(kw in text_upper for kw in TOTAL_KEYWORDS):
            xmin, ymin, xmax, ymax = box
            
            # Scenario A: Check if a price value is already embedded inside this exact text block
            numeric_match = re.search(NUMBER_ONLY_PATTERN, text)
            if numeric_match:
                return numeric_match.group(1) # Return only the number string (e.g., "169.78")
                
            # Step 3: Spatial Proximity Scan (Same-Row Pairing)
            # If the price is in a separate bounding box, scan for the matching row price
            for potential_text, potential_box in sorted_items:
                p_xmin, p_ymin, p_xmax, p_ymax = potential_box
                
                # Enforce vertical layout constraints (same row baseline and to the right)
                if abs(p_ymin - ymin) <= 15 and p_xmin >= xmin:
                    if re.match(PRICE_PATTERN, potential_text.upper()):
                        # Scenario B: Extract only the number from the separate price block
                        numeric_match = re.search(NUMBER_ONLY_PATTERN, potential_text)
                        if numeric_match:
                            return numeric_match.group(1)

    return "Total Not Found"
print(getTotal(textboxes_dict))

def getItem(textboxes_dict):
    # Regex pattern to match prices (e.g., RM117.90, 34.90, .02)
    PRICE_PATTERN = r"^R?M?\d+\.\d{2}$|^\.\d{2}$"
    
    # Global keywords that signal the end of the items list
    FOOTER_KEYWORDS = ["TOTAL", "ROUNDING", "CASH", "CHANGE", "SUBTOTAL", "AMOUNT", "SALES"]
    
    # Sort all items from top to bottom based on ymin
    sorted_items = sorted(textboxes_dict.items(), key=lambda item: item[1][1])
    
    # Calculate merchant and total boundaries
    merchant_bottom_boundary = 0
    total_top_boundary = 999999
    
    merchant_name = getmerchant(textboxes_dict)
    total_value = getTotal(textboxes_dict)
    
    for text, box in sorted_items:
        text_upper = text.upper()
        ymin, ymax = box[1], box[3]
        
        if merchant_name != "Merchant Not Found" and merchant_name in text_upper:
            merchant_bottom_boundary = max(merchant_bottom_boundary, ymax)
                
        if total_value != "Total Not Found" and total_value in text:
            total_top_boundary = min(total_top_boundary, ymin)

    if total_top_boundary == 999999 and len(sorted_items) > 5:
        total_top_boundary = sorted_items[-5][1][1]

    # Extract price-based items
    extracted_items = []
    
    for text, box in sorted_items:
        ymin = box[1]
        
        # Skip if outside the item zone
        if ymin <= merchant_bottom_boundary or ymin >= total_top_boundary:
            continue
        
        # Check if this text is a price
        if re.match(PRICE_PATTERN, text.upper()):
            # Found a price - now search for nearby item names (within 100 pixels above)
            item_name_parts = []
            search_threshold = ymin - 100
            
            for nearby_text, nearby_box in sorted_items:
                nearby_ymin = nearby_box[1]
                # Look for text in the 100 pixels above this price
                if search_threshold <= nearby_ymin < ymin and nearby_ymin > merchant_bottom_boundary:
                    # Skip if it's a number-only line (qty, code) or price-like
                    if not re.match(PRICE_PATTERN, nearby_text.upper()) and not nearby_text.isdigit():
                        if len(nearby_text.strip()) > 1:  # Skip single chars
                            item_name_parts.append(nearby_text.strip())
            
            item_name = " ".join(item_name_parts).strip()
            
            # Only add if we found a meaningful name
            if item_name and len(item_name) > 2:
                extracted_items.append({
                    "item_name": item_name,
                    "item_price": text
                })
            
    return extracted_items

def getTax(textboxes_dict):
    """
    Finds the tax value using text semantics (spaCy) and pixel alignment (Y-axis or X-axis columns).
    
    Args:
        textboxes_dict (dict): Map of text string -> bounding box coordinates.
    """
    normalized_boxes = {}
    
    # 1. Standardize 4-point OCR polygons into [xmin, ymin, xmax, ymax]
    for text, box in textboxes_dict.items():
        if isinstance(box, list) and len(box) == 4 and isinstance(box[0], list):
            xs = [point[0] for point in box]
            ys = [point[1] for point in box]
            normalized_boxes[text] = [min(xs), min(ys), max(xs), max(ys)]
        else:
            normalized_boxes[text] = box

    tax_labels = []
    potential_values = []
    
    PRICE_PATTERN = r"(\d+\.\d{2})"
    
    # 2. NLP and Text Classification Pass
    for text, box in normalized_boxes.items():
        text_lower = text.lower().strip()
        
        # Check text tokens for tax semantics
        is_tax_keyword = "gst" in text_lower or "tax" in text_lower or "sst" in text_lower or "vat" in text_lower
        
        # Registration check
        is_registration = (
            any(reg_word in text_lower for reg_word in ["id.", "id:", "no:", "no.", "n0:", "reg", "num"]) or
            bool(re.search(r"\d{5,}", text_lower))
        )
        
        # Check if the line contains ignore words
        is_ignored = (
            is_registration or
            any(ignore in text_lower for ignore in [
                "summary", "excluded", "total sales", "total amount", "grand total", 
                "net total", "subtotal", "inclusive", "exclusive", "exempt"
            ])
        )
        
        # Isolate clean anchor labels
        if is_tax_keyword and not is_ignored:
            tax_labels.append((text, box))
            
        # Collect candidate values (any box containing numeric digits matching price pattern)
        if re.search(PRICE_PATTERN, text):
            potential_values.append((text, box))

    # Check if any tax label itself contains a price
    for label_text, label_box in tax_labels:
        price_match = re.search(PRICE_PATTERN, label_text)
        if price_match:
            return price_match.group(1)

    # 3. Spatial Alignment Pass (Horizontal and Vertical Checks)
    best_match_value = None
    min_dist = float('inf')
    match_type = None # 'horizontal' or 'vertical'
    
    for label_text, label_box in tax_labels:
        lx_min, ly_min, lx_max, ly_max = label_box
        label_y_center = (ly_min + ly_max) / 2
        label_height = ly_max - ly_min
        label_width = lx_max - lx_min
        
        for val_text, val_box in potential_values:
            if val_text == label_text:
                continue
                
            vx_min, vy_min, vx_max, vy_max = val_box
            val_y_center = (vy_min + vy_max) / 2
            
            # --- Check Horizontal Alignment (Same Row, to the right) ---
            if abs(label_y_center - val_y_center) < (label_height * 0.8):
                if vx_min >= lx_min:
                    horizontal_dist = vx_min - lx_max
                    if 0 <= horizontal_dist < 400:
                        if match_type != 'horizontal' or horizontal_dist < min_dist:
                            min_dist = horizontal_dist
                            best_match_value = val_text
                            match_type = 'horizontal'
                            
            # --- Check Vertical Alignment (Same Column, below) ---
            x_overlap = max(0, min(lx_max, vx_max) - max(lx_min, vx_min))
            min_w = min(label_width, vx_max - vx_min)
            if min_w > 0 and (x_overlap / min_w) > 0.3:
                if vy_min >= ly_min:
                    vertical_dist = vy_min - ly_max
                    if 0 <= vertical_dist < 150:
                        if match_type is None or (match_type == 'vertical' and vertical_dist < min_dist):
                            min_dist = vertical_dist
                            best_match_value = val_text
                            match_type = 'vertical'
                            
    if best_match_value:
        price_match = re.search(PRICE_PATTERN, best_match_value)
        if price_match:
            return price_match.group(1)
        return best_match_value
        
    return "Tax Value Not Found"
print(getTax(textboxes_dict))


def _build_category_anchors():
    return {
        "food": nlp("food restaurant cafe grocery dining kopitiam breakfast lunch dinner beverage eat supermarket"),
        "transport": nlp("transport petrol fuel station parking toll vehicle car taxi grab transit flight drive repair"),
        "medical": nlp("medical clinic pharmacy hospital medicine doctor dentist health pharma drug care supplement clinic"),
        "entertainment": nlp("entertainment cinema movie karaoke ktv concert game arcade theme park show event holiday play"),
        "shopping": nlp("shopping boutique mall store fashion apparel clothing retail hardware tools goods item purchase supermarket")
    }
CATEGORY_ANCHORS = _build_category_anchors()

def _clean_receipt_text(textboxes_dict):
    raw = " ".join(textboxes_dict.keys())
    return raw.lower()
    
def getCategory(textboxes_dict):
    """Semantic classification of receipt text."""
    raw_text = _clean_receipt_text(textboxes_dict)
    # Heuristic shortcuts (mart, clinic, …) stay unchanged …
    if "mart" in raw_text or "supermarket" in raw_text or "mini market" in raw_text:
        return "shopping"
    if "clinic" in raw_text or "hospital" in raw_text or "pharmacy" in raw_text:
        return "medical"
    if "restaurant" in raw_text or "cafe" in raw_text or "kopitiam" in raw_text:
        return "food"
    # Build the document with fast pipeline (vectors stay)
    with nlp.select_pipes(disable=["ner", "parser"]):
        full_doc = nlp(raw_text)
    # Token filtering – keep only meaningful alpha tokens
    semantic_tokens = [
        token.lemma_.lower()
        for token in full_doc
        if not token.is_stop and token.is_alpha and len(token.text) > 1
    ]
    if not semantic_tokens:
        return "shopping"
    clean_text = " ".join(semantic_tokens)
    with nlp.select_pipes(disable=["ner", "parser"]):
        receipt_vector_doc = nlp(clean_text)
    if not receipt_vector_doc.vector_norm:
        return "shopping"
    best_category = "shopping"
    highest_score = -1.0
    for category, anchor_doc in CATEGORY_ANCHORS.items():
        score = receipt_vector_doc.similarity(anchor_doc)
        if score > highest_score:
            highest_score = score
            best_category = category
    # Optional confidence guard
    if highest_score < 0.55:
        return "shopping"
    return best_category

def getWarnings():
    warnings = []
    
    # Check if Merchant is missing
    if getmerchant(textboxes_dict) == "Merchant Not Found":
        warnings.append("Missing Merchant Name")
        
    # Check if Date is missing
    if getdate(textboxes_dict) == "Date Not Found":
        warnings.append("Missing Date")
        
    # Check if Total Expenses is missing
    if getTotal(textboxes_dict) == "Total Not Found":
        warnings.append("Missing Total Expenses")
        
    # Check if Tax is missing
    if getTax(textboxes_dict) == "Tax Not Found":
        warnings.append("Missing Tax")
        
    # Check if Items list is empty
    if not getItem(textboxes_dict):  # Evaluates to True if the list is []
        warnings.append("Missing Items")   
    return warnings

# Compile structured receipt
structured_receipt = {
    "merchant": getmerchant(textboxes_dict),
    "date": getdate(textboxes_dict),
    "total": getTotal(textboxes_dict),
    "tax": getTax(textboxes_dict),
    "items":getItem(textboxes_dict),
    "category": getCategory(textboxes_dict),
    "warnings": getWarnings()    
}

# PRINT RESULT
print("\n========== STRUCTURED RECEIPT ==========\n")
print(json.dumps(
    structured_receipt,
    indent=4,
    ensure_ascii=False
))

# SAVE OUTPUT
with open("structured_receipt.json", "w", encoding="utf-8") as f:
    json.dump(
        structured_receipt,
        f,
        indent=4,
        ensure_ascii=False
    )

print("\nStructured receipt saved successfully.")