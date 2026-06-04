// src/middleware.js
import { defineMiddleware } from 'astro/middleware';

export const onRequest = defineMiddleware((context, next) => {
  const url = new URL(context.request.url);
  const pathname = url.pathname;

  // Si on est sur une route API ou interne, on laisse passer
  if (pathname.startsWith('/api/') || pathname.startsWith('/_astro/') || pathname.startsWith('/@fs/')) {
    return next();
  }

  // --- Règles de redirection pour les anciennes URLs (301 Moved Permanently) ---

  // 1. Anciennes pages avec extension .html (ex: /es/maquillage/1350-stay-satin...html)
  if (pathname.endsWith('.html')) {
    return context.redirect('/', 301);
  }

  // 2. Anciens slugs spécifiques comme /tag/..., /category/..., /wp-content/..., /brands
  if (
    pathname.startsWith('/tag/') ||
    pathname.startsWith('/category/') ||
    pathname.startsWith('/wp-content/') ||
    pathname.startsWith('/brands') ||
    pathname.startsWith('/confirmation-commande') ||
    pathname.startsWith('/connexion') ||
    pathname.startsWith('/2-accueil')
  ) {
    return context.redirect('/', 301);
  }

  // 3. Anciennes langues en préfixe : /fr/..., /es/..., /it/...
  if (
    pathname.startsWith('/fr/') ||
    pathname.startsWith('/es/') ||
    pathname.startsWith('/it/') ||
    pathname.startsWith('/en/') ||
    pathname.startsWith('/de/')
  ) {
    return context.redirect('/', 301);
  }

  // 4. Catégories / sous-catégories avec des ID numériques (ex: /33-yeux, /65_frudia, /125-soin-du-corps)
  // Expressions régulières pour matcher "/{nombre}-texte" ou "/texte/{nombre}-texte" ou "/{nombre}_texte"
  if (/^\/[0-9]+[\-_][a-zA-Z0-9\-_]+/.test(pathname) || /\/[a-zA-Z0-9\-_]+\/[0-9]+[\-_][a-zA-Z0-9\-_]+/.test(pathname)) {
    return context.redirect('/', 301);
  }

  // 5. Mots clés courants des anciennes catégories sans extension
  const oldCategories = [
    '/maquillage', '/cheveux', '/solaires', '/hygiene', '/parfums', '/homme', '/femme',
    '/cosmetique-visage', '/soin-des-pieds', '/rouge-a-levres', '/mascara', '/crayon',
    '/fard-a-paupieres', '/huile-de-corps', '/gel', '/concealer-correcteur', '/teint-',
    '/pinceaux-teint', '/palette-yeux'
  ];
  if (oldCategories.some(cat => pathname.startsWith(cat))) {
    return context.redirect('/', 301);
  }

  // 6. Redirection du favicon.ico vers favicon.svg si demandé (puisque le site utilise un svg)
  if (pathname === '/favicon.ico') {
    return context.redirect('/favicon.svg', 301);
  }

  // 7. Redirection de l'ancienne image OpenGraph
  if (pathname === '/images/og-image.jpg') {
    return context.redirect('/', 301);
  }

  // Si aucune règle n'a matché, on passe à la suite (Astro gérera la route normale ou affichera la 404)
  return next();
});
