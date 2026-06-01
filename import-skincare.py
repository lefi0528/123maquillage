import os
import csv
import json
import sqlite3
import re
from collections import defaultdict

# Setup paths
BASE_DIR = r"c:\laragon\www\123maquillage"
DATA_DIR = os.path.join(BASE_DIR, "donnee")
PRODUCTS_CSV = os.path.join(DATA_DIR, "product_info_skincare.csv", "product_info_skincare.csv")
REVIEWS_PATHS = [
    os.path.join(DATA_DIR, "reviews_0-250_masked.csv", "reviews_0-250_masked.csv"),
    os.path.join(DATA_DIR, "reviews_250-500_masked.csv", "reviews_250-500_masked.csv"),
    os.path.join(DATA_DIR, "reviews_500-750_masked.csv", "reviews_500-750_masked.csv"),
    os.path.join(DATA_DIR, "reviews_750-1250_masked.csv", "reviews_750-1250_masked.csv"),
    os.path.join(DATA_DIR, "reviews_1250-end_masked.csv", "reviews_1250-end_masked.csv"),
]
DB_PATH = os.path.join(BASE_DIR, "skincare.db")

print("--- Skincare Data Aggregator & SQLite Importer ---")

def slugify(text):
    text = text.lower().strip()
    # Remove accents
    import unicodedata
    text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8')
    # Clean characters
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')

# Step 1: Parse and filter skincare products
print("Loading products...")
products = {}
brand_names = set()
existing_slugs = set()

# Active ingredients we want to index
ACTIVE_INGREDIENTS = {
    "retinol": ["retinol", "retinyl"],
    "acide hyaluronique": ["hyaluronic acid", "sodium hyaluronate"],
    "niacinamide": ["niacinamide", "vitamin b3"],
    "vitamine c": ["ascorbic acid", "vitamin c", "tetrahexyldecyl ascorbate"],
    "acide salicylique": ["salicylic acid", "bha"],
    "acide glycolique": ["glycolic acid", "aha"],
    "acide lactique": ["lactic acid"],
    "ceramides": ["ceramide np", "ceramide ap", "ceramide eop", "ceramides"],
    "squalane": ["squalane"],
    "centella asiatica": ["centella asiatica", "cica", "madecassoside"],
    "huile d'arbre a the": ["tea tree oil", "melaleuca alternifolia"]
}

with open(PRODUCTS_CSV, mode='r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        pid = row.get("product_id")
        pname = row.get("product_name")
        brand = row.get("brand_name")
        primary_cat = row.get("primary_category")
        
        # Filter for skincare, body moisturizers, bath and body etc.
        # We also filter out any obvious hair-only brands or non-skincare items
        if primary_cat not in ["Skincare", "Bath & Body", "Mini Size"]:
            continue
        
        # Avoid perfume discovery sets or gift sets if possible
        if "gift set" in pname.lower() or "discovery set" in pname.lower() or "perfume" in pname.lower():
            if primary_cat != "Skincare":
                continue

        slug = slugify(f"{brand}-{pname}")
        if slug in existing_slugs:
            slug = slugify(f"{brand}-{pname}-{pid}")
        existing_slugs.add(slug)
        
        # Extract ingredients from format "['Water', 'Glycerin', ...]"
        ingredients_raw = row.get("ingredients", "")
        ingredients_list = []
        if ingredients_raw:
            try:
                # Basic cleanup of stringified python lists
                cleaned = ingredients_raw.strip().replace("['", "").replace("']", "").replace("', '", "; ").replace('", "', '; ').replace('["', '').replace('"]', '')
                ingredients_list = [i.strip() for i in cleaned.split("; ") if i.strip()]
            except:
                ingredients_list = [ingredients_raw]
        
        # Find active ingredients in this product
        found_actives = []
        ing_text_lower = " ".join(ingredients_list).lower()
        for active_name, keywords in ACTIVE_INGREDIENTS.items():
            for kw in keywords:
                if kw in ing_text_lower:
                    found_actives.append(active_name)
                    break
        
        products[pid] = {
            "product_id": pid,
            "product_name": pname,
            "brand_id": row.get("brand_id"),
            "brand_name": brand,
            "slug": slug,
            "loves_count": int(row.get("loves_count") or 0),
            "rating": float(row.get("rating") or 0.0),
            "reviews_count": int(float(row.get("reviews") or 0)),
            "size": row.get("size"),
            "ingredients": ", ".join(ingredients_list),
            "price_usd": float(row.get("price_usd") or 0.0),
            "primary_category": primary_cat,
            "secondary_category": row.get("secondary_category"),
            "tertiary_category": row.get("tertiary_category"),
            "highlights": row.get("highlights", ""),
            "active_ingredients": found_actives,
            # Skin-type stats to calculate from reviews
            "reviews_dry_count": 0,
            "reviews_dry_rating_sum": 0.0,
            "reviews_dry_recommend_sum": 0,
            
            "reviews_oily_count": 0,
            "reviews_oily_rating_sum": 0.0,
            "reviews_oily_recommend_sum": 0,
            
            "reviews_combination_count": 0,
            "reviews_combination_rating_sum": 0.0,
            "reviews_combination_recommend_sum": 0,
            
            "reviews_normal_count": 0,
            "reviews_normal_rating_sum": 0.0,
            "reviews_normal_recommend_sum": 0,
            
            # Reviews list to store top 5 helpful
            "helpful_reviews": []
        }
        brand_names.add(brand)

print(f"Loaded {len(products)} skincare/body products.")

# Step 2: Read reviews and aggregate stats
print("Loading and aggregating reviews...")
imported_reviews_count = 0

for file_path in REVIEWS_PATHS:
    if not os.path.exists(file_path):
        print(f"Warning: {file_path} does not exist. Skipping.")
        continue
    
    print(f"Processing {os.path.basename(file_path)}...")
    with open(file_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row.get("product_id")
            if pid not in products:
                continue
            
            rating = float(row.get("rating") or 0.0)
            is_rec = row.get("is_recommended")
            is_rec_val = 1 if is_rec in ["1.0", "1", "True", "true"] else 0
            skin_type = row.get("skin_type", "").lower().strip()
            
            # Aggregate stats based on skin type
            p = products[pid]
            if skin_type == "dry":
                p["reviews_dry_count"] += 1
                p["reviews_dry_rating_sum"] += rating
                p["reviews_dry_recommend_sum"] += is_rec_val
            elif skin_type == "oily":
                p["reviews_oily_count"] += 1
                p["reviews_oily_rating_sum"] += rating
                p["reviews_oily_recommend_sum"] += is_rec_val
            elif skin_type == "combination":
                p["reviews_combination_count"] += 1
                p["reviews_combination_rating_sum"] += rating
                p["reviews_combination_recommend_sum"] += is_rec_val
            elif skin_type == "normal":
                p["reviews_normal_count"] += 1
                p["reviews_normal_rating_sum"] += rating
                p["reviews_normal_recommend_sum"] += is_rec_val
            
            # Parse helpfulness metrics to sort reviews later
            helpfulness = float(row.get("helpfulness") or 0.0)
            total_feedback = int(row.get("total_feedback_count") or 0)
            pos_feedback = int(row.get("total_pos_feedback_count") or 0)
            
            review_text = row.get("review_text", "").strip()
            review_title = row.get("review_title", "").strip()
            
            if review_text:
                # Add review to candidate list
                p["helpful_reviews"].append({
                    "rating": rating,
                    "is_recommended": is_rec_val,
                    "pos_feedback": pos_feedback,
                    "total_feedback": total_feedback,
                    "review_text": review_text,
                    "review_title": review_title,
                    "skin_type": skin_type,
                    "skin_tone": row.get("skin_tone", ""),
                    "eye_color": row.get("eye_color", "")
                })
                imported_reviews_count += 1

print(f"Aggregated {imported_reviews_count} reviews.")

# Step 3: Setup SQLite database
print(f"Creating SQLite database at {DB_PATH}...")
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Create Tables
cursor.execute("""
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT UNIQUE,
    product_name TEXT,
    brand_id TEXT,
    brand_name TEXT,
    slug TEXT UNIQUE,
    loves_count INTEGER,
    rating REAL,
    reviews_count INTEGER,
    size TEXT,
    ingredients TEXT,
    price_usd REAL,
    primary_category TEXT,
    secondary_category TEXT,
    tertiary_category TEXT,
    highlights TEXT,
    active_ingredients TEXT,
    
    -- Dry skin stats
    reviews_dry_count INTEGER,
    rating_dry REAL,
    recommend_dry REAL,
    
    -- Oily skin stats
    reviews_oily_count INTEGER,
    rating_oily REAL,
    recommend_oily REAL,
    
    -- Combination skin stats
    reviews_combination_count INTEGER,
    rating_combination REAL,
    recommend_combination REAL,
    
    -- Normal skin stats
    reviews_normal_count INTEGER,
    rating_normal REAL,
    recommend_normal REAL
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT,
    rating INTEGER,
    is_recommended INTEGER,
    pos_feedback INTEGER,
    total_feedback INTEGER,
    review_text TEXT,
    review_title TEXT,
    skin_type TEXT,
    skin_tone TEXT,
    eye_color TEXT,
    FOREIGN KEY(product_id) REFERENCES products(product_id)
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS product_actives (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT,
    active_name TEXT,
    FOREIGN KEY(product_id) REFERENCES products(product_id)
);
""")

# Create performance indexes
cursor.execute("CREATE INDEX idx_products_slug ON products(slug);")
cursor.execute("CREATE INDEX idx_products_brand ON products(brand_name);")
cursor.execute("CREATE INDEX idx_reviews_product_id ON reviews(product_id);")
cursor.execute("CREATE INDEX idx_actives_name ON product_actives(active_name);")

# Step 4: Insert Data
print("Inserting data into SQLite database...")
conn.execute("BEGIN TRANSACTION;")

inserted_products = 0
inserted_reviews = 0
inserted_actives = 0

for pid, p in products.items():
    # Calculate average ratings and recommendation rates per skin type
    rating_dry = round(p["reviews_dry_rating_sum"] / p["reviews_dry_count"], 2) if p["reviews_dry_count"] > 0 else None
    recommend_dry = round(p["reviews_dry_recommend_sum"] / p["reviews_dry_count"] * 100, 1) if p["reviews_dry_count"] > 0 else None
    
    rating_oily = round(p["reviews_oily_rating_sum"] / p["reviews_oily_count"], 2) if p["reviews_oily_count"] > 0 else None
    recommend_oily = round(p["reviews_oily_recommend_sum"] / p["reviews_oily_count"] * 100, 1) if p["reviews_oily_count"] > 0 else None
    
    rating_comb = round(p["reviews_combination_rating_sum"] / p["reviews_combination_count"], 2) if p["reviews_combination_count"] > 0 else None
    recommend_comb = round(p["reviews_combination_recommend_sum"] / p["reviews_combination_count"] * 100, 1) if p["reviews_combination_count"] > 0 else None
    
    rating_norm = round(p["reviews_normal_rating_sum"] / p["reviews_normal_count"], 2) if p["reviews_normal_count"] > 0 else None
    recommend_norm = round(p["reviews_normal_recommend_sum"] / p["reviews_normal_count"] * 100, 1) if p["reviews_normal_count"] > 0 else None

    # Insert product
    cursor.execute("""
    INSERT INTO products (
        product_id, product_name, brand_id, brand_name, slug, loves_count, rating, reviews_count,
        size, ingredients, price_usd, primary_category, secondary_category, tertiary_category, highlights, active_ingredients,
        reviews_dry_count, rating_dry, recommend_dry,
        reviews_oily_count, rating_oily, recommend_oily,
        reviews_combination_count, rating_combination, recommend_combination,
        reviews_normal_count, rating_normal, recommend_normal
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        pid, p["product_name"], p["brand_id"], p["brand_name"], p["slug"], p["loves_count"], p["rating"], p["reviews_count"],
        p["size"], p["ingredients"], p["price_usd"], p["primary_category"], p["secondary_category"], p["tertiary_category"], p["highlights"],
        ", ".join(p["active_ingredients"]),
        p["reviews_dry_count"], rating_dry, recommend_dry,
        p["reviews_oily_count"], rating_oily, recommend_oily,
        p["reviews_combination_count"], rating_comb, recommend_comb,
        p["reviews_normal_count"], rating_norm, recommend_norm
    ))
    inserted_products += 1

    # Insert active ingredient mappings
    for act in p["active_ingredients"]:
        cursor.execute("INSERT INTO product_actives (product_id, active_name) VALUES (?, ?)", (pid, act))
        inserted_actives += 1

    # Sort reviews by pos_feedback descending, then rating descending
    # Filter out extremely short reviews if possible
    sorted_revs = sorted(
        p["helpful_reviews"], 
        key=lambda r: (r["pos_feedback"], r["rating"], len(r["review_text"])), 
        reverse=True
    )
    
    # Insert top 5 reviews
    for rev in sorted_revs[:5]:
        cursor.execute("""
        INSERT INTO reviews (
            product_id, rating, is_recommended, pos_feedback, total_feedback, review_text, review_title, skin_type, skin_tone, eye_color
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pid, rev["rating"], rev["is_recommended"], rev["pos_feedback"], rev["total_feedback"],
            rev["review_text"], rev["review_title"], rev["skin_type"], rev["skin_tone"], rev["eye_color"]
        ))
        inserted_reviews += 1

conn.commit()
conn.close()

print("--- IMPORT COMPLETED ---")
print(f"Products imported: {inserted_products}")
print(f"Active ingredient mappings: {inserted_actives}")
print(f"Selected top-reviews imported: {inserted_reviews}")
print("Database created successfully at skincare.db")
