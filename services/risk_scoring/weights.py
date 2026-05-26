import yaml
import time
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_cache = {"data": None, "loaded_at": 0.0}
CACHE_TTL_SECONDS = 60


def load_weights(path: Path) -> dict:
    now = time.time()
    if _cache["data"] and (now - _cache["loaded_at"]) < CACHE_TTL_SECONDS:
        return _cache["data"]

    try:
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        _cache["data"]      = data
        _cache["loaded_at"] = now
        logger.info(f"Weights reloaded from {path}")
        return data
    except Exception as e:
        logger.error(f"Failed to load weights: {e}")
        if _cache["data"]:
            logger.warning("Serving stale weights cache")
            return _cache["data"]
        raise