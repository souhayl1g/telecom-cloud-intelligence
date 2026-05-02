# CONVENTIONS.md — Telecom Cloud Intelligence

> Codebase conventions and patterns
> Mapped: 2026-04-25

---

## Python Conventions

### Naming
- `snake_case` — functions, variables, module names
- `UPPER_SNAKE_CASE` — constants
- `PascalCase` — Pydantic models, dataclasses, class names
- `_prefix` — private helpers (e.g., `_db()`, `_setup_tracing()`)

### Section separators
```python
# --- Section Name ---
```

### Database access pattern (duplicated across all 4 services)
```python
@contextmanager
def _db():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
```
Uses `RealDictCursor` for dict-like row access. No ORM. No connection pooling.

### Error handling
```python
try:
    # ...
except HTTPException:
    raise  # re-raise FastAPI exceptions unchanged
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
```

### Logging
No logging library — plain `print()` with service prefix:
```python
print(f"[api-gateway] Starting up...")
print(f"[pipeline-worker] Run {run_id} complete")
```

### OTel tracing
`_setup_tracing()` helper duplicated in every service:
```python
def _setup_tracing():
    resource = Resource(attributes={"service.name": SERVICE_NAME})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=OTEL_ENDPOINT)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
```

---

## TypeScript / React Conventions

### Naming
- `camelCase` — functions, variables, hooks
- `PascalCase` — React components, interfaces, types
- `"use client"` — top of any component using hooks/browser APIs

### Section separators (TypeScript)
```typescript
/* ── Section Name ── */
```

### Auth proxy pattern (client pages needing backend data)
```typescript
// NEVER call :8000 directly from client components
// Always route through /api/platform-data
const res = await fetch('/api/platform-data');
```

### Outside-click pattern (menu/modal close)
```typescript
const ref = useRef<HTMLDivElement>(null);
useEffect(() => {
    const handler = (e: MouseEvent) => {
        if (ref.current && !ref.current.contains(e.target as Node)) {
            setOpen(false);
        }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
}, []);
```

### Safe fetch helpers
```typescript
// Returns null on failure — never throws
async function safeFetch(url: string): Promise<T | null>
async function safePost(url: string, body: unknown): Promise<T | null>
```

### Custom SVG charts (no chart library)
All charts are custom SVG components — no Recharts/Chart.js:
- `Sparkline` — mini line trend
- `DonutChart` — circular ratio chart
- `RadarChart` — pentagon radar
- `FeatureImportanceChart` — horizontal bars
- `ConfusionMatrix` — 2×2 heatmap
- `MetricBar` — horizontal progress bar

**Note:** Recharts is pinned to `2.15.3` for legacy pages. v3.x causes React error #310 — do NOT upgrade.

### API routes (Next.js BFF)
```typescript
// /api/platform-data/route.ts — SSR proxy
import { cookies } from "next/headers";
const token = cookies().get("auth_token")?.value;
// Forward to :8000 with Authorization: Bearer <token>
```

---

## Git Commit Convention

```
type(scope): description

Types: feat, fix, chore, docs, phase#
Example: feat(phase-5): L4 agent auto-approve logic
```

---

## CSS Architecture

### Class naming (BEM-like)
```
.l4-{component}        # L4 agent UI
.me-{component}        # Model evaluation page
.ai-copilot-{element}  # AI copilot FAB
```

### Tab panel pattern
```css
/* Panels hidden by default, shown with active class */
.l4-chat-panel { display: none; }
.l4-panel-active { display: flex !important; }
```

---

## Service Structure Pattern

Each microservice follows:
```
services/{name}/
  main.py          # FastAPI app + all routes
  requirements.txt # Python deps
  Dockerfile       # FROM python:3.11-slim
```

No subdirectory splitting — all routes in `main.py`.

---

## Known Anti-Patterns (do not replicate)

| Pattern | Location | Issue |
|---------|----------|-------|
| Pervasive `any` in TypeScript | `dashboard/app/**/*.tsx` | No type safety |
| `_db()` duplicated 4× | All services | Should be shared lib |
| `_setup_tracing()` duplicated 4× | All services | Should be shared lib |
| `print()` for logging | All services | Should use `logging` module |
| No connection pooling | All services | Creates new conn per request |
| Hardcoded metrics | `app/api/model-metrics/route.ts` | Not live from DB |
