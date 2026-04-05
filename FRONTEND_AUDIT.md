# Frontend Hardcoding Audit – Findings & Recommendations

## Summary
Found **20+ hardcoded values** in frontend files that should be externalized to a configuration file for better maintainability and environment-specific customization.

---

## 🔴 Critical Issues

### 1. **Scattered API Endpoints** (7+ locations)
All API calls are hardcoded with `/api/*` paths without any abstraction layer.

**Files:**
- `static/js/app.js` (lines 4, 108, 206)
- `templates/dashboard.html` (inline scripts, multiple locations)
- `templates/verify.html`, `templates/search.html` (presumed)

**Examples:**
```javascript
// ❌ BEFORE
fetch('/api/lang/toggle', { method: 'POST', ... })
fetch('/api/upload', { method: 'POST', body: formData })
fetch('/api/verify')
fetch('/api/demo/login', { method: 'POST', body: JSON.stringify({ role: 'admin' }) })
fetch(`/api/legal/${recordId}/certificate`, ...)

// ✅ AFTER
fetch(window.LekhAIConfig.getApiUrl('langToggle'), { method: 'POST', ... })
fetch(window.LekhAIConfig.getApiUrl('upload'), { method: 'POST', body: formData })
fetch(window.LekhAIConfig.getApiUrl('verify'))
fetch(window.LekhAIConfig.getApiUrl('demoLogin'), ...)
fetch(window.LekhAIConfig.getApiUrl('legal', { id: recordId }))
```

---

## 🟡 Medium Priority Issues

### 2. **Extern CDN URLs** (8+ hardcoded locations)
External CDNs for Tailwind CSS and Google Fonts are duplicated across multiple templates.

**Files:**
- `templates/index.html`, `templates/dashboard.html`, `templates/verify.html`, `templates/search.html`
- `stitch/*/code.html` (backup Stitch designs)

**Current State:**
```html
<!-- Scattered across 8+ files -->
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Noto+Sans:wght@400;500;700;800&display=swap" rel="stylesheet">
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
```

**Recommendation:**
Move to `static/js/config.js` and inject via JavaScript on page load to ensure consistency and allow environment switching (e.g., CDN fallback, local mirror).

---

### 3. **Asset Versioning** (4 hardcoded `?v=1.3`)
CSS and JS files include hardcoded version strings for cache-busting.

**Locations:**
- `templates/index.html` line 9
- `templates/dashboard.html` line 15
- `templates/verify.html` (presumed)
- All style.css and app.js references

**Issue:** Version updates require editing multiple files. Should be centralized.

---

### 4. **Magic Numbers & Timings** (5+ instances)

**Modal Transition Delay:**
- `app.js` line 53: `setTimeout(..., 160)` – hardcoded 160ms delay
- Dashboard HTML: inline `animation: pulseScale 2s` timing

**File Size Units:**
- `app.js` line 66: `const units = ['B', 'KB', 'MB', 'GB']`

**Timeout Values:**
- No explicit timeout configuration (implied 30s from Gemini API)

**Location-specific Strings:**
- `en-GB` date locale hardcoded for formatting

---

### 5. **Session Role Hardcoding** (Dashboard)
Admin role is hardcoded in the dashboard verification script.

**Location:** `templates/dashboard.html` (inline script)
```javascript
// ❌ HARDCODED ADMIN SESSION SETUP
if (!isAdminSessionSet) {
    const loginRes = await fetch('/api/demo/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: 'admin' })  // ← Hardcoded!
    });
    if (loginRes.ok) {
        isAdminSessionSet = true;
    }
}
```

**Impact:** Dashboard only works for admin role, preventing proper RBAC testing.

**Fix:** Make role configurable:
```javascript
const role = window.LekhAIConfig.session.dashboardRole || 'admin';
body: JSON.stringify({ role })
```

---

### 6. **Element ID Dependencies** (15+ hardcoded selectors)
HTML element IDs are scattered throughout JavaScript, making refactoring risky.

**Examples:**
```javascript
// Hardcoded across app.js and dashboard.html
document.getElementById('dpdp-modal')
document.getElementById('upload-modal')
document.getElementById('btn-upload')
document.getElementById('file-input')
document.getElementById('records-tbody')
document.getElementById('verification-status')
// ... many more
```

**Configuration Added:** See `LekhAIConfig.elements.*` in config.js.

---

## 🟢 Low Priority (Already in Config)

### 7. **Modal Styling & Layout**
- Padding: `2rem`, `1rem`, `0.5rem` (inline styles)
- Max-height: `400px` (inline styles)
- Border colors, shadows, etc.

**Status:** These are acceptable to keep inline (CSS can evolve independently).

---

## ✅ Improvements Made

### Config File Created
**File:** `static/js/config.js`
- Centralized API endpoints
- CDN URLs and plugins
- Asset versioning
- UI timings and timeouts
- Upload settings
- Session configuration
- Element ID references
- Feature flags
- Helper methods: `getApiUrl()`, `getCssUrl()`, `getJsUrl()`

### Templates Updated
- `templates/index.html` – Added config.js script tag
- `templates/dashboard.html` – Added config.js script tag

---

## 📋 Action Items for Full Implementation

### Phase 1: Core API Endpoint Refactoring
- [ ] Update `static/js/app.js` to use `window.LekhAIConfig.getApiUrl()`
- [ ] Replace all `fetch('/api/*')` calls with config-driven versions
- [ ] Test all API calls (upload, verify, search, etc.)
- [ ] Update `templates/verify.html` and `templates/search.html`

### Phase 2: Dashboard Hardcoding Cleanup
- [ ] Refactor dashboard inline script to use config element IDs
- [ ] Make admin role configurable in dashboard
- [ ] Use `LekhAIConfig.ui.*` for timings
- [ ] Test ledger verification with different roles

### Phase 3: CDN & Asset Management
- [ ] Move CDN URL injection to `config.js`
- [ ] Create helper for CDN URL construction with dynamic URL building
- [ ] Add fallback mechanism for CDN failures
- [ ] Update version numbers in config for production builds

### Phase 4: Environment-Specific Overrides
- [ ] Create `static/js/config.local.js` template for development
- [ ] Document environment variables for CI/CD pipeline
- [ ] Add CSS class for injecting Tailwind via script tag instead of inline

---

## 📝 Usage Example

After full implementation, developers would use:

```javascript
// Instead of:
fetch('/api/verify')

// Use:
fetch(window.LekhAIConfig.getApiUrl('verify'))
  .then(r => r.json())
  .then(data => console.log(data))
```

---

## 🚀 Benefits

1. **Maintainability:** Change API baseURL, CDN provider, or timings in one place
2. **Environment-Specific:** Support dev/staging/production configs
3. **Testing:** Easy to mock API endpoints or override timings
4. **Refactoring:** Element IDs centralized make DOM updates safer
5. **Deployment:** Version bump only requires updating `config.js`

---

## Notes

- Stitch design files (`stitch/*/code.html`) are backup exports and can be left as-is
- This refactoring is backward compatible; old code continues to work while being migrated
- No breaking changes to public APIs
