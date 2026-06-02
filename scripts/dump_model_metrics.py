#!/usr/bin/env python3
"""Dump real ML metrics from notebook model cards into a single JSON contract.

Reads:
    notebooks/models/cem_v3_model_card.md
    notebooks/models/oss_vae_v3_model_card.md
    notebooks/models/rat_underservice_v3_model_card.md
    notebooks/models/master_v3_training_summary.md   (optional, for sample counts)

Writes:
    notebooks/models/metrics.json

Honest values only — pulled from model cards, no synthetic numbers.
The dashboard /api/model-metrics route reads this JSON at request time, so
re-running this script (or pb-retrain-model) hot-refreshes the dashboard
without redeploys.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "notebooks" / "models"
OUT = MODELS / "metrics.json"


def _read(p: Path) -> str:
    # Strip markdown bold/italic so regex doesn't trip on "**ROC-AUC**: 0.98"
    raw = p.read_text(encoding="utf-8") if p.exists() else ""
    return raw.replace("**", "").replace("__", "")


def _num(text: str, key: str) -> float | None:
    # Matches "R²=0.9784" / "ROC-AUC: 0.9203" / "MAE=0.0304" — allows opt. trailing ":" or "="
    m = re.search(rf"{re.escape(key)}\s*[:=]\s*([0-9]*\.?[0-9]+)", text)
    return float(m.group(1)) if m else None


def _mtime_iso(p: Path) -> str | None:
    if not p.exists():
        return None
    return datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).isoformat()


def parse_samples() -> dict[str, dict]:
    """Pull sample counts from master_v3_training_summary.md (a markdown table)."""
    txt = _read(MODELS / "master_v3_training_summary.md")
    out: dict[str, dict] = {}
    # Row pattern: | CEM | 2,097,822 | 370,204 | 39.2% | 60.8% |
    for m in re.finditer(
        r"\|\s*(CEM|Anomaly|RAT)\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)\s*\|\s*([\d.]+)%?\s*\|\s*([\d.]+)%?\s*\|",
        txt,
    ):
        key, train, test, real, sim = m.groups()
        out[key] = {
            "trainSplit": int(train.replace(",", "")),
            "testSplit": int(test.replace(",", "")),
            "samples": int(train.replace(",", "")) + int(test.replace(",", "")),
            "realPct": float(real),
            "simulatedPct": float(sim),
        }
    return out


def parse_cem() -> dict:
    txt = _read(MODELS / "cem_v3_model_card.md")
    # Prefer Temporal hold-out (more honest); fall back to Random split.
    tem = txt.split("Temporal hold-out", 1)[-1] if "Temporal hold-out" in txt else txt
    rand = txt.split("Random split", 1)[-1].split("##", 1)[0] if "Random split" in txt else ""
    return {
        "name": "CEM Experience Score",
        "algorithm": "LightGBM (DART)",
        "version": "v3.0-gpu",
        "task": "regression",
        "features": 13,
        "featureNames": [
            "usim_bottleneck", "data_intensity", "dou_total", "duration",
            "s1_mme_sr", "iu_attach_sr", "gb_attach_sr",
            "avg_throughput", "avg_latency", "avg_packet_loss", "anomaly_rate",
            "generation_4g", "generation_5g",
        ],
        "metrics": {
            "test": {
                "r2": _num(tem, "R²") or _num(rand, "R²"),
                "mae": _num(tem, "MAE") or _num(rand, "MAE"),
                "rmse": _num(tem, "RMSE") or _num(rand, "RMSE"),
            },
            "randomSplit": {
                "r2": _num(rand, "R²"),
                "mae": _num(rand, "MAE"),
                "rmse": _num(rand, "RMSE"),
            },
        },
        "lastTrained": _mtime_iso(MODELS / "cem_v3_lightgbm.joblib")
                       or _mtime_iso(MODELS / "cem_v3_lightgbm_gpu.joblib"),
        "source": "notebooks/models/cem_v3_model_card.md",
    }


def parse_vae() -> dict:
    txt = _read(MODELS / "oss_vae_v3_model_card.md")
    return {
        "name": "OSS Experience Anomaly",
        "algorithm": "Variational Autoencoder (PyTorch)",
        "version": "v3.0-gpu",
        "task": "anomaly_detection",
        "features": 9,
        "featureNames": [
            "throughput_mbps", "latency_ms", "packet_loss_rate", "jitter_ms",
            "cell_load_pct", "rsrp_dbm", "active_users", "integrity", "call_drop_rate",
        ],
        "metrics": {
            "rocAuc": _num(txt, "ROC-AUC"),
            "prAuc": _num(txt, "PR-AUC"),
        },
        "lastTrained": _mtime_iso(MODELS / "oss_vae_v3.pt")
                       or _mtime_iso(MODELS / "oss_vae_v3_gpu.pt"),
        "source": "notebooks/models/oss_vae_v3_model_card.md",
    }


def parse_rat() -> dict:
    txt = _read(MODELS / "rat_underservice_v3_model_card.md")
    tem_block = txt.split("Temporal hold-out", 1)[-1].split("##", 1)[0] if "Temporal hold-out" in txt else ""
    rand_block = txt.split("Random split", 1)[-1].split("##", 1)[0] if "Random split" in txt else ""
    cv_block = txt.split("CV", 1)[-1].split("##", 1)[0] if "CV" in txt else ""
    return {
        "name": "RAT Underservice Detection",
        "algorithm": "XGBoost Classifier",
        "version": "v3.0-gpu",
        "task": "classification",
        "features": 19,
        "featureNames": [
            "volte_flag", "usim_flag", "dou_total", "duration",
            "voice_onlinetime_3g", "voice_onlinetime_2g",
            "s1_mme_sr", "iu_attach_sr", "gb_attach_sr",
            "session_flag", "attach_gap",
            "avg_integrity_area", "avg_cdr_area", "avg_throughput_area",
            "avg_users_area", "avg_latency_area", "avg_loss_area",
            "cell_count_area", "anomaly_count_area",
        ],
        "metrics": {
            "rocAuc": _num(tem_block, "ROC-AUC") or _num(rand_block, "ROC-AUC"),
            "f1": _num(tem_block, "F1@0.5") or _num(rand_block, "F1@0.5"),
            "randomSplit": {
                "rocAuc": _num(rand_block, "ROC-AUC"),
                "f1": _num(rand_block, "F1@0.5"),
            },
            "temporalHoldOut": {
                "rocAuc": _num(tem_block, "ROC-AUC"),
                "f1": _num(tem_block, "F1@0.5"),
            },
            "cv5fold": {
                "rocAucMean": _num(cv_block, "Mean ROC-AUC"),
                "prAucMean": _num(cv_block, "Mean PR-AUC"),
            },
        },
        "lastTrained": _mtime_iso(MODELS / "rat_underservice_v3_xgb.joblib")
                       or _mtime_iso(MODELS / "rat_v3_xgb_gpu.joblib"),
        "source": "notebooks/models/rat_underservice_v3_model_card.md",
    }


def main() -> int:
    samples = parse_samples()
    models = {
        "cem_score": {**parse_cem(), "trainingData": samples.get("CEM", {})},
        "oss_anomaly": {**parse_vae(), "trainingData": samples.get("Anomaly", {})},
        "rat_underservice": {**parse_rat(), "trainingData": samples.get("RAT", {})},
    }
    payload = {
        "models": models,
        "computedAt": datetime.now(timezone.utc).isoformat(),
        "source": "scripts/dump_model_metrics.py",
        "note": "Honest metrics pulled from notebooks/models/*_model_card.md (no synthetic values).",
    }
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[ok] wrote {OUT.relative_to(ROOT)}")
    # echo headline numbers for sanity
    cem = models["cem_score"]["metrics"]["test"]
    vae = models["oss_anomaly"]["metrics"]
    rat = models["rat_underservice"]["metrics"]
    print(f"  CEM   R²={cem.get('r2')} MAE={cem.get('mae')}")
    print(f"  VAE   ROC-AUC={vae.get('rocAuc')} PR-AUC={vae.get('prAuc')}")
    print(f"  RAT   ROC-AUC={rat.get('rocAuc')} F1={rat.get('f1')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
