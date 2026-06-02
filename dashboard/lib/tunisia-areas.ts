/**
 * Tunisia area-code → governorate mapping.
 * TT cell-site naming mixes ISO-3 governorate codes (SFX, ZGO) with
 * full town names (SFAX_MALL_Indoor, HAMMAM_SIALA) and 2G/3G/4G prefixes.
 * This module normalizes them into the 24 governorate set.
 */

export const GOVERNORATES = [
    'Tunis', 'Ariana', 'Ben Arous', 'Manouba', 'Bizerte', 'Béja',
    'Jendouba', 'El Kef', 'Siliana', 'Kairouan', 'Kasserine',
    'Sidi Bouzid', 'Sousse', 'Monastir', 'Mahdia', 'Sfax',
    'Gabès', 'Médenine', 'Tataouine', 'Gafsa', 'Tozeur',
    'Kébili', 'Zaghouan', 'Nabeul',
] as const;

export type Governorate = typeof GOVERNORATES[number];

/** First-3-letter code → governorate. Covers TT's internal codes. */
const PREFIX_MAP: Record<string, Governorate> = {
    // Tunis metro
    TUN: 'Tunis', TNS: 'Tunis', BAB: 'Tunis', CAR: 'Tunis', CRT: 'Tunis',
    // Ariana
    ARI: 'Ariana', ARN: 'Ariana',
    // Ben Arous
    BAR: 'Ben Arous', BNA: 'Ben Arous', BAS: 'Ben Arous', HMM: 'Ben Arous',
    // Manouba
    MAN: 'Manouba', MNB: 'Manouba', MNO: 'Manouba', MNA: 'Manouba',
    // Bizerte
    BIZ: 'Bizerte', BNZ: 'Bizerte', BZT: 'Bizerte',
    // Béja
    BEJ: 'Béja', BJA: 'Béja',
    // Jendouba
    JEN: 'Jendouba', JND: 'Jendouba', JDB: 'Jendouba',
    // El Kef
    KEF: 'El Kef', KSE: 'El Kef', LKF: 'El Kef',
    // Siliana
    SIL: 'Siliana', SLN: 'Siliana',
    // Kairouan
    KAI: 'Kairouan', KRN: 'Kairouan', KRW: 'Kairouan',
    // Kasserine
    KAS: 'Kasserine', KSR: 'Kasserine', KSS: 'Kasserine',
    // Sidi Bouzid
    SID: 'Sidi Bouzid', SBZ: 'Sidi Bouzid', SDB: 'Sidi Bouzid',
    // Sousse — many TT sub-codes
    SOU: 'Sousse', SSE: 'Sousse', SLT: 'Sousse', SLO: 'Sousse', SAH: 'Sousse',
    // Monastir
    MON: 'Monastir', MSR: 'Monastir', MTR: 'Monastir',
    // Mahdia
    MAH: 'Mahdia', MHD: 'Mahdia',
    // Sfax
    SFX: 'Sfax', SFA: 'Sfax', SFS: 'Sfax', SKR: 'Sfax',
    // Gabès
    GAB: 'Gabès', GBS: 'Gabès', GBA: 'Gabès',
    // Médenine
    MED: 'Médenine', MDN: 'Médenine', DJB: 'Médenine', ZAR: 'Médenine',
    // Tataouine
    TAT: 'Tataouine', TTN: 'Tataouine',
    // Gafsa
    GAF: 'Gafsa', GFS: 'Gafsa', GFA: 'Gafsa',
    // Tozeur
    TOZ: 'Tozeur', TZR: 'Tozeur',
    // Kébili
    KEB: 'Kébili', KBL: 'Kébili', KBI: 'Kébili',
    // Zaghouan
    ZGO: 'Zaghouan', ZGT: 'Zaghouan', ZAG: 'Zaghouan', ZGN: 'Zaghouan',
    // Nabeul / Cap Bon
    NAB: 'Nabeul', NBL: 'Nabeul', HAM: 'Nabeul', KEL: 'Nabeul',
};

/** Full-word starts-with matches — handle descriptive site names. */
const FULL_NAME_MAP: Array<[string, Governorate]> = [
    ['SFAX', 'Sfax'],
    ['TUNIS', 'Tunis'],
    ['ARIANA', 'Ariana'],
    ['MANOUBA', 'Manouba'],
    ['BIZERTE', 'Bizerte'],
    ['BEJA', 'Béja'],
    ['BÉJA', 'Béja'],
    ['JENDOUBA', 'Jendouba'],
    ['KAIROUAN', 'Kairouan'],
    ['KASSERINE', 'Kasserine'],
    ['SOUSSE', 'Sousse'],
    ['MONASTIR', 'Monastir'],
    ['MAHDIA', 'Mahdia'],
    ['NABEUL', 'Nabeul'],
    ['ZAGHOUAN', 'Zaghouan'],
    ['ZAGHOUEN', 'Zaghouan'],
    ['SILIANA', 'Siliana'],
    ['GAFSA', 'Gafsa'],
    ['GABES', 'Gabès'],
    ['GABÈS', 'Gabès'],
    ['MEDENINE', 'Médenine'],
    ['TATAOUINE', 'Tataouine'],
    ['TOZEUR', 'Tozeur'],
    ['KEBILI', 'Kébili'],
    ['KÉBILI', 'Kébili'],
    ['ELKEF', 'El Kef'],
    ['LE_KEF', 'El Kef'],
    ['HAMMAMET', 'Nabeul'],
    ['HAMMAM_SOUSSE', 'Sousse'],
    ['HAMMAM_SIALA', 'Nabeul'],
    ['DJERBA', 'Médenine'],
    ['CARTHAGE', 'Tunis'],
    ['LA_MARSA', 'Tunis'],
    ['BARDO', 'Tunis'],
];

/**
 * Map any TT cell/site code or area name to a Tunisian governorate.
 * Returns null if it cannot be confidently classified.
 */
export function areaToGovernorate(area: string | null | undefined): Governorate | null {
    if (!area) return null;
    let s = area.toUpperCase().trim();
    if (!s || ['NULL', 'NONE', 'N/A'].includes(s)) return null;

    // Strip leading 2G_/3G_/4G_/5G_
    s = s.replace(/^[2-5]G_+/, '');

    // Try full-name match first (longest descriptive prefix wins)
    for (const [prefix, gov] of FULL_NAME_MAP) {
        if (s.startsWith(prefix)) return gov;
    }

    // Try 3-letter ISO-style prefix
    const m = s.match(/^[A-Z]{3}/);
    if (m && PREFIX_MAP[m[0]]) return PREFIX_MAP[m[0]];

    return null;
}

/** Aggregate per-area cell rows into per-governorate counts. */
export interface AreaRow {
    area: string;
    total: number;
    anomaly_count: number;
    rate: number;
}

export interface GovernorateRow {
    governorate: Governorate | 'Other';
    total: number;
    anomaly_count: number;
    rate: number;
    cell_count: number;
}

export function aggregateByGovernorate(rows: AreaRow[]): GovernorateRow[] {
    // Coerce nulls/NaN to 0 so downstream `.toFixed`/`.toLocaleString` calls
    // never crash even when the DB returns sparse rows.
    const safe = (v: unknown): number => (typeof v === 'number' && isFinite(v) ? v : 0);
    const buckets = new Map<Governorate | 'Other', GovernorateRow>();
    for (const r of rows) {
        const gov = areaToGovernorate(r.area) ?? 'Other';
        const t = safe(r.total);
        const ac = safe(r.anomaly_count);
        const b = buckets.get(gov);
        if (b) {
            b.total += t;
            b.anomaly_count += ac;
            b.cell_count += 1;
        } else {
            buckets.set(gov, {
                governorate: gov,
                total: t,
                anomaly_count: ac,
                rate: 0,
                cell_count: 1,
            });
        }
    }
    const out: GovernorateRow[] = [];
    for (const v of Array.from(buckets.values())) {
        v.rate = v.total ? +((v.anomaly_count / v.total) * 100).toFixed(2) : 0;
        out.push(v);
    }
    out.sort((a, b) => b.anomaly_count - a.anomaly_count);
    return out;
}
