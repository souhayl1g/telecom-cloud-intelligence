// Single source of truth for time formatting across the dashboard.
// Backend (PostgreSQL `now()` / Python `datetime.utcnow()`) emits ISO strings
// without a TZ suffix. JavaScript's Date parser then treats them as LOCAL time
// instead of UTC, producing a -1h drift in Tunisia (UTC+1, no DST).
// Forcing the `Z` suffix when missing makes parsing TZ-safe, then we render in
// the project's canonical TZ via `Intl.DateTimeFormat`.

const TUNIS_TZ = 'Africa/Tunis';
const HAS_OFFSET = /[zZ]|[+-]\d{2}:?\d{2}$/;

export function toTunisDate(input: string | number | Date | null | undefined): Date | null {
    if (input == null) return null;
    if (input instanceof Date) return isNaN(input.getTime()) ? null : input;
    if (typeof input === 'number') {
        const d = new Date(input);
        return isNaN(d.getTime()) ? null : d;
    }
    const s = HAS_OFFSET.test(input) ? input : input + 'Z';
    const d = new Date(s);
    return isNaN(d.getTime()) ? null : d;
}

function fmt(input: string | number | Date | null | undefined, opts: Intl.DateTimeFormatOptions, locale = 'en-GB'): string {
    const d = toTunisDate(input);
    if (!d) return '—';
    return d.toLocaleString(locale, { timeZone: TUNIS_TZ, ...opts });
}

export const formatTunisTime = (input: string | number | Date | null | undefined): string =>
    fmt(input, { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });

export const formatTunisShortTime = (input: string | number | Date | null | undefined): string =>
    fmt(input, { hour: '2-digit', minute: '2-digit', hour12: false });

export const formatTunisDate = (input: string | number | Date | null | undefined): string =>
    fmt(input, { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' }, 'en-US');

export const formatTunisDateTime = (input: string | number | Date | null | undefined): string =>
    fmt(input, {
        year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
    });

export const formatTunisDateShort = (input: string | number | Date | null | undefined): string =>
    fmt(input, { year: 'numeric', month: '2-digit', day: '2-digit' });

// Relative time (e.g. "24s ago", "3m ago") — used by LIVE counter / last-refresh chips.
export function formatRelative(input: string | number | Date | null | undefined, nowMs: number = Date.now()): string {
    const d = toTunisDate(input);
    if (!d) return '—';
    const diffSec = Math.max(0, Math.round((nowMs - d.getTime()) / 1000));
    if (diffSec < 60) return `${diffSec}s ago`;
    const m = Math.floor(diffSec / 60);
    if (m < 60) return `${m}m ago`;
    const h = Math.floor(m / 60);
    if (h < 24) return `${h}h ago`;
    return `${Math.floor(h / 24)}d ago`;
}

// Duration in seconds between two timestamps (start, end). Real wall-clock — no faking.
export function durationSeconds(start: string | number | Date | null | undefined, end: string | number | Date | null | undefined): number | null {
    const a = toTunisDate(start);
    const b = toTunisDate(end);
    if (!a || !b) return null;
    return Math.max(0, (b.getTime() - a.getTime()) / 1000);
}

// Safe `.toFixed` for values that may arrive null/undefined/NaN from the API.
// Returns '—' instead of crashing the render tree.
export function safeFixed(value: number | null | undefined, decimals = 2, fallback = "—"): string {
    if (value == null || typeof value !== "number" || !isFinite(value)) return fallback;
    return value.toFixed(decimals);
}

export function formatDuration(seconds: number | null | undefined): string {
    if (seconds == null || isNaN(seconds)) return '—';
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    const m = Math.floor(seconds / 60);
    const s = Math.round(seconds - m * 60);
    return `${m}m ${s}s`;
}
