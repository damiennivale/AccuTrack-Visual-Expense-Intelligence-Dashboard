import sqlite3
import json
import os
from datetime import datetime

# ========== CONFIGURATION ==========
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "receipts.db")
IMAGES_DIR = os.path.join(BASE_DIR, "receipt_images")

# ========== DATABASE SETUP ==========
def init_db():
    """Create the receipts table and images folder if they don't exist."""
    try:
        os.makedirs(IMAGES_DIR, exist_ok=True)
        print(f"Images folder ready: {IMAGES_DIR}")
    except Exception as e:
        print(f"Note: Could not create images folder: {e}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            merchant TEXT NOT NULL,
            items TEXT,
            total REAL NOT NULL,
            tax REAL,
            category TEXT,
            missing_fields TEXT,
            image_path TEXT,
            raw_ocr_text TEXT,
            created_at TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print(f"Database ready at {DB_PATH}")

def save_receipt(extracted_data, image_file=None):
    """Insert one receipt into the database."""
    image_path = None
    if image_file is not None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"receipt_{timestamp}.jpg"
        image_path = os.path.join(IMAGES_DIR, filename)
        
        if hasattr(image_file, 'save'):
            image_file.save(image_path)
        elif isinstance(image_file, bytes):
            with open(image_path, 'wb') as f:
                f.write(image_file)
        elif isinstance(image_file, str):
            image_path = image_file
    
    missing_json = json.dumps(extracted_data.get("missing_fields", []))
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO receipts 
        (date, merchant, items, total, tax, category, missing_fields, image_path, raw_ocr_text, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        extracted_data["date"],
        extracted_data["merchant"],
        extracted_data.get("items", ""),
        extracted_data["total"],
        extracted_data.get("tax"),
        extracted_data["category"],
        missing_json,
        image_path,
        extracted_data.get("raw_ocr_text", ""),
        datetime.now().isoformat()
    ))
    receipt_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return receipt_id

def get_all_receipts():
    """Return all receipts as a list of dictionaries."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM receipts ORDER BY date DESC, created_at DESC")
    rows = cursor.fetchall()
    receipts = []
    for row in rows:
        receipt = dict(row)
        if receipt.get("missing_fields"):
            receipt["missing_fields"] = json.loads(receipt["missing_fields"])
        else:
            receipt["missing_fields"] = []
        receipts.append(receipt)
    conn.close()
    return receipts

def get_receipts_by_date_range(start_date, end_date):
    """Filter receipts by date range (YYYY-MM-DD)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM receipts 
        WHERE date BETWEEN ? AND ? 
        ORDER BY date
    ''', (start_date, end_date))
    rows = cursor.fetchall()
    receipts = [dict(row) for row in rows]
    conn.close()
    for r in receipts:
        r["missing_fields"] = json.loads(r["missing_fields"]) if r["missing_fields"] else []
    return receipts

def get_receipt_by_id(receipt_id):
    """Return a single receipt by its ID."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM receipts WHERE id = ?", (receipt_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        receipt = dict(row)
        receipt["missing_fields"] = json.loads(receipt["missing_fields"]) if receipt["missing_fields"] else []
        return receipt
    return None

def export_to_csv(filename="expenses_export.csv"):
    """Export all receipt records to a CSV file."""
    receipts = get_all_receipts()
    if not receipts:
        return None
    import csv
    # Save CSV in the same base directory
    csv_path = os.path.join(BASE_DIR, filename)
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = receipts[0].keys()
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(receipts)
    return csv_path

def get_spending_summary_by_category():
    """Return {category: total_spent} for pie chart."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT category, SUM(total) as total_spent
        FROM receipts
        GROUP BY category
        ORDER BY total_spent DESC
    ''')
    rows = cursor.fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows if row[0] is not None}

def get_weekly_spending():
    """Return {date: daily_total} for last 7 days."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT date, SUM(total) as daily_total
        FROM receipts
        WHERE date >= date('now', '-7 days')
        GROUP BY date
        ORDER BY date
    ''')
    rows = cursor.fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}

def clear_all_receipts():
    """Delete all records from the receipts table (use with care)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM receipts")
    conn.commit()
    conn.close()