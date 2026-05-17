/**
 * Grouped section nav tabs (News Desk / Regions / Topics)
 */
(function () {
  'use strict';

  const nav = document.querySelector('.site-nav-groups');
  if (!nav) {
    return;
  }

  const tabs = Array.from(nav.querySelectorAll('[data-nav-tab]'));
  const panels = Array.from(nav.querySelectorAll('[data-nav-panel]'));

  function activate(groupId) {
    tabs.forEach((tab) => {
      const active = tab.getAttribute('data-nav-tab') === groupId;
      tab.classList.toggle('is-active', active);
      tab.setAttribute('aria-selected', active ? 'true' : 'false');
    });

    panels.forEach((panel) => {
      const active = panel.getAttribute('data-nav-panel') === groupId;
      panel.classList.toggle('is-active', active);
      if (active) {
        panel.removeAttribute('hidden');
      } else {
        panel.setAttribute('hidden', '');
      }
    });
  }

  tabs.forEach((tab) => {
    tab.addEventListener('click', () => {
      activate(tab.getAttribute('data-nav-tab') || '');
    });
  });
})();
