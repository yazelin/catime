// 卯時的使用者記錄（貓窩）。
// 網址帶 ?embed=larch：存 Larch 變數（外殼卡轉接 postMessage）。
// 直接打開：存 localStorage 的 maoshi:v1。
// 兩種都不行：只記在這次打開的頁面裡，mode 是 'memory'。
(function () {
  var KEYS = ['mao_last_open', 'mao_last_issue', 'mao_saved', 'mao_seen_cast', 'mao_first_visit'];
  var LS_KEY = 'maoshi:v1';
  var data = {}; KEYS.forEach(function (k) { data[k] = ''; });
  var embedded = new URLSearchParams(location.search).get('embed') === 'larch';
  var store = { mode: 'memory', keys: KEYS, onchange: null };
  var saveLocal = function () {};

  store.get = function (k) { return data[k] || ''; };
  store.set = function (k, v) {
    if (KEYS.indexOf(k) < 0) return;
    data[k] = String(v);
    if (store.mode === 'larch') parent.postMessage({ type: 'maoshi:save', name: k, value: data[k] }, '*');
    else if (store.mode === 'local') saveLocal();
  };

  store.ready = new Promise(function (resolve) {
    if (embedded) {
      // 外殼卡收到 Larch 的 larch:init 後回 maoshi:init；讀檔時會再送一次，以新的為準
      var done = false;
      addEventListener('message', function (e) {
        var d = e.data;
        if (e.source !== parent || !d || d.type !== 'maoshi:init') return;
        var v = d.variables || {};
        KEYS.forEach(function (k) { data[k] = v[k] == null ? '' : String(v[k]); });
        store.mode = 'larch';
        if (!done) { done = true; resolve(store); } else if (store.onchange) store.onchange();
      });
      parent.postMessage({ type: 'maoshi:hello' }, '*');
      setTimeout(function () { if (!done) { done = true; resolve(store); } }, 3000); // ponytail: 外殼沒回應就退回 memory
      return;
    }
    try {
      var raw = localStorage.getItem(LS_KEY);
      var saved = raw ? JSON.parse(raw) : {};
      KEYS.forEach(function (k) { if (saved[k] != null) data[k] = String(saved[k]); });
      saveLocal = function () { try { localStorage.setItem(LS_KEY, JSON.stringify(data)); } catch (_) {} };
      localStorage.setItem(LS_KEY, JSON.stringify(data));
      store.mode = 'local';
    } catch (_) { store.mode = 'memory'; }
    resolve(store);
  });
  window.MaoStore = store;
})();
