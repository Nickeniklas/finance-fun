// Shared currency formatting helpers (used by app.js and compare.js).

const CURRENCY_SYMBOLS = { USD: '$', EUR: '€', GBP: '£' };

function currencySymbol(currency) {
  return CURRENCY_SYMBOLS[currency] || (currency ? `${currency} ` : '$');
}

function formatPrice(value, currency) {
  return `${currencySymbol(currency)}${value.toFixed(2)}`;
}
