#!/usr/bin/env python3
"""Manual pipeline test for v3.0 inference endpoints.

Samples real data from PostgreSQL, calls all 3 v3.0 endpoints,
and verifies responses. Does NOT write to DB or MinIO.
"""
import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, "services/pipeline-worker")

import psycopg2
from worker.config import AI_SERVICE_URL
from worker.inference.v3_client import infer_cem, infer_vae_anomaly, infer_rat_underservice

DB_URL = os.getenv("DATABASE_URL", "postgresql://telecom:telecom_pw@localhost:5432/telecom_intel")

def get_conn():
    return psycopg2.connect(DB_URL)


def sample_bss(n: int = 50):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT b.imsi_hash, b.dou_total, b.duration,
                   b.s1_mme_sr, b.iu_attach_sr, b.gb_attach_sr,
                   b.generation, b.highest_rat,
                   s.data_intensity, s.network_experience_index,
                   s.usim_bottleneck, s.rat_gap_score
            FROM bss_subscribers b
            JOIN subscriber_features s ON b.imsi_hash = s.imsi_hash AND b.month_year = s.month_year
            WHERE b.month_year = '2026-03'
            ORDER BY RANDOM()
            LIMIT %s
        """, (n,))
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    return rows


def sample_oss(n: int = 50):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT cell_id, throughput_mbps, latency_ms, packet_loss_rate,
                   jitter_ms, cell_load_pct, rsrp_dbm, active_users,
                   integrity, call_drop_rate, area, rat_type
            FROM oss_cell_kpis
            WHERE month_year = '2026-03'
            ORDER BY RANDOM()
            LIMIT %s
        """, (n,))
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    return rows


def enrich_bss_for_v3(bss_rows: list[dict]) -> list[dict]:
    """Fetch area aggregates and merge into BSS rows for v3 inference."""
    areas = list({r.get("area") for r in bss_rows if r.get("area")})
    area_data = {}
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT area, avg_throughput, avg_latency, avg_packet_loss,
                   anomaly_count, subscriber_count
            FROM area_network_health
            WHERE month_year = '2026-03' AND area = ANY(%s)
        """, (areas,))
        for row in cur.fetchall():
            area_data[row[0]] = {
                "avg_throughput": row[1] or 0.0,
                "avg_latency": row[2] or 0.0,
                "avg_packet_loss": row[3] or 0.0,
                "anomaly_rate": (row[4] / max(row[5], 1)) if row[5] else 0.0,
            }

    enriched = []
    for r in bss_rows:
        area = r.get("area", "")
        agg = area_data.get(area, {})
        gen = r.get("generation", "")
        enriched.append({
            **r,
            "avg_throughput": agg.get("avg_throughput", 80.0),
            "avg_latency": agg.get("avg_latency", 25.0),
            "avg_packet_loss": agg.get("avg_packet_loss", 0.5),
            "anomaly_rate": agg.get("anomaly_rate", 0.05),
            "generation_4g": 1.0 if "4G" in str(gen).upper() or "LTE" in str(gen).upper() else 0.0,
            "generation_5g": 1.0 if "5G" in str(gen).upper() else 0.0,
            "usim_bottleneck": 1.0 if r.get("usim_bottleneck") else 0.0,
        })
    return enriched


def main():
    run_id = f"manual-v3-{uuid.uuid4().hex[:8]}"
    region = "demo"
    print(f"[{datetime.now():%H:%M:%S}] Manual v3.0 Pipeline Test  run_id={run_id}")
    print(f"AI Service: {AI_SERVICE_URL}")
    print("-" * 60)

    print("\n[1/6] Sampling 50 BSS subscribers (Mar 2026 real)...")
    bss_rows = sample_bss(50)
    print(f"  Sampled {len(bss_rows)} subscribers")

    print("\n[2/6] Enriching with area aggregates...")
    bss_enriched = enrich_bss_for_v3(bss_rows)
    print(f"  Enriched {len(bss_enriched)} records")

    print("\n[3/6] Sampling 50 OSS records (Mar 2026 real)...")
    oss_rows = sample_oss(50)
    print(f"  Sampled {len(oss_rows)} OSS records")

    print("\n[4/6] Calling /infer/cem (LightGBM v3.0)...")
    cem_result = infer_cem(run_id, region, bss_enriched)
    print(f"  Status: {cem_result.get('status', 'ok')}")
    print(f"  Model: {cem_result.get('model_version')}")
    scores = [p["cem_score"] for p in cem_result.get("predictions", [])]
    if scores:
        print(f"  Predictions: {len(scores)}")
        print(f"  CEM score range: {min(scores):.4f} - {max(scores):.4f}")
        print(f"  Mean CEM: {sum(scores)/len(scores):.4f}")

    print("\n[5/6] Calling /infer/vae-anomaly (PyTorch VAE v3.0)...")
    vae_result = infer_vae_anomaly(run_id, region, oss_rows)
    print(f"  Status: {vae_result.get('status', 'ok')}")
    print(f"  Model: {vae_result.get('model_version')}")
    print(f"  Anomalies: {vae_result.get('anomalous_count')}/{vae_result.get('total')}")
    print(f"  Anomaly rate: {vae_result.get('anomaly_rate')}")
    print(f"  Threshold: {vae_result.get('threshold')}")

    print("\n[6/6] Calling /infer/rat-underservice (XGBoost v3.0)...")
    rat_result = infer_rat_underservice(run_id, region, bss_enriched)
    print(f"  Status: {rat_result.get('status', 'ok')}")
    print(f"  Model: {rat_result.get('model_version')}")
    print(f"  Underserved: {rat_result.get('underserved_count')}/{rat_result.get('total')}")
    print(f"  Underserved rate: {rat_result.get('underserved_rate')}")

    print("\n" + "=" * 60)
    print("MANUAL V3.0 PIPELINE TEST COMPLETE")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
