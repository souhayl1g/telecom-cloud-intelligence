from fastapi import APIRouter, HTTPException, Depends
from psycopg2.extras import RealDictCursor
from db import _db
from auth import require_auth

router = APIRouter()


@router.get("/platform-stats")
def platform_stats(user=Depends(require_auth)):
    """Return aggregated platform statistics for capacity planning and topology."""
    try:
        with _db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Pipeline run counts
                cur.execute("SELECT COUNT(*) AS total, COUNT(*) FILTER (WHERE status='succeeded') AS succeeded FROM pipeline_runs;")
                run_stats = cur.fetchone()

                # Anomaly counts by severity
                cur.execute("""
                    SELECT
                        COUNT(*) AS total,
                        COUNT(*) FILTER (WHERE severity > 0.9) AS critical,
                        COUNT(*) FILTER (WHERE severity > 0.5 AND severity <= 0.9) AS warning,
                        COUNT(*) FILTER (WHERE severity <= 0.5) AS low,
                        AVG(severity) AS avg_severity
                    FROM anomalies
                    WHERE created_at >= NOW() - INTERVAL '1 hour';
                """)
                anomaly_stats = cur.fetchone()

                # Revenue anomaly stats
                cur.execute("""
                    SELECT COUNT(*) AS total, AVG(severity) AS avg_severity
                    FROM revenue_anomalies
                    WHERE created_at >= NOW() - INTERVAL '1 hour';
                """)
                revenue_stats = cur.fetchone()

                # Average KPIs from recent anomalies (proxy for current network state)
                cur.execute("""
                    SELECT
                        AVG(CAST(value AS FLOAT)) AS avg_kpi_value,
                        COUNT(DISTINCT cell_id) AS unique_cells,
                        COUNT(DISTINCT region) AS unique_regions
                    FROM anomalies
                    WHERE created_at >= NOW() - INTERVAL '1 hour';
                """)
                kpi_stats = cur.fetchone()

                # SLA risk trend (last 20)
                cur.execute("SELECT score, created_at FROM sla_risk_scores ORDER BY created_at DESC LIMIT 20;")
                sla_trend = cur.fetchall()

                return {
                    "pipeline": run_stats,
                    "anomalies": anomaly_stats,
                    "revenue_anomalies": revenue_stats,
                    "network": kpi_stats,
                    "sla_trend": sla_trend,
                }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/infra-stats")
def infra_stats(user=Depends(require_auth)):
    """Return real infrastructure metrics: row counts, DB size, pipeline timing."""
    try:
        with _db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Row counts per table
                cur.execute("""
                    SELECT
                        (SELECT count(*) FROM pipeline_runs) AS pipeline_runs,
                        (SELECT count(*) FROM anomalies) AS anomalies,
                        (SELECT count(*) FROM revenue_anomalies) AS revenue_anomalies,
                        (SELECT count(*) FROM sla_risk_scores) AS sla_scores,
                        (SELECT count(*) FROM correlation_insights) AS correlations,
                        (SELECT count(*) FROM dataset_registry) AS datasets,
                        (SELECT count(*) FROM agent_actions) AS actions,
                        (SELECT count(*) FROM users) AS users;
                """)
                row_counts = cur.fetchone()

                # Total data lake rows from dataset_registry
                cur.execute("SELECT COALESCE(SUM(row_count), 0) AS total_data_rows FROM dataset_registry;")
                data_rows = cur.fetchone()

                # Real DB size
                cur.execute("SELECT pg_database_size(current_database()) AS db_size_bytes;")
                db_size = cur.fetchone()

                # Real table sizes
                cur.execute("""
                    SELECT
                        pg_total_relation_size('anomalies') AS anomalies_bytes,
                        pg_total_relation_size('correlation_insights') AS correlations_bytes,
                        pg_total_relation_size('sla_risk_scores') AS sla_bytes,
                        pg_total_relation_size('revenue_anomalies') AS revenue_bytes,
                        pg_total_relation_size('dataset_registry') AS datasets_bytes,
                        pg_total_relation_size('pipeline_runs') AS pipeline_bytes;
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
                    "db_size_mb": round(int(db_size["db_size_bytes"]) / (1024 * 1024), 1),
                    "table_sizes": {k: int(v) for k, v in table_sizes.items()},
                    "pipeline_timing": {
                        "finished_runs": int(pipeline_timing["finished_runs"]),
                        "avg_duration_sec": round(float(pipeline_timing["avg_duration_sec"]), 1),
                        "max_duration_sec": round(float(pipeline_timing["max_duration_sec"]), 1),
                    },
                    "data_lake_layers": [
                        {"layer": r["layer"], "datasets": int(r["count"]), "rows": int(r["rows"])}
                        for r in layers
                    ],
                }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
