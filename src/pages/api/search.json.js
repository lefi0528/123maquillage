export const prerender = false;

import Database from 'better-sqlite3';
import path from 'path';

export async function GET({ request }) {
  const url = new URL(request.url);
  const q = url.searchParams.get('q') || '';
  
  if (!q || q.length < 2) {
    return new Response(JSON.stringify({ results: [] }), {
      status: 200,
      headers: { 
        'Content-Type': 'application/json',
        'Cache-Control': 'public, max-age=60'
      }
    });
  }

  try {
    const dbPath = path.join(process.cwd(), 'skincare.db');
    const db = new Database(dbPath);

    const stmt = db.prepare(`
      SELECT product_name, brand_name, slug, rating 
      FROM products 
      WHERE product_name LIKE ? OR brand_name LIKE ? 
      ORDER BY loves_count DESC 
      LIMIT 6
    `);

    const results = stmt.all(`%${q}%`, `%${q}%`);
    db.close();

    return new Response(JSON.stringify({ results }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (err) {
    console.error("Database search error:", err);
    return new Response(JSON.stringify({ error: "Failed to query database", results: [] }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}
