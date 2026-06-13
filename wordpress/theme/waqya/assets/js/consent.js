/**
 * Waqya cookie consent — analytics gated until opt-in (GDPR / CCPA-ready).
 */
(function () {
  'use strict';

  var cfg = window.waqyaConsent || {};
  var KEY = cfg.storageKey || 'waqya_consent_v1';

  function read() {
    try {
      var raw = localStorage.getItem(KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  }

  function write(consent) {
    try {
      localStorage.setItem(
        KEY,
        JSON.stringify({
          necessary: true,
          analytics: !!consent.analytics,
          ts: Date.now(),
        })
      );
    } catch (e) {
      /* ignore */
    }
  }

  function gtagConsentUpdate(granted) {
    if (typeof window.gtag !== 'function') {
      return;
    }
    window.gtag('consent', 'update', {
      analytics_storage: granted ? 'granted' : 'denied',
      ad_storage: 'denied',
      ad_user_data: 'denied',
      ad_personalization: 'denied',
    });
  }

  function activateDeferredScripts() {
    var nodes = document.querySelectorAll('script[data-waqya-consent="analytics"]');
    nodes.forEach(function (node) {
      if (node.getAttribute('data-waqya-activated') === '1') {
        return;
      }
      var domain = node.getAttribute('data-plausible-domain');
      if (domain && node.id === 'waqya-plausible-deferred') {
        var s = document.createElement('script');
        s.defer = true;
        s.setAttribute('data-domain', domain);
        s.src = 'https://plausible.io/js/script.js';
        document.head.appendChild(s);
        node.setAttribute('data-waqya-activated', '1');
        return;
      }
      var src = node.getAttribute('data-src') || node.getAttribute('src');
      var inline = node.textContent && node.textContent.trim();
      if (!src && !inline) {
        return;
      }
      var el = document.createElement('script');
      if (src) {
        el.src = src;
      }
      if (node.id) {
        el.id = node.id;
      }
      if (node.async) {
        el.async = true;
      }
      if (node.defer) {
        el.defer = true;
      }
      var inline = node.textContent && node.textContent.trim();
      if (inline && !src) {
        el.textContent = inline;
      }
      node.parentNode.insertBefore(el, node.nextSibling);
      node.setAttribute('data-waqya-activated', '1');
    });

    /* Inline Site Kit gtag bootstrap stored as text/plain */
    document.querySelectorAll('script[data-waqya-consent="analytics"]').forEach(function (node) {
      var inline = node.textContent && node.textContent.trim();
      if (!inline || node.getAttribute('data-waqya-activated') === '1') {
        return;
      }
      if (node.getAttribute('data-src')) {
        return;
      }
      var el = document.createElement('script');
      el.textContent = inline;
      node.parentNode.insertBefore(el, node.nextSibling);
      node.setAttribute('data-waqya-activated', '1');
    });
  }

  function apply(consent, showBanner) {
    var banner = document.getElementById('waqya-consent');
    if (consent.analytics) {
      gtagConsentUpdate(true);
      activateDeferredScripts();
    } else {
      gtagConsentUpdate(false);
    }
    if (banner && !showBanner) {
      banner.setAttribute('hidden', '');
      banner.setAttribute('aria-hidden', 'true');
    }
  }

  function showBanner() {
    var banner = document.getElementById('waqya-consent');
    if (!banner) {
      return;
    }
    banner.removeAttribute('hidden');
    banner.setAttribute('aria-hidden', 'false');
  }

  function bind() {
    var banner = document.getElementById('waqya-consent');
    if (!banner) {
      return;
    }
    var prefs = document.getElementById('waqya-consent-prefs');
    var saveBtn = banner.querySelector('[data-waqya-consent="save"]');
    var manageBtn = banner.querySelector('[data-waqya-consent="manage"]');

    banner.querySelector('[data-waqya-consent="accept"]').addEventListener('click', function () {
      var c = { analytics: true };
      write(c);
      apply(c, false);
    });

    banner.querySelector('[data-waqya-consent="reject"]').addEventListener('click', function () {
      var c = { analytics: false };
      write(c);
      apply(c, false);
    });

    if (manageBtn && prefs) {
      manageBtn.addEventListener('click', function () {
        prefs.removeAttribute('hidden');
        if (saveBtn) {
          saveBtn.removeAttribute('hidden');
        }
        manageBtn.setAttribute('hidden', '');
      });
    }

    if (saveBtn) {
      saveBtn.addEventListener('click', function () {
        var analytics = !!document.getElementById('waqya-consent-analytics')?.checked;
        var c = { analytics: analytics };
        write(c);
        apply(c, false);
      });
    }

    document.querySelectorAll('[data-waqya-open-consent]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        showBanner();
        if (prefs) {
          prefs.removeAttribute('hidden');
        }
        var stored = read();
        var cb = document.getElementById('waqya-consent-analytics');
        if (cb && stored) {
          cb.checked = !!stored.analytics;
        }
        if (saveBtn) {
          saveBtn.removeAttribute('hidden');
        }
      });
    });
  }

  var stored = read();
  bind();
  if (stored) {
    apply(stored, false);
  } else {
    showBanner();
    apply({ analytics: false }, true);
  }
})();
