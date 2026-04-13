function sanitizeMd(str) {
    if (!str) return str;
    return str.replace(/\*\*/g, '');
}

function buildAmazonSearchUrl(title, lang) {
    const raw = String(title || '').replace(/\[[^\]]*\]/g, ' ').replace(/[【】]/g, ' ').trim();
    if (!raw) return '';
    const params = new URLSearchParams();
    params.set('k', raw);
    params.set('language', lang === 'ja' ? 'ja_JP' : 'en_US');
    const tag = (window.AMAZON_ASSOCIATE_TAG || '').trim();
    if (tag) params.set('tag', tag);
    return `https://www.amazon.co.jp/s?${params.toString()}`;
}

function getCategories(entry) {
    if (Array.isArray(entry && entry.categories)) return entry.categories.filter(Boolean);
    if (entry && entry.category) return [entry.category];
    return [];
}

function categoryLabel(cat) {
    return { cafe: 'Collab Cafe', figure: 'Figure', event: 'Event', anime: 'Anime News', vtuber: 'VTuber', game: 'Game News', 'otaku-news': 'OTAKU NEWS', other: 'Other topics' }[cat] || cat;
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

const idDateRe = /^\w+-(\d{8,12})-/;

function idDateFromId(id) {
    const m = idDateRe.exec(id || '');
    return (m ? m[1] : '00000000').padEnd(12, '0');
}

function parseDateForSort(entry) {
    const datesVal = entry && entry.dates;
    let display = '';
    if (datesVal && typeof datesVal === 'object') display = datesVal.display || '';
    else if (typeof datesVal === 'string') display = datesVal;
    if (!display) return null;

    const isoDateRe = /(\d{4})-(\d{2})-(\d{2})/g;
    let match;
    let last = null;
    while ((match = isoDateRe.exec(display)) !== null) last = match;
    if (last) return last[1] + last[2] + last[3];

    const isoMonthRe = /^(\d{4})-(\d{2})(?:\s|$|-)/;
    const monthMatch = display.trim().match(isoMonthRe);
    if (monthMatch) {
        const y = parseInt(monthMatch[1], 10);
        const m = parseInt(monthMatch[2], 10);
        if (m >= 1 && m <= 12) {
            const lastDay = new Date(y, m, 0).getDate();
            return y + String(m).padStart(2, '0') + String(lastDay).padStart(2, '0');
        }
    }

    const d = new Date(display.trim());
    if (!isNaN(d.getTime())) {
        const iso = d.toISOString().slice(0, 10);
        return iso.replace(/-/g, '');
    }
    return null;
}

function sortByNewestFirst(entries) {
    return [...entries].sort((a, b) => {
        const pa = a && a.pinned_top ? 1 : 0;
        const pb = b && b.pinned_top ? 1 : 0;
        if (pa !== pb) return pb - pa;
        const da = idDateFromId(a.id);
        const db = idDateFromId(b.id);
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

    const datesRaw = item.dates;
    const datesDisplay = datesRaw && typeof datesRaw === 'object'
        ? (datesRaw.display || null)
        : (datesRaw || null);
    const thumbHtml = item.thumbnail
        ? `<img class="card-thumb" src="${item.thumbnail}" alt="${item.title}" loading="lazy" referrerpolicy="no-referrer">`
        : '<div class="card-thumb-placeholder"><span>📰</span></div>';
    const isWeekly = item && (item._source === 'joi-weekly' || item._source_id === 'joi-weekly');
    const weeklyHint = isWeekly ? '<div class="card-weekly-hint">Weekly Feature</div>' : '';

    return `
      <div class="card" onclick="openModal('${item.id}')">
        ${thumbHtml}
        <div class="card-toolbar">
          <span class="card-status ${statusClass}">${statusLabel}</span>
          ${categoryPills}
        </div>
        ${weeklyHint}
        <div class="card-title">${sanitizeMd(item.title)}</div>
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
    const datesRaw2 = item.dates;
    const datesDisplay = datesRaw2 && typeof datesRaw2 === 'object'
        ? (datesRaw2.display || null)
        : (datesRaw2 || null);
    const locationDisplay = item.location && typeof item.location === 'object' ? (item.location.name || item.location.area) : item.location;
    const accessDisplay = item.location && typeof item.location === 'object' ? item.location.access : item.access;
    const sourceUrl = item.source && typeof item.source === 'object' ? item.source.url : item.source;
    const isWeekly = item && (item._source === 'joi-weekly' || item._source_id === 'joi-weekly');
    const weeklyArticleUrl = `/weekly.html?id=${encodeURIComponent(item.id)}`;
    const uiLang = (localStorage.getItem('otaku_lang') || 'en');
    const amazonUrl = !isWeekly ? buildAmazonSearchUrl(item.title || item.title_ja || '', uiLang) : '';
    const affiliateText = uiLang === 'ja' ? 'Amazonで関連商品を見る' : 'Find related items on Amazon';

    if (isWeekly) {
        const weeklySummary = uiLang === 'ja'
            ? (item.summary_ja || item.summary_en || sanitizeMd((item.description || '').split('\n\n')[0] || ''))
            : (item.summary_en || item.summary_ja || sanitizeMd((item.description || '').split('\n\n')[0] || ''));
        if (weeklySummary) {
            sections += `<div class="modal-section"><div class="modal-section-title">Overview</div><div class="modal-section-content">${sanitizeMd(weeklySummary)}</div></div>`;
        }
        sections += '<div class="modal-section"><div class="modal-section-title">Read</div><div class="modal-section-content">This weekly issue is published as a full article page.</div></div>';
    } else if (item.description) {
        sections += `<div class="modal-section"><div class="modal-section-title">Overview</div><div class="modal-section-content">${sanitizeMd(item.description)}</div></div>`;
    }
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
    <div class="modal-title">${sanitizeMd(item.title)}</div>
    ${item.thumbnail ? `<img class="modal-thumb" src="${item.thumbnail}" alt="${item.title}" loading="lazy" referrerpolicy="no-referrer">` : ''}
    ${sections}
    ${journeyHtml}
    ${isWeekly ? `<a href="${weeklyArticleUrl}" class="modal-link">Read Weekly Article &rarr;</a>` : (sourceUrl ? `<a href="${sourceUrl}" target="_blank" class="modal-link">View Source &rarr;</a>` : '')}
    ${amazonUrl ? `<a href="${amazonUrl}" target="_blank" rel="noopener noreferrer sponsored nofollow" class="modal-affiliate-link">${affiliateText}</a>` : ''}
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
