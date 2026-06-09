import json
import re
from thefuzz import fuzz

#load json
#Change the path to the json file you want to test
jsonfile="./Dataset/005.json"
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
    Preprocess layer to remove unnecessary bounding boxes like addresses,
    contact info, thank you notes, and pure symbols to reduce noise for feature extraction.
    """
    filtered_entries = []
    
    # Common indicators for noise
    address_keywords = [
        "jalan ", "jln ", "taman ", "tmn ", "kawasan ", "perindustrian", 
        "lorong ", "bangunan ", "tingkat ", "level ", "lot ", "kampung ", "kg "
    ]
    contact_keywords = [
        "tel:", "fax:", "email:", "www.", ".com", ".my", 
        "tel ", "fax ", "h/p", "hp:", "phone", "website"
    ]
    thank_you_keywords = [
        "thank you", "terima kasih", "please come again", "sila datang lagi", 
        "thanks", "have a nice day", "tq", "t.kasih", "welcome", "jumpa lagi"
    ]
    
    for item in entries:
        text = item["text"]
        text_lower = text.lower()
        
        # 1. Remove pure symbols or text with very few alphanumeric characters (meaningless symbols)
        alnum_count = sum(c.isalnum() for c in text)
        if alnum_count == 0 or (len(text) > 3 and alnum_count / len(text) < 0.3):
            continue
            
        # 2. Remove addresses, contact info, and thank you notes
        is_address = any(kw in text_lower for kw in address_keywords)
        is_contact = any(kw in text_lower for kw in contact_keywords)
        is_thank_you = any(kw in text_lower for kw in thank_you_keywords)
        
        has_postcode_pattern = bool(re.search(r"\b\d{5}\s+[a-zA-Z]+\b", text)) # e.g. 81200 Johor
        has_phone_pattern = bool(re.search(r"\b0\d{1,2}[-\s]?\d{7,8}\b", text)) # e.g. 012-3456789
        
        if is_address or is_contact or is_thank_you or has_postcode_pattern or has_phone_pattern:
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


def getmerchant(ocr_entries):
    # Sort elements by ymin (box[1]) to process from the top down
    sorted_items = sorted(ocr_entries, key=lambda item: item["box"][1])
    top_candidates = sorted_items[:5]

    # Explicit business indicators
    merchant_keywords = [
        "PERNIAGAAN", "SDN BHD", "BHD", "ENTERPRISE", "TRADING", "KEDAI", 
        "RESTORAN", "COMPANY", "MARKET", "SHOP", "SERVICES", "VENTURES", "RESTAURANT"]
    # extract merchant if matched merch_keywords
    for item in top_candidates:
        text = item["text"]
        box = item["box"]
        text_upper = text.upper()
        if any(kw in text_upper or fuzz.partial_ratio(kw, text_upper) >= 80 for kw in merchant_keywords):
            return text


    return "Merchant Not Found"

def getdate(ocr_entries):
    sorted_items = sorted(ocr_entries, key=lambda item: item["box"][1])
    if not sorted_items:
        return "Date Not Found"

    date_patterns = [
        # 4-digit year patterns (highest priority)
        r"\b\d{2}/\d{2}/\d{4}\b",
        r"\b\d{2}-\d{2}-\d{4}\b",
        r"\b\d{4}-\d{2}-\d{2}\b",

        # dotted format
        r"\b\d{2}\.\d{2}\.\d{4}\b",
        
        # Word month format
        r"\b\d{1,2}\s+[a-zA-Z]{3,}\s+\d{4}\b",

        # 2-digit year fallback (use carefully)
        r"\b\d{2}/\d{2}/\d{2}\b",
        r"\b\d{2}-\d{2}-\d{2}\b"
    ]

    date_labels = ["date", "tarikh", "dated"]
    
    # 1. Search for a date label and use layout to find the corresponding value
    for i, item in enumerate(sorted_items):
        text = item["text"].lower()
        box = item["box"]
        # Check if text contains any date label
        if any(label in text for label in date_labels):
            # Check if there's a date in the same string
            for pattern in date_patterns:
                match = re.search(pattern, item["text"])
                if match:
                    return match.group(0)
            
            # If not, check layout: adjacent right or directly below
            label_xmin, label_ymin, label_xmax, label_ymax = box
            for other_item in sorted_items:
                if other_item == item:
                    continue
                other_text = other_item["text"]
                other_box = other_item["box"]
                o_xmin, o_ymin, o_xmax, o_ymax = other_box
                
                # Check right side (same row)
                if abs(o_ymin - label_ymin) < 30 and o_xmin > label_xmin:
                    for pattern in date_patterns:
                        match = re.search(pattern, other_text)
                        if match:
                            return match.group(0)
                            
                # Check below
                x_overlap = max(0, min(label_xmax, o_xmax) - max(label_xmin, o_xmin))
                min_w = min(label_xmax - label_xmin, o_xmax - o_xmin)
                if min_w > 0 and (x_overlap / min_w) > 0.3 and o_ymin >= label_ymin and (o_ymin - label_ymax) < 60:
                    for pattern in date_patterns:
                        match = re.search(pattern, other_text)
                        if match:
                            return match.group(0)

    # 2. Fallback: Search all items using date patterns below the top of the merchant
    merchant_name = getmerchant(ocr_entries)
    merchant_top = 0
    
    # Find the merchant's top Y coordinate
    for item in sorted_items[:8]:
        text = item["text"]
        box = item["box"]
        if merchant_name != "Merchant Not Found" and merchant_name in text:
            merchant_top = box[1]
            break

    for item in sorted_items:
        text = item["text"]
        box = item["box"]
        # skip if we're strictly above the merchant header region
        if merchant_top > 0 and box[1] < merchant_top:
            continue

        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)

    return "Date Not Found"

def gettotal(ocr_entries):
    # Regex to capture only the decimal digits structure (e.g., 169.78)
    NUMBER_ONLY_PATTERN = r"(\d+\.\d{2})"
    
    # Standard format regex to validate a price token (e.g., "169.78", "RM169.80")
    PRICE_PATTERN = r"^\d+\.\d{2}$|^R?M?\d+\.\d{2}$"
    
    # Target keywords for final transactional total calculations
    TOTAL_KEYWORDS = ["TOTAL SALES", "GRAND TOTAL", "ROUNDING", "TOTAL"]

    # Step 1: Sort all items from top to bottom based on ymin (box[1])
    sorted_items = sorted(ocr_entries, key=lambda item: item["box"][1])
    
    # Step 2: Loop from top to bottom to find the row text that contains our total anchors
    for item in sorted_items:
        text = item["text"]
        box = item["box"]
        text_upper = text.upper()
        
        if any(kw in text_upper or fuzz.partial_ratio(kw, text_upper) >= 80 for kw in TOTAL_KEYWORDS):
            xmin, ymin, xmax, ymax = box
            
            # Scenario A: Check if a price value is already embedded inside this exact text block
            numeric_match = re.search(NUMBER_ONLY_PATTERN, text)
            if numeric_match:
                return numeric_match.group(1) # Return only the number string (e.g., "169.78")
                
            # Step 3: Spatial Proximity Scan (Same-Row Pairing)
            # If the price is in a separate bounding box, scan for the matching row price
            for potential_item in sorted_items:
                potential_text = potential_item["text"]
                potential_box = potential_item["box"]
                p_xmin, p_ymin, p_xmax, p_ymax = potential_box
                
                # Enforce vertical layout constraints (same row baseline and to the right)
                if abs(p_ymin - ymin) <= 15 and p_xmin >= xmin:
                    if re.match(PRICE_PATTERN, potential_text.upper()):
                        # Scenario B: Extract only the number from the separate price block
                        numeric_match = re.search(NUMBER_ONLY_PATTERN, potential_text)
                        if numeric_match:
                            return numeric_match.group(1)

    return "Total Not Found"


def getItem(ocr_entries):
    # Updated pattern to capture prices with $ or RM or just digits
    PRICE_PATTERN = r"^[$A-Za-z]*\s*\d+\.\d{2}$|^\.\d{2}$"
    
    # Global keywords that signal the end of the items list
    FOOTER_KEYWORDS = ["TOTAL", "ROUNDING", "CASH", "CHANGE", "SUBTOTAL", "AMOUNT", "SALES", "NETT"]
    HEADER_KEYWORDS = ["ITEM", "QTY", "TOTAL", "PRICE", "AMOUNT", "DESC", "DESCRIPTION"]
    
    # Sort all items from top to bottom based on ymin
    sorted_items = sorted(ocr_entries, key=lambda item: item["box"][1])
    
    # Calculate merchant and total boundaries
    merchant_bottom_boundary = 0
    total_top_boundary = 999999
    
    merchant_name = getmerchant(ocr_entries)
    total_value = gettotal(ocr_entries)
    
    for item in sorted_items:
        text = item["text"]
        box = item["box"]
        text_upper = text.upper()
        ymin, ymax = box[1], box[3]
        
        if merchant_name != "Merchant Not Found" and merchant_name in text_upper:
            merchant_bottom_boundary = max(merchant_bottom_boundary, ymax)
                
        if total_value != "Total Not Found" and total_value in text:
            total_top_boundary = min(total_top_boundary, ymin)

    if total_top_boundary == 999999 and len(sorted_items) > 5:
        total_top_boundary = sorted_items[-5]["box"][1]

    # Extract price-based items
    extracted_items = []
    current_item_name = None
    current_item_prices = []
    
    for item in sorted_items:
        text = item["text"]
        box = item["box"]
        ymin = box[1]
        
        # Skip if outside the item zone
        if ymin <= merchant_bottom_boundary or ymin >= total_top_boundary:
            continue
            
        text_clean = text.strip()
        text_upper = text_clean.upper()
        
        # Skip headers first so we don't accidentally break on a header that looks like a footer
        if text_upper in HEADER_KEYWORDS:
            continue
            
        # Stop completely if we hit a footer keyword that is standalone or at start of line
        if any(text_upper.startswith(kw) for kw in FOOTER_KEYWORDS):
            # Ensure we don't accidentally break on a normal item that just happens to have 'amount'
            if len(text_clean) < 15:
                break
            
        is_price = re.match(PRICE_PATTERN, text_upper)
        is_qty = re.match(r"^\d+$", text_clean)  # just integer
        
        if is_price:
            if current_item_name:
                current_item_prices.append(text_clean)
        elif is_qty:
            pass # ignore standalone quantities
        else:
            # It's a new item name (or continuation)
            if current_item_name and current_item_prices:
                # Save previous item
                best_price = current_item_prices[-1]
                extracted_items.append({
                    "item_name": current_item_name,
                    "item_price": best_price
                })
                # Reset for next item
                current_item_name = text_clean
                current_item_prices = []
            else:
                if current_item_name:
                    # Append to current name (multiline item)
                    current_item_name += " " + text_clean
                else:
                    current_item_name = text_clean
                    current_item_prices = []

    # Add the last item if exists
    if current_item_name and current_item_prices:
        best_price = current_item_prices[-1]
        extracted_items.append({
            "item_name": current_item_name,
            "item_price": best_price
        })
            
    return extracted_items



def getTax(ocr_entries):
    """
    Finds the tax value using text semantics and flexible spatial alignment (vertical or horizontal proximity).
    """
    # Normalize boxes to [xmin, ymin, xmax, ymax]
    normalized_items = []
    for item in ocr_entries:
        text = item["text"]
        box = item["box"]
        if isinstance(box, list) and len(box) == 4 and isinstance(box[0], list):
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            box = [min(xs), min(ys), max(xs), max(ys)]
        normalized_items.append((text, box))

    # Identify candidate tax label boxes
    tax_labels = []
    potential_values = []
    PRICE_PATTERN = r"(\d+\.\d{2})"
    tax_keywords = ["gst", "tax", "sst", "vat", "cukai"]
    ignore_words = ["summary", "excluded", "total sales", "total amount", "grand total",
                    "net total", "subtotal", "inclusive", "exclusive", "exempt"]
    for text, box in normalized_items:
        txt_low = text.lower().strip()
        is_tax_label = any(kw in txt_low for kw in tax_keywords)
        # filter out registration / irrelevant lines
        is_registration = (any(reg in txt_low for reg in ["id.", "id:", "no:", "no.", "n0:", "reg", "num"]) or
                         bool(re.search(r"\d{5,}", txt_low)))
        is_ignored = is_registration or any(ig in txt_low or fuzz.partial_ratio(ig, txt_low) >= 85 for ig in ignore_words)
        if is_tax_label and not is_ignored:
            tax_labels.append((text, box))
        if re.search(PRICE_PATTERN, text):
            potential_values.append((text, box))

    # Helper: Euclidean distance between two boxes (center points)
    def box_center(b):
        xmin, ymin, xmax, ymax = b
        return ((xmin + xmax) / 2, (ymin + ymax) / 2)

    best_match = None
    best_dist = float('inf')
    # For each tax label, find the nearest numeric value
    for label_text, label_box in tax_labels:
        lx, ly = box_center(label_box)
        for val_text, val_box in potential_values:
            if val_text == label_text:
                continue
            vx, vy = box_center(val_box)
            # Euclidean distance (more tolerant than strict overlap thresholds)
            dist = ((lx - vx) ** 2 + (ly - vy) ** 2) ** 0.5
            if dist < best_dist:
                best_dist = dist
                best_match = val_text

    # If we found a candidate, extract the numeric part
    if best_match:
        price_match = re.search(PRICE_PATTERN, best_match)
        if price_match:
            return price_match.group(1)
        return best_match

    # Fallback: look for a numeric value on the same line as a tax keyword
    for text, _ in normalized_items:
        txt_low = text.lower()
        if any(kw in txt_low for kw in tax_keywords):
            m = re.search(PRICE_PATTERN, text)
            if m:
                return m.group(1)

    return "Tax Value Not Found"


def getWarnings():
    warnings = []
    
    # Check if Merchant is missing
    if getmerchant(ocr_entries) == "Merchant Not Found":
        warnings.append("Missing Merchant Name")
        
    # Check if Date is missing
    if getdate(ocr_entries) == "Date Not Found":
        warnings.append("Missing Date")
        
    # Check if Total Expenses is missing
    if gettotal(ocr_entries) == "Total Not Found":
        warnings.append("Missing Total Expenses")
        
    # Check if Tax is missing
    if getTax(ocr_entries) == "Tax Value Not Found":
        warnings.append("Missing Tax")
        
    # Check if Items list is empty
    if not getItem(ocr_entries):  # Evaluates to True if the list is []
        warnings.append("Missing Items")   
    return warnings

# Category: can add more if have
# CATEGORY_KEYWORDS = {
#     "Dining": ["STARBUCKS", "COFFEE", "CAFE", "RESTAURANT", "MCDONALD", "KFC", "PIZZA", "FOOD", "EATERY", "BAKERY", "DINER"],
#     "Groceries": ["SPEED MART", "GIANT", "TESCO", "LOTUS", "AEON", "FRESH", "MARKET", "SUPERMARKET", "GROCERIES", "MART", "MINIMART"],
#     "Transport": ["GRAB", "TAXI", "GOJEK", "LRT", "MRT", "BUS", "PARKING", "TOLL", "PETROL", "SHELL", "PETRONAS", "CAL TEX"],
#     "Utilities": ["TNB", "SYABAS", "WATER", "ELECTRIC", "INTERNET", "UNIFI", "MAXIS", "DIGI", "CELCOM", "PHONE", "BILL"],
#     "Shopping": ["SHOPEE", "LAZADA", "AMAZON", "ZALORA", "UNIQLO", "H&M", "PADINI", "POPULAR", "BOOKSTORE", "ELECTRONICS"],
#     "Health": ["PHARMACY", "WATSON", "GUARDIAN", "CLINIC", "HOSPITAL", "DENTAL", "MEDICINE", "VITAMIN", "UNIHEALTH"],
#     "Entertainment": ["CINEMA", "GSC", "TGV", "NETFLIX", "SPOTIFY", "YOUTUBE", "GAME", "STEAM", "CONCERT", "MOVIE"],
#     "Education": ["BOOK", "STATIONERY", "UNIVERSITY", "COLLEGE", "SCHOOL", "TUITION", "COURSE", "TRAINING"],
#     "Travel": ["AIRASIA", "MALAYSIA AIRLINES", "HOTEL", "AGODA", "TRIP", "FLIGHT", "LUGGAGE", "TOUR"],
#     "Others": []   # fallback
# }

# def get_category_from_merchant(merchant):
#     """Determine expense category based on merchant name keywords."""
#     merchant_upper = merchant.upper()
#     for category, keywords in CATEGORY_KEYWORDS.items():
#         for kw in keywords:
#             if kw in merchant_upper:
#                 return category
#     return "Others"



def extract_receipt(ocr_entries):
    """Convenient wrapper to extract receipt information.
    Returns the same dict as extract_receipt.
    """
    return {
    "merchant": getmerchant(ocr_entries),
    "date": getdate(ocr_entries),
    "total": gettotal(ocr_entries),
    "tax": getTax(ocr_entries),
    "items": getItem(ocr_entries),
    "warnings": getWarnings()    
}

# Compile structured receipt
structured_receipt = extract_receipt(ocr_entries)

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

