function setupFilters() {
    document.querySelectorAll('.cat-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.cat-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            const searchInput = document.getElementById('searchInput');
            renderCards(tab.dataset.cat, searchInput ? searchInput.value : '');
        });
    });
}

function setupSearch() {
    const searchInput = document.getElementById('searchInput');
    if (!searchInput) return;

    searchInput.addEventListener('input', (e) => {
        const activeTab = document.querySelector('.cat-tab.active');
        const activeCat = activeTab ? activeTab.dataset.cat : 'all';
        renderCards(activeCat, e.target.value);
    });
}
