(function(){
  /* ── Utilities ── */

  var rIC = window.requestIdleCallback || function(cb) { setTimeout(cb, 1); };

  function debounce(fn, ms) {
    var timer;
    return function() {
      var args = arguments;
      var ctx = this;
      clearTimeout(timer);
      timer = setTimeout(function() { fn.apply(ctx, args); }, ms);
    };
  }

  /* ── State ── */

  var currentView = "grid";
  var clipsData = [];
  var currentVideoUrl = "";
  var ws = null;
  var wsRegions = null;
  var wsRegionEntries = [];
  var musicLibrary = [];
  var currentWatermarkUrl = "";
  var currentSort = "score";
  var activeClipIndex = -1;
  var selectedClips = {};
  var onboardingStorageKey = "sneaclip-onboarding-dismissed";

  /* ── Global Drag-Drop State ── */
  var dragCounter = 0;
  var globalDropOverlay = null;

  /* ── Toast Notifications ── */

  var toastQueue = [];
  var MAX_TOASTS = 5;

  var toastIcons = {
    info: "ℹ",
    success: "✓",
    warning: "⚠",
    error: "✕"
  };

  function toast(msg, type, action) {
    type = type || "info";
    var c = document.getElementById("toast-container");
    if (!c) return;

    // Stack limit enforcement
    if (c.children.length >= MAX_TOASTS) {
      var oldest = c.children[0];
      if (oldest) {
        oldest.classList.remove("enter");
        oldest.classList.add("exit");
        setTimeout(function() { if (oldest.parentNode) oldest.remove(); }, 250);
      }
    }

    var t = document.createElement("div");
    t.className = "toast " + type;
    t.setAttribute("role", "alert");
    t.setAttribute("aria-live", "polite");

    var icon = toastIcons[type] || toastIcons.info;
    var title = type.charAt(0).toUpperCase() + type.slice(1);

    t.innerHTML =
      '<div class="toast-content">' +
        '<div class="toast-icon">' + icon + '</div>' +
        '<div class="toast-body">' +
          '<div class="toast-title">' + title + '</div>' +
          '<div class="toast-message">' + msg + '</div>' +
        '</div>' +
        '<button class="toast-close" aria-label="Close notification">×</button>' +
      '</div>';

    if (action) {
      var actionsDiv = document.createElement("div");
      actionsDiv.className = "toast-actions";
      actionsDiv.innerHTML = '<button class="toast-action">' + action.label + '</button>';
      actionsDiv.querySelector(".toast-action").addEventListener("click", function() {
        if (action.callback) action.callback();
        dismissToast(t);
      });
      t.appendChild(actionsDiv);
    }

    var progressDiv = document.createElement("div");
    progressDiv.className = "toast-progress";
    progressDiv.innerHTML = '<div class="toast-progress-bar"></div>';
    t.appendChild(progressDiv);

    var closeBtn = t.querySelector(".toast-close");
    closeBtn.addEventListener("click", function() { dismissToast(t); });

    var progressBar = progressDiv.querySelector(".toast-progress-bar");
    var startTime = Date.now();
    var duration = 3000;
    var pausedAt = null;
    var remaining = duration;

    function animateProgress() {
      if (pausedAt) return;
      var elapsed = Date.now() - startTime;
      var progress = Math.min(elapsed / remaining, 1);
      progressBar.style.transform = "scaleX(" + (1 - progress) + ")";
      if (progress < 1) {
        requestAnimationFrame(animateProgress);
      }
    }

    t.addEventListener("mouseenter", function() {
      pausedAt = Date.now();
      remaining = remaining - (pausedAt - startTime);
      t.classList.add("paused");
    });

    t.addEventListener("mouseleave", function() {
      if (pausedAt) {
        startTime = Date.now() - (duration - remaining);
        pausedAt = null;
        t.classList.remove("paused");
        requestAnimationFrame(animateProgress);
      }
    });

    c.appendChild(t);
    requestAnimationFrame(function() { t.classList.add("enter"); });

    setTimeout(function() { requestAnimationFrame(animateProgress); }, 50);

    t._dismissTimer = setTimeout(function() { dismissToast(t); }, remaining + 300);
  }

  function dismissToast(t) {
    if (!t || !t.parentNode) return;
    clearTimeout(t._dismissTimer);
    t.classList.remove("enter");
    t.classList.add("exit");
    setTimeout(function() { if (t.parentNode) t.remove(); }, 250);
  }

  /* ── Page Navigation ── */

  function showPage(id) {
    document.querySelectorAll(".page").forEach(function(p) { p.classList.remove("active"); });
    var page = document.getElementById(id);
    if (page) page.classList.add("active");
    document.querySelectorAll(".nav-link").forEach(function(link) {
      var isCurrent = link.dataset.page === id;
      if (isCurrent) {
        link.classList.add("active");
        link.setAttribute("aria-current", "page");
      } else {
        link.classList.remove("active");
        link.removeAttribute("aria-current");
      }
    });
    var navClips = document.getElementById("nav-clips");
    var navEditor = document.getElementById("nav-editor");
    if (navClips) navClips.style.display = clipsData.length ? "inline-flex" : "none";
    if (navEditor) navEditor.style.display = currentVideoUrl ? "inline-flex" : "none";
    var toggle = document.getElementById("layout-toggle");
    if (toggle) toggle.style.display = (id === "page-results") ? "flex" : "none";
    var toolbar = document.querySelector(".results-toolbar-right");
    if (toolbar) {
      var sortEl = document.getElementById("sort-clips");
      if (id === "page-results") {
        if (sortEl) sortEl.parentElement.style.display = "block";
      }
    }
    closeMobileNav();
    updateOnboardingState();
  }

  function closeMobileNav() {
    var nav = document.getElementById("mobile-nav");
    var overlay = document.getElementById("mobile-overlay");
    var hamburger = document.getElementById("hamburger-btn");
    if (nav) nav.classList.remove("open");
    if (overlay) overlay.classList.remove("active");
    if (hamburger) {
      hamburger.classList.remove("open");
      hamburger.setAttribute("aria-expanded", "false");
    }
  }

  function openMobileNav() {
    var nav = document.getElementById("mobile-nav");
    var overlay = document.getElementById("mobile-overlay");
    var hamburger = document.getElementById("hamburger-btn");
    if (nav) nav.classList.add("open");
    if (overlay) overlay.classList.add("active");
    if (hamburger) {
      hamburger.classList.add("open");
      hamburger.setAttribute("aria-expanded", "true");
    }
  }

  function updateEditorEmptyStates() {
    var wmEnabled = document.getElementById("wm-enabled");
    var wmControls = document.getElementById("wm-controls");
    var wmEmpty = document.getElementById("wm-empty-state");
    if (wmEnabled && wmControls) {
      wmControls.style.display = wmEnabled.checked ? "flex" : "none";
      if (wmEmpty) wmEmpty.hidden = wmEnabled.checked;
    }
    var musicSelect = document.getElementById("music-select");
    var musicEmpty = document.getElementById("music-empty-state");
    if (musicSelect && musicEmpty) {
      musicEmpty.hidden = !!musicSelect.value;
    }
  }

  function updateWatermarkUi() {
    var hiddenInput = document.getElementById("wm-image-path");
    var preview = document.getElementById("wm-image-preview");
    var title = document.getElementById("wm-upload-title");
    var subtitle = document.getElementById("wm-upload-subtitle");
    var label = document.getElementById("wm-upload-area-label");
    var clearBtn = document.getElementById("btn-clear-watermark");
    var imageUrl = hiddenInput ? hiddenInput.value : "";
    currentWatermarkUrl = imageUrl || "";

    if (preview) {
      if (imageUrl) {
        preview.hidden = false;
        preview.src = imageUrl + "?t=" + Date.now();
      } else {
        preview.hidden = true;
        preview.src = "";
      }
    }
    if (title) title.textContent = imageUrl ? "Image watermark active" : "Text watermark active";
    if (subtitle) subtitle.textContent = imageUrl
      ? "Current export and preview will use the uploaded image watermark."
      : "Upload an image if you want to switch from text to image watermark.";
    if (label) label.textContent = imageUrl ? "Replace image watermark" : "Drop image or click to upload";
    if (clearBtn) clearBtn.hidden = !imageUrl;
  }

  function updateOnboardingState() {
    var dismissed = false;
    try {
      dismissed = window.localStorage.getItem(onboardingStorageKey) === "1";
    } catch (e) {}
    var uploadTip = document.getElementById("upload-onboarding");
    var resultsTip = document.getElementById("results-onboarding");
    var uploadPage = document.getElementById("page-upload");
    var resultsPage = document.getElementById("page-results");
    if (uploadTip && uploadPage) uploadTip.hidden = dismissed || !uploadPage.classList.contains("active");
    if (resultsTip && resultsPage) resultsTip.hidden = dismissed || !resultsPage.classList.contains("active") || clipsData.length === 0;
  }

  function dismissOnboarding() {
    try {
      window.localStorage.setItem(onboardingStorageKey, "1");
    } catch (e) {}
    updateOnboardingState();
  }

  /* ── Formatting Helpers ── */

  function fmtTime(s) {
    var m = Math.floor(s / 60);
    var sec = Math.floor(s % 60);
    return m + ":" + (sec < 10 ? "0" + sec : sec);
  }

  function scoreClass(s) {
    if (s >= 0.7) return "high";
    if (s >= 0.4) return "mid";
    return "low";
  }

  function scoreLabel(s) {
    return Math.round(s * 100) + "%";
  }

  /* ── Clip Rendering ── */

  /* LAZY-LOAD CANDIDATE: renderGrid/renderList could be deferred until
     results page is shown, since they're only needed there. */

  function getFilteredClips() {
    var filtered = clipsData.slice();
    if (currentSort === "score") {
      filtered.sort(function(a, b) { return b.score - a.score; });
    } else if (currentSort === "newest") {
      filtered.sort(function(a, b) { return b.start - a.start; });
    } else if (currentSort === "duration") {
      filtered.sort(function(a, b) { return (b.end - b.start) - (a.end - a.start); });
    }
    return filtered;
  }

  function fmtDuration(start, end) {
    var dur = end - start;
    var m = Math.floor(dur / 60);
    var s = Math.floor(dur % 60);
    return m > 0 ? m + ":" + (s < 10 ? "0" + s : s) : s + "s";
  }

  function getClipPosterMarkup(clip, className) {
    if (!clip || !clip.poster_url) return "";
    return '<img class="' + className + '" src="' + clip.poster_url + '" alt="Clip poster" loading="lazy">';
  }

  function getSelectedClipObjects() {
    return clipsData.filter(function(_, idx) { return !!selectedClips[idx]; });
  }

  function toggleClipSelection(idx) {
    if (typeof idx !== "number" || idx < 0 || idx >= clipsData.length) return;
    selectedClips[idx] = !selectedClips[idx];
    if (!selectedClips[idx]) delete selectedClips[idx];
    renderClips();
  }

  function updateBatchExportButton() {
    var btn = document.getElementById("btn-export-all");
    if (!btn) return;
    var selectedCount = getSelectedClipObjects().length;
    btn.textContent = selectedCount > 0 ? "Export Selected (" + selectedCount + ")" : "Export All";
  }

  function renderGrid() {
    var c = document.getElementById("clips-container");
    if (!c) return;
    c.className = "clips-grid";
    c.innerHTML = "";
    var clips = getFilteredClips();
    clips.forEach(function(clip, i) {
      var origIdx = clipsData.indexOf(clip);
      var card = document.createElement("div");
      card.className = "clip-card" + (selectedClips[origIdx] ? " selected" : "");
      card.dataset.index = origIdx;
      card.dataset.clipId = origIdx;
      card.style.animationDelay = (i * 50) + "ms";
      var duration = fmtDuration(clip.start, clip.end);
      card.innerHTML =
        '<div class="clip-thumb">' +
          getClipPosterMarkup(clip, "clip-poster") +
          '<button class="clip-select-btn' + (selectedClips[origIdx] ? ' is-selected' : '') + '" data-action="select" aria-label="Select clip">' + (selectedClips[origIdx] ? "✓" : "+") + '</button>' +
          '<div class="clip-rank">#' + (origIdx + 1) + '</div>' +
          '<div class="clip-score-badge ' + scoreClass(clip.score) + '">' + scoreLabel(clip.score) + '</div>' +
          '<div class="clip-duration-badge">' + duration + '</div>' +
        '</div>' +
        '<div class="clip-info">' +
          '<div class="clip-title">Clip ' + (origIdx + 1) + '</div>' +
          '<div class="clip-meta">' +
            '<span class="clip-duration">' + fmtTime(clip.start) + ' &rarr; ' + fmtTime(clip.end) + '</span>' +
            '<span>' + (clip.end - clip.start).toFixed(1) + 's</span>' +
          '</div>' +
        '</div>';
      card.addEventListener("click", function() { openEditor(origIdx); });
      var selectBtn = card.querySelector('[data-action="select"]');
      if (selectBtn) {
        selectBtn.addEventListener("click", function(e) {
          e.stopPropagation();
          toggleClipSelection(origIdx);
        });
      }
      card.addEventListener("mouseenter", function() {
        var thumb = card.querySelector(".clip-thumb");
        if (thumb && !thumb.querySelector("video.hover-preview")) {
          var vid = document.createElement("video");
          vid.className = "hover-preview";
          vid.muted = true;
          vid.playsInline = true;
          vid.preload = "none";
          vid.src = currentVideoUrl + "#t=" + clip.start;
          thumb.appendChild(vid);
          vid.play().catch(function() {});
        }
      });
      card.addEventListener("mouseleave", function() {
        var vid = card.querySelector(".clip-thumb video.hover-preview");
        if (vid) { vid.pause(); vid.remove(); }
      });
      c.appendChild(card);
    });
    updateSelectAll();
  }

  function renderList() {
    var c = document.getElementById("clips-container");
    if (!c) return;
    c.className = "clips-list";
    c.innerHTML = "";
    var clips = getFilteredClips();
    clips.forEach(function(clip, i) {
      var origIdx = clipsData.indexOf(clip);
      var item = document.createElement("div");
      item.className = "clip-list-item" + (selectedClips[origIdx] ? " selected" : "");
      item.dataset.index = origIdx;
      item.dataset.clipId = origIdx;
      item.style.animationDelay = (i * 50) + "ms";
      var duration = fmtDuration(clip.start, clip.end);
      item.innerHTML =
        '<div class="clip-list-thumb">' +
          getClipPosterMarkup(clip, "clip-list-poster") +
          '<div class="clip-score-badge ' + scoreClass(clip.score) + '">' + scoreLabel(clip.score) + '</div>' +
          '<div class="clip-duration-badge">' + duration + '</div>' +
        '</div>' +
        '<div class="clip-list-info">' +
          '<div class="clip-list-title">Clip ' + (origIdx + 1) + '</div>' +
          '<div class="clip-list-meta">' +
            '<span>' + fmtTime(clip.start) + ' &rarr; ' + fmtTime(clip.end) + '</span>' +
            '<span>' + (clip.end - clip.start).toFixed(1) + 's</span>' +
          '</div>' +
        '</div>' +
        '<div class="clip-list-score ' + scoreClass(clip.score) + '">' + scoreLabel(clip.score) + '</div>' +
        '<div class="clip-list-actions">' +
          '<button title="Select" class="' + (selectedClips[origIdx] ? "is-selected" : "") + '" data-action="select">' + (selectedClips[origIdx] ? "✓" : "+") + '</button>' +
          '<button title="Edit" data-action="edit">&#9998;</button>' +
          '<button title="Export" data-action="export">&#8689;</button>' +
        '</div>';
      item.addEventListener("click", function(e) {
        if (e.target.closest("[data-action]")) return;
        openEditor(origIdx);
      });
      item.querySelectorAll("[data-action]").forEach(function(btn) {
        btn.addEventListener("click", function(e) {
          e.stopPropagation();
          var action = btn.dataset.action;
          if (action === "select") toggleClipSelection(origIdx);
          else if (action === "edit") openEditor(origIdx);
          else if (action === "export") startExport([clipsData[origIdx]]);
        });
      });
      c.appendChild(item);
    });
    updateSelectAll();
  }

  function renderClips() {
    if (currentView === "grid") renderGrid();
    else renderList();
    var meta = document.getElementById("results-meta");
    var selectedCount = getSelectedClipObjects().length;
    if (meta) meta.textContent = clipsData.length + " clips found" + (selectedCount ? " · " + selectedCount + " selected" : "");
    var noClips = document.getElementById("no-clips");
    if (noClips) noClips.style.display = clipsData.length === 0 ? "flex" : "none";
    updateBatchExportButton();
  }

  function updateSelectAll() {
    var cb = document.getElementById("select-all-clips");
    if (!cb) return;
    var total = clipsData.length;
    var selected = Object.keys(selectedClips).filter(function(k) { return selectedClips[k]; }).length;
    if (selected === 0) { cb.checked = false; cb.indeterminate = false; }
    else if (selected === total) { cb.checked = true; cb.indeterminate = false; }
    else { cb.checked = false; cb.indeterminate = true; }
    updateBatchExportButton();
  }

  /* ── Editor ── */

  /* LAZY-LOAD CANDIDATE: openEditor/initEditorUI/initWaveform are only
     needed when the user clicks a clip. WaveSurfer and Plyr could be
     loaded dynamically on first editor open. */

  function openEditor(idx) {
    if (!clipsData.length) {
      toast("No clips available", "error");
      return;
    }
    setActiveClipIndex(idx);
    showPage("page-editor");
    initEditorUI(currentVideoUrl, clipsData);
  }

  function resetPreviewToVideo() {
    var video = document.getElementById("editor-video");
    var img = document.getElementById("preview-image");
    if (video) { video.style.display = "block"; }
    if (img) { img.style.display = "none"; img.src = ""; }
    updatePreviewAspect();
  }

  function getValidClipIndex(idx) {
    if (!clipsData.length) return -1;
    if (typeof idx !== "number" || idx < 0 || idx >= clipsData.length) {
      return 0;
    }
    return idx;
  }

  function getActiveClip() {
    var idx = getValidClipIndex(activeClipIndex);
    return idx === -1 ? null : clipsData[idx];
  }

  function setMetaValue(id, text) {
    var el = document.getElementById(id);
    if (!el) return;
    var value = el.querySelector("span:last-child");
    if (value) value.textContent = text;
  }

  function getAspectLabel() {
    var aspect = getSelectedAspect();
    if (aspect === "9:16") return "9:16";
    if (aspect === "16:9") return "16:9";
    return "Original";
  }

  function updateEditorMeta() {
    var clip = getActiveClip();
    var title = document.getElementById("editor-title");
    if (!clip) {
      if (title) title.textContent = "Clip Editor";
      setMetaValue("meta-active-clip", "Clip --");
      setMetaValue("meta-duration", "--:--");
      setMetaValue("meta-resolution", getAspectLabel());
      setMetaValue("meta-size", "--");
      return;
    }
    if (title) title.textContent = "Clip Editor · Clip " + (activeClipIndex + 1);
    setMetaValue("meta-active-clip", "Clip " + (activeClipIndex + 1));
    setMetaValue("meta-duration", fmtDuration(clip.start, clip.end));
    setMetaValue("meta-resolution", getAspectLabel());
    setMetaValue("meta-size", fmtTime(clip.start) + " → " + fmtTime(clip.end));
  }

  function syncEditorClipSelection() {
    var list = document.getElementById("editor-clips-list");
    if (list) {
      list.querySelectorAll(".editor-clip-item").forEach(function(item, idx) {
        item.classList.toggle("active", idx === activeClipIndex);
      });
    }
    syncWaveformRegions();
    updateEditorMeta();
  }

  function focusActiveClip(options) {
    var clip = getActiveClip();
    var video = document.getElementById("editor-video");
    if (!clip) return;
    resetPreviewToVideo();
    if (video) {
      video.currentTime = clip.start;
      if (options && options.autoplay) {
        video.play().catch(function() {});
      }
    }
    syncEditorClipSelection();
  }

  function setActiveClipIndex(idx) {
    activeClipIndex = getValidClipIndex(idx);
    syncEditorClipSelection();
  }

  function renderEditorClipList(clips) {
    var list = document.getElementById("editor-clips-list");
    if (!list) return;
    list.innerHTML = "";
    clips.forEach(function(clip, i) {
      var item = document.createElement("div");
      item.className = "editor-clip-item" + (i === activeClipIndex ? " active" : "");
      item.innerHTML =
        '<div class="num">#' + (i + 1) + '</div>' +
        '<div class="time">' + fmtTime(clip.start) + ' &rarr; ' + fmtTime(clip.end) + '</div>' +
        '<div class="dur">' + (clip.end - clip.start).toFixed(1) + 's</div>' +
        '<div class="score-dot ' + scoreClass(clip.score) + '"></div>';
      item.addEventListener("click", function() {
        setActiveClipIndex(i);
        focusActiveClip({ autoplay: true });
      });
      list.appendChild(item);
    });
  }

  function getRegionColor(isActive) {
    return isActive ? "rgba(124,58,237,0.42)" : "rgba(124,58,237,0.18)";
  }

  function syncWaveformRegions() {
    if (!wsRegionEntries.length) return;
    wsRegionEntries.forEach(function(entry, idx) {
      if (!entry || !entry.region) return;
      var isActive = idx === activeClipIndex;
      if (typeof entry.region.setOptions === "function") {
        entry.region.setOptions({
          color: getRegionColor(isActive),
          drag: isActive,
          resize: isActive
        });
      }
      if (entry.region.element) {
        entry.region.element.classList.toggle("active-region", isActive);
      }
    });
  }

  function findRegionIndex(region) {
    var match = wsRegionEntries.find(function(entry) {
      return entry && entry.region === region;
    });
    return match ? match.index : -1;
  }

  function updateClipFromRegion(idx, region) {
    var clip = clipsData[idx];
    if (!clip || !region) return;
    var start = Math.max(0, Number(region.start || 0));
    var end = Math.max(start + 0.1, Number(region.end || start + 0.1));
    clip.start = Math.round(start * 100) / 100;
    clip.end = Math.round(end * 100) / 100;
    renderEditorClipList(clipsData);
    renderClips();
    syncEditorClipSelection();
  }

  function initEditorUI(url, clips) {
    var video = document.getElementById("editor-video");
    if (video) {
      video.src = url;
      video.load();
    }
    resetPreviewToVideo();
    setActiveClipIndex(activeClipIndex);
    renderEditorClipList(clips);

    focusActiveClip({ autoplay: false });
    initWaveform(url, clips);
  }

  function getSelectedAspect() {
    var aspect = document.querySelector('#aspect-toggle button.active');
    return aspect ? aspect.dataset.value : "original";
  }

  function updatePreviewAspect() {
    var container = document.getElementById("preview-container");
    if (!container) return;
    if (getSelectedAspect() === "9:16") {
      container.classList.add("vertical");
    } else {
      container.classList.remove("vertical");
    }
  }

  function buildEditorOptions() {
    var aspect = document.querySelector('#aspect-toggle button.active');
    var watermarkImagePath = document.getElementById("wm-image-path").value;
    var opts = {
      aspect_ratio: aspect ? aspect.dataset.value : "original",
      blur_background: document.getElementById("blur-bg").checked,
      watermark: {
        enabled: document.getElementById("wm-enabled").checked,
        type: watermarkImagePath ? "image" : "text",
        text: document.getElementById("wm-text").value,
        image_path: watermarkImagePath,
        position: document.getElementById("wm-position").value,
        fontsize: parseInt(document.getElementById("wm-size").value, 10),
        height: parseInt(document.getElementById("wm-size").value, 10),
        opacity: parseInt(document.getElementById("wm-opacity").value, 10) / 100,
        color: "white"
      },
      audio: {
        music_path: document.getElementById("music-select").value,
        music_volume: parseInt(document.getElementById("music-vol").value, 10) / 100,
        original_volume: parseInt(document.getElementById("orig-vol").value, 10) / 100
      },
      fade: {
        fade_in: parseInt(document.getElementById("fade-in").value, 10) / 10,
        fade_out: parseInt(document.getElementById("fade-out").value, 10) / 10
      }
    };
    if (!opts.watermark.enabled) {
      delete opts.watermark;
    }
    if (!opts.audio.music_path) {
      delete opts.audio;
    }
    return opts;
  }

  /* ── Music Library ── */

  /* LAZY-LOAD CANDIDATE: loadMusicLibrary fetches data not needed until
     the editor is opened. Already deferred via requestIdleCallback below. */

  function loadMusicLibrary() {
    fetch("/list-music")
      .then(function(r) { return r.json(); })
      .then(function(data) {
        if (data.success) {
          musicLibrary = data.music;
          var sel = document.getElementById("music-select");
          var current = sel.value;
          sel.innerHTML = '<option value="">None</option>';
          musicLibrary.forEach(function(m) {
            var opt = document.createElement("option");
            opt.value = m.url;
            opt.textContent = m.name;
            sel.appendChild(opt);
          });
          sel.value = current;
          updateEditorEmptyStates();
        }
      })
      .catch(function() {});
  }

  /* ── Waveform ── */

  /* LAZY-LOAD CANDIDATE: WaveSurfer is a heavy library (~200KB).
     Consider dynamic import on first editor open instead of eager load. */

  function initWaveform(url, clips) {
    var container = document.getElementById("editor-waveform");
    if (!container) return;
    container.innerHTML = "";
    if (ws) { try { ws.destroy(); } catch(e) {} }
    wsRegionEntries = [];

    ws = WaveSurfer.create({
      container: container,
      waveColor: "#3a3a5e",
      progressColor: "#7c3aed",
      cursorColor: "#fff",
      height: 60,
      barWidth: 2,
      barGap: 1,
      responsive: true,
      url: url,
    });

    ws.on("ready", function() {
      if (typeof WaveSurfer !== "undefined" && WaveSurfer.Regions) {
        try {
          wsRegions = ws.registerPlugin(WaveSurfer.Regions.create());
          clips.forEach(function(clip, idx) {
            var region = wsRegions.addRegion({
              start: clip.start,
              end: clip.end,
              color: getRegionColor(idx === activeClipIndex),
              drag: idx === activeClipIndex,
              resize: idx === activeClipIndex,
            });
            wsRegionEntries.push({ region: region, index: idx });
          });
          if (typeof ws.on === "function") {
            ws.on("region-clicked", function(region, e) {
              var idx = findRegionIndex(region);
              if (e && typeof e.stopPropagation === "function") e.stopPropagation();
              if (idx === -1) return;
              setActiveClipIndex(idx);
              focusActiveClip({ autoplay: false });
            });
            ws.on("region-update-end", function(region) {
              var idx = findRegionIndex(region);
              if (idx === -1) return;
              updateClipFromRegion(idx, region);
              if (idx === activeClipIndex) {
                focusActiveClip({ autoplay: false });
              }
            });
          }
          syncWaveformRegions();
        } catch(e) {}
      }
    });
  }

  /* ── Progress Bar ── */

  var progressTimer = null;
  var currentProgress = 0;

  function setProgress(percent) {
    currentProgress = Math.min(percent, 99);
    var fill = document.getElementById("progress-fill");
    var pct = document.getElementById("progress-percent");
    if (fill) fill.style.width = currentProgress + "%";
    if (pct) pct.textContent = Math.round(currentProgress) + "%";
  }

  function simulateProgress() {
    clearInterval(progressTimer);
    currentProgress = 0;
    setProgress(0);
    progressTimer = setInterval(function() {
      if (currentProgress < 90) {
        currentProgress += Math.random() * 3;
        setProgress(currentProgress);
      }
    }, 400);
  }

  function stopProgress() {
    clearInterval(progressTimer);
    setProgress(100);
    setTimeout(function() { setProgress(0); }, 500);
  }

  function setLoading(active, text) {
    var section = document.getElementById("progress-section");
    var btn = document.getElementById("btn-analyze");
    var steps = document.getElementById("progress-steps");
    if (active) {
      section.classList.add("active");
      btn.disabled = true;
      btn.textContent = "Processing...";
      if (steps) steps.innerHTML = "";
      simulateProgress();
    } else {
      section.classList.remove("active");
      btn.disabled = false;
      btn.textContent = "Analyze Video";
      stopProgress();
    }
    if (text && steps) {
      var step = document.createElement("div");
      step.className = "step active";
      step.innerHTML = '<span class="step-icon">&#10003;</span> ' + text;
      steps.appendChild(step);
      var prev = steps.querySelectorAll(".step");
      prev.forEach(function(s, i) { if (i < prev.length - 1) s.classList.add("done"); s.classList.remove("active"); });
      step.classList.add("active");
      step.classList.remove("done");
    }
  }

  /* ── Error Handling ── */

  function showUploadError(title, message) {
    var errBox = document.getElementById("upload-error");
    var errTitle = document.getElementById("error-title");
    var errMsg = document.getElementById("error-message");
    if (errTitle) errTitle.textContent = title || "Error";
    if (errMsg) errMsg.textContent = message || "Something went wrong";
    if (errBox) errBox.style.display = "flex";
  }

  function hideUploadError() {
    var errBox = document.getElementById("upload-error");
    if (errBox) errBox.style.display = "none";
  }

  /* ── Global Drag-Drop Functions ── */

  function createGlobalDropOverlay() {
    var overlay = document.createElement("div");
    overlay.className = "global-drop-overlay";
    overlay.innerHTML =
      '<div class="global-drop-overlay__icon">&#128229;</div>' +
      '<div class="global-drop-overlay__text">Drop files here</div>' +
      '<div class="global-drop-overlay__sub">Release to upload</div>' +
      '<div class="global-drop-overlay__badge"></div>';
    document.body.appendChild(overlay);
    return overlay;
  }

  function getGlobalDropOverlay() {
    if (!globalDropOverlay) {
      globalDropOverlay = createGlobalDropOverlay();
    }
    return globalDropOverlay;
  }

  function showGlobalDropOverlay(fileCount, fileType) {
    var overlay = getGlobalDropOverlay();
    var badge = overlay.querySelector(".global-drop-overlay__badge");
    var icon = overlay.querySelector(".global-drop-overlay__icon");
    if (badge) {
      badge.textContent = fileCount + " file" + (fileCount > 1 ? "s" : "");
      badge.classList.add("visible");
    }
    if (fileType === "music") {
      icon.innerHTML = "&#9835;";
    } else if (fileType === "image") {
      icon.innerHTML = "&#128247;";
    } else {
      icon.innerHTML = "&#128229;";
    }
    overlay.classList.add("active");
  }

  function hideGlobalDropOverlay() {
    var overlay = getGlobalDropOverlay();
    overlay.classList.remove("active");
  }

  function getFileTypeFromDataTransfer(dataTransfer) {
    if (!dataTransfer || !dataTransfer.items) return "video";
    for (var i = 0; i < dataTransfer.items.length; i++) {
      var item = dataTransfer.items[i];
      if (item.kind === "file") {
        var type = item.type;
        if (type.startsWith("audio/")) return "music";
        if (type.startsWith("image/")) return "image";
      }
    }
    return "video";
  }

  function handleDragEnter(e) {
    e.preventDefault();
    dragCounter++;
    var dt = e.dataTransfer || e.target.dataTransfer;
    var fileCount = dt && dt.files ? dt.files.length : 0;
    var fileType = getFileTypeFromDataTransfer(dt);
    showGlobalDropOverlay(fileCount || 1, fileType);
  }

  function handleDragLeave(e) {
    e.preventDefault();
    dragCounter--;
    if (dragCounter <= 0) {
      dragCounter = 0;
      hideGlobalDropOverlay();
    }
  }

  function handleDragOver(e) {
    e.preventDefault();
  }

  function handleDrop(e) {
    e.preventDefault();
    dragCounter = 0;
    hideGlobalDropOverlay();
  }

  function initGlobalDragDrop() {
    document.addEventListener("dragenter", handleDragEnter);
    document.addEventListener("dragleave", handleDragLeave);
    document.addEventListener("dragover", handleDragOver);
    document.addEventListener("drop", handleDrop);
  }

  /* ── File Utilities ── */

  function formatBytes(bytes) {
    if (bytes === 0) return "0 B";
    var k = 1024;
    var sizes = ["B", "KB", "MB", "GB"];
    var i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  }

  function validateFile(file) {
    var maxSize = 2 * 1024 * 1024 * 1024;
    var allowed = ["video/mp4", "video/quicktime", "video/x-msvideo", "video/x-matroska", "video/webm", "video/avi", "video/mov"];
    if (!file) return "No file selected";
    if (file.size > maxSize) return "File too large (max 2GB)";
    if (!allowed.includes(file.type) && !/\.(mp4|mov|avi|mkv|webm)$/i.test(file.name)) {
      return "Unsupported format. Use MP4, MOV, AVI, or MKV";
    }
    return null;
  }

  function updateFileDisplay(file) {
    var dropZone = document.getElementById("drop-zone");
    var icon = document.getElementById("upload-icon");
    var thumb = document.getElementById("upload-thumb");
    var thumbVideo = document.getElementById("upload-thumb-video");
    var title = document.getElementById("upload-title");
    var subtitle = document.getElementById("upload-subtitle");
    var fileInfo = document.getElementById("file-info");
    var fileName = document.getElementById("file-name");
    var fileSize = document.getElementById("file-size");

    if (!file) {
      if (dropZone) dropZone.classList.remove("has-file");
      if (icon) icon.style.display = "block";
      if (thumb) thumb.style.display = "none";
      if (title) title.textContent = "Drop your video here";
      if (subtitle) subtitle.textContent = "or click to browse files";
      if (fileInfo) fileInfo.style.display = "none";
      return;
    }

    if (dropZone) dropZone.classList.add("has-file");
    if (icon) icon.style.display = "none";
    if (thumb) thumb.style.display = "block";
    if (title) title.textContent = file.name;
    if (subtitle) subtitle.textContent = "Ready to analyze";
    if (fileInfo) fileInfo.style.display = "flex";
    if (fileName) fileName.textContent = file.name;
    if (fileSize) fileSize.textContent = formatBytes(file.size);

    if (thumbVideo && file.type.startsWith("video/")) {
      var url = URL.createObjectURL(file);
      thumbVideo.src = url;
      thumbVideo.onloadeddata = function() { thumbVideo.currentTime = Math.min(1, thumbVideo.duration / 2); };
    }
  }

  /* ── Settings ── */

  var debouncedSendSettings = debounce(function() {
    sendSettings();
  }, 300);

  function sendSettings() {
    var fd = new FormData();
    fd.set("use-gpu", document.getElementById("toggle-gpu").classList.contains("on") ? "on" : "");
    fd.set("auto-load-model", document.getElementById("toggle-auto-load").classList.contains("on") ? "on" : "");
    fd.set("minimum-clip-length", document.getElementById("setting-min-length").value);
    fd.set("maximum-clip-length", document.getElementById("setting-max-length").value);
    fd.set("number-of-clips", document.getElementById("setting-num-clips").value);
    fd.set("threshold", (parseInt(document.getElementById("setting-threshold").value) / 100).toString());
    fd.set("pad-clip-start", document.getElementById("setting-pad-start").value);
    fd.set("pad-clip-end", document.getElementById("setting-pad-end").value);
    fd.set("segment-length", "600");
    fd.set("leniency", "2");
    fetch("/get-config", { method: "POST", body: fd })
      .then(function(r) { return r.json(); })
      .then(function() { toast("Settings updated", "success"); })
      .catch(function() { toast("Failed to update", "error"); });
  }

  function saveSettings() {
    sendSettings();
    fetch("/save-config", { method: "POST", body: new FormData() })
      .then(function(r) { return r.json(); })
      .then(function() { toast("Settings saved", "success"); })
      .catch(function() { toast("Failed to save", "error"); });
  }

  function initSettings() {
    var gpu = document.getElementById("toggle-gpu");
    var autoLoad = document.getElementById("toggle-auto-load");

    function initToggle(el, val) {
      if (val) el.classList.add("on");
      else el.classList.remove("on");
    }

    var cfg = document.getElementById("app-config");
    initToggle(gpu, cfg && cfg.dataset.useGpu === "true");
    initToggle(autoLoad, cfg && cfg.dataset.autoLoad === "true");

    [gpu, autoLoad].forEach(function(btn) {
      btn.addEventListener("click", function() {
        btn.classList.toggle("on");
        debouncedSendSettings();
      });
    });

    var sliders = [
      { id: "setting-min-length", val: "val-min-length", suffix: "s" },
      { id: "setting-max-length", val: "val-max-length", suffix: "s" },
      { id: "setting-num-clips", val: "val-num-clips", suffix: "" },
      { id: "setting-threshold", val: "val-threshold", suffix: "%" },
      { id: "setting-pad-start", val: "val-pad-start", suffix: "s" },
      { id: "setting-pad-end", val: "val-pad-end", suffix: "s" },
    ];

    sliders.forEach(function(s) {
      var input = document.getElementById(s.id);
      var display = document.getElementById(s.val);
      if (input && display) {
        input.addEventListener("input", function() {
          display.textContent = input.value + s.suffix;
        });
        input.addEventListener("change", function() {
          debouncedSendSettings();
        });
      }
    });
  }

  /* ── Editor Controls ── */

  /* DEFERRED: initEditorControls is deferred via requestIdleCallback
     since editor controls are not needed on initial page load. */

  function initEditorControls() {
    document.querySelectorAll(".editor-card-header").forEach(function(header) {
      header.addEventListener("click", function() {
        var shouldCollapse = header.getAttribute("aria-expanded") !== "false";
        header.setAttribute("aria-expanded", shouldCollapse ? "false" : "true");
      });
    });

    var aspectToggle = document.getElementById("aspect-toggle");
    if (aspectToggle) {
      aspectToggle.querySelectorAll("button").forEach(function(btn) {
        btn.addEventListener("click", function() {
          aspectToggle.querySelectorAll("button").forEach(function(b) { b.classList.remove("active"); });
          btn.classList.add("active");
          var blurCtrl = document.getElementById("blur-control");
          if (blurCtrl) blurCtrl.style.display = btn.dataset.value === "9:16" ? "block" : "none";
          updatePreviewAspect();
          var video = document.getElementById("editor-video");
          var img = document.getElementById("preview-image");
          if (video && video.style.display !== "none") {
            video.style.width = btn.dataset.value === "9:16" ? "auto" : "100%";
          }
          if (img && img.style.display !== "none") {
            updatePreviewAspect();
          }
          updateEditorMeta();
        });
      });
    }

    var wmEnabled = document.getElementById("wm-enabled");
    if (wmEnabled) {
      wmEnabled.addEventListener("change", function() {
        updateEditorEmptyStates();
      });
    }

    var wmPosition = document.getElementById("wm-position");
    var wmPositionGrid = document.getElementById("wm-position-grid");
    if (wmPosition && wmPositionGrid) {
      wmPositionGrid.querySelectorAll(".wm-pos-cell").forEach(function(btn) {
        btn.addEventListener("click", function() {
          wmPositionGrid.querySelectorAll(".wm-pos-cell").forEach(function(cell) { cell.classList.remove("active"); });
          btn.classList.add("active");
          wmPosition.value = btn.dataset.pos;
        });
      });
    }

    var sliders = [
      { id: "wm-size", val: "wm-size-val", suffix: "px" },
      { id: "wm-opacity", val: "wm-opacity-val", suffix: "%" },
      { id: "music-vol", val: "music-vol-val", suffix: "%" },
      { id: "orig-vol", val: "orig-vol-val", suffix: "%" },
      { id: "fade-in", val: "fade-in-val", suffix: "s", scale: 0.1 },
      { id: "fade-out", val: "fade-out-val", suffix: "s", scale: 0.1 },
    ];
    sliders.forEach(function(s) {
      var input = document.getElementById(s.id);
      var display = document.getElementById(s.val);
      if (input && display) {
        input.addEventListener("input", function() {
          var v = parseFloat(input.value);
          if (s.scale) v = (v * s.scale).toFixed(1);
          display.textContent = v + s.suffix;
        });
      }
    });

    var wmUploadArea = document.getElementById("wm-upload-area");
    var wmUploadInput = document.getElementById("wm-upload-input");
    var wmImagePath = document.getElementById("wm-image-path");
    var wmClearBtn = document.getElementById("btn-clear-watermark");

    function handleWatermarkUpload(file) {
      if (!file) return;
      var fd = new FormData();
      fd.append("watermark", file);
      fetch("/upload-watermark", { method: "POST", body: fd })
        .then(function(r) { return r.json(); })
        .then(function(data) {
          if (data.success) {
            if (wmImagePath) wmImagePath.value = data.watermark_url;
            updateWatermarkUi();
            if (wmEnabled && !wmEnabled.checked) {
              wmEnabled.checked = true;
              updateEditorEmptyStates();
            }
            toast("Watermark image uploaded", "success");
          } else {
            toast("Upload failed: " + data.error, "error");
          }
        })
        .catch(function(err) {
          toast("Upload error: " + err.message, "error");
        });
    }

    if (wmUploadArea && wmUploadInput) {
      wmUploadArea.addEventListener("click", function() {
        wmUploadInput.click();
      });
      wmUploadArea.addEventListener("dragover", function(e) {
        e.preventDefault();
        wmUploadArea.classList.add("dragover");
      });
      wmUploadArea.addEventListener("dragleave", function() {
        wmUploadArea.classList.remove("dragover");
      });
      wmUploadArea.addEventListener("drop", function(e) {
        e.preventDefault();
        wmUploadArea.classList.remove("dragover");
        if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]) {
          handleWatermarkUpload(e.dataTransfer.files[0]);
        }
      });
      wmUploadInput.addEventListener("change", function() {
        if (wmUploadInput.files.length === 0) return;
        handleWatermarkUpload(wmUploadInput.files[0]);
        wmUploadInput.value = "";
      });
    }

    if (wmClearBtn && wmImagePath) {
      wmClearBtn.addEventListener("click", function() {
        wmImagePath.value = "";
        updateWatermarkUi();
        toast("Switched back to text watermark", "info");
      });
    }

    var musicUpload = document.getElementById("music-upload");
    var btnUploadMusic = document.getElementById("btn-upload-music");
    var musicSelect = document.getElementById("music-select");
    if (musicSelect) {
      musicSelect.addEventListener("change", updateEditorEmptyStates);
    }
    if (btnUploadMusic && musicUpload) {
      btnUploadMusic.addEventListener("click", function() { musicUpload.click(); });
      musicUpload.addEventListener("change", function() {
        if (musicUpload.files.length === 0) return;
        var fd = new FormData();
        fd.append("music", musicUpload.files[0]);
        fetch("/upload-music", { method: "POST", body: fd })
          .then(function(r) { return r.json(); })
          .then(function(data) {
            if (data.success) {
              loadMusicLibrary();
              setTimeout(function() { document.getElementById("music-select").value = data.music_url; }, 300);
              toast("Music uploaded", "success");
            } else {
              toast("Upload failed: " + data.error, "error");
            }
          })
          .catch(function(err) { toast("Upload error: " + err.message, "error"); });
      });
    }

    loadMusicLibrary();
    updateEditorEmptyStates();
    updateWatermarkUi();
  }

  /* ── DOMContentLoaded: Critical Init ── */

  document.addEventListener("DOMContentLoaded", function() {
    initSettings();
    updateOnboardingState();

    /* DEFERRED: Editor controls and music library are not needed
       until the user opens the editor. Defer to idle time. */
    rIC(function() {
      initEditorControls();
    });

    /* ── Upload Page Event Handlers ── */

    var dropZone = document.getElementById("drop-zone");
    var fileInput = document.getElementById("video-input");
    var uploadForm = document.getElementById("upload-form");

    function scrollToSection(id) {
      var section = document.getElementById(id);
      if (!section) return;
      section.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    var btnHeroStart = document.getElementById("btn-hero-start");
    if (btnHeroStart) {
      btnHeroStart.addEventListener("click", function() {
        scrollToSection("upload-workbench");
        if (fileInput) fileInput.click();
      });
    }

    var btnHeroPreview = document.getElementById("btn-hero-preview");
    if (btnHeroPreview) {
      btnHeroPreview.addEventListener("click", function() {
        scrollToSection("landing-flow");
      });
    }
    if (dropZone && fileInput) {
      /* dragover must call preventDefault to allow drop,
         so it cannot be passive. dragleave is safe to be passive. */
      dropZone.addEventListener("dragover", function(e) {
        e.preventDefault();
        dropZone.classList.add("dragover");
      });
      dropZone.addEventListener("dragleave", function() {
        dropZone.classList.remove("dragover");
      }, { passive: true });
      dropZone.addEventListener("drop", function(e) {
        e.preventDefault();
        dropZone.classList.remove("dragover");
        if (e.dataTransfer.files.length > 0) {
          var err = validateFile(e.dataTransfer.files[0]);
          if (err) { toast(err, "error"); dropZone.classList.add("invalid"); setTimeout(function(){ dropZone.classList.remove("invalid"); }, 500); return; }
          fileInput.files = e.dataTransfer.files;
          updateFileDisplay(e.dataTransfer.files[0]);
          hideUploadError();
        }
      });
      fileInput.addEventListener("change", function() {
        if (fileInput.files.length > 0) {
var err = validateFile(fileInput.files[0]);
            if (err) {
              toast(err, "error");
              dropZone.classList.add("invalid");
              setTimeout(function(){ dropZone.classList.remove("invalid"); }, 500);
              fileInput.value = "";
              updateFileDisplay(null);
              return;
            }
          updateFileDisplay(fileInput.files[0]);
          hideUploadError();
        }
      });
    }

    var fileRemove = document.getElementById("file-remove");
    if (fileRemove && fileInput) {
      fileRemove.addEventListener("click", function(e) {
        e.stopPropagation();
        fileInput.value = "";
        updateFileDisplay(null);
        hideUploadError();
      });
    }

    var errorClose = document.getElementById("error-close");
    if (errorClose) {
      errorClose.addEventListener("click", hideUploadError);
    }

    /* ── Form Submission ── */

    if (uploadForm) {
      uploadForm.addEventListener("submit", function(e) {
        e.preventDefault();
        hideUploadError();
        if (!fileInput || fileInput.files.length === 0) {
          showUploadError("No file selected", "Please choose a video file to analyze.");
          return;
        }
        var err = validateFile(fileInput.files[0]);
        if (err) {
          showUploadError("Invalid file", err);
          dropZone.classList.add("invalid");
          setTimeout(function(){ dropZone.classList.remove("invalid"); }, 500);
          return;
        }

        var progressSteps = document.getElementById("progress-steps");
        if (progressSteps) progressSteps.innerHTML = "";

        setLoading(true, "Uploading video...");
        toast("Analyzing video...", "info");

        setTimeout(function() { setLoading(true, "Extracting audio features..."); }, 1500);
        setTimeout(function() { setLoading(true, "Running AI predictions..."); }, 3000);
        setTimeout(function() { setLoading(true, "Finding best clips..."); }, 5000);

        fetch("/", { method: "POST", body: new FormData(uploadForm) })
          .then(function(r) {
            if (!r.ok) throw new Error("Server returned " + r.status + " " + r.statusText);
            return r.text();
          })
          .then(function(html) {
            setLoading(false);
            var parser = new DOMParser();
            var doc = parser.parseFromString(html, "text/html");
            var dataScript = doc.getElementById("editor-data");
            var errorEl = doc.querySelector(".error-message") || doc.querySelector("[data-error]");

            if (errorEl && errorEl.textContent) {
              showUploadError("Analysis failed", errorEl.textContent.trim());
              return;
            }

            if (dataScript) {
              var data = JSON.parse(dataScript.textContent);
              clipsData = data.clips || [];
              currentVideoUrl = data.video_url || "";
              activeClipIndex = clipsData.length ? 0 : -1;
              selectedClips = {};
              renderClips();
              showPage("page-results");
              var banner = document.getElementById("results-banner");
              var bannerText = document.getElementById("banner-text");
              if (banner) {
                banner.style.display = clipsData.length > 0 ? "flex" : "none";
                if (bannerText) bannerText.textContent = clipsData.length + " clip" + (clipsData.length === 1 ? "" : "s") + " detected";
              }
              if (clipsData.length > 0) {
                toast("Found " + clipsData.length + " clips!", "success");
              } else {
                toast("No clips found — try adjusting settings", "info");
              }
            } else {
              var infoEl = doc.querySelector(".info-message") || doc.querySelector(".message");
              if (infoEl && infoEl.textContent) {
                showUploadError("No clips found", infoEl.textContent.trim());
              } else {
                showUploadError("Unexpected response", "The server returned an unexpected response. Please try again.");
              }
            }
          })
          .catch(function(err) {
            setLoading(false);
            showUploadError("Network error", err.message || "Failed to connect to the server. Please check your connection and try again.");
          });
      });
    }

    /* ── Layout Toggle ── */

    var layoutToggle = document.getElementById("layout-toggle");
    if (layoutToggle) {
      layoutToggle.querySelectorAll("button").forEach(function(btn) {
        btn.addEventListener("click", function() {
          layoutToggle.querySelectorAll("button").forEach(function(b) { b.classList.remove("active"); });
          btn.classList.add("active");
          currentView = btn.dataset.view;
          renderClips();
        });
      });
    }

    /* ── Sort Dropdown ── */

    var sortSelect = document.getElementById("sort-clips");
    if (sortSelect) {
      sortSelect.addEventListener("change", function() {
        currentSort = sortSelect.value;
        renderClips();
      });
    }

    /* ── Select All ── */

    var selectAllCb = document.getElementById("select-all-clips");
    if (selectAllCb) {
      selectAllCb.addEventListener("change", function() {
        var checked = selectAllCb.checked;
        if (!checked) {
          selectedClips = {};
        } else {
          clipsData.forEach(function(_, i) { selectedClips[i] = true; });
        }
        renderClips();
      });
    }

    /* ── Modal & Navigation ── */

    document.getElementById("btn-settings").addEventListener("click", function() {
      document.getElementById("settings-modal").classList.add("active");
    });
    document.getElementById("modal-close").addEventListener("click", function() {
      document.getElementById("settings-modal").classList.remove("active");
    });
    /* Passive: modal overlay click only reads e.target, no preventDefault needed */
    document.getElementById("settings-modal").addEventListener("click", function(e) {
      if (e.target === this) this.classList.remove("active");
    }, { passive: true });

    document.getElementById("btn-new-analysis").addEventListener("click", function() {
      showPage("page-upload");
      selectedClips = {};
      var banner = document.getElementById("results-banner");
      if (banner) banner.style.display = "none";
      hideUploadError();
    });

    var btnAdjustSettings = document.getElementById("btn-adjust-settings");
    if (btnAdjustSettings) {
      btnAdjustSettings.addEventListener("click", function() {
        document.getElementById("settings-modal").classList.add("active");
      });
    }

    document.getElementById("btn-back-results").addEventListener("click", function() {
      showPage("page-results");
    });

    document.querySelectorAll(".nav-link").forEach(function(link) {
      link.addEventListener("click", function(e) {
        e.preventDefault();
        if (link.style.display === "none") return;
        showPage(link.dataset.page);
      });
    });

    var hamburgerBtn = document.getElementById("hamburger-btn");
    if (hamburgerBtn) {
      hamburgerBtn.addEventListener("click", function() {
        if (hamburgerBtn.getAttribute("aria-expanded") === "true") closeMobileNav();
        else openMobileNav();
      });
    }

    var mobileOverlay = document.getElementById("mobile-overlay");
    if (mobileOverlay) {
      mobileOverlay.addEventListener("click", closeMobileNav);
    }

    var dismissUploadOnboarding = document.getElementById("dismiss-upload-onboarding");
    if (dismissUploadOnboarding) dismissUploadOnboarding.addEventListener("click", dismissOnboarding);
    var dismissResultsOnboarding = document.getElementById("dismiss-results-onboarding");
    if (dismissResultsOnboarding) dismissResultsOnboarding.addEventListener("click", dismissOnboarding);

    /* ── Reusable Modal System ── */
var activeModal = null;
var lastFocusedElement = null;
var modalTrapListeners = [];

function showModal(modalId, options) {
  var modal = document.getElementById(modalId);
  if (!modal || !modal.classList.contains("modal-overlay")) return;
  var opts = options || {};
  var overlay = modal;
  var card = modal.querySelector(".modal-card") || modal.querySelector(".modal") || modal;
  activeModal = modalId;
  lastFocusedElement = document.activeElement;
  modal.style.display = "flex";
  overlay.classList.add("is-active");
  requestAnimationFrame(function() {
    overlay.classList.add("is-visible");
    overlay.classList.add("is-animated");
    card.style.transform = "translateY(0)";
    card.style.opacity = "1";
  });
  var closeBtn = modal.querySelector(".modal-close");
  if (closeBtn) closeBtn.addEventListener("click", hideModal.bind(null, modalId));
  modal.addEventListener("click", function(e) {
    if (e.target === modal) hideModal(modalId);
  }, { passive: true });
  enableModalTrap(modalId);
  document.addEventListener("keydown", handleModalKeydown);
  var primaryBtn = modal.querySelector(".modal-footer .btn-primary");
  if (primaryBtn) {
    primaryBtn.addEventListener("click", function() {
      if (opts.onPrimary) opts.onPrimary();
    });
  }
}

function hideModal(modalId) {
  var modal = document.getElementById(modalId);
  if (!modal) return;
  var overlay = modal;
  var card = modal.querySelector(".modal-card") || modal.querySelector(".modal") || modal;
  overlay.classList.remove("is-visible", "is-animated");
  card.style.transform = "translateY(24px)";
  card.style.opacity = "0";
  disableModalTrap(modalId);
  document.removeEventListener("keydown", handleModalKeydown);
  setTimeout(function() {
    modal.style.display = "";
    overlay.classList.remove("is-active");
    card.style.transform = "";
    card.style.opacity = "";
  }, 240);
  activeModal = null;
  if (lastFocusedElement) {
    lastFocusedElement.focus();
    lastFocusedElement = null;
  }
}

function handleModalKeydown(e) {
  if (e.key === "Escape" && activeModal) {
    e.preventDefault();
    hideModal(activeModal);
    return;
  }
  if (e.key === "Tab" && activeModal) {
    e.preventDefault();
    trapTabFocus(activeModal, e.shiftKey);
  }
}

function getFocusableElements(modalId) {
  var modal = document.getElementById(modalId);
  if (!modal) return [];
  var selector = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';
  var focusable = Array.prototype.slice.call(modal.querySelectorAll(selector));
  return focusable.filter(function(el) {
    return !el.disabled && el.offsetParent !== null;
  });
}

function enableModalTrap(modalId) {
  modalTrapListeners[modalId] = {
    keydown: trapTabFocus.bind(null, modalId, false)
  };
}

function trapTabFocus(modalId, reverse) {
  var focusable = getFocusableElements(modalId);
  if (focusable.length === 0) return;
  var first = focusable[0];
  var last = focusable[focusable.length - 1];
  var active = document.activeElement;
  if (reverse) {
    if (active === first || !focusable.includes(active)) {
      last.focus();
    } else {
      var idx = focusable.indexOf(active);
      if (idx > 0) focusable[idx - 1].focus();
    }
  } else {
    if (active === last || !focusable.includes(active)) {
      first.focus();
    } else {
      var idx = focusable.indexOf(active);
      if (idx < focusable.length - 1) focusable[idx + 1].focus();
    }
  }
}

function disableModalTrap(modalId) {
  delete modalTrapListeners[modalId];
}

    var exportPollTimer = null;
    var currentJobId = null;
    var exportStartTime = null;
    var lastExportClips = [];

    var stageLabels = ["Preparing...", "Encoding...", "Finalizing...", "Done!"];

    function getStageFromProgress(pct) {
      if (pct < 30) return stageLabels[0];
      if (pct < 75) return stageLabels[1];
      if (pct < 95) return stageLabels[2];
      return stageLabels[3];
    }

    function showExportInline() {
      var el = document.getElementById("export-inline-progress");
      var exportBtn = document.getElementById("btn-export-edit");
      if (el) {
        el.style.display = "block";
        el.classList.remove("done", "error");
        if (exportBtn) exportBtn.disabled = true;
      }
      exportStartTime = Date.now();
    }

    function hideExportInline() {
      var el = document.getElementById("export-inline-progress");
      var exportBtn = document.getElementById("btn-export-edit");
      if (el) {
        el.style.display = "none";
        el.classList.remove("done", "error");
        if (exportBtn) exportBtn.disabled = false;
      }
      clearInterval(exportPollTimer);
      exportPollTimer = null;
      currentJobId = null;
      exportStartTime = null;
    }

    function updateExportInline(pct, stage) {
      var el = document.getElementById("export-inline-progress");
      var fill = document.getElementById("export-inline-fill");
      var pctEl = document.getElementById("export-inline-percent");
      var stageEl = document.getElementById("export-inline-stage");
      var etaEl = document.getElementById("export-inline-eta");
      if (fill) fill.style.width = pct + "%";
      if (pctEl) pctEl.textContent = pct + "%";
      if (stageEl) {
        stageEl.textContent = stage || getStageFromProgress(pct);
        if (stage === stageLabels[3]) stageEl.classList.add("pulse-done");
      }
      if (etaEl && exportStartTime && pct > 5) {
        var elapsed = (Date.now() - exportStartTime) / 1000;
        var remaining = Math.round((elapsed / pct) * (100 - pct));
        if (remaining < 60) etaEl.textContent = "About " + remaining + "s remaining";
        else etaEl.textContent = "About " + Math.round(remaining / 60) + "m remaining";
      } else if (etaEl && pct > 0) {
        etaEl.textContent = "Calculating...";
      }
    }

    function pollExportStatus(jobId, downloadUrl) {
      currentJobId = jobId;
      showExportInline();
      updateExportInline(0, stageLabels[0]);
      exportPollTimer = setInterval(function() {
        fetch("/export-status/" + jobId)
          .then(function(r) { return r.json(); })
          .then(function(status) {
            var pct = status.progress || 0;
            var stage = getStageFromProgress(pct);
            updateExportInline(pct, stage);
            var fill = document.getElementById("export-inline-fill");
            if (fill) fill.style.width = pct + "%";

            if (status.status === "done") {
              var el = document.getElementById("export-inline-progress");
              if (el) el.classList.add("done");
              updateExportInline(100, stageLabels[3]);
              var downloadBtn = document.getElementById("btn-download-export");
              if (downloadBtn) {
                downloadBtn.onclick = function() { window.open(downloadUrl, "_blank"); };
              }
              clearInterval(exportPollTimer);
              exportPollTimer = null;
              var isVertical = getSelectedAspect() === "9:16";
              toast((isVertical ? "Vertical 9:16 " : "") + "Export complete!", "success");
              setTimeout(function() {
                if (downloadBtn) downloadBtn.click();
              }, 400);
            } else if (status.status === "error") {
              var el = document.getElementById("export-inline-progress");
              if (el) el.classList.add("error");
              updateExportInline(0, "Error");
              var retryBtn = document.getElementById("btn-retry-export");
              if (retryBtn) {
                retryBtn.onclick = function() {
                  hideExportInline();
                  startExport(lastExportClips);
                };
              }
              clearInterval(exportPollTimer);
              exportPollTimer = null;
              toast("Export failed: " + (status.error || "Unknown error"), "error");
            }
          })
          .catch(function() {});
      }, 500);
    }

    document.getElementById("btn-cancel-export").addEventListener("click", hideExportInline);

    function startExport(clipsToExport) {
      if (clipsToExport.length === 0) { toast("No clips to export", "error"); return; }
      lastExportClips = clipsToExport.slice();
      var payload = {
        video_url: currentVideoUrl,
        clips: clipsToExport.map(function(c) { return { start: c.start, end: c.end }; }),
        editor_options: buildEditorOptions()
      };
      fetch("/export-edit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
      .then(function(r) {
        if (!r.ok) throw new Error("Server error " + r.status);
        return r.json();
      })
      .then(function(data) {
        if (data.success && data.job_id) {
          pollExportStatus(data.job_id, data.download_url);
        } else {
          toast("Export failed: " + (data.error || "Unknown error"), "error");
        }
      })
      .catch(function(err) {
        toast("Export error: " + err.message, "error");
      });
    }

    document.getElementById("btn-export-all").addEventListener("click", function() {
      var selected = getSelectedClipObjects();
      startExport(selected.length ? selected : clipsData);
    });

    document.getElementById("btn-export-edit").addEventListener("click", function() {
      var activeClip = getActiveClip();
      startExport(activeClip ? [activeClip] : []);
    });

    /* ── Preview ── */

    document.getElementById("btn-preview-edit").addEventListener("click", function() {
      if (!currentVideoUrl) { toast("No video loaded", "error"); return; }
      var btn = document.getElementById("btn-preview-edit");
      var btnLabel = document.getElementById("btn-preview-edit-label");
      var activeClip = getActiveClip();
      btn.disabled = true;
      if (btnLabel) btnLabel.textContent = "Loading...";
      else btn.textContent = "Loading...";
      toast("Generating preview...", "info");
      var payload = { video_url: currentVideoUrl, editor_options: buildEditorOptions() };
      if (activeClip) {
        payload.t = (activeClip.start + activeClip.end) / 2;
      }
      fetch("/preview-clip", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
      .then(function(r) {
        if (!r.ok) throw new Error("Server error " + r.status);
        return r.json();
      })
      .then(function(data) {
        btn.disabled = false;
        if (btnLabel) btnLabel.textContent = "Preview Active Clip";
        else btn.textContent = "Preview";
        if (data.success) {
          var video = document.getElementById("editor-video");
          var img = document.getElementById("preview-image");
          if (video) video.style.display = "none";
          if (img) {
            img.src = data.preview_url + "?t=" + Date.now();
            img.style.display = "block";
            updatePreviewAspect();
          }
          toast("Preview ready", "success");
        } else {
          toast("Preview failed: " + (data.error || "Unknown error"), "error");
        }
      })
      .catch(function(err) {
        btn.disabled = false;
        if (btnLabel) btnLabel.textContent = "Preview Active Clip";
        else btn.textContent = "Preview";
        toast("Preview error: " + err.message, "error");
      });
    });

    /* ── Initial Data (if returning from analysis) ── */

    var dataScript = document.getElementById("editor-data");
    if (dataScript) {
      try {
        var data = JSON.parse(dataScript.textContent);
        clipsData = data.clips || [];
        currentVideoUrl = data.video_url || "";
        activeClipIndex = clipsData.length ? 0 : -1;
        selectedClips = {};
        renderClips();
        showPage("page-results");
      } catch(e) {}
    }
  });
})();
