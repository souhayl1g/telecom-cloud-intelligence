import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys
sys.path.insert(0, ".")
import model_cache


def test_load_models_raises_when_no_files_and_empty_cache():
    model_cache._cache = {"sla": None, "anomaly": None, "revenue": None, "loaded_at": 0}
    with patch.object(Path, "exists", return_value=False):
        with pytest.raises(FileNotFoundError, match="Pre-trained model"):
            model_cache.load_models(force=True)


def test_load_models_returns_cached_when_fresh():
    import time
    mock_model = MagicMock()
    model_cache._cache = {
        "sla": mock_model, "anomaly": mock_model, "revenue": mock_model, "loaded_at": time.time()
    }
    sla, anomaly, revenue = model_cache.load_models(force=False)
    assert sla is mock_model
    assert anomaly is mock_model
