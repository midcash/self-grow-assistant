import os
import sys
from pathlib import Path


def get_base_dir() -> Path:
    """Returns the exe's directory in frozen mode, or project root in dev."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def get_data_dir() -> Path:
    data_dir = get_base_dir() / "data"
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def get_static_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS) / "static"
    return Path(__file__).resolve().parent.parent / "static"
