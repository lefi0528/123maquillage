import Database from 'better-sqlite3';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const dbPath = path.join(__dirname, '../skincare.db');
const db = new Database(dbPath);

const total = db.prepare("SELECT COUNT(*) as count FROM reviews").get().count;
let translated = 0;
try {
  translated = db.prepare("SELECT COUNT(*) as count FROM reviews WHERE translated = 1").get().count;
} catch (e) {
  console.log("translated column doesn't exist yet or has error:", e.message);
}

console.log(`Total reviews in skincare.db: ${total}`);
console.log(`Translated reviews: ${translated}`);
console.log(`Remaining to translate: ${total - translated}`);
db.close();
