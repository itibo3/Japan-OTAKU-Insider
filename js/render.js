function getCategories(entry) {
    if (Array.isArray(entry && entry.categories)) return entry.categories.filter(Boolean);
    if (entry && entry.category) return [entry.category];
    return [];
}

function categoryLabel(cat) {
    return { cafe: 'Collab Cafe', figure: 'Figure', event: 'Event', anime: 'Anime News', vtuber: 'VTuber', game: 'Game News', 'otaku-news': 'OTAKU NEWS' }[cat] || cat;
}

function renderCategoryPills(entry) {
    const cats = getCategories(entry).slice(0, 3);
    if (cats.length === 0) return '';
    const pills = cats
        .map((c) => {
            const cls = `cat-${c}`;
            const label = categoryLabel(c);
            return `<span class="card-category ${cls}">${label}</span>`;
        })
        .join('');
    return `<div class="card-categories">${pills}</div>`;
}

function sortByNewestFirst(entries) {
    const idDateRe = /^\w+-(\d{8})-/;
    return [...entries].sort((a, b) => {
        const da = (idDateRe.exec(a.id) || [null, '00000000'])[1];
        const db = (idDateRe.exec(b.id) || [null, '00000000'])[1];
        if (da !== db) return db.localeCompare(da);
        return (b.id || '').localeCompare(a.id || '');
    });
}

const CARDS_PER_PAGE = 24;
let currentFiltered = [];
let currentShown = 0;

function renderCardHtml(item) {
    const categoryPills = renderCategoryPills(item);
    const statusClass = `status-${item.status}`;
    const statusLabel = { active: 'Active', upcoming: 'Upcoming', ended: 'Ended' }[item.status] || item.status;

    const datesDisplay = item.dates && item.dates.display ? item.dates.display : item.dates;
    const thumbHtml = item.thumbnail
        ? `<img class="card-thumb" src="${item.thumbnail}" alt="${item.title}" loading="lazy">`
        : '';

    return `
      <div class="card" onclick="openModal('${item.id}')">
        ${thumbHtml}
        <div class="card-toolbar">
          <span class="card-status ${statusClass}">${statusLabel}</span>
          ${categoryPills}
        </div>
        <div class="card-title">${item.title}</div>
        <div class="card-meta">
          ${datesDisplay ? `<div class="meta-row"><span class="meta-label">Dates</span><span class="meta-value">${datesDisplay}</span></div>` : ''}
          ${item.price ? `<div class="meta-row"><span class="meta-label">Price</span><span class="meta-value">${item.price}</span></div>` : ''}
          ${item.location && typeof item.location === 'object' ? `<div class="meta-row"><span class="meta-label">Location</span><span class="meta-value">${item.location.name || item.location.area || item.location}</span></div>` : (item.location ? `<div class="meta-row"><span class="meta-label">Location</span><span class="meta-value">${item.location}</span></div>` : '')}
          ${item.manufacturer ? `<div class="meta-row"><span class="meta-label">Maker</span><span class="meta-value">${item.manufacturer}</span></div>` : ''}
        </div>
      </div>`;
}

function updateLoadMoreButton() {
    let btn = document.getElementById('loadMoreBtn');
    const remaining = currentFiltered.length - currentShown;
    if (remaining <= 0) {
        if (btn) btn.remove();
        return;
    }
    if (!btn) {
        btn = document.createElement('button');
        btn.id = 'loadMoreBtn';
        btn.className = 'load-more-btn';
        btn.addEventListener('click', loadMoreCards);
        const grid = document.getElementById('cardsGrid');
        grid.parentNode.insertBefore(btn, grid.nextSibling);
    }
    const next = Math.min(remaining, CARDS_PER_PAGE);
    btn.textContent = `Load More (${remaining} remaining)`;
}

function loadMoreCards() {
    const grid = document.getElementById('cardsGrid');
    if (!grid) return;
    const next = currentFiltered.slice(currentShown, currentShown + CARDS_PER_PAGE);
    grid.insertAdjacentHTML('beforeend', next.map(renderCardHtml).join(''));
    currentShown += next.length;
    updateLoadMoreButton();
}

function renderCards(filter = 'all', search = '') {
    const grid = document.getElementById('cardsGrid');
    if (!grid) return;
    let filtered = dbEntries;

    if (filter !== 'all') {
        filtered = filtered.filter(item => getCategories(item).includes(filter));
    }

    if (search) {
        const s = search.toLowerCase();
        filtered = filtered.filter(item =>
            item.title.toLowerCase().includes(s) ||
            (item.description && item.description.toLowerCase().includes(s)) ||
            (item.series && item.series.toLowerCase().includes(s))
        );
    }

    filtered = sortByNewestFirst(filtered);
    currentFiltered = filtered;

    if (filtered.length === 0) {
        grid.innerHTML = '<div class="empty-state">No results found. Try a different search or category.</div>';
        const oldBtn = document.getElementById('loadMoreBtn');
        if (oldBtn) oldBtn.remove();
        return;
    }

    const initial = filtered.slice(0, CARDS_PER_PAGE);
    grid.innerHTML = initial.map(renderCardHtml).join('');
    currentShown = initial.length;
    updateLoadMoreButton();
}

function openModal(id) {
    const item = dbEntries.find(i => String(i.id) === String(id));
    if (!item) return;

    const modalCategoriesHtml = (() => {
        const cats = getCategories(item).slice(0, 3);
        if (cats.length === 0) return '';
        const pills = cats
            .map((c) => `<span class="modal-category cat-${c}">${categoryLabel(c)}</span>`)
            .join('');
        return `<div class="modal-categories">${pills}</div>`;
    })();

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

    let journeyHtml = '';
    if (item.series_id) {
        const related = dbEntries.filter(e => e.series_id === item.series_id && e.id !== item.id);
        if (related.length > 0) {
            const relatedItems = related.map(e => {
                const cats = getCategories(e).map(c => categoryLabel(c)).join(', ');
                return `<li class="journey-item" onclick="openModal('${e.id}')">
                    <span class="journey-title">${e.title}</span>
                    ${cats ? `<span class="journey-cats">${cats}</span>` : ''}
                </li>`;
            }).join('');
            journeyHtml = `<div class="modal-section journey-section">
                <div class="modal-section-title">Series: ${item.series || item.series_id}</div>
                <ul class="journey-list">${relatedItems}</ul>
            </div>`;
        }
    }

    document.getElementById('modal').innerHTML = `
    <button class="modal-close" onclick="closeModal()">&times;</button>
    ${modalCategoriesHtml}
    <div class="modal-title">${item.title}</div>
    ${item.thumbnail ? `<img class="modal-thumb" src="${item.thumbnail}" alt="${item.title}" loading="lazy">` : ''}
    ${sections}
    ${journeyHtml}
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

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeModal();
    });
});
