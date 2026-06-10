import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px

st.set_page_config(
    page_title="AccuTrack",
    layout="wide"
)

# Centers the main title and the subheader below it
st.markdown(
    """
    <div style="text-align: center;">
        <h1>AccuTrack</h1>
        <p style="font-size: 20px; color: #666666; margin-top: -10px;">
            Corporate Expense Compliance & Budget Control System
        </p>
    </div>
    """, 
    unsafe_allow_html=True
)

# Adds a clean visual separator below your centered header block
st.divider()
# Connect database
conn = sqlite3.connect("receipts.db")

df = pd.read_sql_query(
    "SELECT * FROM receipts",
    conn
)

# --------------------
# CLEAN DATE FIELDS (IMPORTANT)
# --------------------

df["date"] = pd.to_datetime(df["date"], errors="coerce", dayfirst=True)
df["month"] = df["date"].dt.strftime("%Y-%m")

# --------------------
# COMPANY EXPENSE CATEGORIES 🏢
# --------------------

COMPANY_CATEGORIES = [
    "Groceries",
    "Pantry Supplies",
    "Staff Meals",
    "Office Operations",
    "Stationery",
    "Printing & Photocopy",
    "Office Maintenance",
    "Cleaning Supplies",
    "IT & Software",
    "Software Subscription",
    "Cloud Services",
    "Hardware Purchase",
    "Transport",
    "Fuel",
    "Parking",
    "Toll",
    "Health",
    "Marketing & Advertising",
    "Social Media Ads",
    "Events & Promotions",
    "Office Utilities",
    "Electricity",
    "Water",
    "Internet",
    "Phone Bills",
    "Employee Development",
    "Training & Courses",
    "Workshops",
    "Certifications",
    "Administrative & Compliance",
    "Accounting Fees",
    "Audit Fees",
    "Tax Services",
    "Legal Services",
    "Client Entertainment",
    "Business Meals",
    "Networking Events",
    "Miscellaneous (Approved Only)"
]

BLOCKED_KEYWORDS = [
    "cigarette", "smoking", "vape", "alcohol",
    "casino", "gambling",
    "luxury fashion", "designer", "gucci", "lv",
    "t-shirt", "clothing", "shirt", "shoes"
]

# --------------------
# SIDEBAR
# --------------------

st.sidebar.header("💰 Financial Inputs")

MONTHLY_BUDGET = st.sidebar.number_input(
    "Monthly Budget (RM)",
    min_value=0.0,
    value=5000.0
)

st.sidebar.header("📊 Filters")

selected_month = st.sidebar.selectbox(
    "Select Month",
    sorted(df["month"].dropna().unique(), reverse=True)
)

selected_categories = st.sidebar.multiselect(
    "Filter Category",
    df["category"].dropna().unique(),
    default=df["category"].dropna().unique()
)

filtered_df = df[
    (df["month"] == selected_month) &
    (df["category"].isin(selected_categories))
]

# --------------------
# ACCUTRACK OVERVIEW & BUDGET CONTROL 📊
# --------------------

# Filter selected month first
monthly_df = df[df["month"] == selected_month]

# Monthly calculations
monthly_spending = monthly_df["total"].sum()
monthly_receipts = len(monthly_df)

remaining_budget = MONTHLY_BUDGET - monthly_spending

usage_percent = (
    (monthly_spending / MONTHLY_BUDGET) * 100
    if MONTHLY_BUDGET > 0 else 0
)

remaining_percent = max(0, 100 - usage_percent)

st.markdown(
    f"""
    <div style="background-color:#F8FAFC;
                padding:20px;
                border-radius:10px;
                margin-bottom:20px;
                border-left:5px solid #1E3A8A;">
        <h3 style="margin:0;color:#1E3A8A;">
            📊 Financial Operations Overview
        </h3>
        <p style="margin: 8px 0 0 0; color: #475569; font-size: 14px; line-height: 1.5;">
            Real-time tracking for the allocated RM 5,000.00 monthly company stipend.<br>
            <span style="color: #64748B;">Budget monitoring for:</span> 
            <strong style="color: #1E3A8A; background-color: #E2E8F0; padding: 2px 6px; border-radius: 4px;">{selected_month}</strong>
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

# KPI Cards
col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "💰 Monthly Budget",
    f"RM {MONTHLY_BUDGET:,.2f}"
)

col2.metric(
    "💳 Total Spent",
    f"RM {monthly_spending:,.2f}"
)

col3.metric(
    "🧾 Total Receipts",
    monthly_receipts
)

col4.metric(
    "💵 Remaining Budget",
    f"RM {remaining_budget:,.2f}"
)

# Progress Bar
progress_val = min(usage_percent / 100, 1.0)

st.progress(progress_val)

# Status Message
if remaining_budget < 0:
    st.error(
        f"🚨 Budget exceeded by RM {abs(remaining_budget):,.2f}"
    )

elif usage_percent >= 80:
    st.warning(
        f"⚠ {usage_percent:.1f}% of budget has been used."
    )

else:
    st.success(
        f"✅ Budget healthy. {remaining_percent:.1f}% remaining."
    )

# --------------------
# CATEGORY PIE CHART (MONTH FILTERED)
# --------------------

category_df = (
    monthly_df.groupby("category")["total"]
    .sum()
    .reset_index()
)

# safety check (avoid empty month crash)
if category_df.empty:
    st.info("No category data for selected month.")
else:
    fig = px.pie(
        category_df,
        values="total",
        names="category",
        title=f"Spending by Category - {selected_month}"
    )

    st.plotly_chart(fig, use_container_width=True)

# --------------------
# MONTHLY DAILY TREND 📅 (SIDEBAR FILTERED)
# --------------------

st.subheader(f"📅 Daily Spending Trend - {selected_month}")

# use already-filtered monthly_df if you have it
# otherwise:
month_df = df[df["month"] == selected_month]

# group by day
daily_month_df = (
    month_df.groupby(month_df["date"].dt.date)["total"]
    .sum()
    .reset_index()
)

daily_month_df.columns = ["day", "total"]

# chart
fig = px.line(
    daily_month_df,
    x="day",
    y="total",
    markers=True,
    title=f"Daily Spending Trend - {selected_month}"
)

st.plotly_chart(fig, use_container_width=True)
st.divider()

# --------------------
# FINANCIAL INSIGHTS 🔍 (CORPORATE VERSION)
# --------------------

st.markdown(
    f"""
    <div style="background-color:#F8FAFC;
                padding:20px;
                border-radius:10px;
                margin-bottom:20px;
                border-left:5px solid #1E3A8A;">
        <h3 style="margin:0;color:#1E3A8A;">
            📈 Financial Insights
        </h3>
    </div>
    """,
    unsafe_allow_html=True
)

# --------------------
# 1. Budget Utilization (VERY ACCOUNTANT RELEVANT)
# --------------------

budget = MONTHLY_BUDGET

total_spent = filtered_df["total"].sum()

remaining_budget = budget - total_spent

usage_pct = (
    total_spent / budget * 100
    if budget > 0 else 0
)

# --------------------
# COST DRIVERS & RISK ANALYSIS 💸
# --------------------

# Create a clean, well-spaced 2-column grid layout
col1, col2 = st.columns(2, gap="large")

# --- LEFT COLUMN: TOP COST DRIVERS ---
with col1:
    st.markdown("### 💸 Top Cost Drivers")
    st.markdown("<p style='color: #64748B; font-size: 14px; margin-top: -10px;'>High-priority vendors optimized for audit focus.</p>", unsafe_allow_html=True)
    
    top_merchants = (
        filtered_df.groupby("merchant")["total"]
        .sum()
        .sort_values(ascending=False)
        .head(3)
    )
    
    # Render styled rank blocks instead of standard plain text lists
    for i, (merchant, value) in enumerate(top_merchants.items(), start=1):
        st.markdown(
            f"""
            <div style="background-color: #F1F5F9; padding: 12px 16px; border-radius: 8px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span style="background-color: #1E3A8A; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; margin-right: 8px;">#{i}</span>
                    <strong style="color: #334155; text-transform: uppercase; font-size: 14px;">{merchant}</strong>
                </div>
                <span style="font-family: monospace; font-weight: 600; color: #0F172A; font-size: 15px;">RM {value:,.2f}</span>
            </div>
            """, 
            unsafe_allow_html=True
        )


# --- RIGHT COLUMN: CATEGORY RISK ANALYSIS ---
with col2:
    st.markdown("### 🧾 Category Risk Analysis")
    st.markdown("<p style='color: #64748B; font-size: 14px; margin-top: -10px;'>Budget distribution checks to prevent over-concentration.</p>", unsafe_allow_html=True)
    
    # Safety check for total spending to avoid a Division by Zero error
    total_spent = filtered_df["total"].sum()
    
    if total_spent > 0:
        category_totals = (
            filtered_df.groupby("category")["total"]
            .sum()
        )
        category_pct = (category_totals / total_spent) * 100
        
        for cat, pct in category_pct.sort_values(ascending=False).items():
            # Create a localized percentage math variable for the progress track
            progress_bar_val = min(float(pct / 100), 1.0)
            
            # 1. UI Rendering: Title Row
            st.markdown(f"**{cat}** · `{pct:.1f}% of total spend`")
            
            # 2. UI Rendering: Visual Progress Bar Tracking
            st.progress(progress_bar_val)
            
            # 3. UI Rendering: Dynamic Status Alerts
            if pct > 40:
                st.error(f"🚨 **Over-Concentrated Risk:** {cat} accounts for a critical portion of your budget allocation.")
            elif pct > 20:
                st.warning(f"⚠ **High Dependency Alert:** Tracking close to threshold lines. Monitor closely.")
            else:
                st.info(f"✅ **Healthy Distribution:** Spending profile sits well within standard operational targets.")
            
            st.write("") # Micro spacer between category blocks
    else:
        st.info("No active expenditures recorded yet for analysis.")

# --------------------
# 4. TAX & POLICY COMPLIANCE (ACCOUNTING VIEW) 
# --------------------

# Create a clean 2-column container layout
compliance_col1, compliance_col2 = st.columns(2, gap="large")

# --- LEFT COLUMN: TAX COMPLIANCE ---
with compliance_col1:
    st.markdown("## Tax Compliance Overview")

    total_tax = filtered_df["tax"].fillna(0).sum()
    avg_tax_rate = (total_tax / total_spent * 100) if total_spent > 0 else 0

    col1, col2 = st.columns(2)
    col1.metric("💰 Total Tax Recorded", f"RM {total_tax:,.2f}")
    col2.metric("📊 Effective Tax Rate", f"{avg_tax_rate:.2f}%")

    st.write("")

    if total_tax == 0:
        st.error("🚨 No tax data detected — audit risk")
    elif avg_tax_rate > 15:
        st.warning("⚠ High tax rate detected — verify classification")
    else:
        st.success("✅ Tax records within acceptable range")


# --- RIGHT COLUMN: POLICY COMPLIANCE ---
with compliance_col2:
    st.markdown("## Policy Compliance Summary")

    violations_df = filtered_df[
        (~filtered_df["category"].isin(COMPANY_CATEGORIES)) |
        (filtered_df["total"] > 1000)
    ]

    violations = len(violations_df)
    violation_rate = (violations / len(filtered_df) * 100) if len(filtered_df) > 0 else 0

    col1, col2 = st.columns(2)
    col1.metric("🚨 Total Violations", violations)
    col2.metric("📉 Violation Rate", f"{violation_rate:.1f}%")

    st.progress(min(violation_rate / 100, 1.0))

    st.write("")

    if violations > 0:
        st.error("⚠ Some transactions violate company policy rules")
    else:
        st.success("✅ All transactions are compliant")

# --------------------
# 6. FINANCIAL HEALTH SCORE (NEW ADDITION)
# --------------------

st.markdown("## 📊 Financial Health Score")

score = 100

# Budget control impact
if usage_pct > 100:
    score -= 40
elif usage_pct > 80:
    score -= 20

# Policy violations impact
if violation_rate > 20:
    score -= 25
elif violation_rate > 10:
    score -= 15
elif violation_rate > 0:
    score -= 5

# Tax anomaly check
if avg_tax_rate > 15:
    score -= 10

# Data quality risk
missing_data = filtered_df["tax"].isna().sum() + filtered_df["date"].isna().sum()
if missing_data > 0:
    score -= 10

score = max(score, 0)

# --- UI DISPLAY ---
col1, col2 = st.columns([1, 2])

with col1:
    st.metric("🏢 Financial Score", f"{score}/100")

with col2:
    st.progress(score / 100)

st.write("")

# --- STATUS INTERPRETATION ---
if score >= 80:
    st.success("🟢 Healthy Financial Status — Low Risk")
elif score >= 50:
    st.warning("🟡 Moderate Risk — Monitoring Required")
else:
    st.error("🔴 High Financial Risk — Audit Required")
    
# --------------------
# TABLE
# --------------------

st.subheader("All Receipts")

st.dataframe(
    df[
        [
            "date",
            "merchant",
            "category",
            "total",
            "tax"
        ]
    ],
    use_container_width=True
)

# --------------------
# HIGHEST EXPENSE
# --------------------

if not filtered_df.empty:

    highest = filtered_df.loc[
        filtered_df["total"].idxmax()
    ]

    st.info(
        f"Highest expense: RM {highest['total']:.2f} at {highest['merchant']}"
    )

else:
    st.info("No expense data available.")

# --------------------
# REPORTING SYSTEM 📄
# --------------------

import datetime

st.subheader("📄 Monthly Report Generator")

# Month filter (optional but useful)
selected_month = st.selectbox(
    "Select Month for Report",
    sorted(df["month"].dropna().unique(), reverse=True)
)


# Calculate report metrics
report_total = filtered_df["total"].sum()
report_tax = filtered_df["tax"].fillna(0).sum()

top_merchant = filtered_df.groupby("merchant")["total"].sum().sort_values(ascending=False).head(1)
top_category = filtered_df.groupby("category")["total"].sum().sort_values(ascending=False).head(1)

missing_tax = filtered_df["tax"].isna().sum()
missing_date = filtered_df["date"].isna().sum()

# Button to generate CSV
if st.button("📥 Generate Monthly Report (CSV)"):

    report_data = {
        "Month": selected_month,
        "Total Expenses": report_total,
        "Total Tax": report_tax,
        "Top Merchant": top_merchant.index[0] if not top_merchant.empty else "N/A",
        "Top Category": top_category.index[0] if not top_category.empty else "N/A",
        "Missing Tax Count": missing_tax,
        "Missing Date Count": missing_date
    }

    report_df = pd.DataFrame([report_data])

    filename = f"monthly_report_{selected_month}.csv"
    report_df.to_csv(filename, index=False)

    st.success(f"Report generated successfully: {filename}")
    st.dataframe(report_df)
