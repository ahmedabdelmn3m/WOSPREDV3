/**
 * WOSPREDV3 Frontend Configuration
 *
 * HOW TO SET YOUR RAILWAY API URL
 * ─────────────────────────────────
 * Option A (recommended): Click ⚙ Settings in the app and paste your Railway URL.
 *   It is stored in localStorage and survives page reloads.
 *
 * Option B (hardcode): Replace the string below with your Railway URL, then
 *   push to GitHub — Vercel will pick it up automatically.
 *
 * Local development default: http://localhost:8080
 */
(function () {
  const stored = localStorage.getItem('wos_api_url');
  
  if (stored && stored.trim()) {
    window.WOS_API_URL = stored.trim();
  } else if (window.location.hostname.includes('vercel.app')) {
    // Use the proxy defined in vercel.json
    window.WOS_API_URL = window.location.origin + "/api";
  } else {
    // Localhost or other fallback
    window.WOS_API_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
      ? 'http://localhost:8080'
      : 'https://wospredv3.up.railway.app';
  }
})();
