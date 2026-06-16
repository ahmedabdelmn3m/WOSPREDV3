(function () {
  const stored = localStorage.getItem('wos_api_url');
  const isLocal = ['localhost', '127.0.0.1', ''].includes(window.location.hostname);
  const defaultUrl = isLocal ? 'http://localhost:8080' : 'https://wospredv3-production.up.railway.app';
  window.WOS_API_URL = isLocal && stored && stored.trim() ? stored.trim() : defaultUrl;
})();
