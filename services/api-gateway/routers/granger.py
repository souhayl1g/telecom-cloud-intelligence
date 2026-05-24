import os

from fastapi import APIRouter, Query, Depends, HTTPException
from psycopg2.extras import RealDictCursor
from db import _db
from auth import require_auth

router = APIRouter()

# Conversion factor from a Granger lag unit (one row in the panel) to minutes.
# The current production engine uses monthly area_network_health rows
# (≈ 43,200 min/lag).  The offline gate (notebook 10) and any future
# cycle-grain refresh can override this via LAG_WINDOW_MINUTES.
LAG_WINDOW_MINUTES = int(os.environ.get("LAG_WINDOW_MINUTES", "43200"))


@router.get("/granger-causality")
def list_granger_results(
    limit: int = Query(default=50, ge=1, le=500),
    significant_only: bool = Query(default=False),
    user=Depends(require_auth),
):
    """List Granger causality results from the production engine."""
    try:
        with _db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if significant_only:
                    cur.execute(
                        """
                        SELECT * FROM granger_causality_results
                        WHERE significant = TRUE
                        ORDER BY best_pvalue ASC LIMIT %s;
                        """,
                        (limit,),
                    )
                else:
                    cur.execute(
                        """
                        SELECT * FROM granger_causality_results
                        ORDER BY created_at DESC LIMIT %s;
                        """,
                        (limit,),
                    )
                return {"results": cur.fetchall()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/granger-causality/summary")
def granger_summary(user=Depends(require_auth)):
    """Aggregate summary of Granger causality findings."""
    try:
        with _db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        oss_variable,
                        cem_variable,
                        direction,
                        COUNT(*) as total_tests,
                        COUNT(*) FILTER (WHERE significant = TRUE) as significant_count,
                        ROUND(AVG(best_lag)::numeric, 2) as mean_lag,
                        ROUND(AVG(best_pvalue)::numeric, 4) as mean_pvalue
                    FROM granger_causality_results
                    GROUP BY oss_variable, cem_variable, direction
                    ORDER BY significant_count DESC;
                    """
                )
                return {"summaries": cur.fetchall()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/granger-causality/lead-time")
def granger_lead_time(
    area: str | None = Query(default=None),
    user=Depends(require_auth),
):
    """Detection lead time per (oss, cem) pair, derived from Granger best_lag.

    lead_time_minutes = best_lag * LAG_WINDOW_MINUTES.
    Defaults assume the monthly engine; deploy with LAG_WINDOW_MINUTES set to
    a smaller value once a cycle-grain Granger refresh is wired in.
    """
    try:
        with _db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if area:
                    cur.execute(
                        """
                        SELECT area, oss_variable, cem_variable, direction,
                               AVG(best_lag)::float8                       AS avg_lag,
                               AVG(best_lag * %s)::float8                  AS avg_lead_time_minutes,
                               MIN(best_pvalue)::float8                    AS min_pvalue,
                               COUNT(*) FILTER (WHERE significant)::int    AS significant_count,
                               COUNT(*)::int                               AS total
                        FROM granger_causality_results
                        WHERE area = %s
                        GROUP BY area, oss_variable, cem_variable, direction
                        ORDER BY avg_lead_time_minutes ASC NULLS LAST;
                        """,
                        (LAG_WINDOW_MINUTES, area),
                    )
                else:
                    cur.execute(
                        """
                        SELECT area,
                               AVG(best_lag)::float8                       AS avg_lag,
                               AVG(best_lag * %s)::float8                  AS avg_lead_time_minutes,
                               MIN(best_pvalue)::float8                    AS min_pvalue,
                               COUNT(*) FILTER (WHERE significant)::int    AS significant_count,
                               COUNT(*)::int                               AS total
                        FROM granger_causality_results
                        GROUP BY area
                        ORDER BY avg_lead_time_minutes ASC NULLS LAST;
                        """,
                        (LAG_WINDOW_MINUTES,),
                    )
                rows = cur.fetchall()
                return {
                    "lag_window_minutes": LAG_WINDOW_MINUTES,
                    "area_filter": area,
                    "rows": rows,
                }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/granger-causality/forecast")
def granger_forecast(
    area: str | None = Query(default=None),
    user=Depends(require_auth),
):
    """
    Causal projection of CEM-side variables from Granger-significant OSS drivers.

    For each significant (OSS_X → CEM_Y) pair stored by the production engine:
      1. Pull the area's monthly history from area_network_health
         (avg_throughput, anomaly_count, subscriber_count → avg_cem_score,
          underserved_pct).
      2. Fit ordinary least squares  CEM_Y(t) ~ a + b * OSS_X(t - best_lag)
         on the panel for that area.
      3. Project CEM_Y at t + best_lag using the latest observed OSS_X.

    Returns one row per (area, pair) with both the most recent CEM value and
    the projected value at t + best_lag * LAG_WINDOW_MINUTES, so the UI can
    render a real causal forecast (not extrapolated CEM history).
    """
    try:
        with _db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 1. Significant pairs
                if area:
                    cur.execute(
                        """
                        SELECT area, oss_variable, cem_variable, best_lag,
                               best_pvalue, direction
                          FROM granger_causality_results
                         WHERE significant = TRUE AND area = %s
                         ORDER BY best_pvalue ASC
                         LIMIT 50;
                        """,
                        (area,),
                    )
                else:
                    cur.execute(
                        """
                        SELECT area, oss_variable, cem_variable, best_lag,
                               best_pvalue, direction
                          FROM granger_causality_results
                         WHERE significant = TRUE
                         ORDER BY best_pvalue ASC
                         LIMIT 200;
                        """
                    )
                pairs = cur.fetchall()
                if not pairs:
                    return {
                        "lag_window_minutes": LAG_WINDOW_MINUTES,
                        "area_filter": area,
                        "projections": [],
                        "note": (
                            "No Granger-significant pairs persisted yet — "
                            "run the pipeline-worker live engine for ≥3 cycles."
                        ),
                    }

                # 2. Pull historical panel for the areas we need.
                target_areas = {p["area"] for p in pairs}
                cur.execute(
                    """
                    SELECT area, month_year,
                           avg_throughput, anomaly_count, subscriber_count,
                           avg_cem_score, underserved_pct
                      FROM area_network_health
                     WHERE area = ANY(%s)
                     ORDER BY area, month_year;
                    """,
                    (list(target_areas),),
                )
                history = cur.fetchall()

        # Build per-area dataframe-like index in pure python.
        per_area: dict[str, list[dict]] = {}
        for h in history:
            per_area.setdefault(h["area"], []).append(h)

        projections = []
        for p in pairs:
            rows = per_area.get(p["area"], [])
            oss_col = p["oss_variable"]
            cem_col = p["cem_variable"]
            lag = int(p["best_lag"]) if p["best_lag"] else 1

            xs = [r.get(oss_col) for r in rows]
            ys = [r.get(cem_col) for r in rows]

            # Lagged pair list: (x_{t-lag}, y_t)
            paired = [
                (xs[i - lag], ys[i])
                for i in range(lag, len(rows))
                if xs[i - lag] is not None and ys[i] is not None
            ]
            if len(paired) < 3:
                continue

            xs_arr = [pp[0] for pp in paired]
            ys_arr = [pp[1] for pp in paired]
            n = len(paired)
            mx = sum(xs_arr) / n
            my = sum(ys_arr) / n
            num = sum((xs_arr[i] - mx) * (ys_arr[i] - my) for i in range(n))
            den = sum((xs_arr[i] - mx) ** 2 for i in range(n))
            if den == 0:
                continue
            b = num / den
            a = my - b * mx

            # R² of the lagged regression — honest fit quality signal.
            sst = sum((ys_arr[i] - my) ** 2 for i in range(n))
            ssr = sum((ys_arr[i] - (a + b * xs_arr[i])) ** 2 for i in range(n))
            r2 = 1.0 - ssr / sst if sst > 0 else 0.0

            latest_x = next((x for x in reversed(xs) if x is not None), None)
            latest_y = next((y for y in reversed(ys) if y is not None), None)
            if latest_x is None:
                continue
            projected_y = a + b * latest_x

            projections.append({
                "area": p["area"],
                "oss_variable": oss_col,
                "cem_variable": cem_col,
                "best_lag": lag,
                "lead_time_minutes": lag * LAG_WINDOW_MINUTES,
                "p_value": float(p["best_pvalue"] or 1.0),
                "direction": p.get("direction"),
                "n_observations": n,
                "fit_intercept": float(a),
                "fit_slope": float(b),
                "fit_r2": float(r2),
                "latest_oss": float(latest_x) if latest_x is not None else None,
                "current_cem": float(latest_y) if latest_y is not None else None,
                "projected_cem": float(projected_y),
                "delta_cem": float(projected_y - latest_y) if latest_y is not None else None,
            })

        projections.sort(key=lambda r: r["p_value"])

        return {
            "lag_window_minutes": LAG_WINDOW_MINUTES,
            "area_filter": area,
            "projections": projections,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/granger-causality/explain")
def granger_explain(user=Depends(require_auth)):
    """
    Methodology metadata for the Granger causality engine.
    Returns the parameters, hypothesis, interpretation rules, and convergence
    role used in NeXo's OSS ∩ BSS analysis. Consumed by the dashboard's
    Granger page to render explainability panels and tooltips.
    """
    return {
        "method": {
            "name": "Granger causality F-test",
            "origin": "Granger 1969 — econometric test adapted for telecom KPI time series.",
            "implementation": "statsmodels.tsa.stattools.grangercausalitytests",
            "engine": "services/pipeline-worker/worker/analytics/granger.py",
        },
        "hypothesis": {
            "null": "OSS variable X does NOT Granger-cause CEM variable Y. Past values of X add no predictive information beyond Y's own past.",
            "alternative": "X Granger-causes Y. Adding lags of X to a regression on Y's own lags significantly reduces residual error.",
            "test_statistic": "F-statistic comparing residual sum of squares between restricted (Y on Y_lag) and full (Y on Y_lag + X_lag) models.",
        },
        "parameters": {
            "lag_range": "1..N cycles, where each cycle is a 30s pipeline run",
            "best_lag": "lag with the lowest p-value across the tested range (the temporal delay at which OSS most strongly predicts CEM)",
            "significance_threshold": 0.05,
            "interpretation_thresholds": {
                "significant": "p < 0.05 — high-confidence causal pair, used by L4 ConvergenceSpirit for preemptive remediation",
                "marginal": "0.05 ≤ p < 0.10 — borderline, surfaced as warning",
                "not_significant": "p ≥ 0.10 — no causal evidence, ignored by autonomy logic",
            },
        },
        "convergence_role": {
            "context": "NeXo's L4 ADN architecture treats OSS (network) and CEM (subscriber experience) as two converging streams. Pearson/Spearman correlation tells us they move together; Granger tells us one CAUSES the other after a measurable delay.",
            "downstream_use": [
                "L4 ConvergenceSpirit uses significant pairs to schedule preemptive actions before CEM effects manifest",
                "ExperienceSpirit weights CEM model features by the OSS variables that Granger-cause CEM",
                "AnalystMate cites significant pairs in root-cause narratives",
            ],
            "why_this_matters_for_defense": (
                "Without Granger, the platform can only react to events that have already harmed subscribers. "
                "Granger transforms reactive monitoring into proactive remediation by quantifying the lag between network change and customer impact — "
                "which is the academic core of OSS ∩ CEM convergence as a research contribution."
            ),
        },
        "limitations": {
            "linearity": "Granger assumes a linear relationship — non-linear causality may be missed (mitigated by also computing Spearman rank correlation).",
            "stationarity": "Time series should be stationary; non-stationary series can produce spurious significance (we apply differencing where needed in granger.py).",
            "common_cause": "Granger does not prove direct causation — both variables could share an unmeasured driver. Treated as a hypothesis-generating tool, not deterministic proof.",
        },
    }
