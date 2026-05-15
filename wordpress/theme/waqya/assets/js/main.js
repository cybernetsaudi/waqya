/**
 * Waqya theme — header interactions
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

  if (menuToggle && nav) {
    menuToggle.addEventListener('click', () => {
      const open = menuToggle.getAttribute('aria-expanded') === 'true';
      setExpanded(menuToggle, !open);
      nav.classList.toggle('is-open', !open);
      if (!open && searchToggle) {
        setExpanded(searchToggle, false);
        searchPanel?.setAttribute('hidden', '');
      }
    });
  }

  if (searchToggle && searchPanel) {
    searchToggle.addEventListener('click', () => {
      const open = searchToggle.getAttribute('aria-expanded') === 'true';
      setExpanded(searchToggle, !open);
      if (!open) {
        searchPanel.removeAttribute('hidden');
        searchInput?.focus();
        if (menuToggle) {
          setExpanded(menuToggle, false);
          nav?.classList.remove('is-open');
        }
      } else {
        searchPanel.setAttribute('hidden', '');
      }
    });
  }

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      if (menuToggle) {
        setExpanded(menuToggle, false);
        nav?.classList.remove('is-open');
      }
      if (searchToggle) {
        setExpanded(searchToggle, false);
        searchPanel?.setAttribute('hidden', '');
      }
    }
  });

  window.addEventListener('resize', () => {
    if (window.matchMedia('(min-width: 768px)').matches && nav) {
      nav.classList.remove('is-open');
      if (menuToggle) {
        setExpanded(menuToggle, false);
      }
    }
  });
})();
