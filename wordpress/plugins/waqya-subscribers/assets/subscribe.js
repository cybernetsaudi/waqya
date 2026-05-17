(function () {
  'use strict';

  const cfg = window.waqyaSubscribe;
  if (!cfg) return;

  const STORAGE_KEY = 'waqya_digest_prompt_v1';
  const DISMISS_DAYS = 30;

  const modal = document.getElementById('waqya-subscribe-modal');
  const form = modal?.querySelector('[data-waqya-subscribe-form]');
  const emailInput = modal?.querySelector('#waqya-subscribe-email');
  const messageEl = modal?.querySelector('[data-waqya-form-message]');
  const sectionNote = modal?.querySelector('[data-waqya-section-note]');
  const categoryInput = modal?.querySelector('[data-waqya-category-input]');

  let activeCategoryId = '';
  let activeCategoryName = '';

  function shouldShowAutoPrompt() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return true;
      const data = JSON.parse(raw);
      if (data.subscribed) return false;
      if (data.dismissedAt && Date.now() - data.dismissedAt < DISMISS_DAYS * 86400000) {
        return false;
      }
    } catch (e) {
      return true;
    }
    return true;
  }

  function markDismissed() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ dismissedAt: Date.now() }));
    } catch (e) {
      /* ignore */
    }
  }

  function markSubscribedPending() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ subscribed: true, at: Date.now() }));
    } catch (e) {
      /* ignore */
    }
  }

  function openModal(opts) {
    if (!modal) return;
    activeCategoryId = opts?.categoryId ? String(opts.categoryId) : '';
    activeCategoryName = opts?.categoryName || '';

    if (categoryInput) {
      categoryInput.value = activeCategoryId;
    }

    if (sectionNote) {
      if (activeCategoryName) {
        sectionNote.hidden = false;
        sectionNote.textContent =
          (cfg.i18n.followSection || 'Include stories from this section') +
          ': ' +
          activeCategoryName;
      } else {
        sectionNote.hidden = true;
        sectionNote.textContent = '';
      }
    }

    if (messageEl) messageEl.textContent = '';
    modal.removeAttribute('hidden');
    document.body.classList.add('waqya-modal-open');
    emailInput?.focus();
  }

  function closeModal() {
    if (!modal) return;
    modal.setAttribute('hidden', '');
    document.body.classList.remove('waqya-modal-open');
    markDismissed();
  }

  document.querySelectorAll('[data-waqya-modal-close]').forEach((el) => {
    el.addEventListener('click', closeModal);
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && modal && !modal.hasAttribute('hidden')) {
      closeModal();
    }
  });

  document.querySelectorAll('[data-waqya-follow]').forEach((btn) => {
    btn.addEventListener('click', () => {
      openModal({
        categoryId: btn.getAttribute('data-category-id'),
        categoryName: btn.getAttribute('data-category-name'),
      });
    });
  });

  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (!messageEl) return;

      const email = emailInput?.value?.trim() || '';
      const consent = form.querySelector('[name="consent_digest"]')?.checked;
      const categoryIds = activeCategoryId ? [parseInt(activeCategoryId, 10)] : [];

      messageEl.textContent = '';

      try {
        const res = await fetch(cfg.restUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-WP-Nonce': cfg.nonce,
          },
          body: JSON.stringify({
            email,
            consent_digest: consent,
            category_ids: categoryIds,
            website: form.querySelector('[name="website"]')?.value || '',
          }),
        });
        const data = await res.json();
        if (data.ok) {
          messageEl.textContent = data.message || cfg.i18n.success;
          markSubscribedPending();
          form.reset();
          if (categoryInput) categoryInput.value = activeCategoryId;
        } else {
          messageEl.textContent = data.message || cfg.i18n.error;
        }
      } catch (err) {
        messageEl.textContent = cfg.i18n.error;
      }
    });
  }

  if (cfg.showAutoPrompt !== false && shouldShowAutoPrompt()) {
    window.setTimeout(() => openModal({}), 2500);
  }
})();
