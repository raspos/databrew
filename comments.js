/* STORIES 기사 댓글 (utterances = GitHub Issues). NOW 피드와 같은 방식입니다.
   - 기사 페이지(/articles/<id>/)에서만 동작합니다. 기사 본문과 서비스 링크 박스는 이 스크립트와 무관하게 먼저 표시됩니다.
   - 외부 스크립트(utteranc.es)는 독자가 "댓글 보기·쓰기"를 누를 때만 불러옵니다.
   - 기사마다 고정 ID로 이슈가 하나씩 연결됩니다: issue-term = databrew-story:<기사 ID>. 기사를 수정해 다시 게시해도 댓글이 유지됩니다.
   - 댓글을 쓰려면 GitHub 로그인이 필요하고, 댓글은 raspos/databrew 저장소의 공개 이슈로 저장됩니다. 삭제·잠금은 저장소 Issues에서 관리자가 합니다.
   - 저장소 소유자가 utterances GitHub 앱을 raspos/databrew에 한 번 설치해야 동작합니다: https://github.com/apps/utterances (이 저장소만 선택).
     설치 전에는 댓글 영역에 utterances의 설정 오류 안내가 나옵니다. */
(function () {
  'use strict';
  var REPO = 'raspos/databrew';
  var m = /\/articles\/([\w-]+)\/?$/.exec(location.pathname.replace(/index\.html$/, ''));
  var host = document.querySelector('main.art');
  if (!m || !host || document.getElementById('comments')) return;
  function theme() {
    var o = document.documentElement.dataset.theme;
    var dark = o === 'dark' || (!o && window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches);
    return dark ? 'github-dark' : 'github-light';
  }
  var sec = document.createElement('section'); sec.className = 'art-comments'; sec.id = 'comments';
  var h = document.createElement('h2'); h.textContent = '댓글'; sec.appendChild(h);
  var note = document.createElement('p'); note.className = 'cm-note';
  note.textContent = '댓글을 쓰려면 GitHub 계정으로 로그인해야 하며, 댓글은 GitHub 이슈로 공개 저장됩니다. 읽기만 할 때는 로그인이 필요 없습니다.';
  sec.appendChild(note);
  var btn = document.createElement('button'); btn.type = 'button'; btn.className = 'cm-open'; btn.textContent = '댓글 보기·쓰기';
  var slot = document.createElement('div'); slot.className = 'cm-slot';
  sec.appendChild(btn); sec.appendChild(slot); host.appendChild(sec);
  btn.addEventListener('click', function () {
    btn.hidden = true;
    var s = document.createElement('script'); s.src = 'https://utteranc.es/client.js'; s.async = true; s.crossOrigin = 'anonymous';
    s.setAttribute('repo', REPO); s.setAttribute('issue-term', 'databrew-story:' + m[1]); s.setAttribute('theme', theme());
    s.onerror = function () {
      var e = document.createElement('p'); e.className = 'cm-err'; e.textContent = '댓글을 불러오지 못했습니다. 기사는 정상적으로 읽을 수 있고, 잠시 후 다시 시도해 주세요.';
      slot.textContent = ''; slot.appendChild(e); btn.hidden = false;
    };
    slot.appendChild(s);
  });
  if (window.matchMedia) {
    var mq = window.matchMedia('(prefers-color-scheme: dark)');
    var sync = function () { var f = slot.querySelector('iframe.utterances-frame'); if (f && f.contentWindow) f.contentWindow.postMessage({ type: 'set-theme', theme: theme() }, 'https://utteranc.es'); };
    if (mq.addEventListener) mq.addEventListener('change', sync);
  }
})();
