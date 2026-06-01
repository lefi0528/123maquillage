import sqlite3

def detect_skin_type(text, title):
    content = ((title or "") + " " + (text or "")).lower()
    
    # Priority checks
    if "combination skin" in content or "peau mixte" in content:
        return "combination"
    if "oily skin" in content or "peau grasse" in content:
        return "oily"
    if "dry skin" in content or "peau sèche" in content or "peau seche" in content:
        return "dry"
    if "normal skin" in content or "peau normale" in content:
        return "normal"
    
    # Extra keyword heuristics for robustness
    if "ma peau grasse" in content or "excès de sébum" in content or "tendance acnéique" in content or "tendance acneique" in content:
        return "oily"
    if "ma peau sèche" in content or "ma peau seche" in content or "peau deshydratee" in content or "peau déshydratée" in content or "peaux sèches" in content:
        return "dry"
    if "ma peau mixte" in content or "zone t" in content:
        return "combination"
    
    return None

def main():
    conn = sqlite3.connect("skincare.db")
    c = conn.cursor()
    
    # Select all reviews where skin_type is empty or null
    c.execute("SELECT id, review_title, review_text FROM reviews WHERE skin_type = '' OR skin_type IS NULL")
    rows = c.fetchall()
    
    print(f"Total reviews with missing skin type in DB: {len(rows)}")
    
    enriched_count = 0
    updates = []
    
    for rid, title, text in rows:
        detected = detect_skin_type(text, title)
        if detected:
            updates.append((detected, rid))
            enriched_count += 1
            
    if updates:
        print(f"Updating {enriched_count} reviews with extracted skin types...")
        c.executemany("UPDATE reviews SET skin_type = ? WHERE id = ?", updates)
        conn.commit()
        print("Database updated successfully!")
    else:
        print("No skin types were extracted from review text.")
        
    conn.close()

if __name__ == "__main__":
    main()
