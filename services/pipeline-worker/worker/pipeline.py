"""20-step pipeline orchestration (v3.0 only)."""

import hashlib
import json
import uuid
from datetime import datetime, timezone, timedelta

from worker.config import SYNTHETIC_N_RECORDS
from worker.db import get_conn
from worker.storage import get_s3, ensure_buckets, upload_json
from worker.generators.oss import generate_oss
from worker.generators.bss import generate_bss
from worker.processors.oss import build_processed_oss
from worker.processors.bss import build_processed_bss, build_curated_dataset
from worker.analytics.features import compute_oss_features, compute_bss_features
from worker.analytics.correlations import compute_correlations
from worker.analytics.granger import run_granger_causality
from worker.inference.v3_client import (
    infer_cem,
    infer_vae_anomaly,
    infer_rat_underservice,
)
from worker.sampler import USE_REAL_DATA, sample_bss_records, sample_oss_records
from worker.intervention_tracker import track_outcomes


def _enrich_bss_for_v3(bss_records: list[dict], _oss_records: list[dict]) -> list[dict]:
    """Enrich BSS records with real area aggregates from area_network_health.

    Queries the pre-computed area_network_health table (built from all 18.8M
    real OSS records) instead of computing noisy aggregates from a 200-record
    sample. No hardcoded fallbacks — missing fields are omitted so the
    ai-service feature contract defaults them to 0.0.
    """
    from worker.sampler import _resolve_default_month

    month_year = _resolve_default_month()
    areas = list({r.get("area", "demo") for r in bss_records})
    area_health: dict = {}

    if areas and month_year:
        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    placeholders = ",".join(["%s"] * len(areas))
                    cur.execute(
                        f"""SELECT area, avg_throughput, avg_latency, avg_packet_loss,
                                   anomaly_count, subscriber_count
                            FROM area_network_health
                            WHERE area IN ({placeholders}) AND month_year = %s""",
                        (*areas, month_year),
                    )
                    for row in cur.fetchall():
                        area_health[row[0]] = {
                            "avg_throughput": row[1],
                            "avg_latency": row[2],
                            "avg_packet_loss": row[3],
                            "anomaly_count": row[4],
                            "subscriber_count": row[5],
                        }
        except Exception as e:
            print(f"[pipeline] area_network_health query failed (non-fatal): {e}")

    enriched = []
    for r in bss_records:
        area = r.get("area", "demo")
        health = area_health.get(area, {})
        gen = str(r.get("generation", "")).upper()
        record = {
            **r,
            "generation_4g": 1.0 if "4G" in gen or "LTE" in gen else 0.0,
            "generation_5g": 1.0 if "5G" in gen else 0.0,
        }
        # Only inject area fields when real data exists. Missing fields are
        # omitted; ai-service feature contract defaults them to 0.0.
        if health:
            record["avg_throughput"] = health["avg_throughput"]
            record["avg_latency"] = health["avg_latency"]
            record["avg_packet_loss"] = health["avg_packet_loss"]
            record["anomaly_rate"] = health["anomaly_count"] / max(
                health.get("subscriber_count", 1), 1
            )
            record["avg_throughput_area"] = health["avg_throughput"]
            record["avg_latency_area"] = health["avg_latency"]
            record["avg_loss_area"] = health["avg_packet_loss"]
            record["avg_users_area"] = health["subscriber_count"]
            record["anomaly_count_area"] = health["anomaly_count"]
        enriched.append(record)
    return enriched


def run_once() -> None:
    run_id = f"run-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(minutes=15)
    window_end = now
    region = "demo"

    # Derive reproducible seed from run_id (different data each run)
    run_seed = int(hashlib.sha256(run_id.encode()).hexdigest()[:8], 16) % (2**31)

    print(f"\n[pipeline] run_id={run_id}  seed={run_seed}")

    # Record pipeline start BEFORE any work so started_at captures real total time
    with get_conn() as conn:
        with conn.cursor() as cur:
            print("[1/20] Inserting pipeline_runs record ...")
            cur.execute(
                "INSERT INTO pipeline_runs (run_id, status) VALUES (%s, %s);",
                (run_id, "started"),
            )

    try:
        _run_pipeline_steps(run_id, now, window_start, window_end, region, run_seed)
    except Exception as e:
        print(f"\n[pipeline] ✗ run {run_id} FAILED: {e}")
        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE pipeline_runs SET status=%s, finished_at=now(), error_message=%s WHERE run_id=%s;",
                        ("failed", str(e)[:500], run_id),
                    )
        except Exception as db_err:
            print(f"[pipeline] could not update pipeline_runs: {db_err}")
        raise


def _run_pipeline_steps(
    run_id: str,
    now: datetime,
    window_start: datetime,
    window_end: datetime,
    region: str,
    run_seed: int,
) -> None:
    # ── 2. MinIO buckets ───────────────────────────────────────────────
    print("[2/20] Ensuring MinIO buckets ...")
    s3 = get_s3()
    ensure_buckets(s3, ["raw", "processed", "curated"])

    # ── 3–4. Data generation (real or synthetic) ─────────────────────────
    if USE_REAL_DATA:
        print("[3/20] Sampling real OSS data from Postgres ...")
        oss_records = sample_oss_records(SYNTHETIC_N_RECORDS)
        fault_info = {
            "fault_cells": [],
            "fault_start_idx": 0,
            "fault_end_idx": 0,
            "fault_records": sum(1 for r in oss_records if r.get("is_fault")),
        }
        print(
            f"  {len(oss_records)} OSS records sampled — "
            f"faults: {fault_info['fault_records']} records"
        )

        print("[4/20] Sampling real BSS subscriber data from Postgres ...")
        bss_records = sample_bss_records(SYNTHETIC_N_RECORDS)
        print(f"  {len(bss_records)} BSS records sampled")
    else:
        print("[3/20] Generating synthetic OSS data (with fault injection) ...")
        oss_records, fault_info = generate_oss(
            SYNTHETIC_N_RECORDS, region, seed=run_seed
        )
        print(
            f"  {len(oss_records)} OSS records — "
            f"faults: {fault_info['fault_records']} records on cells {fault_info['fault_cells']}"
        )

        print("[4/20] Generating synthetic BSS data (with correlated dips) ...")
        bss_records = generate_bss(
            SYNTHETIC_N_RECORDS, region, seed=run_seed + 1, fault_info=fault_info
        )
        print(f"  {len(bss_records)} BSS records generated")

    # ── 5–6. Upload raw layer ────────────────────────────────────────────
    date_prefix = now.strftime("%Y/%m/%d")
    oss_key = f"oss/{date_prefix}/{run_id}.json"
    bss_key = f"bss/{date_prefix}/{run_id}.json"

    print("[5/20] Uploading OSS dataset to MinIO raw layer ...")
    upload_json(s3, "raw", oss_key, oss_records)

    print("[6/20] Uploading BSS dataset to MinIO raw layer ...")
    upload_json(s3, "raw", bss_key, bss_records)

    with get_conn() as conn:
        with conn.cursor() as cur:
            # ── 7. dataset_registry (raw) ─────────────────────────────────
            print("[7/20] Registering raw datasets ...")
            for ds_type, key, count in [
                ("oss", oss_key, len(oss_records)),
                ("bss", bss_key, len(bss_records)),
            ]:
                cur.execute(
                    """INSERT INTO dataset_registry
                         (run_id, dataset_type, layer, format, object_key, row_count)
                       VALUES (%s, %s, %s, %s, %s, %s);""",
                    (run_id, ds_type, "raw", "json", key, count),
                )

            # ── 8–9. Processed layer ───────────────────────────────────────
            print("[8/20] Processing OSS data → processed layer ...")
            proc_oss = build_processed_oss(oss_records)
            proc_oss_key = f"oss/{date_prefix}/{run_id}_processed.json"
            upload_json(s3, "processed", proc_oss_key, proc_oss)

            print("[9/20] Processing BSS data → processed layer ...")
            proc_bss = build_processed_bss(bss_records)
            proc_bss_key = f"bss/{date_prefix}/{run_id}_processed.json"
            upload_json(s3, "processed", proc_bss_key, proc_bss)

            # ── 10. Register processed datasets ───────────────────────────
            print("[10/20] Registering processed datasets ...")
            for ds_type, key, count in [
                ("oss", proc_oss_key, len(proc_oss)),
                ("bss", proc_bss_key, len(proc_bss)),
            ]:
                cur.execute(
                    """INSERT INTO dataset_registry
                         (run_id, dataset_type, layer, format, object_key, row_count)
                       VALUES (%s, %s, %s, %s, %s, %s);""",
                    (run_id, ds_type, "processed", "json", key, count),
                )

            # ── 11. Feature engineering ──────────────────────────────────
            print("[11/20] Computing aggregate KPI features ...")
            features = compute_oss_features(oss_records)
            bss_features = compute_bss_features(bss_records)
            print(
                f"  OSS: mean_lat={features['mean_latency_ms']}ms  "
                f"mean_loss={features['mean_packet_loss_pct']}%  "
                f"mean_tput={features['mean_throughput_mbps']}Mbps"
            )
            print(
                f"  BSS: mean_dou={bss_features['mean_dou_total']}  "
                f"mean_nei={bss_features['mean_network_experience_index']}"
            )

    # Enrich BSS records for v3 inference (needs to happen outside the DB cursor block)
    print("[11b] Enriching BSS records for v3 inference ...")
    bss_enriched = _enrich_bss_for_v3(bss_records, oss_records)

    # ── 12. CEM inference ──────────────────────────────────────────────
    inference_failed = False
    cem_result: dict = {"predictions": [], "model_version": "v3.0"}
    print("[12/20] Calling AI service /infer/cem ...")
    try:
        cem_result = infer_cem(run_id, region, bss_enriched)
        cem_scores = [p["cem_score"] for p in cem_result.get("predictions", [])]
        if cem_scores:
            print(
                f"  CEM: {len(cem_scores)} predictions  "
                f"model={cem_result.get('model_version')}  "
                f"mean={sum(cem_scores) / len(cem_scores):.4f}"
            )
        else:
            print("  CEM: no predictions")
    except Exception as e:
        inference_failed = True
        print(f"  CEM: FAILED — {e}")

    # ── 13. RAT underservice inference ─────────────────────────────────
    rat_result: dict = {
        "predictions": [],
        "underserved_count": 0,
        "total": 0,
        "underserved_rate": 0.0,
        "model_version": "v3.0",
    }
    print("[13/20] Calling AI service /infer/rat-underservice ...")
    try:
        rat_result = infer_rat_underservice(run_id, region, bss_enriched)
        print(
            f"  RAT: underserved={rat_result.get('underserved_count')}/{rat_result.get('total')}  "
            f"rate={rat_result.get('underserved_rate')}  "
            f"model={rat_result.get('model_version')}"
        )
    except Exception as e:
        inference_failed = True
        print(f"  RAT: FAILED — {e}")

    # ── 14. VAE anomaly inference ──────────────────────────────────────
    vae_result: dict = {
        "records": [],
        "anomalous_count": 0,
        "total": 0,
        "anomaly_rate": 0.0,
        "model_version": "v3.0",
    }
    print("[14/20] Calling AI service /infer/vae-anomaly ...")
    try:
        vae_result = infer_vae_anomaly(run_id, region, oss_records)
        print(
            f"  VAE: anomalies={vae_result.get('anomalous_count')}/{vae_result.get('total')}  "
            f"rate={vae_result.get('anomaly_rate')}  "
            f"model={vae_result.get('model_version')}"
        )
    except Exception as e:
        inference_failed = True
        print(f"  VAE: FAILED — {e}")

    # ── 15. OSS↔CEM correlations ───────────────────────────────────────
    print("[15/20] Computing OSS↔CEM correlations ...")
    correlations = compute_correlations(oss_records, bss_records)
    for c in correlations:
        p_str = f"{c['p_value']:.4f}" if c["p_value"] is not None else "N/A"
        print(
            f"  {c['method']:>8s}  {c['metric_x']:<28s} ↔ {c['metric_y']:<22s}  "
            f"r={c['corr_value']:+.4f}  p={p_str}"
        )

    # ── 16. Granger causality (skip-guard) ─────────────────────────────
    granger_summary: dict = {"significant_findings": 0}
    try:
        # Compute a simple hash signature of area_network_health
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT area, month_year, avg_throughput, avg_latency, avg_packet_loss, anomaly_count, subscriber_count FROM area_network_health ORDER BY area, month_year"
                )
                rows = cur.fetchall()
        ah_signature = hashlib.sha256(
            json.dumps(rows, default=str).encode()
        ).hexdigest()

        _GRANGER_STATE_FILE = "/tmp/.pipeline_last_granger_hash"
        last_hash = None
        try:
            with open(_GRANGER_STATE_FILE, "r") as f:
                last_hash = f.read().strip()
        except FileNotFoundError:
            pass

        if last_hash == ah_signature:
            print("[16/20] Granger skipped — area_network_health unchanged.")
        else:
            print("[16/20] Running Granger causality analysis ...")
            granger_summary = run_granger_causality()
            with open(_GRANGER_STATE_FILE, "w") as f:
                f.write(ah_signature)
    except Exception as e:
        print(f"[pipeline] Granger step failed (non-fatal): {e}")

    with get_conn() as conn:
        with conn.cursor() as cur:
            # ── 17. Curated dataset ──────────────────────────────────────
            print("[17/20] Building curated dataset → curated layer ...")
            curated = build_curated_dataset(
                oss_records,
                bss_records,
                vae_result,
                cem_result,
                rat_result,
                correlations,
            )
            curated_key = f"joined/{date_prefix}/{run_id}_curated.json"
            upload_json(s3, "curated", curated_key, [curated])

            # ── 18. Register curated dataset ─────────────────────────────
            print("[18/20] Registering curated dataset ...")
            cur.execute(
                """INSERT INTO dataset_registry
                     (run_id, dataset_type, layer, format, object_key, row_count)
                   VALUES (%s, %s, %s, %s, %s, %s);""",
                (run_id, "curated", "curated", "json", curated_key, 1),
            )

            # ── 19. Persist v3 scores ────────────────────────────────────
            print("[19/20] Persisting v3 inference scores ...")

            # CEM scores
            cem_preds = cem_result.get("predictions", [])
            for pred in cem_preds:
                idx = pred["index"]
                src = bss_enriched[idx]
                cur.execute(
                    """INSERT INTO cem_scores
                         (run_id, subscriber_id, region, cem_score, model_version)
                       VALUES (%s, %s, %s, %s, %s);""",
                    (
                        run_id,
                        src.get("subscriber_id", ""),
                        region,
                        pred["cem_score"],
                        cem_result.get("model_version", "v3.0"),
                    ),
                )

            # RAT scores
            rat_preds = rat_result.get("predictions", [])
            for pred in rat_preds:
                idx = pred["index"]
                src = bss_enriched[idx]
                cur.execute(
                    """INSERT INTO rat_underservice_scores
                         (run_id, subscriber_id, region, is_underserved,
                          underservice_prob, model_version)
                       VALUES (%s, %s, %s, %s, %s, %s);""",
                    (
                        run_id,
                        src.get("subscriber_id", ""),
                        region,
                        pred["is_underserved"],
                        pred["underservice_prob"],
                        rat_result.get("model_version", "v3.0"),
                    ),
                )

            # VAE scores
            vae_records = vae_result.get("records", [])
            for rec in vae_records:
                idx = rec["index"]
                src = oss_records[idx]
                cur.execute(
                    """INSERT INTO vae_anomaly_scores
                         (run_id, ts, region, cell_id, is_anomaly,
                          anomaly_score, reconstruction_error, model_version)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s);""",
                    (
                        run_id,
                        src.get("ts"),
                        src.get("region", region),
                        src.get("cell_id", ""),
                        rec["is_anomaly"],
                        rec["anomaly_score"],
                        rec["reconstruction_error"],
                        vae_result.get("model_version", "v3.0"),
                    ),
                )

            # model_registry insert removed — table dropped in migration 002.
            # Inference artifacts live on disk and are loaded by ai-service/model_cache.

            # ── 20. Persist correlations + finish ─────────────────────────
            print("[20/20] Persisting correlation insights ...")
            for c in correlations:
                cur.execute(
                    """INSERT INTO correlation_insights
                         (run_id, region, metric_x, metric_y,
                          window_start, window_end, method,
                          corr_value, p_value)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);""",
                    (
                        run_id,
                        region,
                        c["metric_x"],
                        c["metric_y"],
                        window_start,
                        window_end,
                        c["method"],
                        c["corr_value"],
                        c["p_value"],
                    ),
                )

    # Refresh dashboard materialized views BEFORE marking finished so
    # finished_at reflects total wall-clock work (mat view refresh on 19M
    # rows can take 30-60s — was previously uncounted).
    try:
        with get_conn() as conn:
            conn.autocommit = True
            with conn.cursor() as cur:
                print("[20/20] Refreshing dashboard materialized views ...")
                cur.execute("SELECT refresh_dashboard_views();")
    except Exception as mv_err:
        print(f"[pipeline] mat view refresh failed (non-fatal): {mv_err}")

    # ── Track churn intervention outcomes (longitudinal CEM-delta check) ──
    try:
        print("[intervention] tracking outcomes for pending interventions ...")
        int_summary = track_outcomes()
        print(
            f"  checked={int_summary.get('checked', 0)}  "
            f"improved={int_summary.get('improved', 0)}  "
            f"no_change={int_summary.get('no_change', 0)}  "
            f"worsened={int_summary.get('worsened', 0)}  "
            f"still_pending={int_summary.get('still_pending', 0)}"
        )
    except Exception as it_err:
        print(f"[intervention] tracker failed (non-fatal): {it_err}")

    # ── mark succeeded AFTER all real work ─────────────────────────────
    with get_conn() as conn:
        with conn.cursor() as cur:
            status = "partial" if inference_failed else "succeeded"
            cur.execute(
                "UPDATE pipeline_runs SET status=%s, finished_at=now() "
                "WHERE run_id=%s;",
                (status, run_id),
            )

    print(f"\n[pipeline] ✓ run {run_id} succeeded")
    print(f"  CEM predictions: {len(cem_result.get('predictions', []))}")
    print(
        f"  RAT underserved: {rat_result.get('underserved_count')}/{rat_result.get('total')}"
    )
    print(
        f"  VAE anomalies:   {vae_result.get('anomalous_count')}/{vae_result.get('total')}"
    )
    print(f"  Correlations:    {len(correlations)} computed")
    print(
        f"  Granger:         {granger_summary.get('significant_findings', 0)} significant"
    )
    print(
        f"  Fault injection: {fault_info['fault_records']} records on {fault_info['fault_cells']}"
    )
