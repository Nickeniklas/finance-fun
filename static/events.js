// ── Render helpers ────────────────────────────────────────────────────────────

function formatEventDate(dateStr) {
  // dateStr is YYYY-MM-DD (date-only) — parse as UTC to avoid local-timezone day shift.
  const d = new Date(`${dateStr}T00:00:00Z`);
  if (Number.isNaN(d.getTime())) return escapeHtml(dateStr);
  return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric', timeZone: 'UTC' });
}

function renderDigest(digest) {
  const changes = digest.whatChanged.map(line => `<li>${escapeHtml(line)}</li>`).join('');

  const themes = digest.themes.length
    ? `<div class="theme-list">${digest.themes.map(theme => `
        <div class="theme-card">
          <div class="theme-label">${escapeHtml(theme.label)} <span class="theme-streak">streak ${theme.streak}</span></div>
          <div class="theme-note">${escapeHtml(theme.note)}</div>
        </div>
      `).join('')}</div>`
    : '<p class="status-msg">No themes currently supported.</p>';

  return `
    <div class="digest-card">
      <div class="digest-date">Digest — ${formatEventDate(digest.date)}</div>
      <ul class="digest-changes">${changes}</ul>
      ${themes}
    </div>
  `;
}

function renderPhase(phase) {
  return `
    <li class="phase-item">
      <span class="phase-status status-${escapeHtml(phase.status)}">${escapeHtml(phase.status)}</span>
      <span class="phase-date">${formatEventDate(phase.date)}</span>
      <span class="phase-headline">${escapeHtml(phase.headline)}</span>
      <span class="phase-source">${escapeHtml(phase.source)}</span>
      ${phase.priceReaction ? `<span class="phase-reaction">${escapeHtml(phase.priceReaction)}</span>` : ''}
    </li>
  `;
}

function renderDeal(deal) {
  const phases = [...deal.phases].reverse().map(renderPhase).join('');
  return `
    <div class="deal-card">
      <div class="deal-header">
        <span class="deal-ticker">${escapeHtml(deal.ticker)}</span>
        ${deal.counterparty ? `<span class="deal-counterparty">↔ ${escapeHtml(deal.counterparty)}</span>` : ''}
        <span class="deal-type">${escapeHtml(deal.type)}</span>
        <span class="phase-status status-${escapeHtml(deal.currentStatus)} deal-current-status">${escapeHtml(deal.currentStatus)}</span>
      </div>
      <div class="deal-why">${escapeHtml(deal.whyItMatters)}</div>
      <ul class="phase-list">${phases}</ul>
    </div>
  `;
}

function renderEvents(events) {
  const result = document.getElementById('events-result');
  if (!events.length) {
    result.innerHTML = '<p class="status-msg">No tracked deals yet.</p>';
    return;
  }
  result.innerHTML = `<div class="deal-list">${events.map(renderDeal).join('')}</div>`;
}

// ── Init ──────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', async () => {
  const digestSection = document.getElementById('digest-section');
  const result = document.getElementById('events-result');

  try {
    const [eventsData, digest] = await Promise.all([
      apiGet('/events.json'),
      apiGet('/digest.json'),
    ]);
    digestSection.innerHTML = renderDigest(digest);
    renderEvents(eventsData.events);
  } catch (err) {
    result.innerHTML = '<p class="status-msg">Couldn\'t load events — try again in a moment.</p>';
    console.error(err);
  }
});
