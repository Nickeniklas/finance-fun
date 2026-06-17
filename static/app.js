const STORAGE_KEY = 'ff_watchlist_v1';
const MAX_FAVORITES = 10;

let favorites = [];
let selectedSymbol = null;
let chart = null;
let chartResizeObserver = null;

// ── Storage ──────────────────────────────────────────────────────────────────

function loadFavorites() {
  try {
    favorites = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
  } catch {
    favorites = [];
  }
}

function saveFavorites() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(favorites));
}

// apiGet lives in format.js (loaded before this script).

// ── Watchlist actions ─────────────────────────────────────────────────────────

function addTicker(raw) {
  const symbol = raw.trim().toUpperCase();
  if (!symbol || favorites.includes(symbol)) return;
  if (favorites.length >= MAX_FAVORITES) return;
  favorites.push(symbol);
  saveFavorites();
  renderWatchlist();
  if (!selectedSymbol) selectTicker(symbol);
  refreshPrice(symbol);
}

function removeTicker(symbol) {
  favorites = favorites.filter(s => s !== symbol);
  saveFavorites();
  const wasSelected = selectedSymbol === symbol;
  if (wasSelected) selectedSymbol = favorites[0] || null;
  renderWatchlist();
  if (wasSelected) {
    if (selectedSymbol) loadChart(selectedSymbol);
    else clearChart();
  }
}

function selectTicker(symbol) {
  if (selectedSymbol === symbol) return;
  selectedSymbol = symbol;
  renderWatchlist();
  loadChart(symbol);
}

// ── Render watchlist ──────────────────────────────────────────────────────────

function updateAddState() {
  const atLimit = favorites.length >= MAX_FAVORITES;
  document.getElementById('limit-hint').style.display = atLimit ? '' : 'none';
  document.getElementById('ticker-input').disabled = atLimit;
  document.getElementById('add-btn').disabled = atLimit;
}

function renderWatchlist() {
  const list = document.getElementById('ticker-list');
  const hint = document.getElementById('empty-hint');
  updateAddState();

  if (favorites.length === 0) {
    list.innerHTML = '';
    hint.style.display = '';
    return;
  }
  hint.style.display = 'none';

  // Preserve existing items so prices don't flash on re-render from selection change
  const existing = new Map();
  list.querySelectorAll('.ticker-item').forEach(el => {
    existing.set(el.dataset.symbol, el);
  });

  const fragment = document.createDocumentFragment();
  favorites.forEach(sym => {
    let li = existing.get(sym);
    if (!li) {
      li = buildTickerItem(sym);
    } else {
      // Just update active state
      li.classList.toggle('active', sym === selectedSymbol);
    }
    fragment.appendChild(li);
  });
  list.innerHTML = '';
  list.appendChild(fragment);
}

function buildTickerItem(sym) {
  const li = document.createElement('li');
  li.className = 'ticker-item' + (sym === selectedSymbol ? ' active' : '');
  li.dataset.symbol = sym;
  li.innerHTML = `
    <span class="ticker-sym">${sym}</span>
    <span class="ticker-info">
      <span class="ticker-price" id="tp-${sym}">—</span>
      <span class="ticker-pct" id="tpct-${sym}"></span>
    </span>
    <button class="remove-btn" title="Remove">×</button>
  `;
  li.querySelector('.ticker-sym').addEventListener('click', () => selectTicker(sym));
  li.querySelector('.ticker-info').addEventListener('click', () => selectTicker(sym));
  li.querySelector('.remove-btn').addEventListener('click', (e) => {
    e.stopPropagation();
    removeTicker(sym);
  });
  return li;
}

function updatePriceEl(symbol, quote) {
  const priceEl = document.getElementById(`tp-${symbol}`);
  const pctEl = document.getElementById(`tpct-${symbol}`);
  if (!priceEl || !pctEl) return;
  priceEl.textContent = formatPrice(quote.price, quote.currency);
  const sign = quote.changePercent >= 0 ? '+' : '';
  pctEl.textContent = `${sign}${quote.changePercent.toFixed(2)}%`;
  pctEl.className = `ticker-pct ${quote.changePercent >= 0 ? 'up' : 'down'}`;
}

async function refreshPrice(symbol) {
  try {
    const quote = await apiGet(`/quote/${symbol}`);
    updatePriceEl(symbol, quote);
  } catch {
    // silently ignore — price just stays as placeholder
  }
}

// ── Chart ─────────────────────────────────────────────────────────────────────

function clearChart() {
  const container = document.getElementById('chart-container');
  if (chart) { chart.remove(); chart = null; }
  if (chartResizeObserver) { chartResizeObserver.disconnect(); chartResizeObserver = null; }
  container.innerHTML = '';
  document.getElementById('chart-empty').style.display = '';
  document.getElementById('ticker-header').querySelectorAll('span').forEach(s => s.textContent = '');
}

async function loadChart(symbol) {
  document.getElementById('chart-empty').style.display = 'none';

  // Update header immediately with symbol so it doesn't feel frozen
  document.getElementById('header-sym').textContent = symbol;
  document.getElementById('header-name').textContent = '';
  document.getElementById('header-price').textContent = '…';
  document.getElementById('header-change').textContent = '';
  document.getElementById('header-change').className = 'header-change';

  const [quoteRes, candlesRes, profileRes] = await Promise.allSettled([
    apiGet(`/quote/${symbol}`),
    apiGet(`/candles/${symbol}?days=90`),
    apiGet(`/profile/${symbol}`),
  ]);

  // The user may have switched tickers while these were in flight; if so, a
  // stale response must not overwrite the now-selected ticker's chart/header.
  if (symbol !== selectedSymbol) return;

  if (profileRes.status === 'fulfilled') {
    document.getElementById('header-name').textContent = profileRes.value.name || '';
  } else {
    console.error(profileRes.reason);
  }

  if (quoteRes.status === 'fulfilled') {
    const quote = quoteRes.value;
    document.getElementById('header-price').textContent = formatPrice(quote.price, quote.currency);
    const sign = quote.changePercent >= 0 ? '+' : '';
    const changeEl = document.getElementById('header-change');
    changeEl.textContent = `${sign}${quote.changePercent.toFixed(2)}%`;
    changeEl.className = `header-change ${quote.changePercent >= 0 ? 'up' : 'down'}`;

    // Also update the watchlist price in case it wasn't loaded yet
    updatePriceEl(symbol, quote);
  } else {
    document.getElementById('header-price').textContent = '—';
    console.error(quoteRes.reason);
  }

  if (candlesRes.status === 'fulfilled') {
    drawChart(candlesRes.value.series || []);
  } else {
    drawChart([]);
    console.error(candlesRes.reason);
  }
}

function drawChart(series) {
  const container = document.getElementById('chart-container');

  // Tear down previous chart
  if (chart) { chart.remove(); chart = null; }
  if (chartResizeObserver) { chartResizeObserver.disconnect(); chartResizeObserver = null; }
  container.innerHTML = '';

  if (!series.length) {
    container.innerHTML = '<p class="hint center">No candle data available.</p>';
    return;
  }

  chart = LightweightCharts.createChart(container, {
    width: container.clientWidth,
    height: container.clientHeight || 400,
    layout: {
      background: { color: '#0f1117' },
      textColor: '#d1d4dc',
    },
    grid: {
      vertLines: { color: '#1e2230' },
      horzLines: { color: '#1e2230' },
    },
    crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
    rightPriceScale: { borderColor: '#2a2e3d' },
    timeScale: { borderColor: '#2a2e3d', timeVisible: false },
    handleScroll: true,
    handleScale: true,
  });

  const lineSeries = chart.addLineSeries({
    color: '#2962ff',
    lineWidth: 2,
    priceLineVisible: false,
    lastValueVisible: true,
  });

  lineSeries.setData(series);
  chart.timeScale().fitContent();

  // Keep chart width in sync with container
  chartResizeObserver = new ResizeObserver(() => {
    if (chart) {
      chart.applyOptions({
        width: container.clientWidth,
        height: container.clientHeight || 400,
      });
    }
  });
  chartResizeObserver.observe(container);
}

// ── Init ──────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  loadFavorites();
  renderWatchlist();

  const input = document.getElementById('ticker-input');
  const addBtn = document.getElementById('add-btn');

  addBtn.addEventListener('click', () => {
    addTicker(input.value);
    input.value = '';
  });
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { addTicker(input.value); input.value = ''; }
  });

  if (favorites.length > 0) {
    selectedSymbol = favorites[0];
    renderWatchlist();
    loadChart(selectedSymbol);
    favorites.forEach(sym => refreshPrice(sym));
  } else {
    document.getElementById('chart-empty').style.display = '';
  }
});
