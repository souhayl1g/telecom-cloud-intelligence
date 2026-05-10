"""20-step pipeline orchestration (v3.0 only)."""
import hashlib
import uuid
from datetime import datetime, timezone, timedelta

import numpy as np

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
from worker.inference.v3_client import infer_cem, infer_vae_anomaly, infer_rat_underservice
from worker.sampler import USE_REAL_DATA, sample_bss_records, sample_oss_records


def _enrich_bss_for_v3(bss_records: list[dict], oss_records: list[dict]) -> list[dict]:
    """Compute derived v3 fields + area aggregates for BSS inference."""
    # Build area aggregates from OSS records (works for both real & synthetic)
    area_agg: dict = {}
    for r in oss_records:
        area = r.get("area", r.get("region", "demo"))
        if area not in area_agg:
            area_agg[area] = {"tput": [], "lat": [], "loss": [], "anomaly": 0, "count": 0}
        area_agg[area]["tput"].append(r.get("throughput_mbps", 0))
        area_agg[area]["lat"].append(r.get("latency_ms", 0))
        area_agg[area]["loss"].append(
            r.get("packet_loss_pct", r.get("packet_loss_rate", 0))
        )
        area_agg[area]["count"] += 1
        if r.get("is_fault"):
            area_agg[area]["anomaly"] += 1

    for data in area_agg.values():
        data["avg_throughput"] = float(np.mean(data["tput"])) if data["tput"] else 80.0
        data["avg_latency"] = float(np.mean(data["lat"])) if data["lat"] else 25.0
        data["avg_packet_loss"] = float(np.mean(data["loss"])) if data["loss"] else 0.5
        data["anomaly_rate"] = data["anomaly"] / max(data["count"], 1)

    enriched = []
    for r in bss_records:
        area = r.get("area", "demo")
        agg = area_agg.get(area, {})
        gen = str(r.get("generation", "")).upper()
        enriched.append({
            **r,
            "generation_4g": 1.0 if "4G" in gen or "LTE" in gen else 0.0,
            "generation_5g": 1.0 if "5G" in gen else 0.0,
            "avg_throughput": agg.get("avg_throughput", 80.0),
            "avg_latency": agg.get("avg_latency", 25.0),
            "avg_packet_loss": agg.get("avg_packet_loss", 0.5),
            "anomaly_rate": agg.get("anomaly_rate", 0.05),
        })
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
        oss_records, fault_info = generate_oss(SYNTHETIC_N_RECORDS, region, seed=run_seed)
        print(
            f"  {len(oss_records)} OSS records — "
            f"faults: {fault_info['fault_records']} records on cells {fault_info['fault_cells']}"
        )

        print("[4/20] Generating synthetic BSS data (with correlated dips) ...")
        bss_records = generate_bss(SYNTHETIC_N_RECORDS, region, seed=run_seed + 1, fault_info=fault_info)
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
    print("[12/20] Calling AI service /infer/cem ...")
    cem_result = infer_cem(run_id, region, bss_enriched)
    cem_scores = [p["cem_score"] for p in cem_result.get("predictions", [])]
    print(
        f"  CEM: {len(cem_scores)} predictions  "
        f"model={cem_result.get('model_version')}  "
        f"mean={sum(cem_scores)/len(cem_scores):.4f}" if cem_scores else "  CEM: no predictions"
    )

    # ── 13. RAT underservice inference ─────────────────────────────────
    print("[13/20] Calling AI service /infer/rat-underservice ...")
    rat_result = infer_rat_underservice(run_id, region, bss_enriched)
    print(
        f"  RAT: underserved={rat_result.get('underserved_count')}/{rat_result.get('total')}  "
        f"rate={rat_result.get('underserved_rate')}  "
        f"model={rat_result.get('model_version')}"
    )

    # ── 14. VAE anomaly inference ──────────────────────────────────────
    print("[14/20] Calling AI service /infer/vae-anomaly ...")
    vae_result = infer_vae_anomaly(run_id, region, oss_records)
    print(
        f"  VAE: anomalies={vae_result.get('anomalous_count')}/{vae_result.get('total')}  "
        f"rate={vae_result.get('anomaly_rate')}  "
        f"model={vae_result.get('model_version')}"
    )

    # ── 15. OSS↔CEM correlations ───────────────────────────────────────
    print("[15/20] Computing OSS↔CEM correlations ...")
    correlations = compute_correlations(oss_records, bss_records)
    for c in correlations:
        print(
            f"  {c['method']:>8s}  {c['metric_x']:<28s} ↔ {c['metric_y']:<22s}  "
            f"r={c['corr_value']:+.4f}  p={c['p_value']:.4f}"
        )

    # ── 16. Granger causality ──────────────────────────────────────────
    print("[16/20] Running Granger causality analysis ...")
    granger_summary = run_granger_causality()

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

            # ── mark succeeded ──────────────────────────────────────────
            cur.execute(
                "UPDATE pipeline_runs SET status=%s, finished_at=now() "
                "WHERE run_id=%s;",
                ("succeeded", run_id),
            )

    # Refresh dashboard materialized views so /api/* routes serve fresh data.
    # Runs after the main transaction so a slow refresh can't fail the run.
    try:
        with get_conn() as conn:
            conn.autocommit = True
            with conn.cursor() as cur:
                print("[20/20] Refreshing dashboard materialized views ...")
                cur.execute("SELECT refresh_dashboard_views();")
    except Exception as mv_err:
        print(f"[pipeline] mat view refresh failed (non-fatal): {mv_err}")

    print(f"\n[pipeline] ✓ run {run_id} succeeded")
    print(f"  CEM predictions: {len(cem_result.get('predictions', []))}")
    print(f"  RAT underserved: {rat_result.get('underserved_count')}/{rat_result.get('total')}")
    print(f"  VAE anomalies:   {vae_result.get('anomalous_count')}/{vae_result.get('total')}")
    print(f"  Correlations:    {len(correlations)} computed")
    print(f"  Granger:         {granger_summary.get('significant_findings', 0)} significant")
    print(
        f"  Fault injection: {fault_info['fault_records']} records on {fault_info['fault_cells']}"
    )
