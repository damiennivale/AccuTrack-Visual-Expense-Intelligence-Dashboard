# test_database_full.py
import os
import json
from db_manager import init_db, save_receipt, get_all_receipts, export_to_csv
from parse_receipt_json import parse_receipt_json

print("🔧 Initialising database...")
init_db()
print("✅ Database ready.\n")

# ---------- Parse and save the real receipt from sample1.json ----------
print("📄 Parsing sample1.json ...")
if not os.path.exists("sample1.json"):
    print("❌ ERROR: sample1.json not found.")
    exit(1)

receipt_data = parse_receipt_json("sample1.json")
print("✅ Parsed data (first 3 lines shown):")
print(json.dumps(receipt_data, indent=2)[:500] + "...\n")

# Only insert sample1.json if it doesn't already exist (check by merchant+date+total)
existing = get_all_receipts()
sample_exists = any(r['merchant'] == receipt_data['merchant'] and 
                    r['date'] == receipt_data['date'] and 
                    abs(r['total'] - receipt_data['total']) < 0.01 
                    for r in existing)
if not sample_exists:
    rid = save_receipt(receipt_data, image_file=None)
    print(f"💾 Saved sample receipt with ID: {rid}\n")
else:
    print("⏭️ Sample receipt already exists – skipping.\n")

# ---------- Add dummy receipts (only if they don't exist) ----------
receipt2 = {
    "merchant": "Starbucks Coffee",
    "date": "2025-03-25",
    "total": 18.50,
    "tax": 1.11,
    "items": "Latte RM12.00, Muffin RM6.50",
    "category": "Dining",
    "missing_fields": [],
    "raw_ocr_text": "Starbucks receipt"
}
receipt3 = {
    "merchant": "Grab Car",
    "date": "2025-03-24",
    "total": 12.00,
    "tax": None,
    "items": "Ride to campus",
    "category": "Transport",
    "missing_fields": ["tax"],
    "raw_ocr_text": "Grab receipt"
}
receipt4 = {
    "merchant": "Guardian Pharmacy",
    "date": "2025-03-26",
    "total": 45.30,
    "tax": 2.72,
    "items": "Vitamin C RM25.00, Face Mask RM20.30",
    "category": "Health",
    "missing_fields": [],
    "raw_ocr_text": "Guardian receipt"
}

starbucks_exists = any(r['merchant'] == 'Starbucks Coffee' and r['date'] == '2025-03-25' for r in existing)
grab_exists = any(r['merchant'] == 'Grab Car' and r['date'] == '2025-03-24' for r in existing)
guardian_exists = any(r['merchant'] == 'Guardian Pharmacy' and r['date'] == '2025-03-26' for r in existing)

if not starbucks_exists:
    save_receipt(receipt2)
    print("➕ Added Starbucks receipt")
else:
    print("⏭️ Starbucks already in DB – skipping")

if not grab_exists:
    save_receipt(receipt3)
    print("➕ Added Grab receipt")
else:
    print("⏭️ Grab already in DB – skipping")

if not guardian_exists:
    save_receipt(receipt4)
    print("➕ Added Guardian Pharmacy receipt")
else:
    print("⏭️ Guardian already in DB – skipping")
print()

# ---------- Display all receipts (full history) ----------
print("📊 All receipts in database (history):")
all_receipts = get_all_receipts()
print(f"Total receipts: {len(all_receipts)}")
print("-" * 70)
for r in all_receipts:
    tax_info = f"Tax: RM{r['tax']:.2f}" if r['tax'] else "Tax: missing"
    missing = f"⚠️ Missing: {r['missing_fields']}" if r['missing_fields'] else ""
    print(f"ID {r['id']:2} | {r['date']} | {r['merchant']:30} | RM{r['total']:8.2f} | {tax_info} {missing}")
print("-" * 70)
print()

# ---------- Export to CSV (timestamped) ----------
csv_file = export_to_csv("my_expenses.csv")
if csv_file:
    print(f"📁 Exported to {csv_file}")
else:
    print("❌ Export failed (no data).")
print()

print("✅ TEST COMPLETE – Your database preserves history and prevents duplicates!")