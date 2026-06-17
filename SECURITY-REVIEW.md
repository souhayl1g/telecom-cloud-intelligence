# Security Review Report — NeXoligence Platform
**Date:** 2026-06-10 | **Scope:** Full codebase | **Method:** practicalswan/agent-skills@security-review
**Reviewer:** Claude Code (Sonnet 4.6) | **Status:** ✅ Reviewed — 1 CRITICAL, 0 HIGH, 2 MEDIUM, 2 LOW

---

## Summary Table

| Severity | Count | Items |
|----------|-------|-------|
| 🔴 CRITICAL | 1 | Next.js 14.2.5 cache poisoning CVE |
| 🟠 HIGH | 0 | — |
| 🟡 MEDIUM | 2 | PostCSS XSS, Docker ports bound to 0.0.0.0 |
| 🔵 LOW | 2 | subprocess in actions.py, python-jose version |
| ⚪ INFO | 4 | No secrets in git, no SQL injection, no JWT bypass, no XSS |
| ✅ CLEAN | — | Secrets, SQL injection, JWT, XSS, auth bypass, dangerouslySetInnerHTML |

---

## CRITICAL

### 🔴 C-01 — Next.js 14.2.5 Cache Poisoning
- **File:** `dashboard/package.json:6`
- **CVE/Advisory:** [GHSA-gp8f-8m3g-qvj9](https://github.com/advisories/GHSA-gp8f-8m3g-qvj9)
- **CVSS:** 7.5 (High — but npm marks as Critical due to network exploitability)
- **CWE:** CWE-349 (Improper Data Authentication), CWE-639 (Authorization Bypass)
- **Confidence:** High — version confirmed (14.2.5), vulnerability range ≥14.0.0 <14.2.10

**What an attacker can do:**
An attacker can poison the Next.js page cache by sending crafted requests that cause malicious
content to be cached and served to legitimate users. No authentication required — purely network-level.
For a dashboard shown to a defense jury, this could cause wrong data to display during the live demo.

**Vulnerable code:**
```json
// dashboard/package.json
"next": "14.2.5"   // ← confirmed in range ≥14.0.0 <14.2.10
```

**Patch (review before applying):**
```bash
cd dashboard
npm install next@14.2.26
```
Then verify: `npm list next` should show 14.2.26 or later.
Check that the dashboard still builds: `npm run build`.

> **IMPORTANT:** `recharts` must stay at `2.x` (CLAUDE.md rule). The Next.js upgrade is patch-only
> (14.2.x → 14.2.26) — it does not affect React version or recharts compatibility.

---

## MEDIUM

### 🟡 M-01 — PostCSS XSS via Unescaped `</style>`
- **Advisory:** [GHSA-qx2v-qp2m-jg93](https://github.com/advisories/GHSA-qx2v-qp2m-jg93)
- **CVSS:** 6.1
- **Affected:** postcss < 8.5.10

**What an attacker can do:**
If user-controlled content reaches PostCSS CSS stringification (unlikely in this app — PostCSS
runs at build time, not runtime). Risk is Low in this specific setup but the advisory is MEDIUM.

**Patch:**
```bash
cd dashboard
npm install postcss@8.5.10
```

---

### 🟡 M-02 — Docker Ports Bound to 0.0.0.0 (All Interfaces)
- **File:** `docker-compose.yml`
- **Severity context:** LOW in WSL2 dev (host-only), MEDIUM for HCS deployment

**Exposed ports (all bound to 0.0.0.0):**
| Service | Port | Risk |
|---------|------|------|
| PostgreSQL | 5432 | ⚠️ DB directly reachable from network |
| MinIO | 9000, 9001 | ⚠️ Object storage API + console exposed |
| api-gateway | 8000 | Expected (public API) |
| ai-service | 8001 | ⚠️ Internal inference should not be public |
| auth-service | 8002 | Expected (public auth) |
| dashboard | 3001 | Expected |

**Risk:** In Huawei Cloud ECS deployment, if security groups are misconfigured, PostgreSQL (5432)
and MinIO (9000) would be directly accessible from the internet.

**Fix for HCS deployment** (do NOT change for dev — will break local setup):
```yaml
# docker-compose.prod.yml override — for HCS only
services:
  postgres:
    ports:
      - "127.0.0.1:5432:5432"   # localhost only
  minio:
    ports:
      - "127.0.0.1:9000:9000"
      - "127.0.0.1:9001:9001"
  ai-service:
    ports:
      - "127.0.0.1:8001:8001"   # internal — not public
```

---

## LOW

### 🔵 L-01 — subprocess.run in actions.py (Fixed Scope — Low Risk)
- **File:** `services/api-gateway/routers/actions.py:503`
- **Confidence:** High (safe as-is)

```python
proc = subprocess.run(
    ["python3", "/scripts/dump_model_metrics.py"],
    capture_output=True, text=True, timeout=30,
)
```

**Finding:** Command uses a hardcoded path — no user input reaches this call. Not injectable.
**Residual risk:** If the Docker volume (`./scripts:/scripts:ro`) were replaced with a malicious
script, the subprocess would execute it. The `:ro` (read-only) mount limits this.
**Status:** Acceptable for current scope. No change required.

---

### 🔵 L-02 — python-jose 3.3.0 (Older Version, No Active CVE)
- **Files:** `services/api-gateway/requirements.txt`, `services/auth-service/requirements.txt`
- **Current:** `python-jose[cryptography]==3.3.0`
- **Latest:** 3.3.0 is current stable (no newer version as of 2026-06)
- **Confidence:** High (no active CVE found)

**Note:** python-jose had historical vulnerabilities in <3.3.0. At 3.3.0 this is fine.
The `[cryptography]` extra ensures the secure cryptography backend is used.
**Status:** No action required.

---

## INFO — Clean Areas ✅

| Area | Check | Result |
|------|-------|--------|
| Git secrets | `.env` files tracked by git | ✅ None committed |
| Source secrets | Hardcoded passwords/keys in `.py`/`.ts` | ✅ None found |
| SQL injection | f-string raw queries in psycopg2 `execute()` | ✅ All use parameterized `%s` |
| JWT verification | `jwt.decode()` called without verify=False | ✅ All properly verified |
| Auth bypass | `algorithms=["none"]` or similar | ✅ Not present |
| XSS (Next.js) | `dangerouslySetInnerHTML` in TSX | ✅ Not used |
| SSRF | User-controlled URLs in server-side `fetch()` | ✅ Not present |
| Command injection | User input reaching `subprocess`/`os.system` | ✅ Not found |

---

## Action Priority

| Priority | Action | Effort |
|----------|--------|--------|
| **Do now** | `npm install next@14.2.26` in `dashboard/` | 2 min |
| **Do now** | `npm install postcss@8.5.10` in `dashboard/` | 2 min |
| **Before HCS** | Add `docker-compose.prod.yml` with localhost port bindings | 20 min |
| **Skip** | L-01, L-02 — no action required | — |

---

*Review each patch before applying. Nothing has been changed yet.*
