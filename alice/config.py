"""Configuration loading and small shared helpers."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def load_config(path=None):
    path = Path(path) if path else ROOT / "config.yaml"
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg["_path"] = str(path.resolve())
    return cfg


def hex_to_rgb(h):
    h = str(h).strip().lstrip("#")
    if len(h) != 6:
        raise ValueError(f"Invalid hex colour in config: #{h}")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
