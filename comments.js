/* 기사 댓글 (giscus = GitHub Discussions). 기사 페이지(/articles/<id>/)에서만 동작하며, 설정이 비어 있으면 아무것도 보이지 않습니다.
   기사 본문과 서비스 링크 박스는 이 스크립트와 무관하게 먼저 표시되고, 댓글 서비스가 막혀도 기사 읽기에는 영향이 없습니다.

   설정 방법 (저장소 소유자가 한 번만):
   1) GitHub 저장소 raspos/databrew → Settings → General → Features → Discussions 체크
   2) Discussions에서 카테고리 하나 만들기(예: "댓글", 형식은 Announcements 권장 — 새 토론은 관리자·giscus만 만들 수 있어 스팸 방지)
   3) https://github.com/apps/giscus 에서 Install → raspos/databrew 선택
   4) https://giscus.app 에서 저장소 raspos/databrew와 위 카테고리를 선택하면 data-category-id 값이 나옵니다. 아래 CATEGORY_ID에 넣으세요.
   REPO_ID는 저장소의 고유 ID(R_kgDOVUoIRA)입니다. */
(function () {
  'use strict';
  var GISCUS = { repo: 'raspos/databrew', repoId: 'R_kgDOVUoIRA', category: '댓글', categoryId: '' };
  var m = /\/articles\/([\w-]+)\/?$/.exec(location.pathname.replace(/index\.html$/, ''));
  var host = document.querySelector('main.art');
  if (!m || !host || !GISCUS.repo || !GISCUS.repoId || !GISCUS.categoryId) return;
  if (document.getElementById('comments')) return;
  var sec = document.createElement('section'); sec.className = 'art-comments'; sec.id = 'comments';
  var h = document.createElement('h2'); h.textContent = '댓글'; sec.appendChild(h);
  var note = document.createElement('p'); note.className = 'cm-note'; note.textContent = '댓글을 쓰려면 GitHub 계정으로 로그인해야 합니다. 읽기는 로그인 없이 됩니다.'; sec.appendChild(note);
  host.appendChild(sec);
  var s = document.createElement('script'); s.src = 'https://giscus.app/client.js'; s.async = true; s.crossOrigin = 'anonymous';
  var A = { 'data-repo': GISCUS.repo, 'data-repo-id': GISCUS.repoId, 'data-category': GISCUS.category, 'data-category-id': GISCUS.categoryId,
    'data-mapping': 'specific', 'data-term': 'article-' + m[1], 'data-strict': '1', 'data-reactions-enabled': '1', 'data-emit-metadata': '0',
    'data-input-position': 'top', 'data-theme': 'preferred_color_scheme', 'data-lang': 'ko', 'data-loading': 'lazy' };
  Object.keys(A).forEach(function (k) { s.setAttribute(k, A[k]); });
  s.onerror = function () { var e = document.createElement('p'); e.className = 'cm-err'; e.textContent = '댓글을 불러오지 못했습니다. 기사는 정상적으로 읽을 수 있습니다.'; sec.appendChild(e); };
  sec.appendChild(s);
})();
