from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime, timezone
import hashlib

app = FastAPI(title="AI Service")


class SlaRiskRequest(BaseModel):
    run_id: str
    region: str
    window_start: str
    window_end: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/infer/sla-risk")
def infer_sla_risk(req: SlaRiskRequest):
    # deterministic pseudo-score from inputs (placeholder until real model)
    h = hashlib.sha256(
        f"{req.run_id}|{req.region}|{req.window_start}|{req.window_end}".encode()
    ).hexdigest()
    score = (int(h[:8], 16) % 100) / 100.0

    explanation = {
        "method": "deterministic-placeholder",
        "features": {
            "kpi_anomaly_pressure": 0.63,
            "traffic_spike": 0.27,
            "latency_trend": 0.41,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    return {"score": score, "explanation": explanation, "model_version": "v0.1"}
