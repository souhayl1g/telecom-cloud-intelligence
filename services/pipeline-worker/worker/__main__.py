import os
import uuid
from datetime import datetime, timezone, timedelta

import psycopg2


def get_conn():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(db_url)


def run_once():
    run_id = f"run-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(minutes=15)
    window_end = now

    region = "demo"
    score = 0.42  # placeholder until AI-service integration

    with get_conn() as conn:
        with conn.cursor() as cur:
            # create run
            cur.execute(
                "INSERT INTO pipeline_runs (run_id, status) VALUES (%s, %s);",
                (run_id, "started"),
            )

            # write sla score (FK references pipeline_runs.run_id)
            cur.execute(
                """
                INSERT INTO sla_risk_scores (run_id, region, window_start, window_end, score)
                VALUES (%s, %s, %s, %s, %s);
                """,
                (run_id, region, window_start, window_end, score),
            )

            # mark run succeeded
            cur.execute(
                "UPDATE pipeline_runs SET status=%s, finished_at=now() WHERE run_id=%s;",
                ("succeeded", run_id),
            )

    print(f"pipeline-worker: inserted sla_risk_scores for run_id={run_id}")


def main():
    print("pipeline-worker execution started")
    run_once()
    print("pipeline-worker execution finished")


if __name__ == "__main__":
    main()