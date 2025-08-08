import os
import urllib.parse

import pandas as pd
import streamlit as st
import altair as alt

from sqlalchemy import create_engine
from dotenv import load_dotenv

# ── 0. load local .env (harmless if it doesn’t exist) ──────────────────────
load_dotenv()

# ── 1. helper to prefer st.secrets in Cloud, then os.environ ───────────────
def get_cfg(key: str) -> str:
    # st.secrets.get will return the value from secrets.toml or UI; default=None
    return st.secrets.get(key) or os.getenv(key)

# ── 2. sanity-check that all five vars exist ────────────────────────────────
REQUIRED = ["DRIVER", "SERVER", "DATABASE", "UID", "PWD"]
missing  = [k for k in REQUIRED if not get_cfg(k)]
if missing:
    st.error(
        "🚨 Missing configuration for: " +
        ", ".join(missing) +
        ".\n\n"
        "Locally, put them in a `.env` file (no inline comments).\n"
        "On Cloud, either commit them to `.streamlit/secrets.toml` or "
        "paste them into the Secrets panel."
    )
    st.stop()  # nothing else can run without those

# ── 3. Build the SQLAlchemy engine ──────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def get_engine():
    driver   = urllib.parse.quote_plus(get_cfg("DRIVER"))
    server   = get_cfg("SERVER")
    database = get_cfg("DATABASE")
    uid      = get_cfg("UID")
    pwd      = urllib.parse.quote_plus(get_cfg("PWD"))
    # default port 1433; tweak if you need to
    port     = get_cfg("DB_PORT") or "1433"

    conn_str = (
        f"mssql+pyodbc://{uid}:{pwd}@{server}:{port}/{database}"
        f"?driver={driver}"
        "&Encrypt=yes&TrustServerCertificate=no&Connection+Timeout=30"
    )
    return create_engine(conn_str)

# ── 4. Load data (cached for 10 min) ───────────────────────────────────────
@st.cache_data(ttl=600, show_spinner="Loading data…")
def load_data():
    return pd.read_sql("SELECT * FROM dbo.Clothes", get_engine())

df = load_data()

# ── 5. Your UI ─────────────────────────────────────────────────────────────
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
