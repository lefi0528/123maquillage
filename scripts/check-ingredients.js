import Database from 'better-sqlite3';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const dbPath = path.join(__dirname, '../skincare.db');
const db = new Database(dbPath);

const ingredients = [
  { name: "Rétinol", activeName: "retinol" },
  { name: "Acide Lactique", activeName: "acide lactique" },
  { name: "Acide Hyaluronique", activeName: "acide hyaluronique" },
  { name: "Acide Glycolique", activeName: "acide glycolique" },
  { name: "Vitamine C", activeName: "vitamine c" },
  { name: "Acide Salicylique", activeName: "acide salicylique" },
  { name: "Squalane", activeName: "squalane" },
  { name: "Niacinamide", activeName: "niacinamide" },
  { name: "Centella Asiatica", activeName: "centella asiatica" },
  { name: "Céramides", activeName: "ceramides" },
  { name: "Huile d'Arbre à Thé", activeName: "huile d'arbre a the" }
];

ingredients.forEach(ing => {
  const products = db.prepare("SELECT product_name FROM products WHERE active_ingredients LIKE ?").all(`%${ing.activeName}%`);
  console.log(`Ingredient: ${ing.name} (${ing.activeName}) -> Found ${products.length} products`);
  if (products.length > 0) {
    console.log(`  Sample: ${products.slice(0, 3).map(p => p.product_name).join(', ')}`);
  }
});

db.close();
