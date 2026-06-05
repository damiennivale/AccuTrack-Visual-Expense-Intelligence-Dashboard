import sqlite3
import json
import os
from datetime import datetime

IMAGES_DIR = "receipt_images"
DB_PATH = "receipts.db"

def init_db():
    """Create the receipts table and images folder"""
    os.makedirs(IMAGES_DIR, exist_ok=True)
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
    print("Database ready")

def save_receipt(extracted_data, image_file=None):
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

def export_to_csv(filename="expenses_export.csv"):
    """Export all receipts to CSV (adds timestamp to avoid permission errors)."""
    receipts = get_all_receipts()
    if not receipts:
        return None
    import csv
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base, ext = os.path.splitext(filename)
    csv_path = f"{base}_{timestamp}{ext}"
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = receipts[0].keys()
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(receipts)
    return csv_path

def get_spending_summary_by_category():
    """Return {category: total_spent} for pie chart"""
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
    """Return {date: daily_total} for last 7 days"""
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

def get_daily_spending(start_date=None, end_date=None):
    """Return {date: daily_total} for optional date range."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    query = "SELECT date, SUM(total) as daily_total FROM receipts WHERE 1=1"
    params = []
    
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    
    query += " GROUP BY date ORDER BY date"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}

# ========== NEW SUMMARY FUNCTIONS ==========

def get_net_total():
    """
    Return sum of (total - tax) across all receipts.
    This is the total amount excluding tax.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(total - COALESCE(tax, 0)) FROM receipts")
    net = cursor.fetchone()[0]
    conn.close()
    return net if net is not None else 0.0

def get_gross_total():
    """
    Return sum of total (including tax) across all receipts.
    This is the total amount including tax.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(total) FROM receipts")
    gross = cursor.fetchone()[0]
    conn.close()
    return gross if gross is not None else 0.0

def get_total_tax():
    """
    Return sum of tax across all receipts.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(COALESCE(tax, 0)) FROM receipts")
    total_tax = cursor.fetchone()[0]
    conn.close()
    return total_tax if total_tax is not None else 0.0