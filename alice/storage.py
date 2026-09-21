"""Session folders and file writing.

A session folder is created as soon as participant details are entered, named
with group "PENDING". Each section writes its files the moment it finishes, so
a crash or power cut loses at most the section in progress. On save the folder
is renamed with the chosen group label; on abort it is renamed "PARTIAL".
"""
import csv
import json
import math
import re
import shutil
from datetime import datetime
from pathlib import Path

import numpy as np

from .config import ROOT


def results_root(cfg):
    p = Path(cfg["software"]["results_dir"])
    return p if p.is_absolute() else ROOT / p


def existing_subject_numbers(cfg):
    root = results_root(cfg)
    if not root.exists():
        return set()
    nums = set()
    for p in root.iterdir():
        m = re.match(r"^S(\d+)_", p.name)
        if p.is_dir() and m:
            nums.add(int(m.group(1)))
    return nums


def next_subject_number(cfg):
    return max(existing_subject_numbers(cfg), default=0) + 1


def _clean(v):
    if v is None:
        return ""
    if isinstance(v, (bool, np.bool_)):
        return int(v)
    if isinstance(v, (float, np.floating)):
        return "" if not math.isfinite(float(v)) else round(float(v), 3)
    if isinstance(v, np.integer):
        return int(v)
    return v


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        f = float(o)
        return f if math.isfinite(f) else None
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


def _sanitise(obj):
    """Replace NaN/inf with None so session.json is valid JSON."""
    if isinstance(obj, dict):
        return {k: _sanitise(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitise(v) for v in obj]
    if isinstance(obj, (float, np.floating)) and not math.isfinite(float(obj)):
        return None
    return obj


class SessionStore:
    def __init__(self, cfg, subject_number):
        self.cfg = cfg
        self.subject = int(subject_number)
        self.subject_id = f"S{self.subject:03d}"
        self.datetime = datetime.now().strftime("%Y%m%d_%H%M")
        self.root = results_root(cfg)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self._unique(self._name("PENDING"))
        self.path.mkdir(parents=True)
        shutil.copy(cfg["_path"], self.path / "config_used.yaml")

    def _name(self, group):
        return self.cfg["software"]["folder_name_format"].format(
            subject=self.subject, group=group, datetime=self.datetime)

    def _unique(self, name):
        p = self.root / name
        k = 2
        while p.exists():
            p = self.root / f"{name}_{k}"
            k += 1
        return p

    def file(self, name):
        return self.path / name

    def write_csv(self, name, fieldnames, rows):
        with open(self.file(name), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            w.writeheader()
            for r in rows:
                w.writerow({k: _clean(r.get(k)) for k in fieldnames})

    def write_json(self, name, obj):
        tmp = self.file(name + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(_sanitise(obj), f, indent=2, default=_json_default)
        tmp.replace(self.file(name))

    def _rename(self, group):
        target = self._unique(self._name(group))
        self.path.rename(target)
        self.path = target
        return target

    def finalize(self, group):
        return self._rename(group)

    def mark_partial(self):
        return self._rename("PARTIAL")
