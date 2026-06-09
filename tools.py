#Imran's part (your python filename)
from preprocess import preprocess_receipt

def ocr_tool(image_path):
    text = preprocess_receipt(image_path)
    return text

#Nabilah's part (your python filename)
from parser import extract_receipt

def parser_tool(ocr_text):
    data = extract_receipt(ocr_text)
    return data

#Damia's part (db_manager.py)
from db_manager import (
    init_db,
    save_receipt,
    get_all_receipts,
    export_to_csv,
    get_spending_summary_by_category,
    get_weekly_spending,
    get_daily_spending,
    get_net_total,
    get_gross_total,
    get_total_tax
)

# ========== WRAPPER TOOLS FOR OPENCLAW ==========

def db_save_tool(extracted_data, image_file=None):
    """Save receipt into database"""
    return save_receipt(extracted_data, image_file)


def db_get_all_tool():
    """Get all receipts"""
    return get_all_receipts()


def db_export_tool():
    """Export CSV"""
    return export_to_csv()


def db_category_summary_tool():
    """Pie chart data"""
    return get_spending_summary_by_category()


def db_weekly_tool():
    """Weekly bar chart data"""
    return get_weekly_spending()


def db_daily_tool(start_date=None, end_date=None):
    """Filtered spending"""
    return get_daily_spending(start_date, end_date)


def db_summary_tool():
    """Financial summary for dashboard"""
    return {
        "net_total": get_net_total(),
        "gross_total": get_gross_total(),
        "tax_total": get_total_tax()
    }