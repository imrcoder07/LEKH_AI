/**
 * Frontend Configuration
 * Centralize hardcoded values for easier management and environment-specific customization
 */

window.LekhAIConfig = {
  // API Endpoints
  api: {
    baseUrl: '',  // Empty = use current origin; set to 'http://localhost:5000' for dev
    endpoints: {
      upload: '/api/upload',
      verify: '/api/verify',
      search: '/api/search',
      records: '/api/records',
      legal: '/api/legal',
      health: '/api/health',
      langToggle: '/api/lang/toggle',
      demoLogin: '/api/demo/login'
    }
  },

  // External CDN Resources
  cdn: {
    tailwindcss: 'https://cdn.tailwindcss.com',
    tailwindcssPlugins: ['forms', 'container-queries'],
    googleFonts: {
      preconnect: 'https://fonts.googleapis.com',
      crossorigin: 'https://fonts.gstatic.com',
      inter: 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900',
      notoSans: 'https://fonts.googleapis.com/css2?family=Noto+Sans:wght@400;500;700;800',
      materialSymbols: 'https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1'
    }
  },

  // Asset Versioning
  assets: {
    cssVersion: '1.3',
    jsVersion: '1.3',
    cacheBreaker: true  // Append version to URL for cache busting
  },

  // UI Timing & Animation
  ui: {
    modalTransitionDelay: 160,  // ms
    animationDuration: 2000,    // ms
    spinnerAnimationDuration: '2s',
    fileUploadTimeout: 120000,  // ms (2 minutes)
    verificationTimeout: 30000  // ms (30 seconds)
  },

  // File Upload Settings
  upload: {
    maxSizeBytes: 16 * 1024 * 1024,  // 16 MB
    acceptedExtensions: {
      allowed: ['pdf', 'png', 'jpg', 'jpeg', 'tiff', 'bmp'],
      displayText: 'PNG, JPG, JPEG, TIFF, BMP, PDF'
    },
    fileSizeUnits: ['B', 'KB', 'MB', 'GB']
  },

  // Session & Auth
  session: {
    defaultRole: 'user',  // Can be 'admin', 'user', 'auditor'
    sessionCookieHttpOnly: true,
    sessionCookieSamesite: 'Lax',
    sessionCookieSecure: false  // Set to true in production with HTTPS
  },

  // UI Element IDs (for easier refactoring)
  elements: {
    modals: {
      dpdp: 'dpdp-modal',
      upload: 'upload-modal',
      legal: 'legal-modal'
    },
    buttons: {
      uploadBtn: 'btn-upload',
      verifyBtn: 'btn-verify-ledger',
      toggleLangBtn: 'btn-toggle-lang',
      proceedBtn: 'btn-proceed',
      closeLegalTop: 'btn-close-legal-top',
      closeLegalBottom: 'btn-close-legal-bottom',
      printCert: 'btn-print-cert'
    },
    forms: {
      dpdpConsent: 'dpdp-consent-checkbox',
      fileInput: 'file-input',
      dropZone: 'drop-zone'
    },
    display: {
      uploadText: 'upload-text',
      fileMeta: 'file-meta',
      loadingState: 'loading-state',
      resultState: 'result-state',
      resultTitle: 'result-title',
      resultIcon: 'result-icon',
      resultDetails: 'result-details',
      verificationStatus: 'verification-status',
      recordsTable: 'records-tbody'
    }
  },

  // Feature Flags
  features: {
    enableDpdpConsent: true,
    enableAdminAutoLogin: true,  // Demo-only feature for dashboard
    enableLegalCertificates: true
  },

  // Language Settings
  i18n: {
    default: 'en',
    supported: ['en', 'hi']
  },

  /**
   * Helper: Build full API URL
   * @param {string} endpoint - The endpoint key (e.g., 'upload')
   * @param {object} params - Optional URL parameters {id, query, etc}
   * @returns {string} Full URL
   */
  getApiUrl(endpoint, params = {}) {
    const base = this.api.baseUrl || '';
    const path = this.api.endpoints[endpoint];
    if (!path) throw new Error(`Unknown endpoint: ${endpoint}`);
    
    let url = base + path;
    if (params.id) url = url.replace('<id>', params.id);
    if (params.query) url += `?${new URLSearchParams(params.query).toString()}`;
    
    return url;
  },

  /**
   * Helper: Get CSS asset URL with version
   * @returns {string}
   */
  getCssUrl(filename) {
    const version = this.assets.cacheBreaker ? `?v=${this.assets.cssVersion}` : '';
    return `/static/css/${filename}${version}`;
  },

  /**
   * Helper: Get JS asset URL with version
   * @returns {string}
   */
  getJsUrl(filename) {
    const version = this.assets.cacheBreaker ? `?v=${this.assets.jsVersion}` : '';
    return `/static/js/${filename}${version}`;
  }
};

// Example usage in app.js:
// fetch(window.LekhAIConfig.getApiUrl('upload'), { method: 'POST', body: formData })
// fetch(window.LekhAIConfig.getApiUrl('legal', { id: recordId }))
