(function () {
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var root = document.documentElement;
  root.classList.add('dj');

  var bar = document.createElement('div');
  bar.className = 'read-bar';
  bar.setAttribute('aria-hidden', 'true');
  document.body.appendChild(bar);

  var shot = document.querySelector('.hero-shot img');
  var ticking = false;
  function onScroll() {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(function () {
      var h = root.scrollHeight - window.innerHeight;
      bar.style.transform = 'scaleX(' + (h > 0 ? Math.min(1, window.scrollY / h) : 0) + ')';
      if (shot && !reduce) {
        var r = shot.parentElement.getBoundingClientRect(), vh = window.innerHeight;
        var p = Math.max(-1, Math.min(1, (r.top + r.height / 2 - vh / 2) / vh));
        shot.style.transform = 'translateY(' + (p * -22).toFixed(1) + 'px) scale(' + (1.04 - Math.abs(p) * 0.03).toFixed(3) + ')';
      }
      ticking = false;
    });
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll);
  onScroll();

  var items = document.querySelectorAll('.section, .feat-card, .data-row, .other-card');
  if (reduce || !('IntersectionObserver' in window)) return;
  items.forEach(function (el) { el.classList.add('rv'); });
  var n = 0;
  var io = new IntersectionObserver(function (es) {
    n = 0;
    es.forEach(function (e) {
      if (!e.isIntersecting) return;
      var el = e.target;
      setTimeout(function () { el.classList.add('in'); }, (n++ % 6) * 80);
      io.unobserve(el);
    });
  }, { rootMargin: '0px 0px -8% 0px' });
  items.forEach(function (el) { io.observe(el); });
})();
