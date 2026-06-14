import express from 'express';
import compression from 'compression';
import { handler as astroHandler } from './dist/server/entry.mjs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import fs from 'fs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const clientDir = join(__dirname, 'dist', 'client');

const app = express();

// Enforce security, HTTPS, and clean trailing slashes for SEO
app.use((req, res, next) => {
    // 1. HSTS Header (Strict-Transport-Security)
    res.setHeader('Strict-Transport-Security', 'max-age=31536000; includeSubDomains; preload');
    
    // 2. Redirect HTTP to HTTPS (for proxies like Cloud Run / Vercel)
    if (req.headers['x-forwarded-proto'] === 'http') {
        return res.redirect(301, `https://${req.hostname}${req.url}`);
    }
    
    // 3. Optional: Redirect www to non-www
    if (req.hostname === 'www.123maquillage.com') {
        return res.redirect(301, `https://123maquillage.com${req.url}`);
    }
    
    // 4. Clean trailing slashes for SEO (force no trailing slash)
    if (req.path.length > 1 && req.path.endsWith('/')) {
        const urlObj = new URL(req.url, `http://${req.headers.host}`);
        urlObj.pathname = urlObj.pathname.slice(0, -1);
        return res.redirect(301, urlObj.pathname + urlObj.search);
    }
    
    next();
});

// Enable gzip/brotli compression for all responses
app.use(compression({
    level: 6,
    threshold: 256,
    filter: (req, res) => {
        if (req.headers['x-no-compression']) return false;
        return compression.filter(req, res);
    }
}));

// Serve static directories' index.html without trailing slashes
app.use((req, res, next) => {
    if (req.method !== 'GET' && req.method !== 'HEAD') return next();
    if (req.path === '/' || req.path.match(/\.[^/]+$/)) return next();
    
    const indexPath = join(clientDir, req.path, 'index.html');
    fs.stat(indexPath, (err, stats) => {
        if (!err && stats.isFile()) {
            return res.sendFile(indexPath, { maxAge: '1y', immutable: true });
        }
        next();
    });
});

// Serve Astro's built static files with long cache
app.use(express.static(clientDir, {
    maxAge: '1y',
    immutable: true,
    index: ['index.html'],
    redirect: false
}));

// All other requests go through Astro SSR handler
app.use(astroHandler);

const port = process.env.PORT || 8080;
const host = process.env.HOST || '0.0.0.0';

app.listen(port, host, () => {
    console.log(`Server running on http://${host}:${port}`);
});
