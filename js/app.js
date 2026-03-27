let dbEntries = [];
let dbMeta = {};
let currentLang = localStorage.getItem('otaku_lang') || 'en'; // 'en' or 'ja'

function getCategories(entry) {
  if (Array.isArray(entry && entry.categories)) return entry.categories.filter(Boolean);
  if (entry && entry.category) return [entry.category];
  return [];
}

async function loadDatabase(lang) {
  const url = (lang === 'ja') ? '/data/entries_ja.json' : '/data/entries.json';
  try {
    const response = await fetch(url);
    const db = await response.json();
    dbMeta = {
      last_updated: db.last_updated,
      total_entries: db.total_entries
    };
    return db.entries || [];
  } catch (error) {
    console.error("Failed to load database:", error);
    return [];
  }
}

function updateStats() {
  const statsContainer = document.querySelector('.stats-bar');
  if (!statsContainer) return;

  const total = dbEntries.length;
  const categories = new Set(dbEntries.flatMap(getCategories)).size;
  const active = dbEntries.filter(e => e.status === 'active').length;

  let dateStr = "Unknown";
  if (dbMeta.last_updated) {
    const d = new Date(dbMeta.last_updated);
    dateStr = d.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
  }

  statsContainer.innerHTML = `
      <div class="stat-chip"><strong>${total}</strong> entries</div>
      <div class="stat-chip"><strong>${categories}</strong> categories</div>
      <div class="stat-chip"><strong>${active}</strong> active now</div>
      <div class="stat-chip">Updated: ${dateStr}</div>
    `;
}

// --- 言語トグルUI ---
function applyLangToggleUI(lang) {
  const toggle = document.getElementById('langToggle');
  const enOpt = document.getElementById('langEN');
  const jpOpt = document.getElementById('langJP');
  const badge = document.getElementById('langBadge');
  if (!toggle) return;
  if (lang === 'ja') {
    toggle.classList.add('jp');
    enOpt.classList.remove('active');
    jpOpt.classList.add('active');
    if (badge) { badge.textContent = '(JP)'; badge.classList.add('visible'); }
  } else {
    toggle.classList.remove('jp');
    enOpt.classList.add('active');
    jpOpt.classList.remove('active');
    if (badge) { badge.textContent = ''; badge.classList.remove('visible'); }
  }
}

async function switchLang(lang) {
  if (lang === currentLang) return;
  currentLang = lang;
  localStorage.setItem('otaku_lang', lang);
  applyLangToggleUI(lang);

  const grid = document.getElementById('cardsGrid');
  if (grid) {
    grid.innerHTML = '<div class="loading-spinner"><div class="spinner"></div><p>Loading...</p></div>';
  }
  dbEntries = await loadDatabase(lang);
  if (grid) {
    if (dbEntries.length === 0) {
      grid.innerHTML = '<div class="empty-state">Failed to load entries.</div>';
    } else {
      updateStats();
      renderCards('all', '');
      setupFilters();
      setupSearch();
    }
  }
}

document.addEventListener('DOMContentLoaded', async () => {
  const grid = document.getElementById('cardsGrid');
  if (grid) {
    grid.innerHTML = '<div class="loading-spinner"><div class="spinner"></div><p>Loading entries...</p></div>';
  }

  // トグル初期状態を適用
  applyLangToggleUI(currentLang);

  // トグルクリックイベント
  const toggle = document.getElementById('langToggle');
  if (toggle) {
    toggle.addEventListener('click', () => {
      switchLang(currentLang === 'en' ? 'ja' : 'en');
    });
  }

  dbEntries = await loadDatabase(currentLang);

  if (grid) {
    if (dbEntries.length === 0) {
      grid.innerHTML = '<div class="empty-state">Failed to load entries. Please try refreshing the page.</div>';
    } else {
      updateStats();
      renderCards('all', '');
      setupFilters();
      setupSearch();
    }
  }
});
