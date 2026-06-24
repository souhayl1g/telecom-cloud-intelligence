"""
Bootstrap default ML models if none exist in /app/models/.
This ensures ai-service can start even before notebooks train models.
Models will be replaced by notebook-trained versions once available.
"""

from pathlib import Path

MODELS_DIR = Path("/app/models")


def bootstrap():
    MODELS_DIR.mkdir(exist_ok=True)

    # v3.0 model artifacts (loaded by model_cache.py)
    v3_models = [
        "cem_v3_model.joblib",
        "cem_v3_feature_names.joblib",
        "rat_v3_model.joblib",
        "rat_v3_feature_names.joblib",
        "vae_v3_model.pt",
        "vae_v3_feature_names.joblib",
    ]

    missing = [m for m in v3_models if not (MODELS_DIR / m).exists()]

    if not missing:
        print("[bootstrap] All v3.0 models present.")
        return

    print(f"[bootstrap] WARNING: v3.0 models missing: {missing}")
    print(
        "[bootstrap] Please train models via notebooks or run pb-retrain-model playbook."
    )
    # We intentionally do NOT create synthetic v2.0 fallback models anymore.
    # The v3 routers in ai-service require the real artifacts.


if __name__ == "__main__":
    bootstrap()
