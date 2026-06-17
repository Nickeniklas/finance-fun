// Shared formatting + escaping helpers (used by app.js, compare.js, news.js, prompts.js).

// Fetch JSON from an API path, throwing on a non-2xx response.
async function apiGet(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${res.status} ${path}`);
  return res.json();
}

// Escape text before it goes into an innerHTML template string. Provider-sourced
// strings (news headlines, company names, ...) are untrusted and can contain HTML.
function escapeHtml(value) {
  if (value == null) return '';
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// Only allow http(s) URLs as link targets; reject javascript:/data: and anything
// else by returning '#'. Also HTML-escapes for safe use inside an href attribute.
function safeUrl(value) {
  const url = String(value || '').trim();
  return /^https?:\/\//i.test(url) ? escapeHtml(url) : '#';
}

const CURRENCY_SYMBOLS = { USD: '$', EUR: '€', GBP: '£' };

function currencySymbol(currency) {
  return CURRENCY_SYMBOLS[currency] || (currency ? `${currency} ` : '$');
}

function formatPrice(value, currency) {
  return `${currencySymbol(currency)}${value.toFixed(2)}`;
}
