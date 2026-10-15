"""Settings read from environment variables, so the same code runs in Colab, locally and on a Space.

CLARA_PROVIDER   "anthropic" (default) or "mock" (no API key needed; scripted replies)
CLARA_MODEL_ID   LiteLLM model id, default "anthropic/claude-sonnet-4-5"
ANTHROPIC_API_KEY
CLARA_DATA_DIR   where episodes and session exports are saved, default "./lab"
                 (on a Hugging Face Space with persistent storage, set this to "/data/lab")
CLARA_USERNAME / CLARA_PASSWORD   optional: if both are set, the studio asks for a login
"""
import os
from pathlib import Path


PROVIDER = os.environ.get("CLARA_PROVIDER", "anthropic").lower()
MODEL_ID = os.environ.get("CLARA_MODEL_ID", "anthropic/claude-sonnet-4-5")

LAB = Path(os.environ.get("CLARA_DATA_DIR", "lab"))
EPISODES = LAB / "episodes"
SKILLS = Path(os.environ.get("CLARA_SKILLS_DIR", Path(__file__).resolve().parent / "skills"))

AUTH_USER = os.environ.get("CLARA_USERNAME")
AUTH_PASS = os.environ.get("CLARA_PASSWORD")


def secret(name: str):
    """Read a secret from the environment, falling back to Colab's secret store."""
    value = os.environ.get(name)
    if value:
        return value
    try:
        from google.colab import userdata
        return userdata.get(name)
    except Exception:
        return None
