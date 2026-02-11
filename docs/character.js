(function () {
  'use strict';

  var params = new URLSearchParams(window.location.search);
  var charId = params.get('id');
  if (!charId) {
    document.getElementById('character-profile').innerHTML = '<p style="padding:2rem;text-align:center">No character id specified. <a href="index.html">Back to gallery</a></p>';
    return;
  }

  var charUrl = 'https://raw.githubusercontent.com/yazelin/catime/main/characters/' + encodeURIComponent(charId) + '.json';
  var catlistUrl = 'https://raw.githubusercontent.com/yazelin/catime/main/catlist.json';

  Promise.all([
    fetch(charUrl).then(function (r) { if (!r.ok) throw new Error('Character not found'); return r.json(); }),
    fetch(catlistUrl).then(function (r) { return r.ok ? r.json() : []; })
  ]).then(function (results) {
    var char = results[0];
    var catlist = results[1];
    renderProfile(char);
    renderGallery(char, catlist);
  }).catch(function (err) {
    document.getElementById('character-profile').innerHTML =
      '<p style="padding:2rem;text-align:center">Failed to load character: ' + err.message + '. <a href="index.html">Back</a></p>';
  });

  function renderProfile(c) {
    document.title = (c.name.en || c.id) + ' - Catime Character';

    document.getElementById('char-name').textContent = c.name.zh + ' / ' + c.name.en;

    // Personality
    var perEl = document.getElementById('char-personality');
    var traits = (c.personality && c.personality.traits) || [];
    var quirks = (c.personality && c.personality.quirks) || [];
    perEl.innerHTML = '<h4>🐾 Personality</h4>' +
      (traits.length ? '<p class="tag-list">' + traits.map(tag).join('') + '</p>' : '') +
      (quirks.length ? '<p class="char-quirks">' + quirks.join(' · ') + '</p>' : '');

    // Appearance distinctive_features
    var features = (c.appearance && c.appearance.distinctive_features) || [];
    var appEl = document.getElementById('char-appearance');
    appEl.innerHTML = '<h4>✨ Distinctive Features</h4>' +
      (features.length ? '<ul>' + features.map(function (f) { return '<li>' + esc(f) + '</li>'; }).join('') + '</ul>' : '<p>—</p>');

    // Story context
    var storyEl = document.getElementById('char-story');
    storyEl.innerHTML = '<h4>📖 Story</h4><p>' + esc(c.story_context || '—') + '</p>';

    // Preferred settings
    var settings = c.preferred_settings || [];
    var setEl = document.getElementById('char-settings');
    setEl.innerHTML = '<h4>📍 Preferred Settings</h4>' +
      (settings.length ? '<p class="tag-list">' + settings.map(tag).join('') + '</p>' : '<p>—</p>');

    // Seasonal variants
    var seasons = c.seasonal_variants || {};
    var seasonLabels = { spring: '🌸 Spring', summer: '☀️ Summer', autumn: '🍂 Autumn', winter: '❄️ Winter' };
    var seasEl = document.getElementById('char-seasons');
    var html = '<h4>🗓️ Seasonal Variants</h4><div class="season-list">';
    Object.keys(seasonLabels).forEach(function (k) {
      if (seasons[k]) html += '<div class="season-item"><strong>' + seasonLabels[k] + '</strong><span>' + esc(seasons[k]) + '</span></div>';
    });
    html += '</div>';
    seasEl.innerHTML = html;
  }

  function renderGallery(c, catlist) {
    var container = document.getElementById('char-gallery');
    var emptyMsg = document.getElementById('gallery-empty');

    // Filter: entries with character field matching this character id
    var matched = catlist.filter(function (e) { return e.character === c.id; });

    // Fallback: also check url/filename for character id
    if (matched.length === 0) {
      matched = catlist.filter(function (e) {
        var url = (e.url || '').toLowerCase();
        return url.indexOf(c.id) !== -1;
      });
    }

    if (matched.length === 0) {
      emptyMsg.classList.remove('hidden');
      return;
    }

    // Sort by number descending
    matched.sort(function (a, b) { return (b.number || 0) - (a.number || 0); });

    matched.forEach(function (entry) {
      var card = document.createElement('div');
      card.className = 'gallery-item';

      var img = document.createElement('img');
      img.src = entry.url || '';
      img.alt = entry.title || ('Cat #' + (entry.number || ''));
      img.loading = 'lazy';
      img.onerror = function () { this.parentNode.innerHTML = '<div class="img-error">🐱</div>'; };

      var info = document.createElement('div');
      info.className = 'gallery-item-info';
      info.innerHTML = '<span class="gallery-number">#' + (entry.number || '?') + '</span>' +
        (entry.title ? ' <span class="gallery-title">' + esc(entry.title) + '</span>' : '');

      card.appendChild(img);
      card.appendChild(info);
      container.appendChild(card);
    });
  }

  function esc(s) { var d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
  function tag(t) { return '<span class="char-tag">' + esc(t) + '</span>'; }
})();
