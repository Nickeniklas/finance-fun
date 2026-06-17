const STORAGE_KEY = 'ff_watchlist_v1';

// ── API + storage helpers ─────────────────────────────────────────────────────

async function apiGet(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${res.status} ${path}`);
  return res.json();
}

function loadWatchlist() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
  } catch {
    return [];
  }
}

function formatDate(unixSeconds) {
  return new Date(unixSeconds * 1000).toLocaleString(undefined, {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  });
}

// ── Render ────────────────────────────────────────────────────────────────────

function renderArticle(item) {
  return `
    <div class="article-card">
      <div class="article-meta">${escapeHtml(item.source || 'Unknown source')} · ${formatDate(item.datetime)}</div>
      <div class="article-headline"><a href="${safeUrl(item.url)}" target="_blank" rel="noopener">${escapeHtml(item.headline)}</a></div>
      ${item.summary ? `<div class="article-summary">${escapeHtml(item.summary)}</div>` : ''}
    </div>
  `;
}

async function fetchNews(symbol) {
  const result = document.getElementById('news-result');
  result.innerHTML = '<p class="status-msg">Loading…</p>';

  document.querySelectorAll('.chip').forEach(chip => {
    chip.classList.toggle('active', chip.dataset.sym === symbol);
  });

  try {
    const articles = await apiGet(`/news/${symbol}`);
    if (!articles.length) {
      result.innerHTML = `<p class="status-msg">No news found for ${symbol} in the last 7 days.</p>`;
      return;
    }
    const sorted = [...articles].sort((a, b) => b.datetime - a.datetime);
    result.innerHTML = `<div class="article-list">${sorted.map(renderArticle).join('')}</div>`;
  } catch (err) {
    result.innerHTML = `<p class="status-msg">Couldn't load news for ${symbol} — try again in a moment.</p>`;
    console.error(err);
  }
}

// ── Init ──────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  const input = document.getElementById('news-ticker');
  const btn = document.getElementById('news-btn');
  const chipsEl = document.getElementById('watchlist-chips');

  function go() {
    const symbol = input.value.trim().toUpperCase();
    if (!symbol) return;
    fetchNews(symbol);
  }

  btn.addEventListener('click', go);
  input.addEventListener('keydown', e => { if (e.key === 'Enter') go(); });

  const watchlist = loadWatchlist();
  if (watchlist.length) {
    chipsEl.innerHTML = watchlist.map(sym => `<span class="chip" data-sym="${sym}">${sym}</span>`).join('');
    chipsEl.querySelectorAll('.chip').forEach(chip => {
      chip.addEventListener('click', () => {
        input.value = chip.dataset.sym;
        fetchNews(chip.dataset.sym);
      });
    });
    input.value = watchlist[0];
    fetchNews(watchlist[0]);
  }
});
