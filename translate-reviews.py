import sqlite3
import json
import urllib.request
import urllib.error
import sys
import time

DB_PATH = "skincare.db"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:7b"  # User has this model installed locally!

def check_ollama():
    global MODEL_NAME
    print(f"Checking connection to local Ollama on {OLLAMA_URL}...")
    try:
        req = urllib.request.Request(
            OLLAMA_URL.replace("/generate", "/tags"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            models = [m["name"] for m in data.get("models", [])]
            print(f"Connection successful! Installed models: {', '.join(models)}")
            if MODEL_NAME in models:
                print(f"Using model: {MODEL_NAME}")
                return True
            elif "qwen2.5:14b" in models:
                MODEL_NAME = "qwen2.5:14b"
                print(f"Model {MODEL_NAME} not found, using qwen2.5:14b instead.")
                return True
            else:
                print(f"Warning: model '{MODEL_NAME}' is not pre-installed. Ollama might try to download it dynamically or fail.")
                return True
    except Exception as e:
        print(f"Error connecting to Ollama: {e}")
        print("Please make sure Ollama is running on your machine ('ollama serve').")
        return False

def translate_text(text, is_title=False):
    if not text or not text.strip():
        return text

    # Craft a precise translation prompt for cosmetics reviews
    role = "titre d'avis" if is_title else "avis d'utilisateur"
    prompt = (
        f"Translate the following cosmetic review {role} from English to French. "
        "Keep the translation natural, authentic, and emotional, exactly like a real French beauty customer. "
        "Do NOT add any conversational fluff, notes, introduction, or quotes. "
        "Return ONLY the direct French translation.\n\n"
        f"Text to translate:\n{text}"
    )

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "system": "You are an expert translator of beauty, cosmetics, and skincare consumer reviews.",
        "stream": False,
        "options": {
            "temperature": 0.3,
            "top_p": 0.9
        }
    }

    try:
        req = urllib.request.Request(
            OLLAMA_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode())
            translated = result.get("response", "").strip()
            # Basic cleanup in case Ollama wraps the output in quotes
            if translated.startswith('"') and translated.endswith('"'):
                translated = translated[1:-1].strip()
            if translated.startswith('«') and translated.endswith('»'):
                translated = translated[1:-1].strip()
            return translated
    except Exception as e:
        print(f"\n[Translation Error]: {e}")
        return None

def main():
    if not check_ollama():
        sys.exit(1)

    print(f"Opening database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Step 1: Ensure 'translated' column exists in reviews table
    try:
        cursor.execute("ALTER TABLE reviews ADD COLUMN translated INTEGER DEFAULT 0;")
        conn.commit()
        print("Added 'translated' column to 'reviews' table.")
    except sqlite3.OperationalError:
        # Column already exists, which is fine
        pass

    # Step 2: Count reviews to translate
    cursor.execute("SELECT COUNT(*) FROM reviews WHERE translated = 0")
    total_to_translate = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM reviews")
    total_reviews = cursor.fetchone()[0]

    print(f"Total reviews in database: {total_reviews}")
    print(f"Reviews left to translate: {total_to_translate}")

    if total_to_translate == 0:
        print("All reviews are already translated!")
        conn.close()
        return

    # Step 3: Fetch and translate reviews in chunks
    cursor.execute("SELECT id, review_text, review_title FROM reviews WHERE translated = 0")
    rows = cursor.fetchall()

    translated_count = 0
    start_time = time.time()

    print("\nStarting local translation batch... (Press Ctrl+C to stop safely anytime)\n")

    try:
        for rid, text, title in rows:
            print(f"\rTranslating review ID {rid} ({translated_count + 1}/{total_to_translate})...", end="", flush=True)
            
            # Translate title
            trans_title = translate_text(title, is_title=True)
            if trans_title is None:
                # If translation fails, we skip and will try again next time
                continue

            # Translate text
            trans_text = translate_text(text, is_title=False)
            if trans_text is None:
                continue

            # Update database
            cursor.execute(
                "UPDATE reviews SET review_text = ?, review_title = ?, translated = 1 WHERE id = ?",
                (trans_text, trans_title, rid)
            )
            
            # Commit every 5 reviews to balance safety and performance
            translated_count += 1
            if translated_count % 5 == 0:
                conn.commit()

            # Calculate time metrics
            elapsed = time.time() - start_time
            avg_time = elapsed / translated_count
            eta = avg_time * (total_to_translate - translated_count)
            eta_min = eta / 60
            
            print(f" [Done in {avg_time:.2f}s | ETA: {eta_min:.1f} min]")

    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user. Saving progress and exiting...")
    finally:
        conn.commit()
        conn.close()
        print(f"\nBatch completed! Translated {translated_count} reviews during this run.")
        print("Your progress has been securely saved to skincare.db.")

if __name__ == "__main__":
    main()
