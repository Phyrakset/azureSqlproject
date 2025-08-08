"""
Run:  streamlit run app.py
Interactive dashboard for dbo.Clothes.
"""

import os, urllib.parse
import pandas as pd
import streamlit as st
import altair as alt
from sqlalchemy import create_engine
from dotenv import load_dotenv

# ── 1. SQLAlchemy engine (cached) ─────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def get_engine():
    load_dotenv()
    driver   = os.getenv("DRIVER")
    server   = os.getenv("SERVER")
    database = os.getenv("DATABASE")
    uid      = os.getenv("UID")
    pwd      = urllib.parse.quote_plus(os.getenv("PWD"))
    return create_engine(
        f"mssql+pyodbc://{uid}:{pwd}@{server}:1433/{database}"
        f"?driver={urllib.parse.quote_plus(driver)}"
        f"&Encrypt=yes&TrustServerCertificate=no&Connection+Timeout=30"
    )

# ── 2. read data (cached – refresh every 10 min) ─────────────────────────────
@st.cache_data(ttl=600, show_spinner="Loading data …")
def load_data():
    return pd.read_sql("SELECT * FROM dbo.Clothes", get_engine())

df = load_data()

# ── 3. sidebar filters ───────────────────────────────────────────────────────
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
