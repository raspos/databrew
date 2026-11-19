/* 페이지별 조회수(analytics.js)를 detail.js와 같은 폴더 기준으로 불러옵니다 */
(function () { var cs = document.currentScript; if (!cs || !cs.src) return; var s = document.createElement('script'); s.src = cs.src.replace(/detail\.js(\?.*)?$/, 'analytics.js'); s.defer = true; document.head.appendChild(s); })();
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

/* 사이트 누적 방문: 세션당 1회 hit(허브와 같은 키), 배포 도메인이 아니면 읽기만 */
(function () {
  var els = document.querySelectorAll('[data-hub-views]');
  if (!els.length || typeof fetch !== 'function') return;
  var KEY = 'raspos_databrew_hub_total_v1', API = 'https://countapi.mileshilliard.com/api/v1/';
  var hit = location.hostname === 'raspos.github.io';
  try { if (sessionStorage.getItem('databrew_hub_counted')) hit = false; } catch (e) {}
  fetch(API + (hit ? 'hit/' : 'get/') + KEY, { cache: 'no-store' })
    .then(function (r) { return r.json(); })
    .then(function (j) {
      if (typeof j.value !== 'number') return;
      try { if (hit) sessionStorage.setItem('databrew_hub_counted', '1'); } catch (e) {}
      els.forEach(function (e) { e.textContent = Number(j.value).toLocaleString('en-US'); });
    })
    .catch(function () {});
})();
