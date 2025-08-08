"""
Run:  python seed_clothes.py
Generates ~500 rows of dummy apparel data and inserts
them into dbo.Clothes on your Azure SQL Database.
"""

import os, urllib.parse, random
from datetime import datetime
import numpy as np
import pandas as pd
from faker import Faker
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# ── 1. database engine ────────────────────────────────────────────────────────
load_dotenv()                                               # reads .env
driver   = os.getenv("DRIVER")          # ODBC Driver 18 for SQL Server
server   = os.getenv("SERVER")          # phyhosts.database.windows.net
database = os.getenv("DATABASE")        # sophydb
uid      = os.getenv("UID")
pwd      = urllib.parse.quote_plus(os.getenv("PWD"))

engine = create_engine(
    f"mssql+pyodbc://{uid}:{pwd}@{server}:1433/{database}"
    f"?driver={urllib.parse.quote_plus(driver)}"
    f"&Encrypt=yes&TrustServerCertificate=no&Connection+Timeout=30",
    fast_executemany=True
)

# ── 2. ensure table exists (idempotent) ───────────────────────────────────────
ddl = """
IF OBJECT_ID('dbo.Clothes','U') IS NULL
CREATE TABLE dbo.Clothes (
    ItemID        INT IDENTITY(1,1) PRIMARY KEY,
    Category      NVARCHAR(50),
    Brand         NVARCHAR(50),
    Size          NVARCHAR(5),
    Colour        NVARCHAR(20),
    Price         DECIMAL(10,2),
    UnitsInStock  INT,
    CreatedUtc    DATETIME
)
"""
with engine.begin() as conn:
    conn.exec_driver_sql(ddl)

# ── 3. generate random dataset ────────────────────────────────────────────────
fake = Faker()
random.seed(42)

categories = ["T‑Shirt", "Jeans", "Jacket", "Sneakers", "Hoodie", "Dress"]
brands     = ["Acme", "Contoso", "NorthWind", "Tailspin", "Fabrikam"]
sizes      = ["XS", "S", "M", "L", "XL", "XXL"]
colours    = ["Red", "Blue", "Green", "Black", "White", "Yellow", "Purple"]

rows = []
for _ in range(500):
    cat = random.choice(categories)
    brand = random.choice(brands)
    size = random.choice(sizes)
    colour = random.choice(colours)
    base_price = {
        "T‑Shirt": 15, "Jeans": 45, "Jacket": 90,
        "Sneakers": 75, "Hoodie": 40, "Dress": 60
    }[cat]
    price = round(np.random.normal(loc=base_price, scale=base_price*0.15), 2)
    units = random.randint(5, 120)
    rows.append((cat, brand, size, colour, price, units, datetime.utcnow()))

df = pd.DataFrame(rows, columns=[
    "Category", "Brand", "Size", "Colour",
    "Price", "UnitsInStock", "CreatedUtc"
])

# ── 4. load into SQL ──────────────────────────────────────────────────────────
df.to_sql("Clothes", engine, schema="dbo", if_exists="append", index=False)
print(f"✓ Inserted {len(df)} rows into dbo.Clothes")
