/**
 * Service Worker for AI Clip Creator — Phase 3 Advanced Optimizations
 *
 * Strategies:
 *   - Cache-first for static assets (CSS, JS, images, fonts)
 *   - Network-first for API calls (/list-music)
 *   - Stale-while-revalidate for CDN resources
 *   - Offline fallback page for navigation requests
 *   - Cache versioning with automatic cleanup of old caches
 *   - SkipWaiting + ClientsClaim for immediate activation
 *
 * IMPORTANT: POST/PUT/DELETE requests are NEVER cached.
 */

const CACHE_VERSION = 'v3.1.0';
const STATIC_CACHE = `static-${CACHE_VERSION}`;
const API_CACHE = `api-${CACHE_VERSION}`;
const RUNTIME_CACHE = `runtime-${CACHE_VERSION}`;

// Pre-cache critical assets on install
const PRECACHE_URLS = [
  '/static/style.css',
  '/static/app.js',
];

// Static asset extensions — cache-first strategy
const STATIC_EXTENSIONS = [
  '.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg',
  '.webp', '.ico', '.woff', '.woff2', '.ttf', '.otf', '.eot',
];

// API routes that use network-first strategy (GET only)
const API_ROUTES = [
  '/list-music',
];

// ── Install Event ──────────────────────────────────────────────────────
self.addEventListener('install', (event) => {
  console.log('[SW] Installing Service Worker', CACHE_VERSION);
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => {
        console.log('[SW] Pre-caching critical assets');
        // Pre-cache what we can; failures are non-fatal
        return Promise.allSettled(
          PRECACHE_URLS.map((url) =>
            cache.add(url).catch((err) => {
              console.warn('[SW] Failed to pre-cache:', url, err.message);
            })
          )
        );
      })
      .then(() => self.skipWaiting())
  );
});

// ── Activate Event ─────────────────────────────────────────────────────
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating Service Worker', CACHE_VERSION);
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        // Delete old caches that don't match current version
        return Promise.all(
          cacheNames
            .filter((name) => {
              const isStatic = name.startsWith('static-') && name !== STATIC_CACHE;
              const isApi = name.startsWith('api-') && name !== API_CACHE;
              const isRuntime = name.startsWith('runtime-') && name !== RUNTIME_CACHE;
              // Also clean up Phase 1 single-cache format
              const isLegacy = name === 'ai-clip-creator-v1';
              return isStatic || isApi || isRuntime || isLegacy;
            })
            .map((name) => {
              console.log('[SW] Removing old cache:', name);
              return caches.delete(name);
            })
        );
      })
      .then(() => self.clients.claim())
  );
});

// ── Fetch Event ────────────────────────────────────────────────────────
self.addEventListener('fetch', (event) => {
  const { request } = event;

  // NEVER cache non-GET requests (POST, PUT, DELETE, etc.)
  if (request.method !== 'GET') {
    return;
  }

  const url = new URL(request.url);

  // Only handle same-origin requests for caching
  if (url.origin !== self.location.origin) {
    // For cross-origin CDN resources, use stale-while-revalidate
    if (isStaticAsset(url.pathname)) {
      event.respondWith(staleWhileRevalidate(request, RUNTIME_CACHE));
      return;
    }
    return;
  }

  const pathname = url.pathname;

  // API routes — network-first strategy
  if (isApiRoute(pathname)) {
    event.respondWith(networkFirst(request, API_CACHE, 120)); // 2 min cache
    return;
  }

  // Dynamic user content — network-first with short cache
  if (isDynamicContent(pathname)) {
    event.respondWith(networkFirst(request, RUNTIME_CACHE, 60)); // 1 min cache
    return;
  }

  // Static assets — cache-first strategy
  if (isStaticAsset(pathname)) {
    event.respondWith(cacheFirst(request, STATIC_CACHE));
    return;
  }

  // HTML pages — network-first with offline fallback
  if (isHtmlRequest(request, pathname)) {
    event.respondWith(networkFirstWithOfflineFallback(request));
    return;
  }

  // Default: network-first with runtime cache
  event.respondWith(networkFirst(request, RUNTIME_CACHE, 300));
});

// ── Strategy Implementations ───────────────────────────────────────────

/**
 * Cache-first: Serve from cache if available, fall back to network.
 * Used for static assets that rarely change (CSS, JS, images).
 */
async function cacheFirst(request, cacheName) {
  try {
    const cached = await caches.match(request);
    if (cached) {
      return cached;
    }
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    console.warn('[SW] Cache-first failed for:', request.url, error.message);
    return new Response('Network error', { status: 503, statusText: 'Service Unavailable' });
  }
}

/**
 * Network-first: Try network first, fall back to cache.
 * Used for API calls and dynamic content where freshness matters.
 * @param {number} maxAge - Maximum cache age in seconds
 */
async function networkFirst(request, cacheName, maxAge = 120) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      // Clone and store with timestamp header for TTL
      const responseToCache = response.clone();
      const headers = new Headers(responseToCache.headers);
      headers.set('sw-cache-timestamp', Date.now().toString());
      const body = await responseToCache.blob();
      const cachedResponse = new Response(body, {
        status: responseToCache.status,
        statusText: responseToCache.statusText,
        headers: headers,
      });
      cache.put(request, cachedResponse);
    }
    return response;
  } catch (error) {
    // Network failed — try cache with TTL check
    const cached = await caches.match(request);
    if (cached) {
      const timestamp = cached.headers.get('sw-cache-timestamp');
      if (timestamp) {
        const age = (Date.now() - parseInt(timestamp, 10)) / 1000;
        if (age <= maxAge) {
          // Remove the internal header before serving
          const cleanHeaders = new Headers(cached.headers);
          cleanHeaders.delete('sw-cache-timestamp');
          return new Response(cached.body, {
            status: cached.status,
            statusText: cached.statusText,
            headers: cleanHeaders,
          });
        }
      }
      // Even if stale, serve it (better than nothing)
      return cached;
    }
    console.warn('[SW] Network-first failed, no cache for:', request.url);
    return new Response(
      JSON.stringify({ success: false, error: 'Network unavailable' }),
      {
        status: 503,
        statusText: 'Service Unavailable',
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}

/**
 * Stale-while-revalidate: Serve from cache immediately, update cache in background.
 * Used for CDN resources where stale content is acceptable.
 */
async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);

  // Fetch in background to update cache
  const fetchPromise = fetch(request)
    .then((response) => {
      if (response.ok) {
        cache.put(request, response.clone());
      }
      return response;
    })
    .catch(() => cached);

  // Return cached immediately if available, otherwise wait for network
  return cached || fetchPromise;
}

/**
 * Network-first with offline fallback page for HTML navigation requests.
 */
async function networkFirstWithOfflineFallback(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      // Cache successful HTML responses in runtime cache
      const cache = await caches.open(RUNTIME_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    // Try runtime cache first
    const cached = await caches.match(request);
    if (cached) {
      return cached;
    }
    // Return offline fallback page
    return getOfflineFallback();
  }
}

/**
 * Generate an offline fallback page.
 */
function getOfflineFallback() {
  const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI Clip Creator — Offline</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      background: #0a0a0f;
      color: #f0f0f5;
      font-family: 'Inter', system-ui, sans-serif;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      text-align: center;
      padding: 2rem;
    }
    .offline-container { max-width: 420px; }
    .offline-icon { font-size: 4rem; margin-bottom: 1rem; opacity: 0.6; }
    h1 { font-size: 1.4rem; font-weight: 700; margin-bottom: 0.5rem; }
    p { font-size: 0.9rem; color: #a0a0b8; line-height: 1.6; margin-bottom: 1.5rem; }
    .btn-retry {
      background: linear-gradient(135deg, #7c3aed, #9333ea);
      color: #fff;
      border: none;
      padding: 0.65rem 1.5rem;
      border-radius: 8px;
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
      transition: transform 0.2s, box-shadow 0.2s;
    }
    .btn-retry:hover {
      transform: translateY(-1px);
      box-shadow: 0 4px 20px rgba(124, 58, 237, 0.25);
    }
  </style>
</head>
<body>
  <div class="offline-container">
    <div class="offline-icon">&#128268;</div>
    <h1>You're Offline</h1>
    <p>AI Clip Creator needs an internet connection to process videos. Please check your connection and try again.</p>
    <button class="btn-retry" onclick="window.location.reload()">Try Again</button>
  </div>
</body>
</html>`;

  return new Response(html, {
    status: 503,
    statusText: 'Service Unavailable',
    headers: {
      'Content-Type': 'text/html; charset=utf-8',
      'Cache-Control': 'no-cache',
    },
  });
}

// ── Helper Functions ────────────────────────────────────────────────────

function isStaticAsset(pathname) {
  return STATIC_EXTENSIONS.some((ext) => pathname.endsWith(ext));
}

function isApiRoute(pathname) {
  return API_ROUTES.some((route) => pathname === route || pathname.startsWith(route + '/'));
}

function isDynamicContent(pathname) {
  const dynamicPrefixes = ['/static/clips/', '/static/uploads/', '/static/exports/', '/static/previews/'];
  return dynamicPrefixes.some((prefix) => pathname.startsWith(prefix));
}

function isHtmlRequest(request, pathname) {
  const accept = request.headers.get('Accept') || '';
  return (
    request.mode === 'navigate' ||
    accept.includes('text/html') ||
    pathname === '/' ||
    pathname === '/index.html'
  );
}