"""REST endpoints for capacity report PDFs."""

import os

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from auth import require_auth
from services import notifier, pdf_report, storage

router = APIRouter()

REPORT_RECIPIENT_EMAIL = os.getenv("REPORT_RECIPIENT_EMAIL", "").strip()
REPORTS_BUCKET = os.getenv("REPORTS_BUCKET", "reports")


@router.get("/reports")
def list_reports(
    area: str = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    user=Depends(require_auth),
):
    rows = pdf_report.list_reports(area=area, limit=limit)
    return {"reports": rows, "count": len(rows)}


@router.get("/reports/{report_id}")
def get_report(report_id: str, user=Depends(require_auth)):
    row = pdf_report.get_report(report_id)
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
    return row


@router.post("/reports/capacity")
def create_capacity_report(body: dict = Body(default={}), user=Depends(require_auth)):
    body = body or {}
    area = body.get("area", "ALL")
    want_email = bool(body.get("email"))
    email_to = (body.get("email_to") or REPORT_RECIPIENT_EMAIL or "").strip()
    try:
        result = pdf_report.generate_capacity_report(
            area=area,
            source_action_id=body.get("source_action_id"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if want_email and email_to and result.get("minio_key"):
        try:
            pdf_bytes = storage.download_bytes(bucket=REPORTS_BUCKET, key=result["minio_key"])
            ms = result.get("metrics_summary") or {}
            recs = ms.get("recommendations") or []
            rec_lines = "\n".join(f"  - {r}" for r in recs) if recs else "  (none)"
            per_rat_lines = "\n".join(
                f"  - {rt.get('rat_type')}: {rt.get('row_count', 0):,} rows, "
                f"{rt.get('anomaly_count', 0):,} anomalies, "
                f"integrity={rt.get('avg_integrity_pct', '—')}%, "
                f"CDR={rt.get('avg_cdr_pct', '—')}%"
                for rt in (ms.get("per_rat") or [])
            ) or "  (no per-RAT breakdown)"
            mail_body = (
                f"NeXo Capacity Recommendation Report (Real Huawei OSS data)\n"
                f"Area: {area}\n"
                f"Report ID: {result.get('report_id')}\n"
                f"Hourly buckets analyzed: {ms.get('cycles_analyzed', 0)}\n"
                f"Total cell-rows: {ms.get('total_rows', 0):,}\n"
                f"Avg call integrity: {ms.get('avg_integrity_pct', '—')}%\n"
                f"Avg call drop rate: {ms.get('avg_call_drop_rate_pct', '—')}%\n"
                f"Avg throughput (3G+4G): {ms.get('avg_throughput_mbps', '—')} Mbps\n"
                f"Peak throughput: {ms.get('peak_throughput_mbps', '—')} Mbps\n"
                f"Avg 4G active users: {ms.get('avg_users_4g', '—')}\n"
                f"Avg 4G RSRP: {ms.get('avg_rsrp_dbm', '—')} dBm\n"
                f"Total anomalies: {ms.get('anomaly_count', 0):,}\n\n"
                f"Per-RAT breakdown:\n{per_rat_lines}\n\n"
                f"Recommendations:\n{rec_lines}\n\n"
                f"Note: latency, packet loss, jitter, cell load are not in the "
                f"Huawei source CSV and are intentionally omitted.\n\n"
                f"Download link (expires in 7 days):\n{result.get('presigned_url')}\n\n"
                f"-- NeXo ADN L4 Operations Agent"
            )
            nr = notifier.send_email_with_attachment(
                email_to,
                f"[NeXo] Capacity Report — {area} — {result.get('report_id')}",
                mail_body,
                pdf_bytes,
                f"{result.get('report_id')}.pdf",
                source_action_id=body.get("source_action_id"),
            )
            result["email"] = {
                "to": email_to,
                "provider": nr.provider,
                "status": nr.status,
                "provider_msg_id": nr.provider_msg_id,
                "error": nr.error,
            }
        except Exception as e:
            result["email"] = {"to": email_to, "status": "failed", "error": str(e)[:300]}
    elif want_email and not email_to:
        result["email"] = {
            "status": "skipped",
            "error": "No recipient — set REPORT_RECIPIENT_EMAIL in .env or pass email_to in body.",
        }
    elif want_email and not result.get("minio_key"):
        result["email"] = {
            "status": "skipped",
            "error": "Skipped — MinIO upload failed, no PDF to attach.",
        }

    return result
