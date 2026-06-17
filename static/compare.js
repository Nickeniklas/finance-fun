// ── API helper ────────────────────────────────────────────────────────────────

async function apiGet(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${res.status} ${path}`);
  return res.json();
}

// ── Formatting ────────────────────────────────────────────────────────────────

function fmt(val, type, currency) {
  if (val == null || (typeof val === 'number' && isNaN(val))) return '—';
  if (type === 'pct') return `${val.toFixed(1)}%`;
  if (type === 'x') return `${val.toFixed(1)}x`;
  if (type === 'mcap') {
    // marketCap is raw units in the instrument's native currency
    const symbol = currencySymbol(currency);
    if (val >= 1e12) return `${symbol}${(val / 1e12).toFixed(2)}T`;
    if (val >= 1e9) return `${symbol}${(val / 1e9).toFixed(1)}B`;
    if (val >= 1e6) return `${symbol}${(val / 1e6).toFixed(0)}M`;
    return `${symbol}${val.toFixed(0)}`;
  }
  return val.toFixed(2);
}

// ── Comparison framework — section label, row label, fundamentals key, format type
const FRAMEWORK = [
  { section: 'Valuation', rows: [
    ['P/E Ratio', 'peRatio', 'x'],
    ['P/B Ratio', 'pbRatio', 'x'],
    ['EV / EBITDA', 'evEbitda', 'x'],
  ]},
  { section: 'Growth', rows: [
    ['Revenue Growth (YoY)', 'revenueGrowthYoy', 'pct'],
    ['EPS Growth (YoY)', 'epsGrowthYoy', 'pct'],
  ]},
  { section: 'Profitability', rows: [
    ['Gross Margin', 'grossMargin', 'pct'],
    ['Net Margin', 'netMargin', 'pct'],
    ['Return on Equity', 'roe', 'pct'],
  ]},
  { section: 'Financial Health', rows: [
    ['Current Ratio', 'currentRatio', 'number'],
    ['Debt / Equity', 'debtToEquity', 'number'],
  ]},
];

// ── Fetch + render ────────────────────────────────────────────────────────────

async function fetchTicker(symbol) {
  const [profile, fundamentals] = await Promise.all([
    apiGet(`/profile/${symbol}`),
    apiGet(`/fundamentals/${symbol}`),
  ]);
  return { symbol, profile, fundamentals };
}

async function runCompare(symA, symB) {
  const result = document.getElementById('compare-result');
  result.innerHTML = '<p class="status-msg">Loading…</p>';

  let a, b;
  try {
    [a, b] = await Promise.all([fetchTicker(symA), fetchTicker(symB)]);
  } catch (err) {
    result.innerHTML = `<p class="status-msg">Couldn't load comparison — check both symbols and try again.</p>`;
    console.error(err);
    return;
  }

  result.innerHTML = `
    <div class="company-info-row">
      ${companyCard(a)}
      ${companyCard(b)}
    </div>
    <div class="compare-table-wrap">
      <table class="compare-table">
        <thead>
          <tr><th></th><th>${escapeHtml(a.symbol)}</th><th>${escapeHtml(b.symbol)}</th></tr>
        </thead>
        <tbody>${renderRows(a, b)}</tbody>
      </table>
    </div>
  `;
}

function companyCard(d) {
  const mcap = d.profile.marketCap != null ? fmt(d.profile.marketCap, 'mcap', d.profile.currency) : '—';
  return `
    <div class="company-card">
      <div class="sym">${escapeHtml(d.symbol)}</div>
      <div class="name">${escapeHtml(d.profile.name || '—')}</div>
      <div class="meta">${escapeHtml(d.profile.sector || '—')} · Market Cap: ${mcap}</div>
    </div>
  `;
}

function renderRows(a, b) {
  let html = '';
  for (const group of FRAMEWORK) {
    html += `<tr class="section-header"><td colspan="3">${group.section}</td></tr>`;
    for (const [label, key, type] of group.rows) {
      html += `<tr><td>${label}</td><td>${fmt(a.fundamentals[key], type)}</td><td>${fmt(b.fundamentals[key], type)}</td></tr>`;
    }
  }
  return html;
}

// ── Init ──────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  const symA = document.getElementById('sym-a');
  const symB = document.getElementById('sym-b');
  const btn = document.getElementById('compare-btn');

  function go() {
    const a = symA.value.trim().toUpperCase();
    const b = symB.value.trim().toUpperCase();
    if (!a || !b) return;
    runCompare(a, b);
  }

  btn.addEventListener('click', go);
  [symA, symB].forEach(input => {
    input.addEventListener('keydown', e => { if (e.key === 'Enter') go(); });
  });

  // Pre-fill from ?a=SYM&b=SYM for shareable comparisons
  const params = new URLSearchParams(location.search);
  const pa = params.get('a');
  const pb = params.get('b');
  if (pa) symA.value = pa.toUpperCase();
  if (pb) symB.value = pb.toUpperCase();
  if (pa && pb) go();
});
