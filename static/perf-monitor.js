/**
 * Performance Monitor — Phase 4: Real User Monitoring (RUM)
 * 
 * Lightweight, zero-dependency RUM using native Performance Observer APIs.
 * Measures Core Web Vitals (LCP, INP, CLS, TTFB, FCP) and custom app metrics.
 * Batches data and sends on visibility change or after 5s idle.
 * 
 * Opt-out: Set window.DISABLE_PERF_MONITOR = true before this script loads.
 * 
 * No PII is collected. All data is anonymized.
 */
(function () {
  "use strict";

  // ── Opt-out gate ────────────────────────────────────────────────────
  if (window.DISABLE_PERF_MONITOR) return;

  // ── Configuration ───────────────────────────────────────────────────
  var CONFIG = {
    endpoint: "/metrics",          // Flask endpoint
    batchInterval: 5000,            // Send batch after 5s idle
    maxBatchSize: 30,              // Flush early if batch grows large
    navTimingSample: 1.0,          // 100% sample rate for nav timing
    resourceWarnThreshold: 1000,    // Warn if resource > 1s
    domNodeLimit: 1500,            // Warn if DOM nodes exceed this
    listenerWarnThreshold: 700,    // Warn if event listeners exceed this
    bundleSizeLimits: {             // Budget thresholds (KB, uncompressed)
      "app.js": 50,
      "style.css": 50
    }
  };

  // ── Rating thresholds (Web Vitals) ─────────────────────────────────
  function rateLCP(v) { return v <= 2500 ? "good" : v <= 4000 ? "needs-improvement" : "poor"; }
  function rateFID(v) { return v <= 100 ? "good" : v <= 300 ? "needs-improvement" : "poor"; }
  function rateINP(v) { return v <= 200 ? "good" : v <= 500 ? "needs-improvement" : "poor"; }
  function rateCLS(v) { return v <= 0.1 ? "good" : v <= 0.25 ? "needs-improvement" : "poor"; }
  function rateTTFB(v) { return v <= 800 ? "good" : v <= 1800 ? "needs-improvement" : "poor"; }
  function rateFCP(v) { return v <= 1800 ? "good" : v <= 3000 ? "needs-improvement" : "poor"; }

  // ── Metric batch queue ───────────────────────────────────────────────
  var batch = [];
  var flushTimer = null;
  var sent = false; // prevent double-send on pagehide + visibilitychange

  function scheduleFlush() {
    if (flushTimer) return;
    flushTimer = setTimeout(function () {
      flushBatch();
    }, CONFIG.batchInterval);
  }

  function enqueue(metric) {
    batch.push(metric);
    if (batch.length >= CONFIG.maxBatchSize) {
      flushBatch();
    } else {
      scheduleFlush();
    }
  }

  function flushBatch() {
    clearTimeout(flushTimer);
    flushTimer = null;
    if (batch.length === 0) return;

    var payload = batch.splice(0, batch.length);
    sendPayload(payload);
  }

  function sendPayload(payload) {
    // Use sendBeacon for reliability on page unload; fallback to fetch
    var data = JSON.stringify({
      metrics: payload,
      url: sanitizeUrl(location.href),
      ua: simplifyUA(navigator.userAgent),
      ts: Date.now()
    });

    if (navigator.sendBeacon) {
      try {
        var blob = new Blob([data], { type: "application/json" });
        navigator.sendBeacon(CONFIG.endpoint, blob);
        return;
      } catch (_) { /* fall through to fetch */ }
    }

    // Fallback: fetch with keepalive
    try {
      fetch(CONFIG.endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: data,
        keepalive: true
      }).catch(function () { /* silent */ });
    } catch (_) { /* silent */ }
  }

  // ── Anonymization helpers ────────────────────────────────────────────
  function sanitizeUrl(url) {
    // Strip query strings and hashes to avoid leaking tokens/PII
    try {
      var u = new URL(url);
      return u.origin + u.pathname;
    } catch (_) {
      return url.split("?")[0].split("#")[0];
    }
  }

  function simplifyUA(ua) {
    // Return simplified browser info — no full UA string (PII risk)
    if (ua.indexOf("Edg/") > -1) return "Edge";
    if (ua.indexOf("Chrome/") > -1 && ua.indexOf("Safari/") > -1) return "Chrome";
    if (ua.indexOf("Firefox/") > -1) return "Firefox";
    if (ua.indexOf("Safari/") > -1 && ua.indexOf("Chrome/") === -1) return "Safari";
    return "Other";
  }

  // ── Core Web Vitals observers ────────────────────────────────────────

  // LCP — Largest Contentful Paint
  function observeLCP() {
    if (!("PerformanceObserver" in window)) return;
    try {
      var po = new PerformanceObserver(function (list) {
        var entries = list.getEntries();
        if (entries.length > 0) {
          var last = entries[entries.length - 1];
          enqueue({
            name: "LCP",
            value: Math.round(last.startTime),
            rating: rateLCP(last.startTime),
            source: "PerformanceObserver"
          });
        }
      });
      po.observe({ type: "largest-contentful-paint", buffered: true });
    } catch (_) { /* unsupported */ }
  }

  // INP — Interaction to Next Paint (preferred over FID)
  function observeINP() {
    if (!("PerformanceObserver" in window)) return;
    try {
      var po = new PerformanceObserver(function (list) {
        var entries = list.getEntries();
        for (var i = 0; i < entries.length; i++) {
          var e = entries[i];
          if (e.interactionId > 0) {
            var duration = e.duration || (e.processingEnd - e.startTime);
            enqueue({
              name: "INP",
              value: Math.round(duration),
              rating: rateINP(duration),
              source: "PerformanceObserver"
            });
          }
        }
      });
      po.observe({ type: "event", buffered: true });
    } catch (_) { /* unsupported — fall back to FID */ observeFID(); }
  }

  // FID — First Input Delay (fallback if INP unsupported)
  function observeFID() {
    if (!("PerformanceObserver" in window)) return;
    try {
      var po = new PerformanceObserver(function (list) {
        var entries = list.getEntries();
        for (var i = 0; i < entries.length; i++) {
          var e = entries[i];
          enqueue({
            name: "FID",
            value: Math.round(e.processingStart - e.startTime),
            rating: rateFID(e.processingStart - e.startTime),
            source: "PerformanceObserver"
          });
        }
      });
      po.observe({ type: "first-input", buffered: true });
    } catch (_) { /* unsupported */ }
  }

  // CLS — Cumulative Layout Shift
  function observeCLS() {
    if (!("PerformanceObserver" in window)) return;
    var clsValue = 0;
    var clsEntries = [];
    var sessionValue = 0;
    var sessionEntries = [];

    try {
      var po = new PerformanceObserver(function (list) {
        for (var i = 0; i < list.getEntries().length; i++) {
          var entry = list.getEntries()[i];
          // Only count layout shifts without recent user input
          if (!entry.hadRecentInput) {
            sessionValue += entry.value;
            sessionEntries.push(entry);
          }
        }
      });
      po.observe({ type: "layout-shift", buffered: true });

      // Report final CLS on page hide
      var reportCLS = function () {
        if (sessionValue > clsValue) {
          clsValue = sessionValue;
          clsEntries = sessionEntries.slice();
        }
        enqueue({
          name: "CLS",
          value: Math.round(clsValue * 10000) / 10000, // 4 decimal places
          rating: rateCLS(clsValue),
          source: "PerformanceObserver"
        });
      };

      if (document.visibilityState) {
        document.addEventListener("visibilitychange", function () {
          if (document.visibilityState === "hidden") reportCLS();
        });
      }
      document.addEventListener("pagehide", reportCLS);
    } catch (_) { /* unsupported */ }
  }

  // TTFB — Time to First Byte
  function measureTTFB() {
    try {
      var navEntries = performance.getEntriesByType("navigation");
      if (navEntries.length > 0) {
        var ttfb = navEntries[0].responseStart;
        enqueue({
          name: "TTFB",
          value: Math.round(ttfb),
          rating: rateTTFB(ttfb),
          source: "PerformanceObserver"
        });
      }
    } catch (_) { /* fallback */ }
  }

  // FCP — First Contentful Paint
  function measureFCP() {
    if (!("PerformanceObserver" in window)) return;
    try {
      var po = new PerformanceObserver(function (list) {
        var entries = list.getEntries();
        for (var i = 0; i < entries.length; i++) {
          if (entries[i].name === "first-contentful-paint") {
            enqueue({
              name: "FCP",
              value: Math.round(entries[i].startTime),
              rating: rateFCP(entries[i].startTime),
              source: "PerformanceObserver"
            });
            po.disconnect();
          }
        }
      });
      po.observe({ type: "paint", buffered: true });
    } catch (_) { /* unsupported */ }
  }

  // ── Custom app metrics ───────────────────────────────────────────────
  // These are called from app.js to track video upload, analysis, export durations

  window.__perfMark = function (label) {
    if (window.DISABLE_PERF_MONITOR) return;
    try { performance.mark(label); } catch (_) { /* unsupported */ }
  };

  window.__perfMeasure = function (name, startMark, endMark) {
    if (window.DISABLE_PERF_MONITOR) return;
    try {
      performance.measure(name, startMark, endMark);
      var entries = performance.getEntriesByName(name, "measure");
      if (entries.length > 0) {
        var duration = entries[entries.length - 1].duration;
        enqueue({
          name: name,
          value: Math.round(duration),
          rating: duration <= 3000 ? "good" : duration <= 8000 ? "needs-improvement" : "poor",
          source: "custom"
        });
      }
    } catch (_) { /* unsupported */ }
  };

  // Convenience: track a timed operation returning a promise
  window.__perfTrack = function (name, fn) {
    if (window.DISABLE_PERF_MONITOR) return fn();
    var startMark = name + "-start";
    var endMark = name + "-end";
    performance.mark(startMark);
    var result = fn();
    if (result && typeof result.then === "function") {
      return result.then(function (val) {
        performance.mark(endMark);
        __perfMeasure(name, startMark, endMark);
        return val;
      }).catch(function (err) {
        performance.mark(endMark);
        __perfMeasure(name, startMark, endMark);
        // Also report the error
        enqueue({
          name: name + "-error",
          value: 1,
          rating: "poor",
          source: "custom",
          detail: (err && err.message) ? err.message.substring(0, 200) : "unknown"
        });
        throw err;
      });
    }
    performance.mark(endMark);
    __perfMeasure(name, startMark, endMark);
    return result;
  };

  // ── Resource timing warnings ─────────────────────────────────────────
  function checkResourceTiming() {
    try {
      var resources = performance.getEntriesByType("resource");
      for (var i = 0; i < resources.length; i++) {
        var r = resources[i];
        var duration = r.responseEnd - r.startTime;
        if (duration > CONFIG.resourceWarnThreshold) {
          enqueue({
            name: "slow-resource",
            value: Math.round(duration),
            rating: "needs-improvement",
            source: "resource-timing",
            detail: r.name.split("/").pop().substring(0, 100)
          });
        }
      }
    } catch (_) { /* unsupported */ }
  }

  // ── DOM node count check ─────────────────────────────────────────────
  function checkDOMSize() {
    var count = document.querySelectorAll("*").length;
    if (count > CONFIG.domNodeLimit) {
      enqueue({
        name: "dom-nodes",
        value: count,
        rating: "poor",
        source: "budget-check"
      });
    }
  }

  // ── Event listener count check ────────────────────────────────────────
  function checkListenerCount() {
    // Chrome-only: performance.eventCounts
    var total = 0;
    if (performance && performance.eventCounts) {
      performance.eventCounts.forEach(function (v) { total += v; });
      if (total > CONFIG.listenerWarnThreshold) {
        enqueue({
          name: "event-listeners",
          value: total,
          rating: total > 1500 ? "poor" : "needs-improvement",
          source: "budget-check"
        });
      }
    }
  }

  // ── Bundle size budget check ──────────────────────────────────────────
  function checkBundleSizes() {
    try {
      var resources = performance.getEntriesByType("resource");
      for (var i = 0; i < resources.length; i++) {
        var r = resources[i];
        var filename = r.name.split("/").pop().split("?")[0].split("#")[0];
        for (var key in CONFIG.bundleSizeLimits) {
          if (filename === key || r.name.indexOf("/" + key) > -1) {
            var sizeKB = Math.round(r.transferSize / 1024);
            var limitKB = CONFIG.bundleSizeLimits[key];
            if (sizeKB > limitKB) {
              enqueue({
                name: "bundle-size",
                value: sizeKB,
                rating: "needs-improvement",
                source: "budget-check",
                detail: filename + " (" + sizeKB + "KB > " + limitKB + "KB budget)"
              });
            }
          }
        }
      }
    } catch (_) { /* unsupported */ }
  }

  // ── Global error tracking ─────────────────────────────────────────────
  function setupErrorTracking() {
    window.addEventListener("error", function (evt) {
      enqueue({
        name: "js-error",
        value: 1,
        rating: "poor",
        source: "error-handler",
        detail: (evt.message || "").substring(0, 200),
        filename: (evt.filename || "").split("/").pop().substring(0, 80),
        lineno: evt.lineno || 0,
        colno: evt.colno || 0
      });
    });

    window.addEventListener("unhandledrejection", function (evt) {
      var reason = "";
      if (evt.reason instanceof Error) {
        reason = evt.reason.message;
      } else if (typeof evt.reason === "string") {
        reason = evt.reason;
      } else {
        reason = String(evt.reason);
      }
      enqueue({
        name: "unhandled-promise",
        value: 1,
        rating: "poor",
        source: "error-handler",
        detail: reason.substring(0, 200)
      });
    });
  }

  // ── Failed API call tracking ──────────────────────────────────────────
  // Monkey-patch fetch to track failed API calls
  function setupAPITracking() {
    var originalFetch = window.fetch;
    if (!originalFetch) return;

    window.fetch = function () {
      var args = arguments;
      var url = typeof args[0] === "string" ? args[0] : (args[0] && args[0].url) || "";
      var startTime = performance.now();

      return originalFetch.apply(this, args).then(
        function (response) {
          var duration = performance.now() - startTime;
          if (!response.ok) {
            enqueue({
              name: "api-error",
              value: Math.round(duration),
              rating: response.status >= 500 ? "poor" : "needs-improvement",
              source: "api-tracker",
              detail: sanitizeUrl(url) + " " + response.status
            });
          }
          return response;
        },
        function (err) {
          var duration = performance.now() - startTime;
          enqueue({
            name: "api-failure",
            value: Math.round(duration),
            rating: "poor",
            source: "api-tracker",
            detail: sanitizeUrl(url) + " network-error"
          });
          throw err;
        }
      );
    };
  }

  // ── Page visibility handler (flush on hide) ───────────────────────────
  function setupVisibilityHandler() {
    var handler = function () {
      if (document.visibilityState === "hidden" && !sent) {
        sent = true;
        // Final checks before leaving
        checkResourceTiming();
        checkDOMSize();
        checkListenerCount();
        checkBundleSizes();
        flushBatch();
      }
    };
    document.addEventListener("visibilitychange", handler);
    // Also handle pagehide for older browsers
    window.addEventListener("pagehide", function () {
      if (!sent) {
        sent = true;
        flushBatch();
      }
    });
  }

  // ── Initialize ────────────────────────────────────────────────────────
  function init() {
    if (window.DISABLE_PERF_MONITOR) return;

    // Core Web Vitals
    observeLCP();
    observeINP();
    observeCLS();
    measureTTFB();
    measureFCP();

    // Error & API tracking
    setupErrorTracking();
    setupAPITracking();

    // Visibility handler for batch flush
    setupVisibilityHandler();

    // Delayed budget checks (wait for page to stabilize)
    setTimeout(function () {
      checkResourceTiming();
      checkDOMSize();
      checkListenerCount();
      checkBundleSizes();
    }, 3000);

    // Schedule periodic flush
    scheduleFlush();
  }

  // Start when DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

})();