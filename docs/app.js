(function () {
  const CATLIST_URL = "https://raw.githubusercontent.com/yazelin/catime/main/catlist.json";
  const CATS_BASE_URL = "https://raw.githubusercontent.com/yazelin/catime/main/cats/";
  const LIKES_URL = "likes.json";
  const COMMENT_MAP_URL = "comment_map.json";
  const PAGE_SIZE = 20;

  let allCats = [];
  let filtered = [];
  let loaded = 0;
  let loading = false;
  let selectedDate = ""; // "YYYY-MM-DD" or ""
  let searchQuery = "";
  const detailCache = {}; // month -> detail array
  let likesData = {};    // "catNumber" -> count
  let commentMap = {};   // "catNumber" -> comment URL

  // Lightbox navigation state
  let currentLbIndex = -1;
  let triggerCard = null; // card element that opened lightbox

  // ── Theme toggle ──
  const themeToggle = document.getElementById("theme-toggle");
  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    themeToggle.innerHTML = theme === "dark"
      ? '<svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4" stroke="none"/><path fill="none" d="M12 2v3m0 14v3M4.22 4.22l2.12 2.12m11.32 11.32l2.12 2.12M2 12h3m14 0h3M4.22 19.78l2.12-2.12m11.32-11.32l2.12-2.12"/></svg>'
      : '<svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
    localStorage.setItem("catime-theme", theme);
  }
  // Init: check localStorage, then system preference
  const savedTheme = localStorage.getItem("catime-theme");
  if (savedTheme) {
    applyTheme(savedTheme);
  } else if (window.matchMedia("(prefers-color-scheme: dark)").matches) {
    applyTheme("dark");
  }
  themeToggle.addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme");
    applyTheme(current === "dark" ? "light" : "dark");
  });

  const gallery = document.getElementById("gallery");
  const endMsg = document.getElementById("end-msg");
  const modelSelect = document.getElementById("model-filter");
  const characterSelect = document.getElementById("character-filter");
  const inspirationSelect = document.getElementById("inspiration-filter");
  const searchInput = document.getElementById("search-input");
  const catCount = document.getElementById("cat-count");
  const timelineList = document.getElementById("timeline-list");
  const timelineNav = document.getElementById("timeline");
  const timelineToggle = document.getElementById("timeline-toggle");
  const backToTop = document.getElementById("back-to-top");
  const lightbox = document.getElementById("lightbox");
  const lbImg = document.getElementById("lb-img");
  const lbInfo = document.getElementById("lb-info");
  const lbClose = document.getElementById("lb-close");
  const lbPromptText = document.getElementById("lb-prompt-text");
  const lbCopyBtn = document.getElementById("lb-copy-btn");
  const lbLikeBtn = document.getElementById("lb-like-btn");
  const lbDownloadBtn = document.getElementById("lb-download-btn");
  const lbStory = document.getElementById("lb-story");
  const lbStoryText = document.getElementById("lb-story-text");
  const lbIdea = document.getElementById("lb-idea");
  const lbIdeaText = document.getElementById("lb-idea-text");
  const lbNews = document.getElementById("lb-news");
  const lbNewsList = document.getElementById("lb-news-list");
  const lbAvoid = document.getElementById("lb-avoid");
  const lbAvoidList = document.getElementById("lb-avoid-list");
  const lbTabBar = document.getElementById("lb-tab-bar");
  const lbImgWrap = document.getElementById("lb-img-wrap");
  const lbPrev = document.getElementById("lb-prev");
  const lbNext = document.getElementById("lb-next");
  const lbNavHint = document.getElementById("lb-nav-hint");

  const { clearElement, createSvgElement, setIconLabel } = window.domUtils;
  const SEASON_ICONS = { spring: "🌸", summer: "☀️", autumn: "🍁", winter: "❄️" };

  // Date picker elements
  const datePickerBtn = document.getElementById("date-picker-btn");
  const dateDropdown = document.getElementById("date-dropdown");
  const ddPrev = document.getElementById("dd-prev");
  const ddNext = document.getElementById("dd-next");
  const ddMonthLabel = document.getElementById("dd-month-label");
  const ddDays = document.getElementById("dd-days");
  const ddClear = document.getElementById("dd-clear");

  const SVG_CALENDAR = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>';
  const SVG_CLIPBOARD = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>';
  const SVG_CHECK = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>';
  const SVG_DOWNLOAD = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>';
  const SVG_HEART = '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>';
  let currentCatUrl = "";
  let currentCatNumber = 0;

  let calYear = new Date().getFullYear();
  let calMonth = new Date().getMonth();
  let catDates = new Set();

  function showGalleryError(message) {
    gallery.querySelectorAll(".skeleton-card").forEach(el => el.remove());
    clearElement(gallery);
    const p = document.createElement("p");
    p.style.padding = "2rem";
    p.style.color = "var(--pink)";
    p.textContent = message;
    gallery.appendChild(p);
  }

  function appendWithSpace(parent, el) {
    parent.appendChild(document.createTextNode(" "));
    parent.appendChild(el);
  }

  function normalizeCatlist(data) {
    if (!Array.isArray(data)) throw new Error("Invalid cat list");
    return data.filter(c => (
      c && typeof c === "object" &&
      typeof c.timestamp === "string" &&
      typeof c.number !== "undefined" &&
      typeof c.url === "string"
    ));
  }

  async function fetchCatlist() {
    const resp = await fetch(CATLIST_URL);
    if (!resp.ok) throw new Error("HTTP " + resp.status);
    let data;
    try {
      data = await resp.json();
    } catch {
      throw new Error("Invalid JSON");
    }
    return normalizeCatlist(data);
  }

  // Fetch data
  Promise.all([
    fetchCatlist(),
    fetch(LIKES_URL).then(r => r.ok ? r.json() : {}).catch(() => ({})),
    fetch(COMMENT_MAP_URL).then(r => r.ok ? r.json() : {}).catch(() => ({})),
  ])
    .then(([data, likes, comments]) => {
      likesData = (likes && typeof likes === "object" && !Array.isArray(likes)) ? likes : {};
      commentMap = (comments && typeof comments === "object" && !Array.isArray(comments)) ? comments : {};
      allCats = data.filter(c => c.status !== "failed").reverse();
      allCats.forEach(c => catDates.add(c.timestamp.split(" ")[0]));
      populateModels();
      populateCharacters();
      buildTimeline();
      // Init calendar to latest cat's month
      if (allCats.length) {
        const parts = allCats[0].timestamp.split(" ")[0].split("-");
        calYear = parseInt(parts[0], 10);
        calMonth = parseInt(parts[1], 10) - 1;
      }
      gallery.querySelectorAll(".skeleton-card").forEach(el => el.remove());
      applyFilter();
    })
    .catch(err => {
      showGalleryError("載入貓咪列表失敗，請稍後重試");
    });

  function populateModels() {
    const models = [...new Set(allCats.map(c => c.model).filter(Boolean))].sort();
    models.forEach(m => {
      const opt = document.createElement("option");
      opt.value = m; opt.textContent = m;
      modelSelect.appendChild(opt);
    });
  }

  function populateCharacters() {
    const chars = [...new Set(allCats.map(c => c.character_name).filter(Boolean))].sort();
    chars.forEach(name => {
      const opt = document.createElement("option");
      opt.value = name; opt.textContent = name;
      characterSelect.appendChild(opt);
    });
  }

  function buildTimeline() {
    const map = {};
    allCats.forEach(c => {
      if (typeof c.timestamp !== "string") return;
      const [date] = c.timestamp.split(" ");
      if (!date) return;
      const [y, m] = date.split("-");
      if (!y || !m) return;
      if (!map[y]) map[y] = new Set();
      map[y].add(m);
    });
    clearElement(timelineList);
    const frag = document.createDocumentFragment();
    Object.keys(map).sort().reverse().forEach(y => {
      const year = document.createElement("div");
      year.className = "year";
      year.textContent = y;
      frag.appendChild(year);
      [...map[y]].sort().reverse().forEach(m => {
        const link = document.createElement("a");
        link.href = "#";
        link.dataset.ym = `${y}-${m}`;
        link.textContent = `${y}-${m}`;
        frag.appendChild(link);
      });
    });
    timelineList.appendChild(frag);
  }

  function updateCatCount() {
    catCount.textContent = filtered.length + " cats";
  }

  // ── Search with debounce ──
  let searchTimer = null;
  searchInput.addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      searchQuery = searchInput.value.trim().toLowerCase();
      applyFilter();
    }, 300);
  });

  // ── Date picker ──
  datePickerBtn.addEventListener("click", e => {
    e.stopPropagation();
    dateDropdown.classList.toggle("hidden");
    if (!dateDropdown.classList.contains("hidden")) renderCalendar();
  });
  document.addEventListener("click", e => {
    if (!dateDropdown.classList.contains("hidden") && !document.getElementById("date-picker").contains(e.target)) {
      dateDropdown.classList.add("hidden");
    }
  });
  ddPrev.addEventListener("click", () => { calMonth--; if (calMonth < 0) { calMonth = 11; calYear--; } renderCalendar(); });
  ddNext.addEventListener("click", () => { calMonth++; if (calMonth > 11) { calMonth = 0; calYear++; } renderCalendar(); });
  ddClear.addEventListener("click", () => {
    selectedDate = "";
    setIconLabel(datePickerBtn, SVG_CALENDAR, "All Dates");
    datePickerBtn.classList.remove("active");
    dateDropdown.classList.add("hidden");
    applyFilter();
  });

  function renderCalendar() {
    const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
    ddMonthLabel.textContent = `${months[calMonth]} ${calYear}`;
    const first = new Date(calYear, calMonth, 1);
    const startDay = first.getDay();
    const daysInMonth = new Date(calYear, calMonth + 1, 0).getDate();
    const todayStr = new Date().toISOString().slice(0, 10);

    clearElement(ddDays);
    for (let i = 0; i < startDay; i++) {
      const placeholder = document.createElement("button");
      placeholder.className = "other-month";
      placeholder.disabled = true;
      ddDays.appendChild(placeholder);
    }
    for (let d = 1; d <= daysInMonth; d++) {
      const ds = `${calYear}-${String(calMonth + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
      const cls = [];
      if (ds === todayStr) cls.push("today");
      if (ds === selectedDate) cls.push("selected");
      if (catDates.has(ds)) cls.push("has-cat");
      const btn = document.createElement("button");
      btn.dataset.date = ds;
      if (cls.length) btn.className = cls.join(" ");
      btn.textContent = d;
      ddDays.appendChild(btn);
    }
  }

  ddDays.addEventListener("click", e => {
    const date = e.target.dataset.date;
    if (!date) return;
    selectedDate = date;
    setIconLabel(datePickerBtn, SVG_CALENDAR, date);
    datePickerBtn.classList.add("active");
    dateDropdown.classList.add("hidden");
    applyFilter();
  });

  // ── Filter ──
  function applyFilter() {
    const model = modelSelect.value;
    const charFilter = characterSelect.value;
    filtered = allCats.filter(c => {
      if (model && c.model !== model) return false;
      if (charFilter && c.character_name !== charFilter) return false;
      const inspFilter = inspirationSelect.value;
      if (inspFilter === "original" && c.inspiration !== "original") return false;
      if (inspFilter === "news" && (!c.inspiration || c.inspiration === "original")) return false;
      if (selectedDate && !c.timestamp.startsWith(selectedDate)) return false;
      if (searchQuery) {
        const numStr = String(c.number);
        const title = (c.title || "").toLowerCase();
        if (!numStr.includes(searchQuery) && !title.includes(searchQuery)) return false;
      }
      return true;
    });
    loaded = 0;
    gallery.querySelectorAll(".skeleton-card").forEach(el => el.remove());
    clearElement(gallery);
    endMsg.classList.add("loading");
    endMsg.classList.remove("hidden");
    updateCatCount();
    loadMore();
  }

  modelSelect.addEventListener("change", applyFilter);
  characterSelect.addEventListener("change", applyFilter);
  inspirationSelect.addEventListener("change", applyFilter);

  // ── Image error handler ──
  function handleImgError(img, isLightbox) {
    if (isLightbox) {
      const placeholder = document.createElement("div");
      placeholder.className = "lb-img-error";
      placeholder.textContent = "🐱";
      img.replaceWith(placeholder);
    } else {
      const placeholder = document.createElement("div");
      placeholder.className = "img-error";
      placeholder.textContent = "🐱";
      img.replaceWith(placeholder);
    }
  }

  // ── Render cards ──
  function loadMore() {
    if (loading || loaded >= filtered.length) return;
    loading = true;
    const slice = filtered.slice(loaded, loaded + PAGE_SIZE);
    let lastMonth = "";
    if (loaded > 0) {
      const prev = filtered[loaded - 1];
      lastMonth = prev.timestamp.slice(0, 7);
    }
    const frag = document.createDocumentFragment();
    slice.forEach((cat, i) => {
      const month = cat.timestamp.slice(0, 7);
      if (month !== lastMonth) {
        const sep = document.createElement("div");
        sep.className = "month-sep";
        sep.id = `m-${month}`;
        sep.textContent = month;
        frag.appendChild(sep);
        lastMonth = month;
      }
      const card = document.createElement("div");
      card.className = "card";
      card.dataset.catIndex = loaded + i;
      card.setAttribute("role", "button");
      card.setAttribute("tabindex", "0");
      card.setAttribute("aria-label", "Cat #" + cat.number + (cat.title ? " " + cat.title : "") + " — click to view details");
      const likeCount = likesData[String(cat.number)] || 0;
      const timestamp = typeof cat.timestamp === "string" ? cat.timestamp : "";
      const title = typeof cat.title === "string" ? cat.title : "";
      const characterName = typeof cat.character_name === "string" ? cat.character_name : "";
      const characterId = typeof cat.character === "string" ? cat.character : "";
      const modelName = typeof cat.model === "string" ? cat.model : "";
      const inspiration = typeof cat.inspiration === "string" ? cat.inspiration : "";

      const cardImgWrap = document.createElement("div");
      cardImgWrap.className = "card-img-wrap";
      const img = document.createElement("img");
      img.src = cat.url;
      img.alt = `Cat #${cat.number}`;
      img.loading = "lazy";
      cardImgWrap.appendChild(img);
      if (likeCount > 0) {
        const likeBadge = document.createElement("span");
        likeBadge.className = "like-badge";
        const icon = createSvgElement(SVG_HEART);
        if (icon) likeBadge.appendChild(icon);
        likeBadge.appendChild(document.createTextNode(" " + likeCount));
        cardImgWrap.appendChild(likeBadge);
      }

      const cardInfo = document.createElement("div");
      cardInfo.className = "card-info";
      const time = document.createElement("div");
      time.className = "time";
      time.textContent = `#${cat.number} ${title ? title + " · " : ""}${timestamp}`;
      cardInfo.appendChild(time);
      if (characterName) {
        const charTag = document.createElement("span");
        charTag.className = "character-tag" + (cat.is_seasonal ? " seasonal" : "");
        if (characterId) {
          const charAvatar = document.createElement("img");
          charAvatar.src = "avatars/" + characterId + ".webp";
          charAvatar.alt = characterName;
          charAvatar.width = 16;
          charAvatar.height = 16;
          charAvatar.className = "char-tag-avatar";
          charAvatar.loading = "lazy";
          charTag.appendChild(charAvatar);
        }
        let tagText = characterName;
        if (cat.season && SEASON_ICONS[cat.season]) {
          tagText += " · " + SEASON_ICONS[cat.season];
        }
        charTag.appendChild(document.createTextNode(tagText));
        cardInfo.appendChild(charTag);
      }
      if (inspiration) {
        const isNews = inspiration !== "original";
        const inspirationTag = document.createElement("span");
        inspirationTag.className = `inspiration-tag ${isNews ? "news" : "original"}`;
        inspirationTag.textContent = isNews ? "新聞靈感" : "原創";
        cardInfo.appendChild(inspirationTag);
      }
      if (modelName) {
        const modelTag = document.createElement("span");
        modelTag.className = "model";
        modelTag.textContent = modelName;
        cardInfo.appendChild(modelTag);
      }
      card.appendChild(cardImgWrap);
      card.appendChild(cardInfo);
      // Image error handling
      img.addEventListener("error", () => handleImgError(img, false));
      card.addEventListener("click", () => {
        triggerCard = card;
        openLightbox(cat, loaded - slice.length + i + (frag.contains(card) ? 0 : 0));
      });
      card.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          triggerCard = card;
          openLightbox(cat, loaded - slice.length + i + (frag.contains(card) ? 0 : 0));
        }
      });
      frag.appendChild(card);
    });
    gallery.appendChild(frag);
    loaded += slice.length;
    loading = false;
    if (loaded >= filtered.length) {
      endMsg.classList.remove("loading");
    }
  }

  // ── Infinite scroll ──
  const observer = new IntersectionObserver(entries => {
    if (entries[0].isIntersecting) loadMore();
  }, { rootMargin: "400px" });
  observer.observe(endMsg);

  // ── Timeline click ──
  timelineList.addEventListener("click", e => {
    e.preventDefault();
    const ym = e.target.dataset.ym;
    if (!ym) return;
    const idx = filtered.findIndex(c => c.timestamp.startsWith(ym));
    if (idx === -1) return;
    while (loaded <= idx && loaded < filtered.length) loadMore();
    const el = document.getElementById(`m-${ym}`);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
    if (window.innerWidth <= 1024) timelineNav.classList.remove("open");
  });

  timelineToggle.addEventListener("click", () => timelineNav.classList.toggle("open"));

  // ── Back to top ──
  window.addEventListener("scroll", () => {
    backToTop.classList.toggle("visible", window.scrollY > 600);
  }, { passive: true });
  backToTop.addEventListener("click", () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  });

  // ── Lightbox ──
  const TAB_DEFS = [
    { key: "story", label: "Story", panel: lbStory },
    { key: "idea", label: "Idea", panel: lbIdea },
    { key: "news", label: "News", panel: lbNews },
    { key: "avoid", label: "Constraints", panel: lbAvoid },
  ];

  function switchTab(key) {
    TAB_DEFS.forEach(t => {
      t.panel.classList.add("hidden");
    });
    lbTabBar.querySelectorAll("button").forEach(b => {
      b.classList.toggle("active", b.dataset.tab === key);
    });
    const def = TAB_DEFS.find(t => t.key === key);
    if (def) def.panel.classList.remove("hidden");
  }

  async function fetchDetail(cat) {
    const month = cat.timestamp.slice(0, 7);
    if (!detailCache[month]) {
      try {
        const resp = await fetch(CATS_BASE_URL + month + ".json");
        if (resp.ok) {
          detailCache[month] = await resp.json();
        } else {
          detailCache[month] = [];
        }
      } catch {
        detailCache[month] = [];
      }
    }
    return detailCache[month].find(d => d.number === cat.number) || {};
  }

  function populateLightboxDetail(cat, detail) {
    lbPromptText.textContent = detail.prompt || "";
    setIconLabel(lbCopyBtn, SVG_CLIPBOARD, "Copy Prompt");

    lbStoryText.textContent = detail.story || "";
    const inspirationText = detail.inspiration && detail.inspiration !== "original"
      ? `\n\n靈感來源：${detail.inspiration}`
      : "";
    lbIdeaText.textContent = (detail.idea || "") + inspirationText;
    clearElement(lbNewsList);
    clearElement(lbAvoidList);
    if (Array.isArray(detail.news_inspiration) && detail.news_inspiration.length) {
      detail.news_inspiration.forEach(t => {
        const tag = document.createElement("span");
        tag.className = "news-tag";
        tag.textContent = t;
        lbNewsList.appendChild(tag);
      });
    }
    if (Array.isArray(detail.avoid_list) && detail.avoid_list.length) {
      detail.avoid_list.forEach(t => {
        const tag = document.createElement("span");
        tag.className = "avoid-tag";
        tag.textContent = t;
        lbAvoidList.appendChild(tag);
      });
    }

    const available = [];
    if (detail.story) available.push("story");
    if (detail.idea) available.push("idea");
    if (detail.news_inspiration && detail.news_inspiration.length) available.push("news");
    if (detail.avoid_list && detail.avoid_list.length) available.push("avoid");

    clearElement(lbTabBar);
    TAB_DEFS.forEach(t => t.panel.classList.add("hidden"));
    available.forEach(key => {
      const def = TAB_DEFS.find(t => t.key === key);
      const btn = document.createElement("button");
      btn.dataset.tab = key;
      btn.textContent = def.label;
      lbTabBar.appendChild(btn);
    });

    if (available.length) switchTab(available[0]);
  }

  function openLightbox(cat, index) {
    // Find index in filtered array
    if (typeof index === "number" && index >= 0) {
      currentLbIndex = filtered.indexOf(cat);
    } else {
      currentLbIndex = filtered.indexOf(cat);
    }
    if (currentLbIndex === -1) currentLbIndex = filtered.findIndex(c => c.number === cat.number);

    currentCatUrl = cat.url;
    currentCatNumber = cat.number;

    // Restore img element if it was replaced by error placeholder
    const existingError = lbImgWrap.querySelector(".lb-img-error");
    if (existingError) {
      const newImg = document.createElement("img");
      newImg.id = "lb-img";
      newImg.alt = "Cat";
      existingError.replaceWith(newImg);
    }
    const imgEl = document.getElementById("lb-img") || lbImg;
    imgEl.src = cat.url;
    imgEl.addEventListener("error", function onErr() {
      handleImgError(imgEl, true);
      imgEl.removeEventListener("error", onErr);
    });

    const titleText = typeof cat.title === "string" ? ` ${cat.title}` : "";
    const timestamp = typeof cat.timestamp === "string" ? cat.timestamp : "";
    const characterName = typeof cat.character_name === "string" ? cat.character_name : "";
    const characterId = typeof cat.character === "string" ? cat.character : "";
    const modelName = typeof cat.model === "string" ? cat.model : "";
    const inspiration = typeof cat.inspiration === "string" ? cat.inspiration : "";
    clearElement(lbInfo);
    const title = document.createElement("span");
    title.className = "lb-title";
    title.textContent = `#${cat.number}${titleText} · ${timestamp}`;
    lbInfo.appendChild(title);
    if (characterName) {
      const charTag = document.createElement("span");
      charTag.className = "character-tag" + (cat.is_seasonal ? " seasonal" : "");
      if (characterId) {
        const charAvatar = document.createElement("img");
        charAvatar.src = "avatars/" + characterId + ".webp";
        charAvatar.alt = characterName;
        charAvatar.width = 16;
        charAvatar.height = 16;
        charAvatar.className = "char-tag-avatar";
        charAvatar.loading = "lazy";
        charTag.appendChild(charAvatar);
      }
      let tagText = characterName;
      if (cat.season && SEASON_ICONS[cat.season]) {
        tagText += " · " + SEASON_ICONS[cat.season];
      }
      charTag.appendChild(document.createTextNode(tagText));
      appendWithSpace(lbInfo, charTag);
    }
    if (inspiration) {
      const isNews = inspiration !== "original";
      const inspirationTag = document.createElement("span");
      inspirationTag.className = `inspiration-tag ${isNews ? "news" : "original"}`;
      inspirationTag.textContent = isNews ? "新聞靈感" : "原創";
      appendWithSpace(lbInfo, inspirationTag);
    }
    if (modelName) {
      const modelTag = document.createElement("span");
      modelTag.className = "lb-model-tag";
      modelTag.textContent = modelName;
      appendWithSpace(lbInfo, modelTag);
    }
    setIconLabel(lbDownloadBtn, SVG_DOWNLOAD, "Download");
    lbDownloadBtn.dataset.label = "Download";

    const catKey = String(cat.number);
    const likeCount = likesData[catKey] || 0;
    const commentUrl = commentMap[catKey];
    setIconLabel(lbLikeBtn, SVG_HEART, likeCount > 0 ? String(likeCount) : "");
    lbLikeBtn.style.display = commentUrl ? "" : "none";
    lbLikeBtn.onclick = () => { if (commentUrl) window.open(commentUrl, "_blank"); };

    lbPromptText.textContent = "Loading\u2026";
    setIconLabel(lbCopyBtn, SVG_CLIPBOARD, "Copy Prompt");
    clearElement(lbTabBar);
    TAB_DEFS.forEach(t => t.panel.classList.add("hidden"));

    lightbox.classList.remove("hidden");
    document.body.style.overflow = "hidden";

    // Update nav button state
    updateNavButtons();

    // Show hint, fade after 2s
    lbNavHint.classList.remove("fade-out");
    clearTimeout(lbNavHint._timer);
    lbNavHint._timer = setTimeout(() => lbNavHint.classList.add("fade-out"), 2000);

    // Focus close button (don't use focus to avoid outline)
    lbClose.focus();

    fetchDetail(cat).then(detail => populateLightboxDetail(cat, detail));
  }

  function updateNavButtons() {
    lbPrev.classList.toggle("disabled", currentLbIndex <= 0);
    lbNext.classList.toggle("disabled", currentLbIndex >= filtered.length - 1);
  }

  lbPrev.addEventListener("click", (e) => { e.stopPropagation(); navigateLightbox(-1); });
  lbNext.addEventListener("click", (e) => { e.stopPropagation(); navigateLightbox(1); });

  function closeLightbox() {
    lightbox.classList.add("hidden");
    document.body.style.overflow = "";
    // Return focus to trigger card
    if (triggerCard) {
      triggerCard.focus();
      triggerCard = null;
    }
  }

  function navigateLightbox(dir) {
    if (currentLbIndex === -1) return;
    const newIdx = currentLbIndex + dir;
    if (newIdx < 0 || newIdx >= filtered.length) return;
    // Ensure cards are loaded up to this point
    while (loaded <= newIdx && loaded < filtered.length) loadMore();
    openLightbox(filtered[newIdx], newIdx);
  }

  lbTabBar.addEventListener("click", e => {
    if (e.target.dataset.tab) switchTab(e.target.dataset.tab);
  });
  lbCopyBtn.addEventListener("click", () => {
    navigator.clipboard.writeText(lbPromptText.textContent).then(() => {
      setIconLabel(lbCopyBtn, SVG_CHECK, "Copied!");
      setTimeout(() => { setIconLabel(lbCopyBtn, SVG_CLIPBOARD, "Copy Prompt"); }, 1500);
    });
  });
  lbDownloadBtn.addEventListener("click", async () => {
    if (!currentCatUrl) return;
    const origLabel = lbDownloadBtn.dataset.label || "Download";
    setIconLabel(lbDownloadBtn, SVG_DOWNLOAD, "Downloading\u2026");
    lbDownloadBtn.disabled = true;
    try {
      const resp = await fetch(currentCatUrl);
      if (!resp.ok) throw new Error("HTTP " + resp.status);
      const blob = await resp.blob();
      const blobUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = "catime-cat-" + currentCatNumber + ".png";
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(blobUrl), 1000);
    } catch {
      // Fallback: open in new tab
      window.open(currentCatUrl, "_blank");
    } finally {
      setIconLabel(lbDownloadBtn, SVG_DOWNLOAD, origLabel);
      lbDownloadBtn.dataset.label = origLabel;
      lbDownloadBtn.disabled = false;
    }
  });
  lbClose.addEventListener("click", closeLightbox);
  lightbox.addEventListener("click", e => { if (e.target === lightbox) closeLightbox(); });

  // ── Keyboard: Escape, Arrow keys, Focus trap ──
  document.addEventListener("keydown", e => {
    if (lightbox.classList.contains("hidden")) return;

    if (e.key === "Escape") { closeLightbox(); return; }
    if (e.key === "ArrowLeft") { navigateLightbox(-1); return; }
    if (e.key === "ArrowRight") { navigateLightbox(1); return; }

    // Focus trap
    if (e.key === "Tab") {
      const focusable = lightbox.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
      const items = Array.from(focusable).filter(el => !el.closest('.hidden') && el.offsetParent !== null);
      if (!items.length) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (e.shiftKey) {
        if (document.activeElement === first) { e.preventDefault(); last.focus(); }
      } else {
        if (document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    }
  });

  // ── Random cat button ──
  const randomCatBtn = document.getElementById("random-cat-btn");
  function openRandomCat() {
    const pool = filtered.length ? filtered : allCats;
    if (!pool.length) return;
    const idx = Math.floor(Math.random() * pool.length);
    while (loaded <= idx && loaded < filtered.length) loadMore();
    openLightbox(pool[idx], idx);
  }
  randomCatBtn.addEventListener("click", () => {
    randomCatBtn.classList.add("bounce");
    randomCatBtn.addEventListener("animationend", () => randomCatBtn.classList.remove("bounce"), { once: true });
    openRandomCat();
  });

  // ── Lightbox touch swipe ──
  let touchStartX = 0;
  let touchStartY = 0;
  lightbox.addEventListener("touchstart", e => {
    touchStartX = e.changedTouches[0].clientX;
    touchStartY = e.changedTouches[0].clientY;
  }, { passive: true });
  lightbox.addEventListener("touchend", e => {
    const dx = e.changedTouches[0].clientX - touchStartX;
    const dy = e.changedTouches[0].clientY - touchStartY;
    // Only trigger if horizontal swipe is dominant
    if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy)) {
      if (dx < 0) navigateLightbox(1);  // swipe left = next
      else navigateLightbox(-1);          // swipe right = prev
    }
  }, { passive: true });

})();
