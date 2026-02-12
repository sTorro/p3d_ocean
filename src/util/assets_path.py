# -*- coding: utf-8 -*-

"""
Filename: assets_path.py
Author: storro
Date: 2026-02-11
Description: Utility function to construct asset file paths
"""

import os

from pathlib import Path
from panda3d.core import Filename

# Base folder for this Panda3D project: two levels up from this file, then "assets"
BASE_DIR = os.path.join(Path(__file__).resolve().parents[2], "assets")

def assets_path(*parts: str) -> str:
    return str(
        Filename.from_os_specific(os.path.join(str(BASE_DIR), *parts))
    )
