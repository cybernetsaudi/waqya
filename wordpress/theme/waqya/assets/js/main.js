/**
 * Waqya theme — header interactions + mobile section menu
 */
(function () {
  'use strict';

  const menuToggle = document.querySelector('[data-menu-toggle]');
  const searchToggle = document.querySelector('[data-search-toggle]');
  const nav = document.getElementById('site-nav');
  const searchPanel = document.getElementById('site-search');
  const searchInput = searchPanel?.querySelector('.search-form__input');

  function setExpanded(button, expanded) {
    if (!button) return;
    button.setAttribute('aria-expanded', expanded ? 'true' : 'false');
    document.body.classList.toggle('nav-open', expanded && button === menuToggle);
    document.body.classList.toggle('search-open', expanded && button === searchToggle);
  }

  function closeMenu() {
    if (!menuToggle || !nav) return;
    setExpanded(menuToggle, false);
    nav.classList.remove('is-open');
  }

  function closeSearch() {
    if (!searchToggle || !searchPanel) return;
    setExpanded(searchToggle, false);
    searchPanel.setAttribute('hidden', '');
  }

  if (menuToggle && nav) {
    menuToggle.addEventListener('click', (event) => {
      event.preventDefault();
      const open = menuToggle.getAttribute('aria-expanded') === 'true';
      const next = !open;
      setExpanded(menuToggle, next);
      nav.classList.toggle('is-open', next);
      if (next) {
        closeSearch();
      }
    });
  }

  if (searchToggle && searchPanel) {
    searchToggle.addEventListener('click', (event) => {
      event.preventDefault();
      const open = searchToggle.getAttribute('aria-expanded') === 'true';
      const next = !open;
      setExpanded(searchToggle, next);
      if (next) {
        searchPanel.removeAttribute('hidden');
        searchInput?.focus();
        closeMenu();
      } else {
        searchPanel.setAttribute('hidden', '');
      }
    });
  }

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeMenu();
      closeSearch();
    }
  });

  window.addEventListener('resize', () => {
    if (window.matchMedia('(min-width: 768px)').matches) {
      closeMenu();
    }
  });

  nav?.addEventListener('click', (event) => {
    const link = event.target.closest('a');
    if (link && nav.classList.contains('is-open')) {
      closeMenu();
    }
  });
})();
