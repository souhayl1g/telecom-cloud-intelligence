from fastapi import APIRouter, HTTPException, Depends
from psycopg2.extras import RealDictCursor
from db import _db
from auth import require_auth

router = APIRouter()


@router.get("/platform-stats")
def platform_stats(user=Depends(require_auth)):
    """Return aggregated platform statistics for capacity planning and topology.

    Reads pre-aggregated mv_dashboard_summary so this stays O(1) even at 19M+ rows.
    """
    try:
        with _db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT COUNT(*) AS total,
                           COUNT(*) FILTER (WHERE status='succeeded') AS succeeded
                    FROM pipeline_runs;
                """)
                run_stats = cur.fetchone()

                cur.execute("""
                    SELECT
                        COUNT(*) AS total_pairs,
                        COUNT(*) FILTER (WHERE significant = TRUE) AS significant_pairs,
                        ROUND(AVG(best_pvalue)::numeric, 4) AS mean_pvalue
                    FROM granger_causality_results;
                """)
                granger_stats = cur.fetchone()

                # Pull VAE/RAT/CEM aggregates from materialized view (constant-time read).
                cur.execute("""
                    SELECT oss_total AS total,
                           oss_anomaly_count AS anomalies,
                           oss_areas_affected AS unique_areas,
                           rat_total AS subscriber_total,
                           rat_underserved AS underserved
                    FROM mv_dashboard_summary;
                """)
                summary = cur.fetchone() or {}

                vae_stats = {
                    "total": summary.get("total"),
                    "anomalies": summary.get("anomalies"),
                    "unique_cells": None,  # not in summary; expose via /vae-anomalies if needed
                    "unique_areas": summary.get("unique_areas"),
                }
                subscriber_stats = {
                    "total": summary.get("subscriber_total"),
                    "underserved": summary.get("underserved"),
                    "churn_risk": None,
                }

                return {
                    "pipeline": run_stats,
                    "granger": granger_stats,
                    "vae_anomalies": vae_stats,
                    "subscriber_risks": subscriber_stats,
                }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/infra-stats")
def infra_stats(user=Depends(require_auth)):
    """Return real infrastructure metrics: row counts, DB size, pipeline timing."""
    try:
        with _db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Row counts: exact for small tables, approximate (pg_class.reltuples)
                # for the giant ones. reltuples is updated by ANALYZE / autovacuum and
                # avoids 5+ second sequential scans on 19M-row tables.
                cur.execute("""
                    SELECT
                        (SELECT count(*) FROM pipeline_runs) AS pipeline_runs,
                        (SELECT count(*) FROM correlation_insights) AS correlations,
                        (SELECT count(*) FROM dataset_registry) AS datasets,
                        (SELECT count(*) FROM agent_actions) AS actions,
                        (SELECT count(*) FROM users) AS users,
                        (SELECT count(*) FROM granger_causality_results) AS granger_results,
                        (SELECT reltuples::bigint FROM pg_class WHERE relname='subscriber_features') AS subscriber_features,
                        (SELECT reltuples::bigint FROM pg_class WHERE relname='oss_cell_kpis') AS oss_cell_kpis,
                        (SELECT count(*) FROM area_network_health) AS area_network_health;
                """)
                row_counts = cur.fetchone()

                # Total data lake rows from dataset_registry
                cur.execute(
                    "SELECT COALESCE(SUM(row_count), 0) AS total_data_rows FROM dataset_registry;"
                )
                data_rows = cur.fetchone()

                # Real DB size
                cur.execute(
                    "SELECT pg_database_size(current_database()) AS db_size_bytes;"
                )
                db_size = cur.fetchone()

                # Real table sizes
                cur.execute("""
                    SELECT
                        pg_total_relation_size('correlation_insights') AS correlations_bytes,
                        pg_total_relation_size('dataset_registry') AS datasets_bytes,
                        pg_total_relation_size('pipeline_runs') AS pipeline_bytes,
                        pg_total_relation_size('granger_causality_results') AS granger_bytes,
                        pg_total_relation_size('subscriber_features') AS subscriber_features_bytes,
                        pg_total_relation_size('oss_cell_kpis') AS oss_cell_kpis_bytes,
                        pg_total_relation_size('area_network_health') AS area_network_health_bytes;
                """)
                table_sizes = cur.fetchone()

                # Pipeline execution times
                cur.execute("""
                    SELECT
                        count(*) AS finished_runs,
                        COALESCE(AVG(EXTRACT(EPOCH FROM (finished_at - started_at))), 0) AS avg_duration_sec,
                        COALESCE(MAX(EXTRACT(EPOCH FROM (finished_at - started_at))), 0) AS max_duration_sec
                    FROM pipeline_runs
                    WHERE finished_at IS NOT NULL;
                """)
                pipeline_timing = cur.fetchone()

                # Dataset count per layer
                cur.execute("""
                    SELECT layer, count(*) AS count, COALESCE(SUM(row_count), 0) AS rows
                    FROM dataset_registry
                    GROUP BY layer ORDER BY layer;
                """)
                layers = cur.fetchall()

                total_rows = sum(int(v) for v in row_counts.values())

                return {
                    "row_counts": {k: int(v) for k, v in row_counts.items()},
                    "total_rows": total_rows,
                    "total_data_rows": int(data_rows["total_data_rows"]),
                    "db_size_bytes": int(db_size["db_size_bytes"]),
                    "db_size_mb": round(
                        int(db_size["db_size_bytes"]) / (1024 * 1024), 1
                    ),
                    "table_sizes": {k: int(v) for k, v in table_sizes.items()},
                    "pipeline_timing": {
                        "finished_runs": int(pipeline_timing["finished_runs"]),
                        "avg_duration_sec": round(
                            float(pipeline_timing["avg_duration_sec"]), 1
                        ),
                        "max_duration_sec": round(
                            float(pipeline_timing["max_duration_sec"]), 1
                        ),
                    },
                    "data_lake_layers": [
                        {
                            "layer": r["layer"],
                            "datasets": int(r["count"]),
                            "rows": int(r["rows"]),
                        }
                        for r in layers
                    ],
                }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
