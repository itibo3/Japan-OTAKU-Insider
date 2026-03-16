function renderCards(filter = 'all', search = '') {
    const grid = document.getElementById('cardsGrid');
    if (!grid) return;
    let filtered = dbEntries;

    if (filter !== 'all') {
        filtered = filtered.filter(item => item.category === filter);
    }

    if (search) {
        const s = search.toLowerCase();
        filtered = filtered.filter(item =>
            item.title.toLowerCase().includes(s) ||
            (item.description && item.description.toLowerCase().includes(s)) ||
            (item.series && item.series.toLowerCase().includes(s))
        );
    }

    grid.innerHTML = filtered.map(item => {
        const catClass = `cat-${item.category}`;
        const catLabel = { cafe: 'Collab Cafe', figure: 'Figure', event: 'Event', anime: 'Anime News' }[item.category];
        const statusClass = `status-${item.status}`;
        const statusLabel = { active: 'Active', upcoming: 'Upcoming', ended: 'Ended' }[item.status] || item.status;

        const datesDisplay = item.dates && item.dates.display ? item.dates.display : item.dates;

        return `
      <div class="card" onclick="openModal('${item.id}')">
        <span class="card-status ${statusClass}">${statusLabel}</span>
        <div class="card-category ${catClass}">${catLabel}</div>
        <div class="card-title">${item.title}</div>
        <div class="card-meta">
          ${datesDisplay ? `<div class="meta-row"><span class="meta-label">Dates</span><span class="meta-value">${datesDisplay}</span></div>` : ''}
          ${item.price ? `<div class="meta-row"><span class="meta-label">Price</span><span class="meta-value">${item.price}</span></div>` : ''}
          ${item.location && typeof item.location === 'object' ? `<div class="meta-row"><span class="meta-label">Location</span><span class="meta-value">${item.location.name || item.location.area || item.location}</span></div>` : (item.location ? `<div class="meta-row"><span class="meta-label">Location</span><span class="meta-value">${item.location}</span></div>` : '')}
          ${item.manufacturer ? `<div class="meta-row"><span class="meta-label">Maker</span><span class="meta-value">${item.manufacturer}</span></div>` : ''}
        </div>
      </div>
    `;
    }).join('');
}

function openModal(id) {
    const item = dbEntries.find(i => String(i.id) === String(id));
    if (!item) return;

    const catClass = `cat-${item.category}`;
    const catLabel = { cafe: 'Collab Cafe', figure: 'Figure', event: 'Event', anime: 'Anime News' }[item.category];

    let sections = '';
    const datesDisplay = item.dates && item.dates.display ? item.dates.display : item.dates;
    const locationDisplay = item.location && typeof item.location === 'object' ? (item.location.name || item.location.area) : item.location;
    const accessDisplay = item.location && typeof item.location === 'object' ? item.location.access : item.access;
    const sourceUrl = item.source && typeof item.source === 'object' ? item.source.url : item.source;

    if (item.description) sections += `<div class="modal-section"><div class="modal-section-title">Overview</div><div class="modal-section-content">${item.description}</div></div>`;
    if (datesDisplay) sections += `<div class="modal-section"><div class="modal-section-title">Dates</div><div class="modal-section-content">${datesDisplay}</div></div>`;
    if (locationDisplay) sections += `<div class="modal-section"><div class="modal-section-title">Location</div><div class="modal-section-content">${locationDisplay}</div></div>`;
    if (accessDisplay) sections += `<div class="modal-section"><div class="modal-section-title">Access</div><div class="modal-section-content">${accessDisplay}</div></div>`;
    if (item.reservation) sections += `<div class="modal-section"><div class="modal-section-title">Reservation</div><div class="modal-section-content">${item.reservation}</div></div>`;
    if (item.price) sections += `<div class="modal-section"><div class="modal-section-title">Price</div><div class="modal-section-content">${item.price}</div></div>`;
    if (item.series) sections += `<div class="modal-section"><div class="modal-section-title">Series</div><div class="modal-section-content">${item.series}</div></div>`;
    if (item.manufacturer) sections += `<div class="modal-section"><div class="modal-section-title">Manufacturer</div><div class="modal-section-content">${item.manufacturer}</div></div>`;
    if (item.releaseDate) sections += `<div class="modal-section"><div class="modal-section-title">Release</div><div class="modal-section-content">${item.releaseDate}</div></div>`;
    if (item.whereToBuy) sections += `<div class="modal-section"><div class="modal-section-title">Where to Buy</div><div class="modal-section-content">${item.whereToBuy}</div></div>`;

    document.getElementById('modal').innerHTML = `
    <button class="modal-close" onclick="closeModal()">&times;</button>
    <div class="modal-category ${catClass}">${catLabel}</div>
    <div class="modal-title">${item.title}</div>
    ${sections}
    ${sourceUrl ? `<a href="${sourceUrl}" target="_blank" class="modal-link">View Source &rarr;</a>` : ''}
  `;

    document.getElementById('modalOverlay').classList.add('show');
}

function closeModal() {
    document.getElementById('modalOverlay').classList.remove('show');
}

document.addEventListener('DOMContentLoaded', () => {
    const overlay = document.getElementById('modalOverlay');
    if (overlay) {
        overlay.addEventListener('click', (e) => {
            if (e.target === e.currentTarget) closeModal();
        });
    }
});
