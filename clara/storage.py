"""All reading and writing of results goes through here, so moving from files to a
Hugging Face dataset or a database later only means changing this module."""
import json
from pathlib import Path

from . import config


def ensure_dirs():
    config.EPISODES.mkdir(parents=True, exist_ok=True)


def save_episode(filename: str, payload: dict) -> Path:
    ensure_dirs()
    path = config.EPISODES / filename
    path.write_text(json.dumps(payload, indent=2))
    return path


def load_episodes() -> list:
    ensure_dirs()
    return [json.loads(f.read_text()) | {"_file": f.stem}
            for f in sorted(config.EPISODES.glob("*.json"))]


def save_text(filename: str, text: str) -> Path:
    ensure_dirs()
    path = config.LAB / filename
    path.write_text(text)
    return path
