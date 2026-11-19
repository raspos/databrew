/* databrew 조회수: 페이지별 카운터(countapi) + 선택적 GoatCounter.
   - 세션당 페이지마다 1회만 올립니다(새로고침·뒤로 가기로 부풀지 않음). 배포 도메인이 아니면 읽기만 합니다.
   - 키: databrew_pv_<페이지키>. 페이지키는 경로를 밑줄로 이은 것(허브=home, 영어 허브=en, projects_<이름>, articles_<날짜>_<코드>).
   - GoatCounter를 쓰려면 아래 GC_CODE에 사이트 코드(https://<코드>.goatcounter.com 의 <코드>)를 넣으세요. null이면 쓰지 않습니다. */
(function () {
  'use strict';
  var GC_CODE = null;
  var API = 'https://countapi.mileshilliard.com/api/v1/';
  function pageKey(path) {
    var p = String(path || location.pathname).replace(/^\/databrew\//, '').replace(/index\.html$/, '').replace(/\/+$/, '').replace(/^\/+/, '');
    if (!p) return 'home';
    return p.replace(/[^a-z0-9]+/gi, '_').toLowerCase().replace(/^_|_$/g, '') || 'home';
  }
  var me = document.currentScript;
  if (me && me.src && document.querySelector('main.art')) { var c = document.createElement('script'); c.src = me.src.replace(/analytics\.js(\?.*)?$/, 'comments.js'); c.defer = true; document.head.appendChild(c); }
  window.DatabrewAnalytics = { pageKey: pageKey, prefix: 'databrew_pv_' };
  if (GC_CODE && /^[a-z0-9][a-z0-9-]{1,29}$/.test(GC_CODE) && !document.querySelector('script[data-goatcounter]')) {
    var g = document.createElement('script'); g.async = true; g.src = 'https://gc.zgo.at/count.js';
    g.setAttribute('data-goatcounter', 'https://' + GC_CODE + '.goatcounter.com/count'); document.head.appendChild(g);
  }
  if (typeof fetch !== 'function') return;
  var key = 'databrew_pv_' + pageKey(), flag = 'pv_' + key, hit = location.hostname === 'raspos.github.io';
  try { if (sessionStorage.getItem(flag)) hit = false; } catch (e) {}
  fetch(API + (hit ? 'hit/' : 'get/') + key, { cache: 'no-store' })
    .then(function (r) { return r.json(); })
    .then(function (j) {
      if (typeof j.value !== 'number') return;
      try { if (hit) sessionStorage.setItem(flag, '1'); } catch (e) {}
      document.querySelectorAll('[data-pv]').forEach(function (el) {
        el.textContent = Number(j.value).toLocaleString('en-US');
        var h = el.closest('[hidden]'); if (h) h.hidden = false;
      });
    })
    .catch(function () {});
})();
