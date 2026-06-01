export const prerender = false;

import Database from 'better-sqlite3';
import path from 'path';

export async function POST({ request }) {
  try {
    const data = await request.json();
    const email = (data.email || '').trim().toLowerCase();

    // Basic email validation regex
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!email || !emailRegex.test(email)) {
      return new Response(JSON.stringify({ error: "Adresse e-mail invalide." }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const dbPath = path.join(process.cwd(), 'skincare.db');
    const db = new Database(dbPath);

    // Create table if not exists
    db.prepare(`
      CREATE TABLE IF NOT EXISTS newsletter_subscribers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        subscribed_at DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    `).run();

    // Insert subscriber (IGNORE if already exists)
    const stmt = db.prepare(`
      INSERT OR IGNORE INTO newsletter_subscribers (email) VALUES (?)
    `);
    const info = stmt.run(email);
    
    db.close();

    return new Response(JSON.stringify({ success: true, changes: info.changes }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });

  } catch (err) {
    console.error("Newsletter subscription database error:", err);
    return new Response(JSON.stringify({ error: "Une erreur est survenue lors de l'enregistrement." }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}
