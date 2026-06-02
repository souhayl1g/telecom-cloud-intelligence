"""
CEMAgent ("Mate") — Customer Experience Management Agent
--------------------------------------------------------
Capabilities:
  - analyze_subscriber: deep-dive CEM profile for one subscriber
  - score_experience: compute or retrieve CEM score (0-1)
  - find_underserved: list subscribers with high rat_gap_score in an area
  - predict_nps: rough NPS prediction based on CEM score + network quality
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


class CEMAgent(BaseAgent):
    name = "CEMAgent"
    capabilities = [
        "analyze_subscriber",
        "score_experience",
        "find_underserved",
        "predict_nps",
        "area_cem_summary",
    ]

    async def handle(self, intent: AgentIntent) -> AgentResult:
        action = intent.action
        params = intent.params

        if action == "analyze_subscriber":
            return self._analyze_subscriber(params.get("imsi_hash"), params.get("month_year", "2026-03"))
        elif action == "score_experience":
            return self._score_experience(params.get("imsi_hash"), params.get("month_year", "2026-03"))
        elif action == "find_underserved":
            return self._find_underserved(params.get("area"), params.get("month_year", "2026-03"), params.get("limit", 20))
        elif action == "predict_nps":
            return self._predict_nps(params.get("imsi_hash"), params.get("month_year", "2026-03"))
        elif action == "area_cem_summary":
            return self._area_cem_summary(params.get("area"), params.get("month_year", "2026-03"))
        else:
            return AgentResult(agent_name=self.name, success=False, error=f"Unknown action: {action}")

    def _analyze_subscriber(self, imsi_hash: str, month_year: str) -> AgentResult:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT s.*, f.rat_gap_score, f.usim_bottleneck, f.data_intensity,
                           f.network_experience_index, f.cem_score, f.churn_risk_flag,
                           f.features_json
                    FROM bss_subscribers s
                    LEFT JOIN subscriber_features f ON s.imsi_hash = f.imsi_hash AND s.month_year = f.month_year
                    WHERE s.imsi_hash = %s AND s.month_year = %s
                    LIMIT 1
                """, (imsi_hash, month_year))
                row = cur.fetchone()

        if not row:
            return AgentResult(agent_name=self.name, success=False, error="Subscriber not found")

        # Build narrative
        rat_gap = row["rat_gap_score"] or 0.0
        usim_block = row["usim_bottleneck"]
        cem = row["cem_score"] or 0.0
        ne_idx = row["network_experience_index"] or 0.0

        drivers = []
        if rat_gap > 0.3:
            drivers.append(f"RAT gap = {rat_gap:.2f} (device {row['generation']} but using {row['highest_rat']})")
        if usim_block:
            drivers.append("USIM bottleneck: 4G-capable device with legacy 2G SIM")
        if ne_idx < 0.5:
            drivers.append(f"Poor attach success rates (NEI = {ne_idx:.2f})")
        if row["churn_risk_flag"]:
            drivers.append("Churn risk flagged")

        summary = (
            f"Subscriber in {row['area']} ({row['area_delegation']}) — "
            f"Device: {row['brand']} {row['model']} ({row['generation']}). "
            f"CEM Score: {cem:.2f}/1.0. "
            f"User type: {row['usertype']}. "
            f"Highest RAT used: {row['highest_rat']}."
        )

        return AgentResult(
            agent_name=self.name,
            success=True,
            data={
                "imsi_hash": imsi_hash,
                "month_year": month_year,
                "area": row["area"],
                "device": f"{row['brand']} {row['model']}",
                "generation": row["generation"],
                "highest_rat": row["highest_rat"],
                "usertype": row["usertype"],
                "cem_score": round(cem, 4),
                "rat_gap_score": round(rat_gap, 4),
                "usim_bottleneck": usim_block,
                "network_experience_index": round(ne_idx, 4),
                "churn_risk": row["churn_risk_flag"],
                "drivers": drivers,
            },
            summary=summary,
        )

    def _score_experience(self, imsi_hash: str, month_year: str) -> AgentResult:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT cem_score, rat_gap_score, network_experience_index
                    FROM subscriber_features
                    WHERE imsi_hash = %s AND month_year = %s
                """, (imsi_hash, month_year))
                row = cur.fetchone()

        if not row:
            return AgentResult(agent_name=self.name, success=False, error="No feature record found")

        return AgentResult(
            agent_name=self.name,
            success=True,
            data={
                "imsi_hash": imsi_hash,
                "cem_score": round(row["cem_score"] or 0, 4),
                "rat_gap_score": round(row["rat_gap_score"] or 0, 4),
                "network_experience_index": round(row["network_experience_index"] or 0, 4),
            },
            summary=f"CEM Score for {imsi_hash}: {row['cem_score']:.2f}",
        )

    def _find_underserved(self, area: str, month_year: str, limit: int) -> AgentResult:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT s.imsi_hash, s.generation, s.highest_rat, s.usertype,
                           f.rat_gap_score, f.cem_score, f.usim_bottleneck
                    FROM bss_subscribers s
                    JOIN subscriber_features f ON s.imsi_hash = f.imsi_hash AND s.month_year = f.month_year
                    WHERE s.area = %s AND s.month_year = %s AND f.rat_gap_score > 0.3
                    ORDER BY f.rat_gap_score DESC
                    LIMIT %s
                """, (area, month_year, limit))
                rows = cur.fetchall()

        data = [
            {
                "imsi_hash": r["imsi_hash"],
                "generation": r["generation"],
                "highest_rat": r["highest_rat"],
                "usertype": r["usertype"],
                "rat_gap_score": round(r["rat_gap_score"], 4),
                "cem_score": round(r["cem_score"], 4),
                "usim_bottleneck": r["usim_bottleneck"],
            }
            for r in rows
        ]

        summary = f"Found {len(data)} underserved subscribers in {area} for {month_year}"
        return AgentResult(agent_name=self.name, success=True, data={"subscribers": data}, summary=summary)

    def _predict_nps(self, imsi_hash: str, month_year: str) -> AgentResult:
        # Rough heuristic: CEM score 0-1 mapped to NPS -100 to +100
        res = self._score_experience(imsi_hash, month_year)
        if not res.success:
            return res

        cem = res.data["cem_score"]
        nps = int((cem * 200) - 100)
        category = "Promoter" if nps > 50 else "Passive" if nps > 0 else "Detractor"

        return AgentResult(
            agent_name=self.name,
            success=True,
            data={"imsi_hash": imsi_hash, "predicted_nps": nps, "category": category, "cem_score": cem},
            summary=f"Predicted NPS for {imsi_hash}: {nps} ({category})",
        )

    def _area_cem_summary(self, area: str, month_year: str) -> AgentResult:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM area_network_health
                    WHERE area = %s AND month_year = %s
                """, (area, month_year))
                row = cur.fetchone()

        if not row:
            return AgentResult(agent_name=self.name, success=False, error="Area not found")

        return AgentResult(
            agent_name=self.name,
            success=True,
            data={k: v for k, v in row.items() if not k.startswith("_")},
            summary=f"{area} ({month_year}): Avg CEM {row['avg_cem_score']:.2f}, {row['underserved_pct']:.1f}% underserved",
        )
