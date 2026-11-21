/* NOW rolling preview on the main databrew hub.
 * Only published NOW WATCH, STORIES, new projects and connected Meta Threads.
 * The UI never invents a post or relabels source observation dates as today.
 */
(function () {
  'use strict';
  // Resolve from the script itself, so both /databrew/ and /databrew/en/ work.
  var scriptSource = document.currentScript && document.currentScript.src;
  var nowBase = new URL('.', scriptSource || new URL('now/', document.baseURI).href);
  var root = document.getElementById('now-roll');
  if (!root || typeof fetch !== 'function') return;

  var link = document.getElementById('now-roll-link');
  var type = document.getElementById('now-roll-type');
  var line = document.getElementById('now-roll-text');
  var date = document.getElementById('now-roll-date');
  var prev = root.querySelector('[data-roll-prev]');
  var next = root.querySelector('[data-roll-next]');
  var reduced = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : { matches: false };
  var items = [], current = 0, timeout = 0, interval = 0;

  function load(path) {
    return fetch(path, { cache: 'no-cache' }).then(function (response) {
      if (!response.ok) throw new Error('NOW preview request failed');
      return response.json();
    });
  }

  function dateValue(value) {
    var stamp = String(value || '');
    if (/^\d{4}-\d{2}-\d{2}$/.test(stamp)) stamp += 'T12:00:00+09:00';
    var n = Date.parse(stamp);
    return isFinite(n) ? n : 0;
  }

  function readableDate(value) {
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(value || ''));
    return m ? m[2] + '.' + m[3] : '';
  }

  function stripLine(value) {
    return String(value || '').replace(/\s+/g, ' ').trim();
  }

  function add(out, tag, heading, when, filter, key) {
    var text = stripLine(heading);
    var at = dateValue(when);
    if (!text || !at) return;
    out.push({
      tag: tag,
      text: text,
      date: readableDate(when),
      time: at,
      path: new URL('?filter=' + encodeURIComponent(filter) + (key ? '&item=' + encodeURIComponent(String(key)) : ''), nowBase).href,
      key: key || tag + ':' + when + ':' + text
    });
  }

  function paint(index, animate) {
    if (!items.length) return;
    var idx = ((index % items.length) + items.length) % items.length;
    if (timeout) window.clearTimeout(timeout);
    function apply() {
      current = idx;
      var post = items[current];
      type.textContent = post.tag;
      line.textContent = post.text;
      date.textContent = post.date;
      link.href = post.path;
      link.setAttribute('aria-label', 'NOW ' + post.tag + ': ' + post.text + ' · 피드 보기');
      root.classList.remove('now-roll-changing');
    }
    if (animate && !reduced.matches) {
      root.classList.add('now-roll-changing');
      timeout = window.setTimeout(apply, 190);
    } else {
      apply();
    }
  }

  function stop() {
    if (interval) window.clearInterval(interval);
    interval = 0;
  }

  function start() {
    stop();
    if (items.length < 2 || reduced.matches) return;
    interval = window.setInterval(function () {
      if (document.hidden || root.matches(':hover') || root.contains(document.activeElement)) return;
      paint(current + 1, true);
    }, 4900);
  }

  Promise.allSettled([
    load(new URL('activity.json', nowBase).href),
    load(new URL('../articles.json', nowBase).href),
    load(new URL('threads.json', nowBase).href)
  ]).then(function (responses) {
    var activity = responses[0].status === 'fulfilled' ? responses[0].value : {};
    var articles = responses[1].status === 'fulfilled' ? responses[1].value : [];
    var threads = responses[2].status === 'fulfilled' ? responses[2].value : {};
    var posts = [];

    (Array.isArray(activity.watch) ? activity.watch : []).forEach(function (p) {
      if (p && p.day) add(posts, 'WATCH', p.title, p.day, 'watch', p.id);
    });

    (Array.isArray(activity.projects) ? activity.projects : []).forEach(function (p) {
      // Previous projects are in the archive, but not fake fresh updates.
      if (p && p.first_seen) add(posts, 'PROJECT', p.name, p.first_seen, 'projects', p.id);
    });

    (Array.isArray(articles) ? articles : []).forEach(function (p) {
      if (p && p.date) add(posts, 'STORY', p.title, p.date, 'stories', p.id);
    });

    (Array.isArray(threads.posts) ? threads.posts : []).forEach(function (p) {
      if (p && p.timestamp && p.text) add(posts, 'THREADS', p.text, p.timestamp, 'threads', p.id);
    });

    posts.sort(function (a, b) { return b.time - a.time; });

    var used = Object.create(null);
    items = posts.filter(function (p) {
      if (used[p.key]) return false;
      used[p.key] = true;
      return true;
    }).slice(0, 8);

    if (!items.length) return; // hide preview on source outage; do not fabricate news
    root.hidden = false;
    paint(0, false);
    start();

    if (prev) prev.addEventListener('click', function () {
      paint(current - 1, true);
      start();
    });
    if (next) next.addEventListener('click', function () {
      paint(current + 1, true);
      start();
    });
    if (reduced.addEventListener) reduced.addEventListener('change', start);
    document.addEventListener('visibilitychange', function () {
      if (!document.hidden) start();
    });
  }).catch(function () {
    root.hidden = true;
  });
})();
