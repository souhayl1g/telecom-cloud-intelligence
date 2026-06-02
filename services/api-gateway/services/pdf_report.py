"""Capacity report PDF generation via fpdf2 (pure-Python, no system deps).

Layout: header → exec summary → KPI history table → anomalies → recommendations → footer.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fpdf import FPDF

from psycopg2.extras import RealDictCursor, Json

from db import _db
from services.storage import upload_report_pdf


# ── Tunisie Telecom brand-ish colors (kept neutral if logo missing) ────────
TT_BLUE = (10, 36, 99)
TT_RED = (227, 30, 36)
GREY = (90, 90, 100)
LIGHT = (235, 238, 245)


class CapacityPDF(FPDF):
    def __init__(self, *, area: str):
        super().__init__(orientation="L", unit="mm", format="A4")
        self.area = area
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(left=10, top=15, right=10)
        self.alias_nb_pages()

    def header(self):  # noqa: D401
        self.set_fill_color(*TT_BLUE)
        self.rect(0, 0, 210, 18, "F")
        self.set_xy(10, 4)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, _sanitize("NeXo  -  Capacity Recommendation Report"), ln=0)
        self.set_font("Helvetica", "", 9)
        self.set_xy(10, 12)
        self.cell(
            0,
            4,
            _sanitize(f"Area: {self.area}   |   Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"),
            ln=0,
        )
        self.ln(14)

    def footer(self):  # noqa: D401
        self.set_y(-12)
        self.set_text_color(*GREY)
        self.set_font("Helvetica", "I", 8)
        self.cell(
            0,
            6,
            _sanitize(f"NeXo ADN L4 Operations  -  Tunisie Telecom  -  Page {self.page_no()}/{{nb}}"),
            align="C",
        )


def _sanitize(text: str) -> str:
    """Replace Unicode chars fpdf2 Helvetica doesn't support with ASCII equivalents."""
    if not isinstance(text, str):
        text = str(text)
    # Math / symbols
    text = (
        text
        .replace("\u2014", "-")
        .replace("\u2013", "-")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2026", "...")
        .replace("\u2020", "*")
        .replace("\u2212", "-")
        .replace("\u00d7", "x")
        .replace("\u2265", ">=")
        .replace("\u2264", "<=")
        .replace("\u00b0", "deg")
        .replace("\u00b1", "+/-")
        .replace("\u221a", "sqrt")
        .replace("\u03bc", "u")
        .replace("\u03a9", "Ohm")
    )
    # Strip remaining non-ASCII to avoid FPDFUnicodeEncodingException
    return text.encode("ascii", "ignore").decode("ascii")


def _section_title(pdf: FPDF, text: str) -> None:
    pdf.ln(2)
    pdf.set_text_color(*TT_BLUE)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 6, _sanitize(text), ln=1)
    pdf.set_draw_color(*TT_RED)
    pdf.set_line_width(0.4)
    pdf.line(15, pdf.get_y(), 60, pdf.get_y())
    pdf.ln(2)
    pdf.set_text_color(30, 30, 35)
    pdf.set_font("Helvetica", "", 10)


def _kv_row(pdf: FPDF, label: str, value: str) -> None:
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(60, 5, _sanitize(label), ln=0)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 5, _sanitize(value), ln=1)


def _fmt(val, prec: int = 2, na: str = "-") -> str:
    if val is None:
        return na
    try:
        return f"{float(val):.{prec}f}"
    except (TypeError, ValueError):
        return na


def _kpi_table(pdf: FPDF, kpi_history: list[dict]) -> None:
    # Headers: * = derived (deterministic formula). Real columns unmarked.
    headers = ["Time", "Integ%", "CDR%", "Thrpt", "Lat*", "Loss*", "Load%", "Users", "RSRP", "Anoms"]
    widths = [28, 18, 14, 20, 18, 16, 18, 18, 16, 16]
    pdf.set_fill_color(*LIGHT)
    pdf.set_font("Helvetica", "B", 7)
    for h, w in zip(headers, widths):
        pdf.cell(w, 6, _sanitize(h), border=1, ln=0, fill=True, align="C")
    pdf.ln()
    pdf.set_font("Helvetica", "", 7)
    for row in kpi_history[:30]:
        ts = row.get("created_at")
        ts_str = ts.strftime("%m-%d %H:%M") if hasattr(ts, "strftime") else str(ts)[:16]
        users_4g = row.get("avg_users_4g")
        cells = [
            ts_str,
            _fmt(row.get("avg_integrity"), prec=2),
            _fmt(row.get("avg_cdr"), prec=3),
            _fmt(row.get("avg_throughput"), prec=2),
            _fmt(row.get("avg_latency_derived"), prec=1),
            _fmt(row.get("avg_loss_derived"), prec=2),
            _fmt(row.get("avg_load_real"), prec=1),
            "-" if users_4g is None else _fmt(users_4g, prec=1),
            _fmt(row.get("avg_rsrp"), prec=1),
            str(int(row.get("anomaly_count") or 0)),
        ]
        for c, w in zip(cells, widths):
            pdf.cell(w, 5, _sanitize(c), border=1, ln=0, align="C")
        pdf.ln()


def _rat_table(pdf: FPDF, rat_breakdown: list[dict]) -> None:
    headers = ["RAT", "Rows", "Anoms", "Anom%", "Integ%", "CDR%", "Thrpt", "Peak", "Users", "RSRP", "Lat*", "Loss*", "Load%"]
    widths = [12, 18, 18, 14, 16, 14, 18, 18, 14, 14, 14, 14, 14]
    pdf.set_fill_color(*LIGHT)
    pdf.set_font("Helvetica", "B", 7)
    for h, w in zip(headers, widths):
        pdf.cell(w, 6, _sanitize(h), border=1, ln=0, fill=True, align="C")
    pdf.ln()
    pdf.set_font("Helvetica", "", 7)
    for r in rat_breakdown:
        rows_r = int(r.get("row_count") or 0)
        anom_r = int(r.get("anomaly_count") or 0)
        anom_pct = (anom_r / rows_r * 100) if rows_r else 0
        cells = [
            str(r.get("rat_type", "-")),
            f"{rows_r:,}",
            f"{anom_r:,}",
            f"{anom_pct:.1f}",
            _fmt(r.get("avg_integrity"), prec=2),
            _fmt(r.get("avg_cdr"), prec=3),
            _fmt(r.get("avg_throughput"), prec=2),
            _fmt(r.get("peak_throughput"), prec=2),
            "-" if r.get("avg_users") is None else _fmt(r["avg_users"], prec=1),
            _fmt(r.get("avg_rsrp"), prec=1),
            _fmt(r.get("avg_latency_derived"), prec=1),
            _fmt(r.get("avg_loss_derived"), prec=2),
            _fmt(r.get("avg_load_real"), prec=1),
        ]
        for v, w in zip(cells, widths):
            pdf.cell(w, 5, _sanitize(v), border=1, ln=0, align="C")
        pdf.ln()


def _top_cells_table(pdf: FPDF, top_cells: list[dict]) -> None:
    headers = ["Cell", "Site", "Area", "RAT", "Integ%", "CDR%", "Thrpt", "RSRP", "Lat*", "Loss*", "Anoms"]
    widths = [18, 38, 22, 12, 18, 14, 18, 14, 14, 14, 14]
    pdf.set_fill_color(*LIGHT)
    pdf.set_font("Helvetica", "B", 7)
    for h, w in zip(headers, widths):
        pdf.cell(w, 6, _sanitize(h), border=1, ln=0, fill=True, align="C")
    pdf.ln()
    pdf.set_font("Helvetica", "", 7)
    for c in top_cells:
        cells = [
            str(c.get("cell_id", ""))[:8],
            str(c.get("site_name", ""))[:22],
            str(c.get("area", ""))[:12],
            str(c.get("rat_type", ""))[:4],
            _fmt(c.get("avg_integrity"), prec=2),
            _fmt(c.get("avg_cdr"), prec=3),
            _fmt(c.get("avg_throughput"), prec=2),
            _fmt(c.get("avg_rsrp"), prec=1),
            _fmt(c.get("avg_latency_derived"), prec=1),
            _fmt(c.get("avg_loss_derived"), prec=2),
            str(int(c.get("anom_count") or 0)),
        ]
        for v, w in zip(cells, widths):
            pdf.cell(w, 5, _sanitize(v), border=1, ln=0, align="C")
        pdf.ln()


def _bullet_list(pdf: FPDF, items: list[str]) -> None:
    pdf.set_font("Helvetica", "", 10)
    for it in items:
        pdf.cell(5, 5, "-", ln=0)
        pdf.multi_cell(0, 5, _sanitize(it), ln=1)


def _compute_recommendations(
    *,
    avg_integrity: Optional[float],
    avg_cdr: Optional[float],
    avg_throughput: Optional[float],
    peak_throughput: Optional[float],
    avg_latency: Optional[float] = None,
    avg_loss: Optional[float] = None,
    avg_load: Optional[float] = None,
    anomaly_count: int = 0,
    cycles_analyzed: int = 0,
    rat_breakdown: list[dict] = None,
    area: str = "ALL",
) -> list[str]:
    """Recommendations from REAL Huawei OSS fields only.

    Thresholds (3GPP TR 38.913 + TT contractual):
      - integrity < 98 %        → call setup degradation
      - call_drop_rate > 2 %    → SLA breach
      - per-RAT anomaly rate > 5 % → batch triage
    """
    recs: list[str] = []

    if cycles_analyzed == 0:
        return [
            f"No OSS data found for area '{area}'. Verify pipeline-worker has "
            "run a recent cycle and that oss_cell_kpis has rows."
        ]

    if avg_integrity is not None and avg_integrity < 98.0:
        recs.append(
            f"Average call integrity {avg_integrity:.2f}% is below 98% target. "
            "Investigate signaling-plane health and RAN handover success rate."
        )
    if avg_cdr is not None and avg_cdr > 2.0:
        recs.append(
            f"Average call drop rate {avg_cdr:.3f}% exceeds 2% TT contractual SLA. "
            "Trigger physical-layer audit and cell-site KPI review on top offenders."
        )
    if avg_throughput is not None and peak_throughput and avg_throughput / peak_throughput < 0.5:
        recs.append(
            f"Average throughput ({avg_throughput:.2f} Mbps) is below 50% of peak "
            f"({peak_throughput:.2f} Mbps). Consider load-balancing across sectors "
            "or capacity expansion in cells with sustained congestion."
        )
    if avg_latency is not None and avg_latency > 60:
        recs.append(
            f"Engineered latency proxy {avg_latency:.1f} ms exceeds 60 ms target. "
            "Integrity drop or CDR rise is driving estimated RTT - investigate "
            "RAN handover success rate and physical-layer KPIs on top offenders."
        )
    if avg_loss is not None and avg_loss > 1.0:
        recs.append(
            f"Engineered packet-loss proxy {avg_loss:.2f}% exceeds 1% target. "
            "CDR-driven - schedule physical-layer audit."
        )
    if avg_load is not None and avg_load > 75:
        recs.append(
            f"Real 4G cell load (avg/max users) {avg_load:.1f}% exceeds 75% - "
            "capacity exhaustion risk. Plan densification or sector reshape."
        )

    # Per-RAT highlights - most useful insight for this heterogeneous data.
    for r in rat_breakdown or []:
        rt = r.get("rat_type")
        rows_r = int(r.get("row_count") or 0)
        anom_r = int(r.get("anomaly_count") or 0)
        if rows_r and anom_r / rows_r > 0.05:
            recs.append(
                f"{rt}: {anom_r:,}/{rows_r:,} cells flagged ({anom_r/rows_r*100:.1f}%). "
                f"Open a P2 ticket for {rt} batch triage if not already actioned."
            )
        avg_int = r.get("avg_integrity")
        if avg_int is not None and avg_int < 95.0:
            recs.append(
                f"{rt} integrity is critical ({avg_int:.1f}%). "
                "Escalate to RAN engineering - likely RRC/handover failures."
            )

    if anomaly_count == 0:
        recs.append(
            f"No anomalies recorded for area '{area}'. Network operating nominally."
        )

    if not recs:
        recs.append(
            f"Area '{area}' is within nominal thresholds (integrity ≥ 98%, CDR ≤ 2%). "
            "Continue routine monitoring; next review in 24h."
        )
    return recs


def generate_capacity_report(
    *,
    area: str = "ALL",
    source_action_id: Optional[str] = None,
) -> dict:
    """Build PDF from DB state, upload to MinIO, register in capacity_reports.

    Returns: {report_id, minio_key, presigned_url, url_expires_at, metrics_summary}.
    """
    # ── Pull KPI history + anomaly count from DB ─────────────────────────────
    #
    # KPI history is bucketed by hour from oss_cell_kpis (the same table that
    # powers the "OSS ANOMALIES 200" badge in the header). The materialized
    # monthly aggregate (`area_network_health`) only has one row per
    # (area, month_year) so it can't render a 30-row trend.
    #
    # No time-window cutoff: defense data may be days old. We just take the
    # most recent 30 hourly buckets we have.
    is_all = (not area) or area.upper() == "ALL"
    with _db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Real OSS CSV (Huawei exports) only populates:
            #   - integrity (%)             - all RATs
            #   - call_drop_rate (%)        - all RATs
            #   - throughput_mbps           - 3G + 4G only
            #   - active_users              - 4G only
            #   - rat_type ∈ {2G, 3G, 4G}
            # latency_ms, packet_loss_rate, cell_load_pct are NULL by design
            # (the ingest script leaves them empty). PDF must reflect what
            # exists in the data, not invent zeros for missing fields.
            # Reads from vw_oss_cell_derived (see docs/db/migrations/004_oss_derived_view.sql).
            # That view exposes:
            #   REAL fields: integrity, call_drop_rate, throughput_mbps,
            #                active_users, active_users_max (4G), rsrp_dbm, anomaly_flag.
            #   DERIVED fields: latency_ms_derived, packet_loss_pct_derived,
            #                   jitter_ms_derived (deterministic formulas keyed on
            #                   integrity + CDR + RAT - 3GPP TR 38.913 baselines).
            #   REAL cell_load: cell_load_pct_real = active_users / active_users_max × 100
            #                   (4G only - uses two real Huawei columns).
            kpi_sql = """
                SELECT date_trunc('hour', timestamp) AS created_at,
                       AVG(integrity)               AS avg_integrity,
                       AVG(call_drop_rate)          AS avg_cdr,
                       AVG(throughput_mbps) FILTER (WHERE throughput_mbps IS NOT NULL) AS avg_throughput,
                       AVG(active_users)    FILTER (WHERE active_users IS NOT NULL AND rat_type = '4G') AS avg_users_4g,
                       AVG(rsrp_dbm)        FILTER (WHERE rsrp_dbm IS NOT NULL)        AS avg_rsrp,
                       AVG(latency_ms_derived)       AS avg_latency_derived,
                       AVG(packet_loss_pct_derived)  AS avg_loss_derived,
                       AVG(jitter_ms_derived)        AS avg_jitter_derived,
                       AVG(cell_load_pct_real)       AS avg_load_real,
                       SUM(CASE WHEN anomaly_flag THEN 1 ELSE 0 END) AS anomaly_count,
                       COUNT(*)                     AS row_count
                  FROM vw_oss_cell_derived
                 WHERE timestamp IS NOT NULL
                   {area_clause}
              GROUP BY date_trunc('hour', timestamp)
              ORDER BY 1 DESC
                 LIMIT 30;
            """
            if is_all:
                cur.execute(kpi_sql.format(area_clause=""))
            else:
                cur.execute(kpi_sql.format(area_clause="AND area = %s"), (area,))
            kpi_history = list(cur.fetchall())

            # Total anomalies - no time filter.
            if is_all:
                cur.execute(
                    "SELECT COUNT(*) AS n FROM oss_cell_kpis WHERE anomaly_flag = TRUE;"
                )
            else:
                cur.execute(
                    "SELECT COUNT(*) AS n FROM oss_cell_kpis WHERE anomaly_flag = TRUE AND area = %s;",
                    (area,),
                )
            anomaly_row = cur.fetchone() or {}
            anomaly_count = int(anomaly_row.get("n") or 0)

            # Per-RAT breakdown (the data is heterogeneous, an aggregate
            # over all RATs is misleading).
            rat_sql = """
                SELECT rat_type,
                       COUNT(*)                                                       AS row_count,
                       COUNT(*) FILTER (WHERE anomaly_flag)                           AS anomaly_count,
                       AVG(integrity)                                                 AS avg_integrity,
                       AVG(call_drop_rate)                                            AS avg_cdr,
                       AVG(throughput_mbps) FILTER (WHERE throughput_mbps IS NOT NULL) AS avg_throughput,
                       MAX(throughput_mbps) FILTER (WHERE throughput_mbps IS NOT NULL) AS peak_throughput,
                       AVG(active_users)    FILTER (WHERE active_users IS NOT NULL)    AS avg_users,
                       AVG(rsrp_dbm)        FILTER (WHERE rsrp_dbm IS NOT NULL)        AS avg_rsrp,
                       AVG(latency_ms_derived)      AS avg_latency_derived,
                       AVG(packet_loss_pct_derived) AS avg_loss_derived,
                       AVG(cell_load_pct_real)      AS avg_load_real
                  FROM vw_oss_cell_derived
                 WHERE rat_type IS NOT NULL
                   {area_clause}
              GROUP BY rat_type
              ORDER BY rat_type;
            """
            if is_all:
                cur.execute(rat_sql.format(area_clause=""))
            else:
                cur.execute(rat_sql.format(area_clause="AND area = %s"), (area,))
            rat_breakdown = list(cur.fetchall())

            # Top degraded cells - rank by anomaly count + lowest integrity.
            top_cells_sql = """
                SELECT cell_id, area, rat_type, site_name,
                       AVG(integrity)              AS avg_integrity,
                       AVG(call_drop_rate)         AS avg_cdr,
                       AVG(throughput_mbps)        AS avg_throughput,
                       AVG(rsrp_dbm)               AS avg_rsrp,
                       AVG(latency_ms_derived)     AS avg_latency_derived,
                       AVG(packet_loss_pct_derived) AS avg_loss_derived,
                       COUNT(*) FILTER (WHERE anomaly_flag) AS anom_count
                  FROM vw_oss_cell_derived
                 WHERE anomaly_flag = TRUE
                   {area_clause}
              GROUP BY cell_id, area, rat_type, site_name
              ORDER BY anom_count DESC, avg_integrity ASC NULLS LAST
                 LIMIT 10;
            """
            if is_all:
                cur.execute(top_cells_sql.format(area_clause=""))
            else:
                cur.execute(top_cells_sql.format(area_clause="AND area = %s"), (area,))
            top_cells = list(cur.fetchall())

    # ── Compute summary stats ────────────────────────────────────────────────
    def _avg(field: str) -> Optional[float]:
        vals = [r.get(field) for r in kpi_history if r.get(field) is not None]
        return (sum(vals) / len(vals)) if vals else None

    def _max(field: str) -> Optional[float]:
        vals = [r.get(field) for r in kpi_history if r.get(field) is not None]
        return max(vals) if vals else None

    avg_integrity = _avg("avg_integrity")
    avg_cdr = _avg("avg_cdr")
    avg_throughput = _avg("avg_throughput")
    avg_users_4g = _avg("avg_users_4g")
    avg_rsrp = _avg("avg_rsrp")
    avg_latency = _avg("avg_latency_derived")     # derived
    avg_loss = _avg("avg_loss_derived")           # derived
    avg_jitter = _avg("avg_jitter_derived")       # derived
    avg_load = _avg("avg_load_real")              # real (4G only, requires users_max)
    peak_throughput = _max("avg_throughput")
    peak_users_4g = _max("avg_users_4g")
    peak_load = _max("avg_load_real")
    total_rows = sum(int(r.get("row_count") or 0) for r in kpi_history)

    recs = _compute_recommendations(
        avg_integrity=avg_integrity,
        avg_cdr=avg_cdr,
        avg_throughput=avg_throughput,
        peak_throughput=peak_throughput,
        avg_latency=avg_latency,
        avg_loss=avg_loss,
        avg_load=avg_load,
        anomaly_count=anomaly_count,
        cycles_analyzed=len(kpi_history),
        rat_breakdown=rat_breakdown,
        area=area,
    )

    # ── Render PDF ───────────────────────────────────────────────────────────
    pdf = CapacityPDF(area=area)
    pdf.add_page()

    try:
        _section_title(pdf, "Executive Summary - Real KPIs")
        _kv_row(pdf, "Area:", area)
        _kv_row(pdf, "Hourly buckets analyzed:", str(len(kpi_history)))
        _kv_row(pdf, "Total cell-rows aggregated:", f"{total_rows:,}")
        _kv_row(pdf, "Avg call integrity (%):", _fmt(avg_integrity, prec=2))
        _kv_row(pdf, "Avg call drop rate (%):", _fmt(avg_cdr, prec=3))
        _kv_row(pdf, "Avg throughput 3G+4G (Mbps):", _fmt(avg_throughput, prec=2))
        _kv_row(pdf, "Peak throughput (Mbps):", _fmt(peak_throughput, prec=2))
        _kv_row(pdf, "Avg active users (4G):",
                "-" if avg_users_4g is None else _fmt(avg_users_4g, prec=1))
        _kv_row(pdf, "Peak active users (4G):",
                "-" if peak_users_4g is None else _fmt(peak_users_4g, prec=1))
        _kv_row(pdf, "Avg RSRP (4G, dBm):", _fmt(avg_rsrp, prec=1))
        _kv_row(pdf, "Avg cell load 4G (%, real avg/max):", _fmt(avg_load, prec=1))
        _kv_row(pdf, "Peak cell load 4G (%):", _fmt(peak_load, prec=1))
        _kv_row(pdf, "Total anomalies:", f"{anomaly_count:,}")

        _section_title(pdf, "Engineered KPIs (deterministic proxies from real signals)")
        _kv_row(pdf, "Avg latency * (ms):", _fmt(avg_latency, prec=1))
        _kv_row(pdf, "Avg packet loss * (%):", _fmt(avg_loss, prec=2))
        _kv_row(pdf, "Avg jitter * (ms):", _fmt(avg_jitter, prec=1))
        pdf.ln(1)
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(*GREY)
        pdf.multi_cell(0, 4,
            _sanitize("* Latency / loss / jitter are not measured by the Huawei OSS export. "
            "They are computed by deterministic formulas (3GPP TR 38.913 baselines "
            "+ Huawei eRAN handbook) from REAL integrity, CDR, and RAT type. "
            "Same input -> same output, never random."))
        pdf.set_text_color(30, 30, 35)

        if rat_breakdown:
            _section_title(pdf, "Per-RAT Breakdown")
            _rat_table(pdf, rat_breakdown)

        _section_title(pdf, "KPI History (hourly buckets, most recent first)")
        if kpi_history:
            _kpi_table(pdf, kpi_history)
        else:
            pdf.set_font("Helvetica", "I", 10)
            pdf.cell(0, 5, _sanitize("No KPI history available for this area."), ln=1)

        if top_cells:
            _section_title(pdf, "Top 10 Degraded Cells")
            _top_cells_table(pdf, top_cells)

        _section_title(pdf, "Recommendations")
        _bullet_list(pdf, recs)

        _section_title(pdf, "Methodology")
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(
            0,
            4,
            _sanitize(
                "Data source: real Huawei OSS CSV exports (Tunisie Telecom production). "
                "Engineered features are computed deterministically from real signals. "
                "Same input -> same output. Never random. "
                "Thresholds: integrity >= 98%, CDR <= 2%, latency <= 60 ms, loss <= 1%, load <= 75%.",
            ),
        )
    except Exception as e:
        # Fallback: generate a minimal PDF
        pdf = CapacityPDF(area=area)
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, _sanitize("NeXo Capacity Report"), ln=1)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 8, _sanitize(f"Area: {area}"), ln=1)
        pdf.cell(0, 8, _sanitize(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"), ln=1)
        pdf.ln(5)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, _sanitize("Key Metrics"), ln=1)
        pdf.set_font("Helvetica", "", 10)
        _kv_row(pdf, "Avg integrity:", _fmt(avg_integrity, prec=2) + "%")
        _kv_row(pdf, "Avg CDR:", _fmt(avg_cdr, prec=3) + "%")
        _kv_row(pdf, "Avg throughput:", _fmt(avg_throughput, prec=2) + " Mbps")
        _kv_row(pdf, "Total anomalies:", str(anomaly_count))
        pdf.ln(5)
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(*GREY)
        pdf.multi_cell(0, 4, _sanitize(f"Note: Full report generation failed ({e}). Key metrics shown above."))

    pdf_bytes = bytes(pdf.output(dest="S"))

    # ── Upload + register ────────────────────────────────────────────────────
    report_id = f"cap-{uuid.uuid4().hex[:12]}"
    try:
        minio_key, url, expires_at = upload_report_pdf(
            pdf_bytes=pdf_bytes, report_id=report_id, area=area
        )
    except Exception as e:
        # Storage failure must not crash the playbook - return inline error result
        return {
            "report_id": report_id,
            "minio_key": None,
            "presigned_url": None,
            "url_expires_at": None,
            "error": f"upload failed: {e}",
            "metrics_summary": {},
        }

    def _r(v, prec=2):
        return round(float(v), prec) if v is not None else None

    metrics_summary = {
        "area": area,
        "cycles_analyzed": len(kpi_history),
        "total_rows": total_rows,
        # Real Huawei measurements
        "avg_integrity_pct": _r(avg_integrity),
        "avg_call_drop_rate_pct": _r(avg_cdr, 3),
        "avg_throughput_mbps": _r(avg_throughput),
        "peak_throughput_mbps": _r(peak_throughput),
        "avg_users_4g": _r(avg_users_4g, 1),
        "peak_users_4g": _r(peak_users_4g, 1),
        "avg_rsrp_dbm": _r(avg_rsrp, 1),
        "avg_cell_load_pct_real": _r(avg_load, 1),
        "peak_cell_load_pct_real": _r(peak_load, 1),
        # Engineered proxies (deterministic from real signals)
        "avg_latency_ms_derived": _r(avg_latency, 1),
        "avg_packet_loss_pct_derived": _r(avg_loss, 2),
        "avg_jitter_ms_derived": _r(avg_jitter, 1),
        "anomaly_count": anomaly_count,
        "per_rat": [
            {
                "rat_type": r.get("rat_type"),
                "row_count": int(r.get("row_count") or 0),
                "anomaly_count": int(r.get("anomaly_count") or 0),
                "avg_integrity_pct": _r(r.get("avg_integrity")),
                "avg_cdr_pct": _r(r.get("avg_cdr"), 3),
                "avg_throughput_mbps": _r(r.get("avg_throughput")),
                "avg_users": int(r["avg_users"]) if r.get("avg_users") is not None else None,
            }
            for r in rat_breakdown
        ],
        "recommendations": recs,
    }

    with _db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO capacity_reports
                    (report_id, area, report_type, minio_key, presigned_url,
                     url_expires_at, metrics_summary, source_action_id)
                VALUES (%s, %s, 'capacity_recommendation', %s, %s, %s, %s, %s)
                RETURNING *;
                """,
                (
                    report_id,
                    area,
                    minio_key,
                    url,
                    expires_at,
                    Json(metrics_summary),
                    source_action_id,
                ),
            )

    return {
        "report_id": report_id,
        "minio_key": minio_key,
        "presigned_url": url,
        "url_expires_at": expires_at.isoformat(),
        "metrics_summary": metrics_summary,
    }


def list_reports(*, area: Optional[str] = None, limit: int = 50) -> list[dict]:
    where = []
    params: list = []
    if area:
        where.append("area = %s")
        params.append(area)
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    params.append(limit)
    with _db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                f"""
                SELECT * FROM capacity_reports
                {where_sql}
                ORDER BY created_at DESC
                LIMIT %s;
                """,
                tuple(params),
            )
            return list(cur.fetchall())


def get_report(report_id: str) -> Optional[dict]:
    """Get report; if presigned URL expired, refresh it."""
    with _db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM capacity_reports WHERE report_id = %s;", (report_id,))
            row = cur.fetchone()
            if not row:
                return None
            # Refresh URL if expired or close to expiry
            expires_at = row.get("url_expires_at")
            now = datetime.now(timezone.utc)
            if expires_at is not None and expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at is None or expires_at <= now:
                from services.storage import presign_url, REPORTS_BUCKET
                try:
                    new_url, new_exp = presign_url(bucket=REPORTS_BUCKET, key=row["minio_key"])
                    cur.execute(
                        """
                        UPDATE capacity_reports
                        SET presigned_url = %s, url_expires_at = %s
                        WHERE report_id = %s
                        RETURNING *;
                        """,
                        (new_url, new_exp, report_id),
                    )
                    row = cur.fetchone()
                except Exception as e:
                    print(f"[pdf_report] URL refresh failed for {report_id}: {e}")
            return row
