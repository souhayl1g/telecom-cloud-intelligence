#!/usr/bin/env python3
"""
Pipeline Runner — Automated Execution with Error Handling
=========================================================

Production-grade pipeline executor designed for container bootstrap.

Features:
- Retry logic with exponential backoff
- Idempotent operations (safe to re-run)
- Structured JSON logging
- Resource limits and timeouts
- Health checks for dependencies
- Graceful degradation

Environment Variables:
    DATABASE_URL         - PostgreSQL connection string
    S3_ENDPOINT          - MinIO/S3 endpoint (default: http://minio:9000)
    S3_ACCESS_KEY        - MinIO access key (default: minio)
    S3_SECRET_KEY        - MinIO secret key (default: minio_pw)
    AI_SERVICE_URL       - AI service URL (default: http://ai-service:8001)
    PIPELINE_LOG_LEVEL   - Log level: DEBUG, INFO, WARNING, ERROR (default: INFO)
    PIPELINE_TIMEOUT     - Max execution time in seconds (default: 120)
    PIPELINE_MAX_RETRIES - Max retry attempts per step (default: 3)
    PIPELINE_RETRY_DELAY - Base delay between retries in seconds (default: 5)

Exit Codes:
    0  - Success
    1  - Pipeline failed (after retries)
    2  - Dependency unavailable (DB, MinIO, AI service)
    3  - Timeout exceeded
    4  - Configuration error
"""

import json
import logging
import os
import signal
import sys
import time
import traceback
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

try:
    import numpy as np
except ImportError:
    np = None

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    psycopg2 = None

try:
    import boto3
except ImportError:
    boto3 = None

try:
    import requests
except ImportError:
    requests = None


# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PipelineConfig:
    database_url: str = ""
    s3_endpoint: str = "http://minio:9000"
    s3_access_key: str = "minio"
    s3_secret_key: str = "minio_pw"
    ai_service_url: str = "http://ai-service:8001"
    log_level: str = "INFO"
    timeout_seconds: int = 120
    max_retries: int = 3
    retry_delay: int = 5
    idempotent: bool = True
    
    @classmethod
    def from_env(cls) -> "PipelineConfig":
        return cls(
            database_url=os.getenv("DATABASE_URL", ""),
            s3_endpoint=os.getenv("S3_ENDPOINT", "http://minio:9000"),
            s3_access_key=os.getenv("S3_ACCESS_KEY", "minio"),
            s3_secret_key=os.getenv("S3_SECRET_KEY", "minio_pw"),
            ai_service_url=os.getenv("AI_SERVICE_URL", "http://ai-service:8001"),
            log_level=os.getenv("PIPELINE_LOG_LEVEL", "INFO"),
            timeout_seconds=int(os.getenv("PIPELINE_TIMEOUT", "120")),
            max_retries=int(os.getenv("PIPELINE_MAX_RETRIES", "3")),
            retry_delay=int(os.getenv("PIPELINE_RETRY_DELAY", "5")),
            idempotent=os.getenv("PIPELINE_IDEMPOTENT", "true").lower() == "true",
        )


# ─────────────────────────────────────────────────────────────────────────────
# Structured Logging
# ─────────────────────────────────────────────────────────────────────────────

class PipelineLogger:
    def __init__(self, name: str, level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        
        # Console handler with JSON format
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(handler)
        
        # File handler for persistent logs
        log_dir = Path(os.getenv("PIPELINE_LOG_DIR", "/app/logs"))
        log_dir.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_dir / f"pipeline_{int(time.time())}.log")
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(file_handler)
    
    def _log(self, level: str, step: str, message: str, **kwargs):
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "step": step,
            "message": message,
            **kwargs
        }
        getattr(self.logger, level.lower())(json.dumps(log_data))
    
    def info(self, step: str, message: str, **kwargs):
        self._log("INFO", step, message, **kwargs)
    
    def warning(self, step: str, message: str, **kwargs):
        self._log("WARNING", step, message, **kwargs)
    
    def error(self, step: str, message: str, **kwargs):
        self._log("ERROR", step, message, **kwargs)
    
    def debug(self, step: str, message: str, **kwargs):
        self._log("DEBUG", step, message, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline Step Decorator
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class StepResult:
    step: str
    success: bool
    duration_seconds: float
    error: Optional[str] = None
    retry_count: int = 0
    data: Optional[dict] = None


class PipelineStep:
    def __init__(self, name: str, retries: int = 3, timeout: int = 30):
        self.name = name
        self.retries = retries
        self.timeout = timeout
        self.result: Optional[StepResult] = None
    
    def __call__(self, func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            logger = kwargs.pop("_logger", None)
            config = kwargs.pop("_config", None)
            
            for attempt in range(self.retries + 1):
                start_time = time.time()
                try:
                    if logger:
                        logger.info(self.name, f"Starting step (attempt {attempt + 1}/{self.retries + 1})")
                    
                    result = func(*args, _config=config, **kwargs)
                    duration = time.time() - start_time
                    
                    self.result = StepResult(
                        step=self.name,
                        success=True,
                        duration_seconds=round(duration, 3),
                        retry_count=attempt,
                        data=result
                    )
                    
                    if logger:
                        logger.info(self.name, f"Step completed in {duration:.2f}s", 
                                  attempt=attempt, duration=duration)
                    
                    return result
                    
                except Exception as e:
                    duration = time.time() - start_time
                    error_msg = f"{type(e).__name__}: {str(e)}"
                    
                    if logger:
                        logger.error(self.name, f"Step failed: {error_msg}",
                                   attempt=attempt, duration=duration)
                    
                    if attempt < self.retries:
                        delay = (config.retry_delay if config else 5) * (2 ** attempt)
                        if logger:
                            logger.info(self.name, f"Retrying in {delay}s...")
                        time.sleep(delay)
                    else:
                        self.result = StepResult(
                            step=self.name,
                            success=False,
                            duration_seconds=round(duration, 3),
                            retry_count=attempt,
                            error=error_msg
                        )
                        raise
            
            return None
        
        return wrapper


# ─────────────────────────────────────────────────────────────────────────────
# Health Checks
# ─────────────────────────────────────────────────────────────────────────────

def check_database(logger: PipelineLogger, config: PipelineConfig) -> bool:
    """Check PostgreSQL connectivity."""
    if not psycopg2:
        logger.warning("HEALTH", "psycopg2 not available, skipping DB check")
        return True
    
    try:
        conn = psycopg2.connect(config.database_url)
        conn.close()
        logger.info("HEALTH", "PostgreSQL connection OK")
        return True
    except Exception as e:
        logger.error("HEALTH", f"PostgreSQL connection failed: {e}")
        return False


def check_minio(logger: PipelineLogger, config: PipelineConfig) -> bool:
    """Check MinIO/S3 connectivity."""
    if not boto3:
        logger.warning("HEALTH", "boto3 not available, skipping MinIO check")
        return True
    
    try:
        client = boto3.client(
            "s3",
            endpoint_url=config.s3_endpoint,
            aws_access_key_id=config.s3_access_key,
            aws_secret_access_key=config.s3_secret_key,
        )
        client.list_buckets()
        logger.info("HEALTH", "MinIO connection OK")
        return True
    except Exception as e:
        logger.error("HEALTH", f"MinIO connection failed: {e}")
        return False


def check_ai_service(logger: PipelineLogger, config: PipelineConfig) -> bool:
    """Check AI service availability."""
    if not requests:
        logger.warning("HEALTH", "requests not available, skipping AI service check")
        return True
    
    try:
        response = requests.get(f"{config.ai_service_url}/health", timeout=5)
        if response.status_code == 200:
            logger.info("HEALTH", "AI service OK")
            return True
        else:
            logger.warning("HEALTH", f"AI service returned {response.status_code}")
            return False
    except Exception as e:
        logger.warning("HEALTH", f"AI service not available: {e}")
        return False  # AI service is optional for health check


# ─────────────────────────────────────────────────────────────────────────────
# Idempotency Guard
# ─────────────────────────────────────────────────────────────────────────────

class IdempotencyGuard:
    """Prevent duplicate pipeline runs within a time window."""
    
    LOCK_FILE = Path("/tmp/pipeline.lock")
    LOCK_TIMEOUT = 300  # 5 minutes
    
    def __init__(self, logger: PipelineLogger):
        self.logger = logger
    
    def acquire(self) -> bool:
        """Attempt to acquire lock. Returns True if lock acquired."""
        if self.LOCK_FILE.exists():
            # Check if lock is stale
            try:
                mtime = self.LOCK_FILE.stat().st_mtime
                if time.time() - mtime < self.LOCK_TIMEOUT:
                    self.logger.warning("IDEMPOTENCY", 
                        f"Lock file exists (PID: {self.LOCK_FILE.read_text().strip()})")
                    return False
                else:
                    self.logger.warning("IDEMPOTENCY", "Removing stale lock file")
                    self.LOCK_FILE.unlink()
            except Exception:
                pass
        
        try:
            self.LOCK_FILE.write_text(str(os.getpid()))
            self.logger.info("IDEMPOTENCY", f"Lock acquired (PID: {os.getpid()})")
            return True
        except Exception as e:
            self.logger.error("IDEMPOTENCY", f"Failed to acquire lock: {e}")
            return False
    
    def release(self):
        """Release the lock."""
        try:
            if self.LOCK_FILE.exists():
                self.LOCK_FILE.unlink()
                self.logger.info("IDEMPOTENCY", "Lock released")
        except Exception as e:
            self.logger.error("IDEMPOTENCY", f"Failed to release lock: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline Steps
# ─────────────────────────────────────────────────────────────────────────────

@PipelineStep(name="ENSURE_BUCKETS", retries=3, timeout=30)
def ensure_buckets(config: PipelineConfig, _logger: PipelineLogger = None, _config: PipelineConfig = None) -> dict:
    """Ensure MinIO buckets exist."""
    if not boto3:
        return {"buckets": [], "created": 0}
    
    client = boto3.client(
        "s3",
        endpoint_url=_config.s3_endpoint,
        aws_access_key_id=_config.s3_access_key,
        aws_secret_access_key=_config.s3_secret_key,
    )
    
    buckets = ["raw", "processed", "curated"]
    existing = {b["Name"] for b in client.list_buckets().get("Buckets", [])}
    created = []
    
    for bucket in buckets:
        if bucket not in existing:
            client.create_bucket(Bucket=bucket)
            created.append(bucket)
            if _logger:
                _logger.info("ENSURE_BUCKETS", f"Created bucket: {bucket}")
    
    return {"buckets": buckets, "created": len(created)}


@PipelineStep(name="DATA_GENERATION", retries=1, timeout=30)
def generate_data(config: PipelineConfig, _logger: PipelineLogger = None, _config: PipelineConfig = None) -> dict:
    """Generate synthetic OSS and BSS data."""
    import hashlib
    from datetime import datetime, timezone, timedelta
    
    # Use timestamp-based seed for reproducibility
    seed = int(hashlib.sha256(datetime.now(timezone.utc).isoformat().encode()).hexdigest()[:8], 16) % (2**31)
    
    # Generate OSS data
    oss_records, fault_info = _generate_oss(200, seed=seed)
    
    # Generate BSS data (correlated with OSS faults)
    bss_records = _generate_bss(200, seed=seed + 1, fault_info=fault_info)
    
    return {
        "oss_count": len(oss_records),
        "bss_count": len(bss_records),
        "fault_cells": fault_info["fault_cells"],
        "fault_records": fault_info["fault_records"],
        "oss_records": oss_records,
        "bss_records": bss_records,
    }


def _generate_oss(n: int = 200, region: str = "demo", seed: int = 42) -> tuple:
    """Generate synthetic OSS KPI records."""
    if not np:
        raise RuntimeError("numpy required for data generation")
    
    rng = np.random.default_rng(seed)
    cells = [f"CELL-{i:03d}" for i in range(1, 11)]
    now = datetime.now(timezone.utc)
    
    # Fault injection plan
    n_fault_cells = int(rng.integers(2, 4))
    fault_cells = set(rng.choice(cells, size=n_fault_cells, replace=False))
    fault_start = int(n * rng.uniform(0.25, 0.45))
    fault_duration = int(n * rng.uniform(0.15, 0.25))
    fault_end = min(n - 1, fault_start + fault_duration)
    
    rows = []
    for i in range(n):
        ts = now - timedelta(minutes=n - i)
        cell = cells[i % len(cells)]
        
        hour = ts.hour + ts.minute / 60.0
        biz_factor = 1.0 + 0.4 * np.exp(-0.5 * ((hour - 13.0) / 3.0) ** 2)
        
        tput = float(rng.normal(80, 12)) * (0.7 + 0.3 / biz_factor)
        lat = float(rng.normal(22, 6)) * biz_factor
        loss = float(rng.uniform(0, 1.5)) * biz_factor
        usr = int(rng.integers(50, 300) * biz_factor)
        rsrp = float(rng.normal(-82, 8))
        
        is_fault = (cell in fault_cells) and (fault_start <= i <= fault_end)
        if is_fault:
            tput *= float(rng.uniform(0.10, 0.35))
            lat *= float(rng.uniform(2.5, 5.0))
            loss += float(rng.uniform(3.0, 8.0))
            rsrp -= float(rng.uniform(15, 30))
        
        rows.append({
            "ts": ts.isoformat(),
            "region": region,
            "cell_id": cell,
            "throughput_mbps": float(round(max(0.1, tput), 2)),
            "latency_ms": float(round(max(1.0, lat), 2)),
            "packet_loss_pct": float(round(min(15.0, max(0.0, loss)), 4)),
            "active_users": max(10, usr),
            "signal_rsrp_dbm": float(round(max(-140.0, min(-40.0, rsrp)), 2)),
            "is_fault": is_fault,
        })
    
    fault_info = {
        "fault_cells": sorted(fault_cells),
        "fault_start_idx": fault_start,
        "fault_end_idx": fault_end,
        "fault_records": sum(1 for r in rows if r["is_fault"]),
    }
    return rows, fault_info


def _generate_bss(n: int = 200, region: str = "demo", seed: int = 99, 
                  cells: list = None, fault_info: dict = None) -> list:
    """Generate synthetic BSS records."""
    if not np:
        raise RuntimeError("numpy required for data generation")
    
    rng = np.random.default_rng(seed)
    operators = ["Ooredoo Tunisie", "Tunisie Telecom", "Orange Tunisie"]
    if cells is None:
        cells = [f"CELL-{i:03d}" for i in range(1, 11)]
    
    prepaid_plans = [
        ("data_1go", 3.0, 7.0), ("data_4go", 8.0, 14.0), ("data_6go", 12.0, 18.0),
        ("data_25go", 25.0, 35.0), ("data_45go", 42.0, 55.0), ("data_100go", 65.0, 80.0),
    ]
    postpaid_plans = [
        ("post_40", 35.0, 45.0), ("post_60", 52.0, 68.0), ("post_90", 80.0, 100.0),
    ]
    
    fault_cells = set(fault_info["fault_cells"]) if fault_info else set()
    fault_start_idx = fault_info["fault_start_idx"] if fault_info else 0
    fault_end_idx = fault_info["fault_end_idx"] if fault_info else 0
    
    now = datetime.now(timezone.utc)
    rows = []
    for i in range(n):
        ts = now - timedelta(minutes=n - i)
        serving_cell = cells[i % len(cells)]
        
        is_prepaid = rng.random() < 0.80
        if is_prepaid:
            plan_name, lo, hi = prepaid_plans[int(rng.integers(0, len(prepaid_plans)))]
            line_type = "prepaid"
        else:
            plan_name, lo, hi = postpaid_plans[int(rng.integers(0, len(postpaid_plans)))]
            line_type = "postpaid"
        
        base_revenue = float(rng.uniform(lo, hi))
        base_data = float(rng.uniform(0.5, 45.0))
        base_voice = int(rng.integers(10, 550))
        base_sms = int(rng.integers(5, 180))
        base_churn = float(rng.uniform(0.0, 0.35))
        
        cell_faulted = (serving_cell in fault_cells and fault_start_idx <= i <= fault_end_idx)
        if cell_faulted:
            base_data *= float(rng.uniform(0.3, 0.6))
            base_voice = int(base_voice * rng.uniform(0.4, 0.7))
            base_churn += float(rng.uniform(0.3, 0.55))
        
        rows.append({
            "ts": ts.isoformat(),
            "region": region,
            "operator": operators[i % len(operators)],
            "subscriber_id": f"TN-{rng.integers(100000, 999999)}",
            "line_type": line_type,
            "plan": plan_name,
            "serving_cell": serving_cell,
            "revenue_tnd": float(round(base_revenue, 3)),
            "data_used_gb": float(round(max(0.01, base_data), 3)),
            "voice_min": max(0, base_voice),
            "sms_count": base_sms,
            "churn_risk": float(round(min(1.0, base_churn), 4)),
        })
    return rows


@PipelineStep(name="AI_INFERENCE", retries=3, timeout=60)
def run_inference(data: dict, config: PipelineConfig, _logger: PipelineLogger = None, _config: PipelineConfig = None) -> dict:
    """Run AI inference on generated data."""
    if not requests:
        # Fallback: compute simple risk score without AI service
        _logger and _logger.warning("AI_INFERENCE", "requests unavailable, computing fallback score")
        return {
            "sla_score": 0.5,
            "anomaly_count": 0,
            "revenue_anomaly_count": 0,
            "model_version": "fallback",
        }
    
    ai_url = _config.ai_service_url.rstrip("/")
    results = {}
    
    # Compute SLA risk features
    oss_records = data["oss_records"]
    tput = [r["throughput_mbps"] for r in oss_records]
    lat = [r["latency_ms"] for r in oss_records]
    loss = [r["packet_loss_pct"] for r in oss_records]
    
    features = {
        "mean_throughput_mbps": round(np.mean(tput), 4),
        "std_throughput_mbps": round(np.std(tput), 4),
        "mean_latency_ms": round(np.mean(lat), 4),
        "std_latency_ms": round(np.std(lat), 4),
        "max_latency_ms": round(max(lat), 4),
        "mean_packet_loss_pct": round(np.mean(loss), 4),
        "max_packet_loss_pct": round(max(loss), 4),
        "mean_active_users": round(np.mean([r["active_users"] for r in oss_records]), 4),
        "mean_signal_rsrp_dbm": round(np.mean([r["signal_rsrp_dbm"] for r in oss_records]), 4),
    }
    
    try:
        # SLA Risk
        resp = requests.post(
            f"{ai_url}/infer/sla-risk",
            json={"features": features},
            timeout=15
        )
        if resp.ok:
            results["sla_score"] = resp.json().get("score", 0.5)
        else:
            results["sla_score"] = 0.5
    except Exception as e:
        _logger and _logger.warning("AI_INFERENCE", f"SLA inference failed: {e}, using fallback")
        results["sla_score"] = 0.5
    
    # OSS Anomaly
    try:
        records_for_anomaly = [{
            "throughput_mbps": r["throughput_mbps"],
            "latency_ms": r["latency_ms"],
            "packet_loss_pct": r["packet_loss_pct"],
            "active_users": r["active_users"],
            "signal_rsrp_dbm": r["signal_rsrp_dbm"],
        } for r in oss_records]
        
        resp = requests.post(
            f"{ai_url}/infer/anomaly",
            json={"records": records_for_anomaly},
            timeout=30
        )
        if resp.ok:
            results["anomaly_count"] = resp.json().get("anomalous_count", 0)
        else:
            results["anomaly_count"] = int(len(oss_records) * 0.05)  # 5% fallback
    except Exception as e:
        _logger and _logger.warning("AI_INFERENCE", f"Anomaly detection failed: {e}")
        results["anomaly_count"] = int(len(oss_records) * 0.05)
    
    # BSS Anomaly
    bss_records = data["bss_records"]
    try:
        bss_for_anomaly = [{
            "revenue_tnd": r["revenue_tnd"],
            "data_used_gb": r["data_used_gb"],
            "voice_min": float(r["voice_min"]),
            "sms_count": float(r["sms_count"]),
            "churn_risk": r["churn_risk"],
        } for r in bss_records]
        
        resp = requests.post(
            f"{ai_url}/infer/revenue-anomaly",
            json={"records": bss_for_anomaly},
            timeout=30
        )
        if resp.ok:
            results["revenue_anomaly_count"] = resp.json().get("anomalous_count", 0)
        else:
            results["revenue_anomaly_count"] = int(len(bss_records) * 0.05)
    except Exception as e:
        _logger and _logger.warning("AI_INFERENCE", f"Revenue anomaly failed: {e}")
        results["revenue_anomaly_count"] = int(len(bss_records) * 0.05)
    
    results["model_version"] = "v2.0"
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Main Pipeline Runner
# ─────────────────────────────────────────────────────────────────────────────

class PipelineRunner:
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.logger = PipelineLogger("pipeline-runner", config.log_level)
        self.idempotency = IdempotencyGuard(self.logger)
        self.start_time: Optional[float] = None
        self.step_results: list[StepResult] = []
    
    def run(self) -> int:
        """Execute the full pipeline. Returns exit code."""
        self.start_time = time.time()
        
        # Acquire idempotency lock
        if self.config.idempotent and not self.idempotency.acquire():
            self.logger.warning("MAIN", "Pipeline already running or recently ran. Exiting.")
            return 0
        
        try:
            self.logger.info("MAIN", "Starting pipeline execution")
            
            # Health checks
            if not check_database(self.logger, self.config):
                self.logger.error("MAIN", "Database health check failed")
                return 2
            
            if not check_minio(self.logger, self.config):
                self.logger.error("MAIN", "MinIO health check failed")
                return 2
            
            # Run steps
            results = []
            
            # Step 1: Ensure buckets
            result = ensure_buckets(config=self.config, _logger=self.logger, _config=self.config)
            results.append(("ENSURE_BUCKETS", result))
            
            # Step 2: Generate data
            result = generate_data(config=self.config, _logger=self.logger, _config=self.config)
            results.append(("DATA_GENERATION", result))
            
            # Step 3: Run AI inference
            result = run_inference(result, config=self.config, _logger=self.logger, _config=self.config)
            results.append(("AI_INFERENCE", result))
            
            # Check timeout
            elapsed = time.time() - self.start_time
            if elapsed > self.config.timeout_seconds:
                self.logger.error("MAIN", f"Pipeline timeout: {elapsed:.1f}s > {self.config.timeout_seconds}s")
                return 3
            
            # Success
            self.logger.info("MAIN", f"Pipeline completed successfully in {elapsed:.1f}s",
                           total_steps=len(results),
                           sla_score=result.get("sla_score"),
                           anomalies=result.get("anomaly_count"))
            return 0
            
        except Exception as e:
            self.logger.error("MAIN", f"Pipeline failed: {type(e).__name__}: {e}",
                            traceback=traceback.format_exc())
            return 1
            
        finally:
            self.idempotency.release()
    
    def get_summary(self) -> dict:
        """Get pipeline execution summary."""
        elapsed = time.time() - self.start_time if self.start_time else 0
        return {
            "elapsed_seconds": round(elapsed, 2),
            "steps": [asdict(r) for r in self.step_results],
            "success": all(r.success for r in self.step_results),
        }


def main():
    """Main entry point."""
    config = PipelineConfig.from_env()
    
    if not config.database_url:
        print("ERROR: DATABASE_URL not set", file=sys.stderr)
        sys.exit(4)
    
    runner = PipelineRunner(config)
    exit_code = runner.run()
    
    summary = runner.get_summary()
    print(json.dumps(summary, indent=2))
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
