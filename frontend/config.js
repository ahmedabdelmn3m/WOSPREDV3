(function () {
  const DEFAULT_API_URL = 'https://wospredv3-production.up.railway.app';
  const STORAGE_KEY = 'wos_api_url';
  const VERSION = {
    label: 'WOSPREDV3 strategy-update-v1',
    source: '/frontend',
    commit: '',
    buildTime: '2026-07-07 deployed',
  };

  function normalizeUrl(value) {
    return String(value || '').trim().replace(/\/+$/, '');
  }

  function readStoredUrl() {
    try {
      return normalizeUrl(localStorage.getItem(STORAGE_KEY));
    } catch {
      return '';
    }
  }

  const apiUrl = readStoredUrl() || DEFAULT_API_URL;

  window.WOS_DEFAULT_API_URL = DEFAULT_API_URL;
  window.WOS_API_URL = apiUrl;
  window.WOS_API_STORAGE_KEY = STORAGE_KEY;
  window.WOS_APP_VERSION = VERSION;
  window.WOS_CONFIG = {
    apiUrl,
    defaultApiUrl: DEFAULT_API_URL,
    storageKey: STORAGE_KEY,
    version: VERSION,
  };
})();
