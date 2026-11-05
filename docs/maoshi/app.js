// 卯時 MAO SHI：封面、每日刊（無限往下）、單隻內頁、角色專訪、貓窩、同風格。
// 資料：data/index.json（每天一行）、data/days/26.11.04.json（那天的貓）、data/cast.json、data/all.json（貓窩與同風格才載）。
(function () {
  'use strict';
  var DATA = 'data/';
  var SHI = '子丑寅卯辰巳午未申酉戌亥';
  var SEASONS = [['spring', '春'], ['summer', '夏'], ['autumn', '秋'], ['winter', '冬']];
  var PICKS = [['art_style', '畫風'], ['composition', '構圖'], ['lighting', '光線'], ['texture', '質感'], ['color_palette', '配色']];
  var S = { index: null, cast: {}, days: new Map(), all: null, store: null, prevOpen: '', rendered: 0, busy: false, ended: false, opened: false, lastCat: null };
  window.__mao = S; // 給自動驗收看狀態用
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var esc = function (s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); };

  // ---------- 資料 ----------
  function json(u, fresh) {
    return fetch(u, fresh ? { cache: 'no-cache' } : undefined).then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); });
  }
  function day(k) {
    if (!S.days.has(k)) S.days.set(k, json(DATA + 'days/' + k + '.json').catch(function (e) { S.days.delete(k); throw e; }));
    return S.days.get(k);
  }
  // all.json 一列：[編號, 標題, 期, 縮圖, 平均色, 角色, [畫風, 構圖, 光線, 質感, 配色]]；中文名在 styles.json
  function all() {
    if (!S.all) S.all = Promise.all([json(DATA + 'all.json'), json(DATA + 'styles.json')]).then(function (r) {
      S.styles = r[1];
      var m = new Map();
      r[0].forEach(function (x) {
        // 舊格式 [編號, 標題, 期, 縮圖, 平均色, 畫風, 角色, 畫風中文]（舊版產生器推上來的）也認得
        var picks = Array.isArray(x[6]) ? x[6] : [x[5] || '', '', '', '', ''], ch = Array.isArray(x[6]) ? x[5] : x[6];
        m.set(x[0], { n: x[0], t: x[1], d: x[2], th: x[3], avg: x[4], ch: ch || '', picks: picks, style: picks[0] });
      });
      return m;
    }).catch(function (e) { S.all = null; throw e; });
    return S.all;
  }
  var SAME = { a: [0, 'art_style', '同畫風'], c: [1, 'composition', '同構圖'], l: [2, 'lighting', '同光線'], t: [3, 'texture', '同質感'], p: [4, 'color_palette', '同配色'] };
  var SAME_BY_KEY = { art_style: 'a', composition: 'c', lighting: 'l', texture: 't', color_palette: 'p' };
  function zhOf(key, en) { return (S.styles && S.styles[key] && S.styles[key][en]) || ''; }
  var full = function (th) { return th.replace('/download/thumbs-', '/download/cats-').replace(/_480\.webp$/, '.webp'); };
  var EMBED = new URLSearchParams(location.search).get('embed') === 'larch';
  // Larch 的框不准開新視窗，外部連結按了沒反應：嵌在 Larch 時藏起來，改放在市集介紹
  if (EMBED) document.documentElement.classList.add('embed');
  function exitToLarch() { parent.postMessage({ type: 'maoshi:exit' }, '*'); } // 外殼卡收到後送 larch:complete，回 Larch 標題畫面
  var todayKey = function () { var t = new Date(Date.now() + 8 * 3600e3); return String(t.getUTCFullYear()).slice(2) + '.' + String(t.getUTCMonth() + 1).padStart(2, '0') + '.' + String(t.getUTCDate()).padStart(2, '0'); };
  var nowIso = function () { return new Date(Date.now() + 8 * 3600e3).toISOString().slice(0, 16) + '+08:00'; };
  var isNew = function (c) { return S.prevOpen && c.at > S.prevOpen; };

  // ---------- 貓窩（使用者記錄） ----------
  function saved() { var v = S.store.get('mao_saved'); return v ? v.split(',').map(Number).filter(Boolean) : []; }
  function isSaved(n) { return saved().indexOf(n) >= 0; }
  function toggleSave(n) {
    var list = saved(), i = list.indexOf(n);
    if (i >= 0) list.splice(i, 1); else list.push(n);
    S.store.set('mao_saved', list.join(','));
    var on = i < 0;
    document.querySelectorAll('[data-save="' + n + '"]').forEach(function (b) {
      b.classList.toggle('on', on);
      if (b.classList.contains('sv')) b.textContent = on ? '已在貓窩' : '＋ 收進貓窩';
      else { b.setAttribute('aria-label', on ? '已收進貓窩' : '收進貓窩'); b.title = b.getAttribute('aria-label'); }
      b.setAttribute('aria-pressed', on);
    });
    denCount(true);
    toast(on ? (S.store.mode === 'memory' ? '收進貓窩了，但這次的收藏不會保留' : '收進貓窩了') : '從貓窩拿出來了');
  }
  function denCount(bump) {
    var el = $('#denCount'); el.textContent = saved().length;
    if (bump) { var b = el.parentNode; b.classList.remove('bump'); void b.offsetWidth; b.classList.add('bump'); }
  }
  function markSeen(id) {
    var v = S.store.get('mao_seen_cast'), list = v ? v.split(',') : [];
    if (list.indexOf(id) < 0) { list.push(id); S.store.set('mao_seen_cast', list.join(',')); }
  }
  var toastT;
  function toast(msg) { var t = $('#toast'); t.textContent = msg; t.classList.add('on'); clearTimeout(toastT); toastT = setTimeout(function () { t.classList.remove('on'); }, 1800); }

  // ---------- 小元件 ----------
  // 縮圖載不到時（還沒補好、或網路抖一下）改用原圖；data-full 沒給就從縮圖網址推
  window.__maoImgErr = function (im) {
    if (im.dataset.tried) return; im.dataset.tried = 1;
    var f = im.dataset.full || im.src.replace('/download/thumbs-', '/download/cats-').replace(/_480\.webp$/, '.webp');
    if (f && f !== im.src) im.src = f;
  };
  function ph(src, avg, alt, extra, attrs, fullSrc) {
    return '<div class="ph"' + (attrs || '') + ' style="--avg:' + avg + '"><img src="' + esc(src) + '"' + (fullSrc ? ' data-full="' + esc(fullSrc) + '"' : '') +
      ' alt="' + esc(alt || '') + '" loading="lazy" decoding="async" onload="this.classList.add(\'in\')" onerror="__maoImgErr(this)">' + (extra || '') + '</div>';
  }
  function kick(c) {
    var p = c.picks && c.picks.art_style;
    if (!p || !p.en) return '';
    return '<button class="kick" type="button" data-style="' + esc(p.en) + '">' + esc(p.en) + (p.zh ? ' · ' + esc(p.zh) : '') + '</button>';
  }
  function first(s) { s = (s || '').trim(); var i = s.indexOf('。'); return i > 0 ? s.slice(0, i) : s; }
  function by(c) { return [c.chn, c.shi + '時 ' + c.hm].filter(Boolean).join(' · '); }
  function badges(c) {
    return (isNew(c) ? '<span class="badge">NEW</span>' : '') + (c.season ? '<span class="season">' + ({ spring: '春', summer: '夏', autumn: '秋', winter: '冬' }[c.season] || '') + '</span>' : '');
  }
  function saveBtn(n) { var on = isSaved(n); return '<button class="save' + (on ? ' on' : '') + '" type="button" data-save="' + n + '" aria-pressed="' + on + '" aria-label="' + (on ? '已收進貓窩' : '收進貓窩') + '" title="' + (on ? '已收進貓窩' : '收進貓窩') + '"></button>'; }

  // 排版：第一列＝第一隻（6 欄橫放）＋兩隻 3 欄；之後每列 4 隻；最後剩 3 隻各 4 欄、剩 2 隻各 6 欄橫放；整天只有 1 隻就佔滿 12 欄
  function layout(list) {
    var n = list.length, out = [], i = 1;
    if (!n) return out;
    out.push([list[0], n === 1 ? 12 : 6, true, true]);
    if (n >= 3 && (n - 3) % 4 !== 1) { out.push([list[1], 3], [list[2], 3]); i = 3; } else if (n >= 2) { out.push([list[1], 6, true]); i = 2; }
    while (i < n) {
      var r = n - i, k = r >= 4 && r !== 5 ? 4 : (r === 5 ? 3 : r);
      list.slice(i, i + k).forEach(function (c) { out.push(k === 4 ? [c, 3] : k === 3 ? [c, 4] : [c, 6, true]); });
      i += k;
    }
    return out;
  }
  function card(c, span, wide, lead) {
    return '<article class="ar' + (wide ? ' wide' : '') + (lead ? ' lead' : '') + '" style="--span:' + span + ';--acc:' + c.acc + ';--avg:' + c.avg + '">' +
      ph(c.th, c.avg, c.t, saveBtn(c.n), ' data-cat="' + c.n + '"', c.img) +
      '<div class="tx" data-cat="' + c.n + '">' + kick(c) + '<div class="t">' + badges(c) + esc(c.t) + '</div><div class="by">' + esc(by(c)) + '</div>' +
      (wide && c.story ? '<q>' + esc(first(c.story)) + '</q>' : '') + '</div></article>';
  }

  // ---------- 封面 ----------
  function renderCover(d, prev) {
    var cv = d.cats[0], cast = S.cast, inIssue = {};
    d.cats.forEach(function (c) { if (c.ch) inIssue[c.ch] = 1; });
    var el = $('#cover'); el.style.setProperty('--acc', cv.acc);
    var p = $('#cvPh'); p.className = 'cv-ph'; p.style.background = cv.avg;
    var mast = $('#cvMast') || el.insertBefore(document.createElement('header'), el.firstChild);
    mast.id = 'cvMast'; mast.className = 'cv-mast';
    mast.innerHTML = '<b class="mh">MAO SHI</b><div class="cv-id"><span class="zh">卯時</span><span class="tag">每天一期的貓咪時尚雜誌</span>' +
      '<span class="vol">VOL. <b>' + d.vol + '</b> · ' + d.d + ' 週' + d.wd + ' · 本期 ' + d.cats.length + ' 隻</span></div>';
    p.innerHTML = '<img src="' + esc(cv.th) + '" alt="' + esc(cv.t) + '" fetchpriority="high">' +
      '<button class="cl" type="button" data-cat="' + cv.n + '"><span class="kick">本期封面 · ' + cv.shi + '時 ' + cv.hm + (cv.chn ? ' · ' + esc(cv.chn) : '') + '</span><b>' + esc(cv.t) + '</b></button>';
    var img = p.querySelector('img'), big = new Image();
    big.onload = function () { img.src = big.src; };
    big.src = cv.img;
    var keys = Object.keys(cast);
    var cont = S.store.get('mao_last_issue');
    var side = $('#cvSide');
    side.innerHTML = '<div class="ti">This issue</div><div class="src kick">' + (d.topicFrom === 'news' ? '今日話題 · 啟發了今天的貓' : '本期封面故事') + '</div><div class="nw">' + esc(d.topic) + '</div>' +
      // 目錄最多四行，放不下就截掉，不讓版面擠
      '<ol class="toc">' + d.cats.slice(1, 5).map(tocItem).join('') +
      (prev && d.cats.length < 4 ? '<li class="toc-h">上一期 ' + prev.d + '</li>' + prev.cats.slice(0, 4 - (d.cats.length - 1) - 1).map(tocItem).join('') : '') + '</ol>' +
      '<div class="cast"><span class="kick">本期出場</span>' + keys.map(function (k) {
        return '<button class="chip' + (inIssue[k] ? '' : ' off') + '" type="button" data-cast="' + k + '"><img src="' + esc(cast[k].av) + '" alt="">' + esc(cast[k].name) + '</button>';
      }).join('') + '</div>' +
      '<div class="cta"><button class="link" type="button" data-go="feed">翻開本期 <i>→</i></button>' +
      (cont && cont !== d.d && S.index.days.some(function (x) { return x.d === cont; }) ? '<button class="link quiet" type="button" data-go="continue">接著看 ' + cont + '</button>' : '') +
      (EMBED ? '<button class="link quiet" type="button" data-go="exit">合上雜誌</button>' : '') +
      '<span class="new" id="newCount"></span></div>';
    $('#castMini').innerHTML = keys.map(function (k) { return '<button type="button" data-cast="' + k + '" aria-label="' + esc(cast[k].name) + '"><img src="' + esc(cast[k].av) + '" alt=""></button>'; }).join('');
    countNew();
  }
  function tocItem(c, i) {
    return '<li style="animation-delay:' + (i * 60) + 'ms"><button type="button" data-cat="' + c.n + '"><i>' + c.shi + '</i><span><span class="tt">' + esc(c.t) + '</span><em>' + esc((c.picks.art_style || {}).en || '') + '</em></span></button></li>';
  }
  function countNew() {
    if (!S.prevOpen) return;
    var total = 0, i = 0;
    (function next() {
      var row = S.index.days[i++];
      if (!row || i > 7) return show();
      day(row.d).then(function (d) {
        var k = d.cats.filter(isNew).length; total += k;
        if (k === d.cats.length) next(); else show();
      }).catch(show);
    })();
    function show() { if (total) $('#newCount').textContent = '上次來之後新增 ' + total + ' 隻'; }
  }

  // ---------- 每日刊 ----------
  function renderIssue(d, live) {
    var s = document.createElement('section');
    s.className = 'issue' + (live ? ' live' : ''); s.id = 'i-' + d.d; s.dataset.d = d.d; s.dataset.wd = d.wd;
    s.style.setProperty('--acc', d.cats[0].acc);
    if (live) {
      // 今天還沒過完：小卡一列六隻，明天卯時才出刊
      s.innerHTML = '<header class="ih"><b>' + d.d + '</b><span class="kick">NEXT ISSUE · 製作中 · ' + d.cats.length + ' LOOKS</span><span class="bar"></span><span class="ln">VOL. ' + d.vol + ' · 週' + d.wd + '</span>' +
        '<div class="tp"><small>下一期</small>每個整點都可能多一隻貓，明天卯時（05:00）出刊。</div></header>' +
        '<div class="sp">' + d.cats.map(function (c) { return card(c, 2, false, false); }).join('') + '</div>';
      var old = document.getElementById(s.id);
      if (old) old.replaceWith(s); else $('#feed').insertBefore(s, $('#feed').firstChild);
    } else {
      s.innerHTML = '<header class="ih"><b>' + d.d + '</b><span class="kick">DAILY ISSUE · ' + d.cats.length + ' LOOKS</span><span class="bar"></span><span class="ln">VOL. ' + d.vol + ' · 週' + d.wd + '</span>' +
        '<div class="tp"><small>' + (d.topicFrom === 'news' ? '今日話題' : '本期封面故事') + '</small>' + esc(d.topic) + '</div></header>' +
        '<div class="sp">' + layout(d.cats).map(function (x) { return card(x[0], x[1], !!x[2], !!x[3]); }).join('') + '</div>';
      $('#feed').appendChild(s);
    }
    drawObs.observe(s); viewObs.observe(s);
  }
  // 每 5 分鐘看一次有沒有新貓：下一期多了就提示；過了午夜（新的一期出刊）就提示重新整理
  function liveBar(msg, act) {
    var b = $('#liveBar');
    if (!b) { b = document.createElement('button'); b.id = 'liveBar'; b.type = 'button'; b.className = 'live-bar'; document.body.appendChild(b); }
    b.textContent = msg; b.dataset.act = act; b.hidden = false;
  }
  function pollLive() {
    json(DATA + 'index.json', true).then(function (idx) {
      if (todayKey() !== S.today) { liveBar('新的一期出刊了　重新整理 →', 'reload'); return; }
      var top = idx.days[0];
      if (!top || top.d !== S.today) return;
      var had = S.live ? S.live.n : 0;
      if (top.n > had) { S.liveNew = top; liveBar('下一期多了 ' + (top.n - had) + ' 隻　看看 →', 'live'); }
    }).catch(function () {});
  }
  function showLive() {
    var top = S.liveNew; if (!top) return;
    json(DATA + 'days/' + top.d + '.json?t=' + Date.now(), true).then(function (d) {
      S.live = top; S.days.set(top.d, Promise.resolve(d)); renderIssue(d, true);
      var el = document.getElementById('i-' + top.d); if (el) el.scrollIntoView({ behavior: 'smooth' });
      $('#liveBar').hidden = true;
    });
  }
  function prefetch(i) {
    var row = S.index.days[i];
    if (!row) return;
    day(row.d).then(function (d) { d.cats.forEach(function (c) { var im = new Image(); im.decoding = 'async'; im.src = c.th; }); }).catch(function () {});
  }
  function appendNext() {
    if (S.busy || S.ended) return Promise.resolve();
    var row = S.index.days[S.rendered];
    if (!row) { showEnd(); return Promise.resolve(); }
    S.busy = true;
    $('#more').innerHTML = '<div class="skel-issue"><div class="sk"></div><div class="sk"></div><div class="sk"></div><div class="sk"></div></div>';
    return day(row.d).then(function (d) {
      renderIssue(d); S.rendered++;
      $('#more').innerHTML = '';
      prefetch(S.rendered); prefetch(S.rendered + 1); // 看一天、備兩天
    }).catch(function () {
      $('#more').innerHTML = '<div class="msg"><b>連不上 catime</b>可能是網路斷了，或 GitHub 暫時沒有回應。已經載入的期數還能看。<br><button class="btn" type="button" data-retry="more">再試一次</button></div>';
      S.failed = true;
    }).then(function () {
      S.busy = false;
      // 用實際位置判斷，不用 observer 的舊旗標，不然剛插進去的期還沒排版就會一路連載下去
      if (!S.failed && nearEnd()) appendNext();
      else requestAnimationFrame(onScroll); // content-visibility 會先用估計高度，排完版再量一次
    });
  }
  function showEnd() {
    S.ended = true;
    var last = S.index.days[S.index.days.length - 1];
    $('#more').innerHTML = '<div class="end"><b>' + last.d + '</b><span class="kick">VOL. 1 起點</span><p>第一隻貓在 2026 年 1 月 30 日誕生，從 2 月 3 日起每一隻都有故事。到這裡一共 ' + S.index.total + ' 隻。</p><button class="btn" type="button" data-go="top">回到最新一期</button></div>';
  }
  function renderUntil(k) {
    var target = S.index.days.findIndex(function (x) { return x.d === k; });
    (function step() {
      if (S.rendered > target || S.failed) { var el = document.getElementById('i-' + k); if (el) el.scrollIntoView({ behavior: 'smooth' }); return; }
      appendNext().then(step);
    })();
  }

  // 捲到離底部還有 1.5 個畫面高時接下一期。用捲動事件＋實際位置，比 IntersectionObserver 可靠（後者在剛插入內容時不一定再通知）
  var ticking = false;
  function nearEnd() { return $('#more').getBoundingClientRect().top < innerHeight * 2.5; }
  function onScroll() { if (ticking) return; ticking = true; requestAnimationFrame(function () { ticking = false; if (S.index && nearEnd()) appendNext(); }); }
  var drawObs = new IntersectionObserver(function (es) { es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('drawn'); drawObs.unobserve(e.target); } }); }, { threshold: .05 });
  var issueT;
  var viewObs = new IntersectionObserver(function (es) {
    es.forEach(function (e) {
      if (!e.isIntersecting) return;
      var d = e.target.dataset.d;
      $('#now').textContent = '正在看 · ' + d + ' 週' + e.target.dataset.wd;
      clearTimeout(issueT); issueT = setTimeout(function () { S.store.set('mao_last_issue', d); }, 1500);
    });
  }, { rootMargin: '-40% 0px -55% 0px' });
  var coverObs = new IntersectionObserver(function (es) { $('#tb').classList.toggle('on', !es[0].isIntersecting); }, { threshold: .02 });

  // ---------- 內頁 ----------
  function findCat(n) {
    for (var i = 0; i < S.index.days.length; i++) {
      var k = S.index.days[i].d, p = S.days.get(k);
      if (!p) continue;
      // 已載入的天裡先找
      var hit = p.__v && p.__v.cats.find(function (c) { return c.n === n; });
      if (hit) return Promise.resolve({ c: hit, d: p.__v });
    }
    return all().then(function (m) { var r = m.get(n); if (!r) throw new Error('沒有這隻貓'); return day(r.d).then(function (d) { return { c: d.cats.find(function (c) { return c.n === n; }), d: d }; }); });
  }
  function openPanel(html, after) {
    var p = $('#panel');
    $('#panelBody').innerHTML = html;
    p.hidden = false; p.scrollTop = 0;
    document.documentElement.style.overflow = 'hidden';
    if (after) after();
    $('#close').focus({ preventScroll: true });
  }
  function closePanel() {
    $('#panel').hidden = true; $('#panelBody').innerHTML = '';
    document.documentElement.style.overflow = '';
  }
  function catHtml(c, d) {
    var picks = c.picks || {}, st = picks.art_style || {};
    var news = c.news || [];
    return '<div class="at" style="--acc:' + c.acc + ';--avg:' + c.avg + '">' +
      '<div class="ph" style="--avg:' + c.avg + ';view-transition-name:hero"><img class="in" id="atImg" src="' + esc(c.th) + '" alt="' + esc(c.t) + '"></div>' +
      '<div class="tx">' + kick(c) + '<h1>' + badges(c) + esc(c.t) + '</h1>' +
      '<div class="by">No.' + c.n + ' · ' + d.d + ' · ' + esc(by(c)) + '</div>' +
      (c.story || c.idea ? '<p class="st">' + esc(c.story || c.idea) + '</p>' : '') +
      (news.length ? '<div class="ins"><span class="kick">靈感來自</span>' + esc(news[0]) +
        (news.length > 1 ? '<details><summary>還有 ' + (news.length - 1) + ' 則</summary>' + news.slice(1).map(function (x) { return '<p>' + esc(x) + '</p>'; }).join('') + '</details>' : '') + '</div>' : '') +
      (Object.keys(picks).length ? '<dl class="recipe">' + PICKS.filter(function (p) { return picks[p[0]]; }).map(function (p) {
        var v = picks[p[0]];
        var label = esc(v.en) + (v.zh ? '<small>' + esc(v.zh) + '</small>' : '');
        return '<dt>' + p[1] + '</dt><dd><button type="button" data-same="' + SAME_BY_KEY[p[0]] + '|' + esc(v.en) + '" title="看' + SAME[SAME_BY_KEY[p[0]]][2] + '的貓">' + label + '</button></dd>';
      }).join('') + '</dl>' : '') +
      '<div class="nav"><button class="sv' + (isSaved(c.n) ? ' on' : '') + '" type="button" data-save="' + c.n + '">' + (isSaved(c.n) ? '已在貓窩' : '＋ 收進貓窩') + '</button>' +
      (st.en ? '<button class="ghost" type="button" data-style="' + esc(st.en) + '">同畫風</button>' : '') +
      (c.ch && S.cast[c.ch] ? '<button class="ghost" type="button" data-cast="' + c.ch + '">' + esc(S.cast[c.ch].name) + '的專訪</button>' : '') +
      '<span class="pn"><button type="button" data-step="-1">← 上一隻</button><button type="button" data-step="1">下一隻 →</button></span></div></div></div>';
  }
  function showCat(n, srcEl) {
    return findCat(n).then(function (r) {
      S.lastCat = r;
      var go = function () {
        if (srcEl) srcEl.style.viewTransitionName = '';
        openPanel(catHtml(r.c, r.d), function () {
          var img = $('#atImg'), big = new Image();
          big.onload = function () { img.src = big.src; };
          big.src = r.c.img;
        });
      };
      var im = srcEl && srcEl.querySelector('img');
      if (im && document.startViewTransition && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
        im.style.viewTransitionName = 'hero';
        document.startViewTransition(function () { im.style.viewTransitionName = ''; go(); });
      } else go();
    });
  }
  function step(dir) {
    var r = S.lastCat; if (!r) return;
    var list = r.d.cats, i = list.findIndex(function (c) { return c.n === r.c.n; }) + dir;
    if (i >= 0 && i < list.length) return go(list[i].n);
    var di = S.index.days.findIndex(function (x) { return x.d === r.d.d; }) + dir;
    var row = S.index.days[di]; if (!row) return;
    day(row.d).then(function (d) { var c = dir > 0 ? d.cats[0] : d.cats[d.cats.length - 1]; go(c.n); });
    function go(n) { history.replaceState(null, '', '#cat-' + n); route(); }
  }

  function clock(hours) {
    var mx = Math.max.apply(null, hours) || 1, out = '';
    for (var i = 0; i < 12; i++) {
      var a0 = i / 12 * 2 * Math.PI - Math.PI / 2 - Math.PI / 12, a1 = a0 + 2 * Math.PI / 12, r = 46 + hours[i] / mx * 50;
      out += '<path d="M100 100 L' + (100 + r * Math.cos(a0)).toFixed(1) + ' ' + (100 + r * Math.sin(a0)).toFixed(1) + ' A' + r.toFixed(1) + ' ' + r.toFixed(1) + ' 0 0 1 ' + (100 + r * Math.cos(a1)).toFixed(1) + ' ' + (100 + r * Math.sin(a1)).toFixed(1) + ' Z" fill="' + (hours[i] === mx ? '#111010' : '#ddd7cf') + '" stroke="#fbf9f6" stroke-width="2"/>';
      var am = a0 + Math.PI / 12;
      out += '<text x="' + (100 + 32 * Math.cos(am)).toFixed(1) + '" y="' + (100 + 32 * Math.sin(am) + 5).toFixed(1) + '" text-anchor="middle" font-size="13" fill="' + (hours[i] === mx ? '#fbf9f6' : '#3b3836') + '" font-family="Noto Serif TC">' + SHI[i] + '</text>';
    }
    return '<svg viewBox="0 0 200 200" role="img" aria-label="各時辰出場次數">' + out + '</svg>';
  }
  function showCast(id) {
    var c = S.cast[id]; if (!c) return Promise.reject(new Error('沒有這位角色'));
    markSeen(id);
    return all().then(function (m) {
      var looks = c.recent.map(function (n) { return m.get(n); }).filter(Boolean);
      var hero = looks[0], hours = c.hours, mx = Math.max.apply(null, hours), topShi = SHI[hours.indexOf(mx)];
      var mon = new Date(Date.now() + 8 * 3600e3).getUTCMonth() + 1;
      var cur = mon >= 3 && mon <= 5 ? 'spring' : mon >= 6 && mon <= 8 ? 'summer' : mon >= 9 && mon <= 11 ? 'autumn' : 'winter';
      var last = c.last ? c.last.slice(2).replace(/-/g, '.') : '—';
      openPanel('<div class="iv">' + (hero ? ph(full(hero.th), hero.avg, c.name) : '<div class="ph"></div>') +
        '<div class="tx"><div class="kick">COVER STORY · 角色專訪</div><h1>' + esc(c.name) + '<small>' + esc(c.en) + '</small></h1>' +
        '<div class="stats"><div>出場<b>' + c.count + '</b></div><div>最常出現<b class="zh">' + topShi + '時</b></div><div>最近一次<b>' + last + '</b></div></div>' +
        '<p class="intro">' + esc(c.bio) + '</p>' +
        '<div class="qa"><div><b>最喜歡待在哪？</b><span>' + esc(c.settings.slice(0, 5).join('、')) + '。</span></div><div><b>有什麼小習慣？</b><span>' + esc(c.quirks.join('；')) + '。</span></div>' +
        (c.voice ? '<div><b>說起話來？</b><span>' + esc(c.voice) + '。</span></div>' : '') + '<div><b>個性</b><span>' + esc(c.traits.join('、')) + '。</span></div></div>' +
        '<div class="clock">' + clock(hours) + '<p>' + c.count + ' 次出場裡，' + topShi + '時最多，有 ' + mx + ' 次。每一格是一個時辰，越長代表那個時辰越常被畫出來。</p></div>' +
        '<div><div class="seas" role="group" aria-label="季節">' + SEASONS.map(function (s) { return '<button type="button" data-season="' + s[0] + '" aria-pressed="' + (s[0] === cur) + '">' + s[1] + '</button>'; }).join('') + '</div>' +
        '<p class="seas-tx" id="seasTx">' + esc(c.seasons[cur] || '') + '</p></div>' +
        '<div class="kick" style="border-top:1px solid var(--rule);padding-top:calc(var(--u)*28)">Recent looks · 近期造型</div>' +
        '<div class="grid" style="--cols:4">' + looks.slice(0, 8).map(function (x) { return '<figure data-cat="' + x.n + '">' + ph(x.th, x.avg, x.t) + esc(x.t) + '<small>' + x.d + '</small></figure>'; }).join('') + '</div></div></div>');
      S.castOpen = c;
    });
  }
  function showDen() {
    return all().then(function (m) {
      var list = saved().slice().reverse().map(function (n) { return m.get(n); }).filter(Boolean);
      var since = S.store.get('mao_first_visit'), seen = S.store.get('mao_seen_cast');
      var sinceTx = since ? '從 ' + Number(since.slice(5, 7)) + ' 月 ' + Number(since.slice(8, 10)) + ' 日開始收' : '';
      var tab = S.denTab || 'all';
      var body;
      if (!list.length) body = '<p class="empty">在任何一隻貓的右上角按「＋貓窩」，牠就會住進這裡。</p>';
      else if (tab === 'all') body = grid(list);
      else {
        var key = tab === 'cast' ? 'ch' : 'style', groups = new Map();
        list.forEach(function (x) { var g = x[key] || ''; if (!groups.has(g)) groups.set(g, []); groups.get(g).push(x); });
        body = Array.from(groups.entries()).sort(function (a, b) { return b[1].length - a[1].length; }).map(function (g) {
          var name = tab === 'cast' ? (g[0] && S.cast[g[0]] ? S.cast[g[0]].name : '路過的貓') : (g[0] ? g[0] + (zhOf('art_style', g[0]) ? ' · ' + zhOf('art_style', g[0]) : '') : '其他');
          return '<h2>' + esc(name) + '　<small style="font-family:var(--sans);font-weight:400;color:var(--mute);font-size:.6em">' + g[1].length + ' 隻</small></h2>' + grid(g[1]);
        }).join('');
      }
      openPanel('<div class="pg"><div class="hd"><h1>我的貓窩</h1><span class="kick">愛貓人士的貓窩</span><span>' +
        ['收了 ' + list.length + ' 隻', sinceTx, seen ? '看過 ' + seen.split(',').length + ' 位角色' : ''].filter(Boolean).join(' · ') + '</span>' +
        '<div class="tabs">' + [['all', '全部'], ['cast', '角色'], ['style', '依風格']].map(function (t) { return '<button type="button" data-den-tab="' + t[0] + '" aria-pressed="' + (tab === t[0]) + '">' + t[1] + '</button>'; }).join('') + '</div></div>' +
        (S.store.mode === 'memory' ? '<p class="note">這次的收藏不會保留：這個瀏覽器不讓網頁存資料，例如無痕視窗。</p>' : '') + body + '</div>');
    });
  }
  function grid(list, cols) {
    return '<div class="grid" style="--cols:' + (cols || 6) + '">' + list.map(function (x) {
      return '<figure data-cat="' + x.n + '">' + ph(x.th, x.avg, x.t) + esc(x.t) + '<small>' + [x.d, x.ch && S.cast[x.ch] ? S.cast[x.ch].name : ''].filter(Boolean).join(' · ') + '</small></figure>';
    }).join('') + '</div>';
  }
  function showSame(k, en, limit) {
    var s = SAME[k] || SAME.a;
    return all().then(function (m) {
      var list = Array.from(m.values()).filter(function (x) { return x.picks[s[0]] === en; }).reverse();
      limit = limit || 60;
      openPanel('<div class="pg"><div class="hd"><h1 style="font-family:var(--latin);font-weight:500;letter-spacing:.02em">' + esc(en) + '</h1><span class="kick">' + s[2] + '</span><span>' +
        [zhOf(s[1], en), '一共 ' + list.length + ' 隻'].filter(Boolean).join(' · ') + '</span></div>' +
        grid(list.slice(0, limit)) + (list.length > limit ? '<p style="text-align:center"><button class="btn" type="button" data-same-more="' + k + '|' + esc(en) + '" data-limit="' + (limit + 60) + '">再看 ' + Math.min(60, list.length - limit) + ' 隻</button></p>' : '') + '</div>');
    });
  }

  // ---------- 路由 ----------
  function route() {
    var h = decodeURIComponent(location.hash.slice(1)), job = null;
    if (/^cat-\d+$/.test(h)) job = showCat(Number(h.slice(4)), S.srcEl);
    else if (/^cast-/.test(h)) job = showCast(h.slice(5));
    else if (h === 'den') job = showDen();
    else if (/^style-/.test(h)) job = showSame('a', h.slice(6));
    else if (/^same-[aclpt]-/.test(h)) job = showSame(h[5], h.slice(7));
    S.srcEl = null;
    if (!job) { closePanel(); return; }
    job.catch(function () { toast('這一頁打不開，可能是網路斷了'); });
  }
  function go(hash, srcEl) { S.srcEl = srcEl || null; S.opened = true; location.hash = hash; }

  document.addEventListener('click', function (e) {
    var lb = e.target.closest('#liveBar');
    if (lb) { if (lb.dataset.act === 'reload') location.reload(); else showLive(); return; }
    var t = e.target.closest('[data-save],[data-style],[data-same],[data-cast],[data-cat],[data-go],[data-step],[data-season],[data-den-tab],[data-retry],[data-same-more]');
    if (!t) return;
    var ds = t.dataset;
    if (ds.save) { toggleSave(Number(ds.save)); return; }
    if (ds.sameMore) { var q = ds.sameMore.split('|'); showSame(q[0], q.slice(1).join('|'), Number(ds.limit)); return; }
    if (ds.same) { var q2 = ds.same.split('|'); go('same-' + q2[0] + '-' + encodeURIComponent(q2.slice(1).join('|'))); return; }
    if (ds.style) { go('style-' + encodeURIComponent(ds.style)); return; }
    if (ds.cast) { go('cast-' + ds.cast); return; }
    if (ds.cat) { go('cat-' + ds.cat, t.classList.contains('ph') ? t : t.closest('.ar') && t.closest('.ar').querySelector('.ph')); return; }
    if (ds.step) { step(Number(ds.step)); return; }
    if (ds.season) {
      document.querySelectorAll('[data-season]').forEach(function (b) { b.setAttribute('aria-pressed', b === t); });
      $('#seasTx').textContent = (S.castOpen && S.castOpen.seasons[ds.season]) || ''; return;
    }
    if (ds.denTab) { S.denTab = ds.denTab; showDen(); return; }
    if (ds.retry) { S.failed = false; if (S.index) appendNext(); else location.reload(); return; }
    if (ds.go === 'den') { go('den'); return; }
    if (ds.go === 'exit') { exitToLarch(); return; }
    if (ds.go === 'top') { closeAndClear(); scrollTo({ top: 0, behavior: 'smooth' }); return; }
    if (ds.go === 'feed') { var f = $('#feed .issue:not(.live)') || $('#feed').firstElementChild; if (f) f.scrollIntoView({ behavior: 'smooth' }); return; }
    if (ds.go === 'continue') { renderUntil(S.store.get('mao_last_issue')); return; }
  });
  function closeAndClear() {
    if (!location.hash) return closePanel();
    if (S.opened) history.back(); else { history.replaceState(null, '', location.pathname + location.search); closePanel(); }
  }
  $('#close').addEventListener('click', closeAndClear);
  addEventListener('hashchange', route);
  addEventListener('keydown', function (e) {
    if ($('#panel').hidden) return;
    if (e.key === 'Escape') closeAndClear();
    else if (/^#cat-/.test(location.hash) && (e.key === 'ArrowRight' || e.key === 'ArrowLeft')) step(e.key === 'ArrowRight' ? 1 : -1);
  });
  var tx0 = null;
  $('#panel').addEventListener('touchstart', function (e) { tx0 = e.touches[0].clientX; }, { passive: true });
  $('#panel').addEventListener('touchend', function (e) {
    if (tx0 == null || !/^#cat-/.test(location.hash)) return;
    var dx = e.changedTouches[0].clientX - tx0; tx0 = null;
    if (Math.abs(dx) > 70) step(dx < 0 ? 1 : -1);
  }, { passive: true });

  // ---------- 開始 ----------
  // 記住每一天載入後的內容，findCat 才能不用等網路
  var _day = day;
  day = function (k) { var p = _day(k); p.then(function (v) { p.__v = v; }, function () {}); return p; };

  MaoStore.ready.then(function (store) {
    S.store = store;
    S.prevOpen = store.get('mao_last_open');
    if (!store.get('mao_first_visit')) store.set('mao_first_visit', nowIso().slice(0, 10));
    store.set('mao_last_open', nowIso());
    store.onchange = function () { denCount(false); };
    denCount(false);
    return Promise.all([json(DATA + 'index.json', true), json(DATA + 'cast.json', true).catch(function () { return {}; })]);
  }).then(function (r) {
    S.index = r[0]; S.cast = r[1];
    if (!S.index.days.length) throw new Error('還沒有資料');
    // 本期＝最新一期已經過完的（台北的昨天以前）；今天的貓放在最上面「下一期・製作中」
    S.today = todayKey();
    S.live = S.index.days[0].d === S.today ? S.index.days[0] : null;
    S.rendered = S.live ? 1 : 0;
    var base = S.index.days[S.rendered] || S.index.days[0];
    var p1 = S.index.days[S.rendered + 1] ? day(S.index.days[S.rendered + 1].d).catch(function () { return null; }) : Promise.resolve(null);
    var pl = S.live ? json(DATA + 'days/' + S.live.d + '.json', true).catch(function () { return null; }) : Promise.resolve(null);
    return Promise.all([day(base.d), p1, pl]);
  }).then(function (ds) {
    renderCover(ds[0], ds[1]);
    if (ds[2]) renderIssue(ds[2], true);
    setInterval(pollLive, 5 * 60 * 1000);
    $('#tb').hidden = false;
    if (EMBED) $('#exitBtn').hidden = false;
    coverObs.observe($('#cover'));
    addEventListener('scroll', onScroll, { passive: true }); addEventListener('resize', onScroll); appendNext();
    if (location.hash) route();
  }).catch(function () {
    $('#cvPh').className = 'cv-ph';
    $('#cvSide').innerHTML = '<div class="msg"><b>連不上 catime</b>可能是網路斷了，或 GitHub 暫時沒有回應。<br><button class="btn" type="button" data-retry="all">再試一次</button></div>';
  });
})();
