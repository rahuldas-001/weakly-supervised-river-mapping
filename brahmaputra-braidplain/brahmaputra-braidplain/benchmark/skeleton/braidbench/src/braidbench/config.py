"""Configuration loading.

All paths, thresholds, and asset IDs live in configs/*.yaml, never in notebooks.
This means a reviewer can see every parameter in one place, and a rerun with
different settings does not require editing code.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "configs" / "default.yaml"


@dataclass
class Config:
    """Flat access to nested YAML config, with environment overrides."""

    raw: dict[str, Any] = field(default_factory=dict)

    def __getitem__(self, key: str) -> Any:
        node: Any = self.raw
        for part in key.split("."):
            node = node[part]
        return node

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except (KeyError, TypeError):
            return default

    @property
    def data_root(self) -> Path:
        """Where working data lives.

        On Colab this is a Drive path; locally it is ./data. Override with the
        BRAIDBENCH_DATA environment variable. Never committed to git.
        """
        env = os.environ.get("BRAIDBENCH_DATA")
        if env:
            return Path(env)
        if Path("/content/drive/MyDrive").exists():
            return Path("/content/drive/MyDrive") / self.get("project.drive_folder", "BRAIDBENCH")
        return REPO_ROOT / "data"

    def path(self, *parts: str) -> Path:
        p = self.data_root.joinpath(*parts)
        p.mkdir(parents=True, exist_ok=True)
        return p


def load(path: str | Path | None = None) -> Config:
    path = Path(path) if path else DEFAULT_CONFIG
    with open(path) as fh:
        return Config(yaml.safe_load(fh))
