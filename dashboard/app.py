
from pathlib import Path
import pandas as pd
import streamlit as st

# ---------------------------------
# 1. Page Configuration
# ---------------------------------

st.set_page_config(
    page_title="Customer Shopping Analytics",
    page_icon="🛍️",
    layout="wide"
)

# ---------------------------------
# 2. Load Dataset
# ---------------------------------

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = PROJECT_DIR / "dataset" / "online_retail_II_cleaned.csv.gz"

st.title("🛍️ Customer Shopping Behavior Analytics")
st.markdown("### Interactive Business Intelligence Dashboard")
st.caption("Sales, Revenue, Products and Customer Analysis")

if not DATA_FILE.exists():
    st.error(f"Dataset not found: {DATA_FILE}")
    st.info("Please check that online_retail_II_cleaned.csv is inside the dataset folder.")
    st.stop()

df = pd.read_csv(DATA_FILE, low_memory=False)

# Standardize column names
df.columns = (
    df.columns.astype(str)
    .str.strip()
    .str.lower()
    .str.replace(r"[^a-z0-9]+", "_", regex=True)
    .str.strip("_")
)

# Handle common alternative column names
aliases = {
    "invoice_no": "invoice",
    "invoicedate": "invoice_date",
    "customerid": "customer_id",
    "customer": "customer_id",
    "unit_price": "price",
    "product": "description"
}

df = df.rename(columns={
    old: new for old, new in aliases.items()
    if old in df.columns and new not in df.columns
})

# ---------------------------------
# 3. Check Required Columns
# ---------------------------------

required_columns = [
    "invoice", "quantity", "price",
    "invoice_date", "country"
]

missing_columns = [
    col for col in required_columns
    if col not in df.columns
]

if missing_columns:
    st.error(f"Missing columns in dataset: {missing_columns}")
    st.write("Available columns:", df.columns.tolist())
    st.stop()

# ---------------------------------
# 4. Data Preparation
# ---------------------------------

df["invoice_date"] = pd.to_datetime(
    df["invoice_date"], errors="coerce"
)

df["quantity"] = pd.to_numeric(
    df["quantity"], errors="coerce"
)

df["price"] = pd.to_numeric(
    df["price"], errors="coerce"
)

if "sales" not in df.columns:
    df["sales"] = df["quantity"] * df["price"]
else:
    df["sales"] = pd.to_numeric(
        df["sales"], errors="coerce"
    )

def convert_flag(series):
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)

    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .isin(["true", "1", "yes", "y"])
    )

if "is_cancelled" in df.columns:
    df["is_cancelled"] = convert_flag(df["is_cancelled"])
else:
    df["is_cancelled"] = (
        df["invoice"].astype(str).str.startswith("C")
    )

if "is_return" in df.columns:
    df["is_return"] = convert_flag(df["is_return"])
else:
    df["is_return"] = df["quantity"] < 0

df["country"] = df["country"].fillna("Unknown")

# Keep valid normal sales
sales_df = df[
    (~df["is_cancelled"]) &
    (~df["is_return"]) &
    (df["quantity"] > 0) &
    (df["sales"] > 0)
].copy()

sales_df = sales_df.dropna(
    subset=["invoice_date", "sales", "invoice"]
)

if sales_df.empty:
    st.warning("No valid sales records were found.")
    st.stop()

# ---------------------------------
# 5. Sidebar Filters
# ---------------------------------

st.sidebar.header("Dashboard Filters")

min_date = sales_df["invoice_date"].min().date()
max_date = sales_df["invoice_date"].max().date()

selected_dates = st.sidebar.date_input(
    "Select Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

countries = sorted(sales_df["country"].unique().tolist())

selected_country = st.sidebar.selectbox(
    "Select Country",
    ["All Countries"] + countries
)

filtered_df = sales_df.copy()

if isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 2:
    start_date, end_date = selected_dates

    filtered_df = filtered_df[
        filtered_df["invoice_date"].dt.date.between(
            start_date, end_date
        )
    ]

if selected_country != "All Countries":
    filtered_df = filtered_df[
        filtered_df["country"] == selected_country
    ]

if filtered_df.empty:
    st.warning("No sales data available for the selected filters.")
    st.stop()

# ---------------------------------
# 6. KPI Cards
# ---------------------------------

total_revenue = filtered_df["sales"].sum()

total_orders = filtered_df["invoice"].nunique()

if "customer_id" in filtered_df.columns:
    total_customers = filtered_df["customer_id"].nunique()
else:
    total_customers = 0

average_order_value = (
    total_revenue / total_orders
    if total_orders > 0 else 0
)

st.subheader("📊 Business Overview")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Total Revenue",
    f"{total_revenue:,.2f}"
)

col2.metric(
    "Total Orders",
    f"{total_orders:,}"
)

col3.metric(
    "Total Customers",
    f"{total_customers:,}"
)

col4.metric(
    "Average Order Value",
    f"{average_order_value:,.2f}"
)

st.divider()

# ---------------------------------
# 7. Monthly Revenue Trend
# ---------------------------------

st.subheader("📈 Monthly Revenue Trend")

monthly_sales = (
    filtered_df.set_index("invoice_date")["sales"]
    .resample("ME")
    .sum()
)

if not monthly_sales.empty:
    st.line_chart(monthly_sales)

# ---------------------------------
# 8. Country-wise Revenue
# ---------------------------------

st.subheader("🌍 Country-wise Revenue")

country_sales = (
    filtered_df.groupby("country")["sales"]
    .sum()
    .sort_values(ascending=False)
    .head(10)
)

st.bar_chart(country_sales)

# ---------------------------------
# 9. Top 10 Products
# ---------------------------------

st.subheader("🏆 Top 10 Products")

if "description" in filtered_df.columns:
    product_sales = (
        filtered_df.groupby("description")["sales"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
    )

    st.bar_chart(product_sales)

# ---------------------------------
# 10. Customer Analysis
# ---------------------------------

st.subheader("👥 Customer Analysis")

if "customer_id" in filtered_df.columns:

    customer_sales = (
        filtered_df.dropna(subset=["customer_id"])
        .groupby("customer_id")["sales"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
    )

    st.write("Top 10 Customers by Revenue")
    st.dataframe(
        customer_sales.reset_index(),
        use_container_width=True
    )

# ---------------------------------
# 11. Dataset Preview
# ---------------------------------

st.divider()

with st.expander("View Filtered Sales Dataset"):
    st.dataframe(
        filtered_df.head(100),
        use_container_width=True
    )

st.success("Dashboard loaded successfully!")
st.caption("Customer Shopping Behavior Analytics | Python + Streamlit")
