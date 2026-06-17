"""OSS↔CEM correlation engine — Pearson + Spearman on real available KPIs.

Join-key contract
-----------------
OSS rows carry a fine-grained cell-site `area` (4300+ distinct names like
``2G_Africa``, ``SFAX_MALL_Indoor``); BSS rows carry a 24-value governorate
``area`` (``Tunis``, ``GABES`` …). A raw string join intersects on ~1 value,
so the engine used to return zero correlations. `_canon_gov` normalizes BOTH
sides to the same canonical governorate key before bucketing — the Python
mirror of ``dashboard/lib/tunisia-areas.ts``.
"""
import numpy as np
from scipy import stats

# ── Geo normalization: any TT area/cell name → canonical governorate ──
# Canonical keys are ASCII-uppercase to dodge accent/encoding mismatches.
_GOV_SYNONYMS = {
    "TUNIS": "TUNIS", "ARIANA": "ARIANA",
    "BEN_AROUS": "BEN_AROUS", "BEN AROUS": "BEN_AROUS",
    "MANOUBA": "MANOUBA", "BIZERTE": "BIZERTE",
    "BEJA": "BEJA", "BÉJA": "BEJA",
    "JENDOUBA": "JENDOUBA", "KEF": "EL_KEF", "EL_KEF": "EL_KEF", "ELKEF": "EL_KEF",
    "SILIANA": "SILIANA", "KAIROUAN": "KAIROUAN", "KASSERINE": "KASSERINE",
    "SIDI_BOUZID": "SIDI_BOUZID", "SIDI BOUZID": "SIDI_BOUZID",
    "SOUSSE": "SOUSSE", "MONASTIR": "MONASTIR", "MAHDIA": "MAHDIA",
    "SFAX": "SFAX", "GABES": "GABES", "GABÈS": "GABES",
    "MEDENINE": "MEDENINE", "TATAOUINE": "TATAOUINE",
    "GAFSA": "GAFSA", "TOZEUR": "TOZEUR",
    "KEBILI": "KEBILI", "KÉBILI": "KEBILI",
    "ZAGHOUAN": "ZAGHOUAN", "ZAGHOUEN": "ZAGHOUAN",
    "NABEUL": "NABEUL",
}

# Full-word starts-with matches for descriptive OSS site names.
_FULL_NAME_MAP = [
    ("SFAX", "SFAX"), ("TUNIS", "TUNIS"), ("ARIANA", "ARIANA"),
    ("MANOUBA", "MANOUBA"), ("BIZERTE", "BIZERTE"), ("BEJA", "BEJA"),
    ("JENDOUBA", "JENDOUBA"), ("KAIROUAN", "KAIROUAN"), ("KASSERINE", "KASSERINE"),
    ("SOUSSE", "SOUSSE"), ("MONASTIR", "MONASTIR"), ("MAHDIA", "MAHDIA"),
    ("NABEUL", "NABEUL"), ("ZAGHOUAN", "ZAGHOUAN"), ("ZAGHOUEN", "ZAGHOUAN"),
    ("SILIANA", "SILIANA"), ("GAFSA", "GAFSA"), ("GABES", "GABES"),
    ("MEDENINE", "MEDENINE"), ("TATAOUINE", "TATAOUINE"), ("TOZEUR", "TOZEUR"),
    ("KEBILI", "KEBILI"), ("ELKEF", "EL_KEF"), ("LE_KEF", "EL_KEF"),
    ("HAMMAMET", "NABEUL"), ("HAMMAM_SOUSSE", "SOUSSE"), ("HAMMAM_SIALA", "NABEUL"),
    ("DJERBA", "MEDENINE"), ("CARTHAGE", "TUNIS"), ("LA_MARSA", "TUNIS"),
    ("BARDO", "TUNIS"), ("SIDI_BOUZID", "SIDI_BOUZID"),
]

# First-3-letter ISO-style codes TT embeds in cell names.
_PREFIX_MAP = {
    "TUN": "TUNIS", "TNS": "TUNIS", "BAB": "TUNIS", "CAR": "TUNIS", "CRT": "TUNIS",
    "ARI": "ARIANA", "ARN": "ARIANA",
    "BAR": "BEN_AROUS", "BNA": "BEN_AROUS", "BAS": "BEN_AROUS", "HMM": "BEN_AROUS",
    "MAN": "MANOUBA", "MNB": "MANOUBA", "MNO": "MANOUBA", "MNA": "MANOUBA",
    "BIZ": "BIZERTE", "BNZ": "BIZERTE", "BZT": "BIZERTE",
    "BEJ": "BEJA", "BJA": "BEJA",
    "JEN": "JENDOUBA", "JND": "JENDOUBA", "JDB": "JENDOUBA",
    "KEF": "EL_KEF", "KSE": "EL_KEF", "LKF": "EL_KEF",
    "SIL": "SILIANA", "SLN": "SILIANA",
    "KAI": "KAIROUAN", "KRN": "KAIROUAN", "KRW": "KAIROUAN",
    "KAS": "KASSERINE", "KSR": "KASSERINE", "KSS": "KASSERINE",
    "SID": "SIDI_BOUZID", "SBZ": "SIDI_BOUZID", "SDB": "SIDI_BOUZID",
    "SOU": "SOUSSE", "SSE": "SOUSSE", "SLT": "SOUSSE", "SLO": "SOUSSE", "SAH": "SOUSSE",
    "MON": "MONASTIR", "MSR": "MONASTIR", "MTR": "MONASTIR",
    "MAH": "MAHDIA", "MHD": "MAHDIA",
    "SFX": "SFAX", "SFA": "SFAX", "SFS": "SFAX", "SKR": "SFAX",
    "GAB": "GABES", "GBS": "GABES", "GBA": "GABES",
    "MED": "MEDENINE", "MDN": "MEDENINE", "DJB": "MEDENINE", "ZAR": "MEDENINE",
    "TAT": "TATAOUINE", "TTN": "TATAOUINE",
    "GAF": "GAFSA", "GFS": "GAFSA", "GFA": "GAFSA",
    "TOZ": "TOZEUR", "TZR": "TOZEUR",
    "KEB": "KEBILI", "KBL": "KEBILI", "KBI": "KEBILI",
    "ZGO": "ZAGHOUAN", "ZGT": "ZAGHOUAN", "ZAG": "ZAGHOUAN", "ZGN": "ZAGHOUAN",
    "NAB": "NABEUL", "NBL": "NABEUL", "HAM": "NABEUL", "KEL": "NABEUL",
}


def _canon_gov(area):
    """Map any TT area/cell name to a canonical governorate key, or None."""
    if not area:
        return None
    s = str(area).upper().strip()
    if not s or s in ("NULL", "NONE", "N/A"):
        return None
    # Exact governorate-name match (BSS side: 'GABES', 'Ben Arous', 'Zaghouen'…).
    if s in _GOV_SYNONYMS:
        return _GOV_SYNONYMS[s]
    # Strip leading 2G_/3G_/4G_/5G_ (OSS cell-site prefixes).
    import re
    s = re.sub(r"^[2-5]G_+", "", s)
    if s in _GOV_SYNONYMS:
        return _GOV_SYNONYMS[s]
    # Descriptive full-name prefix (longest wins by table order).
    for prefix, gov in _FULL_NAME_MAP:
        if s.startswith(prefix):
            return gov
    # 3-letter ISO-style prefix.
    m = re.match(r"^[A-Z]{3}", s)
    if m and m.group(0) in _PREFIX_MAP:
        return _PREFIX_MAP[m.group(0)]
    return None

try:
    import dcor
    DCOR_AVAILABLE = True
except Exception as e:
    DCOR_AVAILABLE = False
    print(f"[correlations] dcor unavailable ({e}) — distance correlation skipped")


def _mean(vals):
    return np.mean(vals) if vals else np.nan


def _safe_correlation(arr_x, arr_y, method):
    """Compute correlation only if both arrays have variance and no NaN."""
    if len(arr_x) < 3 or len(arr_y) < 3:
        return np.nan, np.nan
    if np.all(arr_x == arr_x[0]) or np.all(arr_y == arr_y[0]):
        return np.nan, np.nan
    if np.any(np.isnan(arr_x)) or np.any(np.isnan(arr_y)):
        return np.nan, np.nan
    fn = stats.pearsonr if method == "pearson" else stats.spearmanr
    try:
        corr_val, p_val = fn(arr_x, arr_y)
        return float(corr_val), float(p_val)
    except Exception:
        return np.nan, np.nan


def compute_correlations(oss_records: list[dict], bss_records: list[dict]) -> list[dict]:
    """Compute Pearson + Spearman between available OSS KPIs and BSS outcomes per area."""
    # Aggregate OSS KPIs by area (area = region/governorate)
    area_oss: dict = {}
    for r in oss_records:
        raw_area = r.get("area", r.get("region", r.get("cell_id", "unknown")))
        area = _canon_gov(raw_area)
        if area is None:
            continue  # unmappable cell-site name — can't join to a governorate
        if area not in area_oss:
            area_oss[area] = {
                "tput": [], "lat": [], "loss": [], "jitter": [],
                "users": [], "rsrp": [], "load": [], "cdr": [], "users_max": [],
            }
        if r.get("throughput_mbps") is not None:
            area_oss[area]["tput"].append(r["throughput_mbps"])
        if r.get("latency_ms") is not None:
            area_oss[area]["lat"].append(r["latency_ms"])
        pl = r.get("packet_loss_pct", r.get("packet_loss_rate"))
        if pl is not None:
            area_oss[area]["loss"].append(pl)
        if r.get("jitter_ms") is not None:
            area_oss[area]["jitter"].append(r["jitter_ms"])
        if r.get("active_users") is not None:
            area_oss[area]["users"].append(r["active_users"])
        if r.get("signal_rsrp_dbm") is not None:
            area_oss[area]["rsrp"].append(r["signal_rsrp_dbm"])
        if r.get("cell_load_pct") is not None:
            area_oss[area]["load"].append(r["cell_load_pct"])
        if r.get("call_drop_rate") is not None:
            area_oss[area]["cdr"].append(r["call_drop_rate"])
        if r.get("active_users_max") is not None:
            area_oss[area]["users_max"].append(r["active_users_max"])

    # Aggregate BSS outcomes by area
    area_bss: dict = {}
    for r in bss_records:
        area = _canon_gov(r.get("area", "unknown"))
        if area is None:
            continue
        if area not in area_bss:
            area_bss[area] = {"dou": [], "nei": [], "s1": [], "duration": [], "rat_gap": []}
        if r.get("dou_total") is not None:
            area_bss[area]["dou"].append(r["dou_total"])
        nei = r.get("network_experience_index")
        if nei is not None:
            area_bss[area]["nei"].append(nei)
        if r.get("s1_mme_sr") is not None:
            area_bss[area]["s1"].append(r["s1_mme_sr"])
        if r.get("duration") is not None:
            area_bss[area]["duration"].append(r["duration"])
        if r.get("rat_gap_score") is not None:
            area_bss[area]["rat_gap"].append(r["rat_gap_score"])

    common = sorted(set(area_oss.keys()) & set(area_bss.keys()))
    if len(common) < 3:
        return []

    # Build area-level mean arrays
    oss_tput = np.array([_mean(area_oss[c]["tput"]) for c in common])
    oss_lat = np.array([_mean(area_oss[c]["lat"]) for c in common])
    oss_loss = np.array([_mean(area_oss[c]["loss"]) for c in common])
    oss_jitter = np.array([_mean(area_oss[c]["jitter"]) for c in common])
    oss_users = np.array([_mean(area_oss[c]["users"]) for c in common])
    oss_rsrp = np.array([_mean(area_oss[c]["rsrp"]) for c in common])
    oss_load = np.array([_mean(area_oss[c]["load"]) for c in common])
    oss_cdr = np.array([_mean(area_oss[c]["cdr"]) for c in common])
    oss_users_max = np.array([_mean(area_oss[c]["users_max"]) for c in common])

    bss_dou = np.array([_mean(area_bss[c]["dou"]) for c in common])
    bss_nei = np.array([_mean(area_bss[c]["nei"]) for c in common])
    bss_s1 = np.array([_mean(area_bss[c]["s1"]) for c in common])
    bss_duration = np.array([_mean(area_bss[c]["duration"]) for c in common])
    bss_rat_gap = np.array([_mean(area_bss[c]["rat_gap"]) for c in common])

    # Pairs to test. These use the metrics that actually exist in the TT data.
    pairs = [
        ("mean_throughput_mbps", "mean_network_experience_index", oss_tput, bss_nei),
        ("mean_throughput_mbps", "mean_dou_total", oss_tput, bss_dou),
        ("mean_call_drop_rate", "mean_network_experience_index", oss_cdr, bss_nei),
        ("mean_call_drop_rate", "mean_s1_mme_sr", oss_cdr, bss_s1),
        ("mean_active_users", "mean_dou_total", oss_users, bss_dou),
        ("mean_rsrp_dbm", "mean_network_experience_index", oss_rsrp, bss_nei),
        ("mean_active_users_max", "mean_rat_gap_score", oss_users_max, bss_rat_gap),
        ("mean_latency_ms", "mean_network_experience_index", oss_lat, bss_nei),
        ("mean_packet_loss_pct", "mean_s1_mme_sr", oss_loss, bss_s1),
    ]

    results = []
    for metric_x, metric_y, arr_x, arr_y in pairs:
        for method in ("pearson", "spearman"):
            corr_val, p_val = _safe_correlation(arr_x, arr_y, method)
            if np.isnan(corr_val):
                continue
            results.append({
                "metric_x": metric_x,
                "metric_y": metric_y,
                "method": method,
                "corr_value": round(float(corr_val), 6),
                "p_value": round(float(p_val), 6),
            })

        if DCOR_AVAILABLE:
            try:
                dc = dcor.distance_correlation(
                    np.nan_to_num(arr_x, nan=0.0),
                    np.nan_to_num(arr_y, nan=0.0),
                )
                results.append({
                    "metric_x": metric_x,
                    "metric_y": metric_y,
                    "method": "dcor",
                    "corr_value": round(float(dc), 6),
                    "p_value": None,
                })
            except Exception:
                pass

    return results
