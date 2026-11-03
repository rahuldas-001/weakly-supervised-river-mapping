"""Colab bootstrap helpers.

Notebooks should contain analysis and figures, not setup logic. The single
bootstrap cell at the top of every notebook calls setup() and nothing else.
"""

from __future__ import annotations

import os
import subprocess
import sys


def in_colab() -> bool:
    return "google.colab" in sys.modules


def setup(mount_drive: bool = True, ee_project: str | None = None) -> str:
    """Prepare a Colab session and return the current git commit hash.

    The commit hash is returned so it can be written into output metadata.
    Every artefact should record the code version that produced it.
    """
    if in_colab() and mount_drive:
        from google.colab import drive  # type: ignore

        drive.mount("/content/drive", force_remount=False)

    if ee_project is None:
        ee_project = os.environ.get("BRAIDBENCH_EE_PROJECT")
        if ee_project is None and in_colab():
            try:
                from google.colab import userdata  # type: ignore

                ee_project = userdata.get("EE_PROJECT")
            except Exception:
                ee_project = None

    if ee_project:
        import ee

        try:
            ee.Initialize(project=ee_project)
        except Exception:
            ee.Authenticate()
            ee.Initialize(project=ee_project)
        os.environ["BRAIDBENCH_EE_PROJECT"] = ee_project

    return git_hash()


def git_hash() -> str:
    """Short commit hash of the installed repo, or 'unknown' outside a checkout."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return out.stdout.strip()
    except Exception:
        return "unknown"
