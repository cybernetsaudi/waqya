/**
 * Post hero slider
 */
(function () {
  'use strict';

  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const AUTO_MS = 6500;

  document.querySelectorAll('[data-post-slider]').forEach((root) => {
    const slides = Array.from(root.querySelectorAll('[data-slider-slide]'));
    if (slides.length <= 1) {
      return;
    }

    const prevBtn = root.querySelector('[data-slider-prev]');
    const nextBtn = root.querySelector('[data-slider-next]');
    const dots = Array.from(root.querySelectorAll('[data-slider-goto]'));
    const currentEl = root.querySelector('[data-slider-current]');
    let index = slides.findIndex((s) => s.classList.contains('is-active'));
    if (index < 0) {
      index = 0;
    }
    let timer = null;

    function goTo(next) {
      const total = slides.length;
      index = (next + total) % total;

      slides.forEach((slide, i) => {
        const active = i === index;
        slide.classList.toggle('is-active', active);
        slide.setAttribute('aria-hidden', active ? 'false' : 'true');
      });

      dots.forEach((dot, i) => {
        const active = i === index;
        dot.classList.toggle('is-active', active);
        dot.setAttribute('aria-selected', active ? 'true' : 'false');
      });

      if (currentEl) {
        currentEl.textContent = String(index + 1);
      }
    }

    function startAuto() {
      if (reducedMotion) {
        return;
      }
      stopAuto();
      timer = window.setInterval(() => goTo(index + 1), AUTO_MS);
    }

    function stopAuto() {
      if (timer) {
        window.clearInterval(timer);
        timer = null;
      }
    }

    prevBtn?.addEventListener('click', () => {
      goTo(index - 1);
      startAuto();
    });

    nextBtn?.addEventListener('click', () => {
      goTo(index + 1);
      startAuto();
    });

    dots.forEach((dot) => {
      dot.addEventListener('click', () => {
        const target = parseInt(dot.getAttribute('data-slider-goto') || '0', 10);
        goTo(target);
        startAuto();
      });
    });

    root.addEventListener('mouseenter', stopAuto);
    root.addEventListener('mouseleave', startAuto);
    root.addEventListener('focusin', stopAuto);
    root.addEventListener('focusout', startAuto);

    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        stopAuto();
      } else {
        startAuto();
      }
    });

    startAuto();
  });
})();
