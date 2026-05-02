"""
Build cell-to-governorate mapping for OSS cell KPIs.

The OSS data has cell tower names as 'area' values (e.g., '3G_Ariana', 'SFX3058'),
while BSS subscribers have governorate names (e.g., 'Ariana', 'Sfax').

This script analyzes all unique cell names and maps them to the 24 Tunisian governorates
using multiple signals:
  1. Site_name BSC/RNC codes (BSCZAG51 → Zaghouen, BSCSIL51 → Siliana, etc.)
  2. Cell_id prefixes (SFX → Sfax, SLO/SLT → Siliana, ZGO/ZGT → Zaghouen, etc.)
  3. Area name substring matching for governorate names
  4. Manual overrides for ambiguous cases

Output: `cell_governorate_map.json` — {cell_area: governorate}
"""

import json
import os
import re

import psycopg2

DB_URL = os.getenv("DATABASE_URL", "postgresql://telecom:telecom_pw@localhost:5432/telecom_intel")

# Tunisia governorates as they appear in BSS data
GOVERNORATES = [
    "Ariana", "Beja", "Ben Arous", "Bizerte", "GABES", "GAFSA",
    "Jendouba", "KAIROUAN", "KASSERINE", "KEBILI", "Kef", "MAHDIA",
    "Manouba", "MEDENINE", "MONASTIR", "NABEUL", "Sfax", "SIDI_BOUZID",
    "Siliana", "SOUSSE", "TATAOUINE", "TOZEUR", "Tunis", "Zaghouen",
]

# Site_name → governorate mapping (derived from manual analysis)
SITE_NAME_MAP = {
    "BEJAGU": "Beja",
    "BSCSIL51": "Siliana",
    "BSCZAG51": "Zaghouen",
    "SFXBSC": "Sfax",
    "SFXRNC": "Sfax",
    # Tunis area (Grand Tunis)
    "KSBRNC": "Tunis",
    "KSBBSC6910": "Tunis",
    "HCHRNC": "Tunis",
    "HCHBSC6910": "Tunis",
    "RNCMNB51": "Tunis",
}

# Cell_id prefix → governorate
CELL_PREFIX_MAP = {
    "SFX": "Sfax",
    "SLO": "Siliana",
    "SLT": "Siliana",
    "ZGO": "Zaghouen",
    "ZGT": "Zaghouen",
}

# 3-letter area code → governorate
AREA_CODE_MAP = {
    "ZGO": "Zaghouen", "ZGT": "Zaghouen",
    "SLT": "Siliana", "SLO": "Siliana",
    "SFX": "Sfax",
    "BEJ": "Beja", "BIZ": "Bizerte",
    "GAF": "GAFSA", "GAB": "GABES",
    "JEN": "Jendouba", "KAI": "KAIROUAN", "KAS": "KASSERINE",
    "KEB": "KEBILI", "KEF": "Kef", "MAH": "MAHDIA",
    "MED": "MEDENINE", "MON": "MONASTIR", "NAB": "NABEUL",
    "SID": "SIDI_BOUZID", "SIL": "Siliana", "SOU": "SOUSSE",
    "TAT": "TATAOUINE", "TOZ": "TOZEUR", "TUN": "Tunis",
    "ZAG": "Zaghouen",
}

# Neighborhood/city → governorate
NEIGHBORHOOD_MAP = {
    "tunis": "Tunis", "bardo": "Tunis", "carthage": "Tunis",
    "gammarth": "Tunis", "marsa": "Tunis", "lac": "Tunis",
    "menzah": "Tunis", "ennasr": "Tunis", "ouardia": "Tunis",
    "medina": "Tunis", "charguia": "Tunis", "kram": "Tunis",
    "goulette": "Tunis", "essijoumi": "Tunis", "borj": "Tunis",
    "rades": "Ben Arous", "mourouj": "Ben Arous", "fouchana": "Ben Arous",
    "mornag": "Ben Arous", "benarous": "Ben Arous",
    "ariana": "Ariana", "soukra": "Ariana",
    "manouba": "Manouba",
    "sfax": "Sfax",
    "sousse": "SOUSSE", "hammamsousse": "SOUSSE",
    "bizerte": "Bizerte",
    "beja": "Beja",
    "gabes": "GABES",
    "gafsa": "GAFSA",
    "jendouba": "Jendouba",
    "kairouan": "KAIROUAN",
    "kasserine": "KASSERINE",
    "kebili": "KEBILI",
    "kef": "Kef",
    "mahdia": "MAHDIA",
    "medenine": "MEDENINE", "jerba": "MEDENINE",
    "monastir": "MONASTIR",
    "nabeul": "NABEUL", "hammamet": "NABEUL",
    "sidibouzid": "SIDI_BOUZID",
    "siliana": "Siliana",
    "tataouine": "TATAOUINE",
    "tozeur": "TOZEUR",
    "zaghouen": "Zaghouen", "zaghouan": "Zaghouen",
}


def get_conn():
    return psycopg2.connect(DB_URL)


def normalize(name: str) -> str:
    return re.sub(r"[^a-z]", "", name.lower())


def map_cell_to_governorate(area: str, site_name: str | None, cell_id: str | None) -> str | None:
    """Map a cell area name to its governorate."""
    area_norm = normalize(area)

    # 1. Site_name direct mapping
    if site_name and site_name in SITE_NAME_MAP:
        return SITE_NAME_MAP[site_name]

    # 1b. Strip 4G_ prefix from site_name and try mapping
    if site_name and site_name.startswith("4G_"):
        stripped = normalize(site_name[3:])
        for gov in sorted(GOVERNORATES, key=len, reverse=True):
            if normalize(gov) in stripped:
                return gov
        for neighborhood, gov in NEIGHBORHOOD_MAP.items():
            if neighborhood in stripped:
                return gov

    # 2. Cell_id prefix mapping
    if cell_id and len(cell_id) >= 3:
        prefix = cell_id[:3].upper()
        if prefix in CELL_PREFIX_MAP:
            return CELL_PREFIX_MAP[prefix]

    # 3. Area code embedded in area name (e.g., "MCHERGA_ZGO1018")
    for code, gov in AREA_CODE_MAP.items():
        pattern = rf"(^|[_\-]){code}([_\-]|$|[0-9])"
        if re.search(pattern, area, re.IGNORECASE):
            return gov

    # 4. Substring matching for governorate names
    for gov in sorted(GOVERNORATES, key=len, reverse=True):
        if normalize(gov) in area_norm:
            return gov

    # 5. Neighborhood mapping
    for neighborhood, gov in NEIGHBORHOOD_MAP.items():
        if neighborhood in area_norm:
            return gov

    # 6. Strip coBTS_/CoBTS_/coBBTS_ prefix and retry
    for prefix in ["cobts", "cobbts"]:
        if area_norm.startswith(prefix):
            stripped = area_norm[len(prefix):]
            for gov in sorted(GOVERNORATES, key=len, reverse=True):
                if normalize(gov) in stripped:
                    return gov
            for neighborhood, gov in NEIGHBORHOOD_MAP.items():
                if neighborhood in stripped:
                    return gov

    return None


def build_mapping():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT area, site_name, cell_id
        FROM oss_cell_kpis
        WHERE source = 'real'
        ORDER BY area
    """)

    mapping = {}
    unmapped_areas = set()

    for area, site_name, cell_id in cur.fetchall():
        gov = map_cell_to_governorate(area, site_name, cell_id)
        if gov:
            mapping[area] = gov
        else:
            unmapped_areas.add(area)

    unmapped = sorted(unmapped_areas)
    cur.close()
    conn.close()

    print(f"Mapped: {len(mapping)} unique areas")
    print(f"Unmapped: {len(unmapped)} unique areas")

    if unmapped:
        print("\nFirst 30 unmapped areas:")
        for area in unmapped[:30]:
            print(f"  area='{area}'")

    out_path = os.path.join(os.path.dirname(__file__), "cell_governorate_map.json")
    with open(out_path, "w") as f:
        json.dump(mapping, f, indent=2, sort_keys=True)

    print(f"\nMapping saved to {out_path}")

    from collections import Counter
    dist = Counter(mapping.values())
    print("\nGovernorate distribution:")
    for gov, count in dist.most_common():
        print(f"  {gov}: {count} cells")

    return mapping


if __name__ == "__main__":
    build_mapping()
