let dbEntries = [];
let dbMeta = {};

async function loadDatabase() {
  try {
    const response = await fetch('./data/entries.json');
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
    const categories = new Set(dbEntries.map(e => e.category)).size;
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

document.addEventListener('DOMContentLoaded', async () => {
  dbEntries = await loadDatabase();
  
  if (document.getElementById('cardsGrid')) {
      updateStats();
      renderCards('all', '');
      setupFilters();
      setupSearch();
  }
});
