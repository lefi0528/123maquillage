import fs from 'fs';
import path from 'path';
import Database from 'better-sqlite3';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const DB_PATH = path.join(__dirname, '../skincare.db');
const PUBLIC_DIR = path.join(__dirname, '../public');
const BASE_URL = 'https://123maquillage.com';

console.log("🚀 Lancement du générateur de sitemaps pour 123maquillage.com...");

if (!fs.existsSync(DB_PATH)) {
  console.error(`❌ Erreur : La base de données skincare.db est introuvable à l'emplacement : ${DB_PATH}`);
  process.exit(1);
}

const db = new Database(DB_PATH);

try {
  // 1. Récupérer les slugs des cosmétiques
  const products = db.prepare("SELECT slug FROM products").all();
  console.log(`✓ Récupération de ${products.length} produits depuis la base de données.`);

  // 2. Récupérer les marques uniques
  const brands = db.prepare("SELECT DISTINCT brand_name FROM products").all();
  console.log(`✓ Récupération de ${brands.length} marques uniques.`);

  // 3. Récupérer les ingrédients actifs uniques
  const rows = db.prepare("SELECT active_ingredients FROM products WHERE active_ingredients IS NOT NULL AND active_ingredients != ''").all();
  const activeSet = new Set();
  rows.forEach(r => {
    r.active_ingredients.split(', ').forEach(act => {
      activeSet.add(act.trim());
    });
  });
  const ingredients = Array.from(activeSet);
  console.log(`✓ Récupération de ${ingredients.length} ingrédients actifs.`);

  // 4. Générer les sitemaps
  generate(products, brands, ingredients);

} catch (error) {
  console.error("❌ Une erreur est survenue lors de la génération :", error);
} finally {
  db.close();
}

function slugify(text) {
  return text
    .toString()
    .toLowerCase()
    .trim()
    .normalize('NFD') // Normalise les accents
    .replace(/[\u0300-\u036f]/g, '') // Supprime les diacritiques
    .replace(/[^\w\s-]/g, '') // Enlève les caractères spéciaux
    .replace(/[-\s]+/g, '-') // Remplace les espaces et tirets multiples par un seul tiret
    .replace(/^-+|-+$/g, ''); // Enlève les tirets en début et fin
}

function writeSitemapFile(filename, urls) {
  const filePath = path.join(PUBLIC_DIR, filename);
  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls.map(url => `  <url>
    <loc>${url}</loc>
    <changefreq>weekly</changefreq>
    <priority>0.7</priority>
  </url>`).join('\n')}
</urlset>`;
  
  fs.writeFileSync(filePath, xml, 'utf8');
  console.log(`  → Sitemap écrit avec succès : ${filename} (${urls.length} URLs)`);
}

function generate(products, brands, ingredients) {
  const sitemapsList = [];

  // A. Sitemap Principal (Routes Statiques & Indexation autoritaire)
  const staticUrls = [
    `${BASE_URL}/`,
    `${BASE_URL}/diagnostic`,
    `${BASE_URL}/contact`,
    `${BASE_URL}/politique-de-confidentialite`,
    `${BASE_URL}/mentions-legales`
  ];
  writeSitemapFile('sitemap-main.xml', staticUrls);
  sitemapsList.push('sitemap-main.xml');

  // B. Sitemap des Marques
  const brandUrls = brands.map(b => `${BASE_URL}/marques/${slugify(b.brand_name)}`);
  writeSitemapFile('sitemap-brands.xml', brandUrls);
  sitemapsList.push('sitemap-brands.xml');

  // C. Sitemap des Produits (Cosmétiques de soin)
  const productUrls = products.map(p => `${BASE_URL}/produits/${p.slug}`);
  writeSitemapFile('sitemap-products.xml', productUrls);
  sitemapsList.push('sitemap-products.xml');

  // D. Sitemap des Ingrédients
  const ingredientUrls = ingredients.map(ing => `${BASE_URL}/ingredients/${slugify(ing)}`);
  writeSitemapFile('sitemap-ingredients.xml', ingredientUrls);
  sitemapsList.push('sitemap-ingredients.xml');

  // E. Index Master Sitemap (sitemap.xml)
  const indexPath = path.join(PUBLIC_DIR, 'sitemap.xml');
  const indexXml = `<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${sitemapsList.map(filename => `  <sitemap>
    <loc>${BASE_URL}/${filename}</loc>
    <lastmod>${new Date().toISOString().split('T')[0]}</lastmod>
  </sitemap>`).join('\n')}
</sitemapindex>`;
  
  fs.writeFileSync(indexPath, indexXml, 'utf8');
  console.log(`✓ Index des sitemaps créé à l'emplacement : sitemap.xml`);

  // F. Créer le robots.txt liant vers le sitemap
  const robotsPath = path.join(PUBLIC_DIR, 'robots.txt');
  const robotsTxt = `User-agent: *
Allow: /

Sitemap: ${BASE_URL}/sitemap.xml`;
  fs.writeFileSync(robotsPath, robotsTxt, 'utf8');
  console.log(`✓ robots.txt créé et configuré avec le sitemap principal.`);
}
