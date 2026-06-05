import json
import re

# Category: can add more if have
CATEGORY_KEYWORDS = {
    "Dining": ["STARBUCKS", "COFFEE", "CAFE", "RESTAURANT", "MCDONALD", "KFC", "PIZZA", "FOOD", "EATERY", "BAKERY", "DINER"],
    "Groceries": ["SPEED MART", "GIANT", "TESCO", "LOTUS", "AEON", "FRESH", "MARKET", "SUPERMARKET", "GROCERIES", "MART", "MINIMART"],
    "Transport": ["GRAB", "TAXI", "GOJEK", "LRT", "MRT", "BUS", "PARKING", "TOLL", "PETROL", "SHELL", "PETRONAS", "CAL TEX"],
    "Utilities": ["TNB", "SYABAS", "WATER", "ELECTRIC", "INTERNET", "UNIFI", "MAXIS", "DIGI", "CELCOM", "PHONE", "BILL"],
    "Shopping": ["SHOPEE", "LAZADA", "AMAZON", "ZALORA", "UNIQLO", "H&M", "PADINI", "POPULAR", "BOOKSTORE", "ELECTRONICS"],
    "Health": ["PHARMACY", "WATSON", "GUARDIAN", "CLINIC", "HOSPITAL", "DENTAL", "MEDICINE", "VITAMIN", "UNIHEALTH"],
    "Entertainment": ["CINEMA", "GSC", "TGV", "NETFLIX", "SPOTIFY", "YOUTUBE", "GAME", "STEAM", "CONCERT", "MOVIE"],
    "Education": ["BOOK", "STATIONERY", "UNIVERSITY", "COLLEGE", "SCHOOL", "TUITION", "COURSE", "TRAINING"],
    "Travel": ["AIRASIA", "MALAYSIA AIRLINES", "HOTEL", "AGODA", "TRIP", "FLIGHT", "LUGGAGE", "TOUR"],
    "Others": []   # fallback
}

def get_category_from_merchant(merchant):
    """Determine expense category based on merchant name keywords."""
    merchant_upper = merchant.upper()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in merchant_upper:
                return category
    return "Others"


def parse_receipt_json(json_path):
    """Convert OCR JSON into structured receipt"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    texts = data["rec_texts"]
    
    # 1. Merchant (first non‑empty line)
    merchant = texts[0].strip()
    
    # 2. Date – look for DD-MM-YY or DD/MM/YY
    date_str = None
    for line in texts:
        match = re.search(r'\b(\d{2})[-/](\d{2})[-/](\d{2})\b', line)
        if match:
            day, month, year = match.groups()
            date_str = f"20{year}-{month}-{day}"
            break
    
    # 3. Total 
    total = None
    for i, line in enumerate(texts):
        if "Total Sales" in line or "TOTAL" in line.upper():
            if i+1 < len(texts):
                amount_match = re.search(r'(\d+\.\d{2})', texts[i+1])
                if amount_match:
                    total = float(amount_match.group(1))
                    break
    
    # 4. Tax line 
    tax = None
    for i, line in enumerate(texts):
        if "Tax(RH)" in line or "SST" in line:
            if i+1 < len(texts):
                tax_match = re.search(r'(\d+\.\d{2})', texts[i+1])
                if tax_match:
                    tax = float(tax_match.group(1))
                    break
    
    # 5. Items in the receipt (do not have RM)
    items_list = []
    for i, line in enumerate(texts):
        if "RM" in line and "Total" not in line and "Tax" not in line:
            # If line has both text and price, take it
            if re.search(r'[A-Za-z]', line) and re.search(r'RM\d+\.\d{2}', line):
                items_list.append(line)
            # If next line is a price, combine
            elif i+1 < len(texts) and re.search(r'RM\d+\.\d{2}', texts[i+1]):
                items_list.append(f"{line} {texts[i+1]}")
    items = "; ".join(items_list) if items_list else "No items found"
    
    # 6. Category 
    category = get_category_from_merchant(merchant)
    
    # 7. Missing fields
    missing_fields = []
    if total is None:
        missing_fields.append("total")
    if tax is None:
        missing_fields.append("tax")
    if date_str is None:
        missing_fields.append("date")
    
    # 8. Raw OCR text
    raw_ocr_text = "\n".join(texts)
    
    return {
        "merchant": merchant,
        "date": date_str if date_str else "1970-01-01",
        "total": total if total is not None else 0.0,
        "tax": tax,
        "net": (total if total is not None else 0.0) - (tax if tax is not None else 0.0),
        "items": items,
        "category": category,
        "missing_fields": missing_fields,
        "raw_ocr_text": raw_ocr_text
    }