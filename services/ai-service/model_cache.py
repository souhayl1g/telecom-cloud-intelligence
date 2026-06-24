import time
from pathlib import Path

import joblib
import torch

from config import (
    CEM_MODEL_PATH,
    RAT_MODEL_PATH,
    VAE_MODEL_PATH,
    VAE_SCALER_PATH,
    MODELS_DIR,
)
from vae_arch import ExperienceVAE, ExperienceVAELegacy, ExperienceVAEv3

CEM_FEATURE_NAMES_PATH = MODELS_DIR / "cem_v3_feature_names.joblib"
RAT_FEATURE_NAMES_PATH = MODELS_DIR / "rat_v3_feature_names.joblib"
VAE_FEATURE_NAMES_PATH = MODELS_DIR / "vae_v3_feature_names.joblib"

_cache = {
    "cem": None,
    "rat": None,
    "vae": None,
    "vae_scaler": None,
    "cem_features": None,
    "rat_features": None,
    "vae_features": None,
    "loaded_at": 0,
}
_cache_ttl = 30  # reload models every 30 seconds max


def _get_model_file_mtime(path: Path) -> float:
    """Get model file modification time, return 0 if doesn't exist."""
    try:
        return path.stat().st_mtime if path.exists() else 0
    except Exception:
        return 0


def load_models(force: bool = False):
    """Load pre-trained models from disk with caching.

    Models are reloaded if:
    - force=True
    - Cache is empty
    - Model files have been modified since last load

    This allows notebooks to retrain and save models while AI service runs.
    """
    global _cache

    now = time.time()
    should_reload = force or _cache["cem"] is None

    # Check if models need reload based on file mtime
    if not should_reload and now - _cache["loaded_at"] > _cache_ttl:
        paths = [
            CEM_MODEL_PATH,
            RAT_MODEL_PATH,
            VAE_MODEL_PATH,
            VAE_SCALER_PATH,
        ]
        if any(_get_model_file_mtime(p) > _cache["loaded_at"] for p in paths):
            should_reload = True

    if not should_reload:
        return _cache

    # --- v3.0 CEM (LightGBM) ---
    try:
        if CEM_MODEL_PATH.exists():
            _cache["cem"] = joblib.load(CEM_MODEL_PATH)
            print(f"  [ml] loaded CEM v3 model from {CEM_MODEL_PATH}")
            # Load the feature-name contract trained alongside the model. The
            # router builds X in this exact order so retraining with a wider
            # feature set never causes a shape-mismatch 422 at inference time.
            if CEM_FEATURE_NAMES_PATH.exists():
                _cache["cem_features"] = list(joblib.load(CEM_FEATURE_NAMES_PATH))
                print(
                    f"  [ml]   CEM feature contract: {len(_cache['cem_features'])} cols"
                )
        else:
            print(f"  [ml] warning: CEM v3 model not found at {CEM_MODEL_PATH}")
    except Exception as e:
        print(f"  [ml] warning: failed to reload CEM v3 model: {e}")

    # --- v3.0 RAT (XGBoost) ---
    try:
        if RAT_MODEL_PATH.exists():
            _cache["rat"] = joblib.load(RAT_MODEL_PATH)
            print(f"  [ml] loaded RAT v3 model from {RAT_MODEL_PATH}")
            if RAT_FEATURE_NAMES_PATH.exists():
                _cache["rat_features"] = list(joblib.load(RAT_FEATURE_NAMES_PATH))
                print(
                    f"  [ml]   RAT feature contract: {len(_cache['rat_features'])} cols"
                )
        else:
            print(f"  [ml] warning: RAT v3 model not found at {RAT_MODEL_PATH}")
    except Exception as e:
        print(f"  [ml] warning: failed to reload RAT v3 model: {e}")

    # --- v3.0 VAE (PyTorch) ---
    try:
        if VAE_MODEL_PATH.exists() and VAE_SCALER_PATH.exists():
            checkpoint = torch.load(
                VAE_MODEL_PATH, map_location="cpu", weights_only=True
            )
            input_dim = checkpoint.get("input_dim", 9)
            latent_dim = checkpoint.get("latent_dim", 8)
            hidden_dim = checkpoint.get("hidden_dim", 32)

            # Try architectures in order: new deep → legacy sequential → old linear
            for arch_class in [ExperienceVAEv3, ExperienceVAELegacy, ExperienceVAE]:
                try:
                    vae_model = arch_class(
                        input_dim=input_dim,
                        latent_dim=latent_dim,
                        hidden_dim=hidden_dim,
                    )
                    vae_model.load_state_dict(checkpoint["model_state_dict"])
                    vae_model.eval()
                    _cache["vae"] = vae_model
                    _cache["vae_threshold"] = checkpoint.get("threshold", 0.18)
                    ckpt_names = checkpoint.get("feature_names", [])
                    if not ckpt_names and VAE_FEATURE_NAMES_PATH.exists():
                        ckpt_names = list(joblib.load(VAE_FEATURE_NAMES_PATH))
                    _cache["vae_feature_names"] = ckpt_names
                    _cache["vae_features"] = ckpt_names
                    _cache["vae_scaler"] = joblib.load(VAE_SCALER_PATH)
                    print(
                        f"  [ml] loaded VAE v3 model ({arch_class.__name__}) from {VAE_MODEL_PATH}"
                    )
                    break
                except RuntimeError:
                    continue
            else:
                raise RuntimeError(
                    f"VAE checkpoint at {VAE_MODEL_PATH} does not match any known architecture "
                    f"(tried ExperienceVAEv3, ExperienceVAELegacy, ExperienceVAE)"
                )
        else:
            print("  [ml] warning: VAE v3 model or scaler not found")
    except Exception as e:
        print(f"  [ml] warning: failed to reload VAE v3 model: {e}")

    _cache["loaded_at"] = now
    return _cache
