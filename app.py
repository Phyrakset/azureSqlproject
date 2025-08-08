import os
import urllib.parse
import pandas as pd
import streamlit as st
import altair as alt
from sqlalchemy import create_engine
from dotenv import load_dotenv

# ── 0. Load local .env if present ───────────────────────────────────────────
load_dotenv()

# ── 1. Helper to prefer st.secrets on Cloud, then os.environ ────────────────
def get_cfg(key: str, default: str = "") -> str:
    return st.secrets.get(key, default) or os.getenv(key, default)

# ── 2. Build SQLAlchemy engine (cached) ────────────────────────────────────
@st.cache_resource(show_spinner=False)
def get_engine():
    driver   = get_cfg("DRIVER")
    server   = get_cfg("SERVER")
    database = get_cfg("DATABASE")
    uid      = get_cfg("UID")
    pwd      = urllib.parse.quote_plus(get_cfg("PWD"))
    port     = get_cfg("DB_PORT", "1433")
    # URL-encode the driver name
    driver_enc = urllib.parse.quote_plus(driver)

    connection_string = (
        f"mssql+pyodbc://{uid}:{pwd}@{server}:{port}/{database}"
        f"?driver={driver_enc}"
        "&Encrypt=yes&TrustServerCertificate=no&Connection+Timeout=30"
    )
    return create_engine(connection_string)

# ── 3. Read data (cached – refresh every 10 min) ─────────────────────────────
@st.cache_data(ttl=600, show_spinner="Loading data …")
def load_data():
    sql = "SELECT * FROM dbo.Clothes"
    return pd.read_sql(sql, get_engine())

df = load_data()

# ── 4. Sidebar filters ───────────────────────────────────────────────────────
st.sidebar.header("Filters")

cat_sel   = st.sidebar.multiselect(
    "Category", sorted(df.Category.unique()), default=list(df.Category.unique()))
brand_sel = st.sidebar.multiselect(
    "Brand",    sorted(df.Brand.unique()),    default=list(df.Brand.unique()))
size_sel  = st.sidebar.multiselect(
    "Size",     sorted(df.Size.unique()),     default=list(df.Size.unique()))
colour_sel = st.sidebar.multiselect(
    "Colour",   sorted(df.Colour.unique()),   default=list(df.Colour.unique()))
price_min, price_max = st.sidebar.slider(
    "Price range ($)", float(df.Price.min()), float(df.Price.max()),
    (float(df.Price.min()), float(df.Price.max()))
)

mask = (
    df.Category.isin(cat_sel) &
    df.Brand.isin(brand_sel)   &
    df.Size.isin(size_sel)     &
    df.Colour.isin(colour_sel) &
    df.Price.between(price_min, price_max)
)
data = df[mask]

# ── 4. layout ────────────────────────────────────────────────────────────────
st.title("Clothes Inventory Dashboard")

kpi1, kpi2, kpi3 = st.columns(3)
kpi1.metric("Items",  f"{len(data):,}")
kpi2.metric("Units",  f"{int(data.UnitsInStock.sum()):,}")
kpi3.metric("Avg Price ($)", f"{data.Price.mean():.2f}")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Average Price by Category")
    chart = (
        alt.Chart(data)
        .mark_bar()
        .encode(x="Category", y="mean(Price):Q", tooltip=["Category", "mean(Price):Q"])
    )
    st.altair_chart(chart, use_container_width=True)

with col2:
    st.subheader("Units in Stock by Size")
    chart2 = (
        alt.Chart(data)
        .mark_bar()
        .encode(x="Size", y="sum(UnitsInStock):Q", tooltip=["Size", "sum(UnitsInStock):Q"])
    )
    st.altair_chart(chart2, use_container_width=True)

st.subheader("Detailed Rows")
st.dataframe(data, use_container_width=True)
