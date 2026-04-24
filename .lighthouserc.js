module.exports = {
  ci: {
    collect: {
      // Start a static server for Lighthouse CI audits
      startServerCommand: "python main.py",
      startServerReadyPattern: "Running on",
      url: ["http://localhost:5000/"],
      numberOfRuns: 3,
    },
    assert: {
      assertions: {
        // ── Performance budgets ──────────────────────────────────────
        // Core Web Vitals thresholds (Lighthouse CI will fail if these
        // are not met, keeping regressions from slipping through.)

        "categories:performance": ["warn", { minScore: 0.85 }],
        "categories:accessibility": ["warn", { minScore: 0.90 }],
        "categories:best-practices": ["warn", { minScore: 0.90 }],
        "categories:seo": ["warn", { minScore: 0.90 }],

        // Largest Contentful Paint < 2.5s (good)
        "largest-contentful-paint": ["error", { maxNumericValue: 2500 }],

        // Cumulative Layout Shift < 0.1 (good)
        "cumulative-layout-shift": ["error", { maxNumericValue: 0.1 }],

        // Total Blocking Time < 200ms (good)
        "total-blocking-time": ["warn", { maxNumericValue: 200 }],

        // First Contentful Paint < 1.8s (good)
        "first-contentful-paint": ["warn", { maxNumericValue: 1800 }],

        // Time to Interactive < 3.8s
        "interactive": ["warn", { maxNumericValue: 3800 }],

        // ── Resource budgets ─────────────────────────────────────────
        "resource-summary:scriptSize": ["warn", { maxNumericValue: 200000 }],
        "resource-summary:stylesheetSize": ["warn", { maxNumericValue: 50000 }],
        "resource-summary:imageSize": ["warn", { maxNumericValue: 500000 }],
        "resource-summary:totalSize": ["warn", { maxNumericValue: 1500000 }],

        // ── Accessibility & SEO ──────────────────────────────────────
        "document-title": ["error", { minLength: 1 }],
        "meta-description": ["error", { minLength: 1 }],
        "html-has-lang": ["error"],
        "viewport": ["error"],
      },
    },
    upload: {
      // Uncomment and configure to upload results to Lighthouse CI server
      // target: "lhci",
      // serverBaseUrl: "http://your-lhci-server:9001",
      // token: process.env.LHCI_TOKEN,
    },
  },
};