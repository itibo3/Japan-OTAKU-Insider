/**
 * menu.js - ハンバーガーメニュー開閉制御
 * Japan OTAKU Insider
 */
(function () {
    function initMenu() {
        var btn = document.getElementById('hamburgerBtn');
        var menu = document.getElementById('mobileMenu');
        var overlay = document.getElementById('mobileMenuOverlay');
        var closeBtn = document.getElementById('mobileMenuClose');

        if (!btn || !menu || !overlay) return;

        function openMenu() {
            menu.classList.add('open');
            overlay.classList.add('open');
            document.body.style.overflow = 'hidden';
            btn.setAttribute('aria-expanded', 'true');
        }

        function closeMenu() {
            menu.classList.remove('open');
            overlay.classList.remove('open');
            document.body.style.overflow = '';
            btn.setAttribute('aria-expanded', 'false');
        }

        btn.addEventListener('click', openMenu);
        overlay.addEventListener('click', closeMenu);
        if (closeBtn) closeBtn.addEventListener('click', closeMenu);

        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') closeMenu();
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initMenu);
    } else {
        initMenu();
    }
})();
