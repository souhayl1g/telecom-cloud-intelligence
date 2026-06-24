"""Native MinIO object browser (Data Scientist surface).

Replaces the external MinIO console with an in-dashboard browser (the "no external
links" mandate). Read-only listing + presigned download over the existing boto3
client in services/storage.py. Honesty: unreachable store / missing bucket → null
fields, never fabricated counts.
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from auth import require_role
from services import storage

router = APIRouter()

# The 3-layer lake plus the reports bucket the actuation layer writes to.
_KNOWN_BUCKETS = ["raw", "processed", "curated", "reports"]


@router.get("/storage/buckets")
def list_buckets(user=Depends(require_role("data_scientist"))):
    """Buckets with object count + total bytes (per-bucket null on failure)."""
    try:
        s3 = storage.get_s3()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    out = []
    for name in _KNOWN_BUCKETS:
        objects = total = 0
        ok = True
        try:
            paginator = s3.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=name):
                for obj in page.get("Contents", []):
                    objects += 1
                    total += obj.get("Size", 0)
        except Exception:
            ok = False
        out.append({
            "name": name,
            "objects": objects if ok else None,
            "bytes": total if ok else None,
        })
    return {"buckets": out}


@router.get("/storage/objects")
def list_objects(
    bucket: str = Query(...),
    prefix: str = Query(""),
    limit: int = Query(100, ge=1, le=1000),
    user=Depends(require_role("data_scientist")),
):
    """Objects in a bucket under an optional prefix (key, size, last-modified)."""
    if bucket not in _KNOWN_BUCKETS:
        raise HTTPException(status_code=400, detail=f"unknown bucket: {bucket}")
    try:
        s3 = storage.get_s3()
        resp = s3.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    objects = [
        {
            "key": o["Key"],
            "size": o.get("Size", 0),
            "last_modified": o["LastModified"].isoformat() if o.get("LastModified") else None,
        }
        for o in resp.get("Contents", [])
    ]
    return {
        "bucket": bucket,
        "prefix": prefix,
        "objects": objects,
        "truncated": resp.get("IsTruncated", False),
        "count": len(objects),
    }


@router.get("/storage/presign")
def presign(
    bucket: str = Query(...),
    key: str = Query(...),
    user=Depends(require_role("data_scientist")),
):
    """Short-lived presigned GET URL for one object (browser-reachable host)."""
    if bucket not in _KNOWN_BUCKETS:
        raise HTTPException(status_code=400, detail=f"unknown bucket: {bucket}")
    try:
        url, expires_at = storage.presign_url(bucket=bucket, key=key, ttl_seconds=600)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"url": url, "expires_at": expires_at.isoformat(), "expires_in": 600}
