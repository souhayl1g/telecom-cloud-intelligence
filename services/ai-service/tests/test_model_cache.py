from unittest.mock import patch, MagicMock
from pathlib import Path
import sys
sys.path.insert(0, ".")
import model_cache


def test_load_models_returns_cache_when_models_missing():
    """When model files are missing, cache should be returned with None values."""
    model_cache._cache = {"cem": None, "rat": None, "vae": None, "vae_scaler": None, "loaded_at": 0}
    with patch.object(Path, "exists", return_value=False):
        result = model_cache.load_models(force=True)
    assert result["cem"] is None
    assert result["rat"] is None
    assert result["vae"] is None
    assert result["loaded_at"] > 0


def test_load_models_returns_cached_when_fresh():
    import time
    mock_model = MagicMock()
    model_cache._cache = {
        "cem": mock_model, "rat": mock_model, "vae": mock_model, "vae_scaler": mock_model, "loaded_at": time.time()
    }
    result = model_cache.load_models(force=False)
    assert result["cem"] is mock_model
    assert result["rat"] is mock_model
    assert result["vae"] is mock_model
