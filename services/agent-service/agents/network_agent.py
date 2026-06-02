"""
NetworkAgent ("Spirit") — Cell-Level Network Monitoring
-------------------------------------------------------
Capabilities:
  - monitor_cells: current KPI snapshot for cells in an area
  - detect_anomaly: flag cells with abnormal KPIs
  - capacity_forecast: estimate headroom based on load trends
  - correlate_with_cem: join cell health with subscriber CEM scores
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor

from agents.base import BaseAgent, AgentIntent, AgentResult

DB_URL = os.getenv("DATABASE_URL", "")
if not DB_URL:
    raise RuntimeError("DATABASE_URL environment variable is required")


def get_conn():
    return psycopg2.connect(DB_URL)


class NetworkAgent(BaseAgent):
    name = "NetworkAgent"
    capabilities = [
        "monitor_cells",
        "detect_anomaly",
        "capacity_forecast",
        "correlate_with_cem",
        "area_health",
    ]

    async def handle(self, intent: AgentIntent) -> AgentResult:
        action = intent.action
        params = intent.params

        if action == "monitor_cells":
            return self._monitor_cells(params.get("area"), params.get("month_year", "2026-03"))
        elif action == "detect_anomaly":
            return self._detect_anomaly(params.get("area"), params.get("month_year", "2026-03"))
        elif action == "capacity_forecast":
            return self._capacity_forecast(params.get("area"), params.get("month_year", "2026-03"))
        elif action == "correlate_with_cem":
            return self._correlate_with_cem(params.get("area"), params.get("month_year", "2026-03"))
        elif action == "area_health":
            return self._area_health(params.get("area"), params.get("month_year", "2026-03"))
        else:
            return AgentResult(agent_name=self.name, success=False, error=f"Unknown action: {action}")

    def _monitor_cells(self, area: str, month_year: str) -> AgentResult:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT cell_id, throughput_mbps, latency_ms, packet_loss_rate,
                           jitter_ms, active_users, rsrp_dbm, cell_load_pct, anomaly_flag
                    FROM oss_cell_kpis
                    WHERE area = %s AND month_year = %s
                    ORDER BY cell_id
                """, (area, month_year))
                rows = cur.fetchall()

        cells = [dict(r) for r in rows]
        avg_load = sum(c["cell_load_pct"] or 0 for c in cells) / max(len(cells), 1)
        anomaly_count = sum(1 for c in cells if c["anomaly_flag"])

        summary = (
            f"{area} ({month_year}): {len(cells)} cells monitored, "
            f"avg load {avg_load:.1f}%, {anomaly_count} anomalies flagged."
        )
        return AgentResult(agent_name=self.name, success=True, data={"cells": cells, "anomaly_count": anomaly_count}, summary=summary)

    def _detect_anomaly(self, area: str, month_year: str) -> AgentResult:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT cell_id, throughput_mbps, latency_ms, packet_loss_rate,
                           rsrp_dbm, cell_load_pct
                    FROM oss_cell_kpis
                    WHERE area = %s AND month_year = %s
                """, (area, month_year))
                rows = cur.fetchall()

        if not rows:
            return AgentResult(agent_name=self.name, success=False, error="No cells found")

        # Simple threshold-based anomaly detection
        anomalies = []
        for r in rows:
            reasons = []
            if r["throughput_mbps"] < 15:
                reasons.append("low_throughput")
            if r["latency_ms"] > 60:
                reasons.append("high_latency")
            if r["packet_loss_rate"] > 2.0:
                reasons.append("high_packet_loss")
            if r["rsrp_dbm"] < -105:
                reasons.append("weak_signal")
            if r["cell_load_pct"] > 85:
                reasons.append("high_load")
            if reasons:
                anomalies.append({
                    "cell_id": r["cell_id"],
                    "reasons": reasons,
                    "severity": "critical" if len(reasons) >= 3 else "warning" if len(reasons) == 2 else "info",
                })

        summary = f"Detected {len(anomalies)} anomalous cells in {area} for {month_year}"
        return AgentResult(agent_name=self.name, success=True, data={"anomalies": anomalies}, summary=summary)

    def _capacity_forecast(self, area: str, month_year: str) -> AgentResult:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT AVG(cell_load_pct) AS avg_load,
                           MAX(cell_load_pct) AS max_load,
                           COUNT(*) AS cell_count,
                           SUM(active_users) AS total_users
                    FROM oss_cell_kpis
                    WHERE area = %s AND month_year = %s
                """, (area, month_year))
                row = cur.fetchone()

        avg_load = row["avg_load"] or 0
        max_load = row["max_load"] or 0
        headroom = max(0, 100 - max_load)
        recommendation = (
            "Urgent capacity expansion needed" if max_load > 90 else
            "Plan capacity within 30 days" if max_load > 75 else
            "Capacity healthy"
        )

        return AgentResult(
            agent_name=self.name,
            success=True,
            data={
                "area": area,
                "month_year": month_year,
                "avg_load_pct": round(avg_load, 1),
                "max_load_pct": round(max_load, 1),
                "headroom_pct": round(headroom, 1),
                "cell_count": row["cell_count"],
                "total_users": row["total_users"],
                "recommendation": recommendation,
            },
            summary=f"{area} capacity: avg load {avg_load:.1f}%, max {max_load:.1f}%. {recommendation}.",
        )

    def _correlate_with_cem(self, area: str, month_year: str) -> AgentResult:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT h.avg_throughput, h.avg_latency, h.avg_packet_loss,
                           h.avg_cem_score, h.underserved_pct, h.subscriber_count
                    FROM area_network_health h
                    WHERE h.area = %s AND h.month_year = %s
                """, (area, month_year))
                row = cur.fetchone()

        if not row:
            return AgentResult(agent_name=self.name, success=False, error="No area health data")

        # Simple narrative correlation
        issues = []
        if row["avg_latency"] > 40:
            issues.append("High latency correlates with lower CEM scores")
        if row["avg_packet_loss"] > 1.0:
            issues.append("Packet loss degrades subscriber experience")
        if row["underserved_pct"] > 20:
            issues.append("Large underserved population suggests network-device mismatch")

        return AgentResult(
            agent_name=self.name,
            success=True,
            data={
                "area": area,
                "avg_throughput": row["avg_throughput"],
                "avg_latency": row["avg_latency"],
                "avg_packet_loss": row["avg_packet_loss"],
                "avg_cem_score": row["avg_cem_score"],
                "underserved_pct": row["underserved_pct"],
                "correlations": issues,
            },
            summary=f"{area}: CEM={row['avg_cem_score']:.2f}, {row['underserved_pct']:.1f}% underserved. " + " ".join(issues),
        )

    def _area_health(self, area: str, month_year: str) -> AgentResult:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM area_network_health
                    WHERE area = %s AND month_year = %s
                """, (area, month_year))
                row = cur.fetchone()

        if not row:
            return AgentResult(agent_name=self.name, success=False, error="Area not found")

        # Compute a simple health score 0-100
        cem = row["avg_cem_score"] or 0
        under = (row["underserved_pct"] or 0) / 100.0
        loss = (row["avg_packet_loss"] or 0)
        health_score = max(0, min(100, (cem * 50) + (50 * (1 - under)) - (loss * 10)))

        data = {k: v for k, v in row.items() if not k.startswith("_")}
        data["health_score"] = round(health_score, 1)

        return AgentResult(
            agent_name=self.name,
            success=True,
            data=data,
            summary=f"{area} ({month_year}) health score: {health_score:.1f}/100, CEM avg {cem:.2f}",
        )
