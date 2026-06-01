import os
import csv
import sqlite3

BASE_DIR = r"c:\laragon\www\123maquillage"
CSV_PATH = os.path.join(BASE_DIR, "donnee", "archive", "cosmetics_sales_data.csv")
DB_PATH = os.path.join(BASE_DIR, "skincare.db")

print("--- B2B Sales Data SQLite Importer ---")

if not os.path.exists(CSV_PATH):
    print(f"Error: CSV file not found at {CSV_PATH}")
    exit(1)

# Connect to database
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Create table sales_trends
cursor.execute("""
CREATE TABLE IF NOT EXISTS sales_trends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sales_person TEXT,
    country TEXT,
    product_name TEXT,
    sale_date TEXT,
    amount REAL,
    boxes_shipped INTEGER
);
""")

# Clean existing sales data to avoid duplicates if rerun
cursor.execute("DELETE FROM sales_trends")
print("Cleared existing sales_trends data.")

# Process CSV
inserted_count = 0
rows_to_insert = []

with open(CSV_PATH, mode='r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        # Clean amount (convert e.g. "7897.13" to float)
        try:
            amount_str = row.get("Amount ($)", "0").replace("$", "").replace(",", "").strip()
            amount = float(amount_str)
        except:
            amount = 0.0
            
        try:
            boxes = int(row.get("Boxes Shipped", "0").replace(",", "").strip())
        except:
            boxes = 0
            
        rows_to_insert.append((
            row.get("Sales Person"),
            row.get("Country"),
            row.get("Product"),
            row.get("Date"),
            amount,
            boxes
        ))

if rows_to_insert:
    cursor.executemany("""
    INSERT INTO sales_trends (sales_person, country, product_name, sale_date, amount, boxes_shipped)
    VALUES (?, ?, ?, ?, ?, ?)
    """, rows_to_insert)
    conn.commit()
    inserted_count = len(rows_to_insert)

# Print verification stats
cursor.execute("SELECT COUNT(*) FROM sales_trends")
total_in_db = cursor.fetchone()[0]

cursor.execute("SELECT SUM(amount), SUM(boxes_shipped) FROM sales_trends")
sum_amount, sum_boxes = cursor.fetchone()

conn.close()

print("--- IMPORT COMPLETED ---")
print(f"Rows imported: {inserted_count}")
print(f"Total rows in DB: {total_in_db}")
print(f"Total revenue: {sum_amount:,.2f} $")
print(f"Total boxes shipped: {sum_boxes:,}")
