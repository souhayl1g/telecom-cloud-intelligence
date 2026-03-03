from fastapi import FastAPI, HTTPException
import os
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI()

def get_conn():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(db_url)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/sla-risk")
def sla_risk_latest():
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        id,
                        run_id,
                        region,
                        window_start,
                        window_end,
                        score,
                        explanation,
                        model_name,
                        model_version,
                        created_at
                    FROM sla_risk_scores
                    ORDER BY created_at DESC
                    LIMIT 1;
                """)
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="No SLA risk scores found")
                return row
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
