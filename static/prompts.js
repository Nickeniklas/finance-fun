// ── Render ────────────────────────────────────────────────────────────────────

function renderPrompt(prompt) {
  return `
    <div class="prompt-card" data-id="${prompt.id}">
      <div>
        <div class="prompt-title">${prompt.title}</div>
        <div class="prompt-description">${prompt.description}</div>
      </div>
      <button class="btn-primary prompt-copy-btn" data-id="${prompt.id}">Copy</button>
    </div>
  `;
}

function renderPrompts(prompts) {
  const result = document.getElementById('prompts-result');
  if (!prompts.length) {
    result.innerHTML = '<p class="status-msg">No prompts in this category yet.</p>';
    return;
  }
  result.innerHTML = `<div class="article-list">${prompts.map(renderPrompt).join('')}</div>`;

  result.querySelectorAll('.prompt-copy-btn').forEach(btn => {
    btn.addEventListener('click', () => copyPrompt(btn, prompts));
  });
}

async function copyPrompt(btn, prompts) {
  const prompt = prompts.find(p => p.id === btn.dataset.id);
  if (!prompt) return;

  try {
    await navigator.clipboard.writeText(prompt.text.join('\n'));
    const original = btn.textContent;
    btn.textContent = 'Copied!';
    btn.disabled = true;
    setTimeout(() => {
      btn.textContent = original;
      btn.disabled = false;
    }, 1500);
  } catch (err) {
    console.error(err);
  }
}

// ── Init ──────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', async () => {
  const result = document.getElementById('prompts-result');
  const chipsEl = document.getElementById('category-chips');

  let prompts;
  try {
    const res = await fetch('/prompts.json');
    if (!res.ok) throw new Error(`${res.status} /prompts.json`);
    prompts = await res.json();
  } catch (err) {
    result.innerHTML = '<p class="status-msg">Couldn\'t load the prompt library — try again in a moment.</p>';
    console.error(err);
    return;
  }

  const categories = ['all', ...new Set(prompts.map(p => p.category))];
  chipsEl.innerHTML = categories
    .map(cat => `<span class="chip${cat === 'all' ? ' active' : ''}" data-category="${cat}">${cat}</span>`)
    .join('');

  chipsEl.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => {
      chipsEl.querySelectorAll('.chip').forEach(c => c.classList.toggle('active', c === chip));
      const category = chip.dataset.category;
      renderPrompts(category === 'all' ? prompts : prompts.filter(p => p.category === category));
    });
  });

  renderPrompts(prompts);
});
