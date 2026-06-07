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
  window.WOS_API_URL = stored && stored.trim()
    ? stored.trim()
    : 'http://localhost:8080';
})();
