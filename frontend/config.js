(function () {
  const stored = localStorage.getItem('wos_api_url');
  window.WOS_API_URL = stored && stored.trim() ? stored.trim() : 'http://localhost:8080';
})();
