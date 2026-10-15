"""The research-agent setup from notebook section 6: file tools, Clara tools and new_agent().
Imported only when you run the agent (from a notebook or a script), not by the studio."""
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from smolagents import CodeAgent, Tool, tool

from . import config, storage
from .episode import run_episode
from .llm import get_model
from .personas import PROFILES
from .tasks import TASKS

ROOTS = {"lab": lambda: config.LAB, "skills": lambda: config.SKILLS}


def _safe(path: str) -> Path:
    p = Path(path)
    if p.is_absolute() or ".." in p.parts or not p.parts or p.parts[0] not in ROOTS:
        raise ValueError("Paths must stay inside lab/ or skills/, e.g. 'lab/notes.md'.")
    return ROOTS[p.parts[0]]().joinpath(*p.parts[1:])


@tool
def read_file(path: str) -> str:
    """Read a text file from lab/ or skills/.

    Args:
        path: Relative path such as 'lab/clara-findings.md' or 'skills/clara-accessibility-review/SKILL.md'.
    """
    p = _safe(path)
    if not p.exists():
        return f"No file at {path}. Use list_files to see what exists."
    text = p.read_text()
    return text if len(text) < 12000 else text[:12000] + "\n[...truncated; file is longer]"


@tool
def write_file(path: str, content: str) -> str:
    """Create or overwrite a text file under lab/. Use for plans, notes and findings.

    Args:
        path: Relative path under lab/, e.g. 'lab/clara-findings.md'.
        content: Full text to write.
    """
    if Path(path).parts[:1] != ("lab",):
        return "Only lab/ is writable."
    p = _safe(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return f"Saved {len(content)} characters to {path}."


@tool
def list_files(folder: str) -> str:
    """List files under lab/ or skills/.

    Args:
        folder: 'lab', 'skills', or a subfolder such as 'lab/episodes'.
    """
    p = _safe(folder)
    top = ROOTS[Path(folder).parts[0]]()
    files = sorted(f"{Path(folder).parts[0]}/{f.relative_to(top)}" for f in p.rglob("*") if f.is_file())
    return "\n".join(files) or f"{folder} is empty."


def trace(step, agent=None):
    """Print a one-line summary per agent step and append it to lab/trace.log."""
    n = getattr(step, "step_number", "?")
    calls = getattr(step, "tool_calls", None) or []
    names = ", ".join(getattr(c, "name", "?") for c in calls) or "-"
    err = getattr(step, "error", None)
    line = f"step {n}: tools={names}" + (f"  ERROR: {err}" if err else "")
    print("  ·", line)
    storage.ensure_dirs()
    with open(config.LAB / "trace.log", "a") as f:
        f.write(line + "\n")


class ClaraListTool(Tool):
    name = "clara_list_setup"
    description = ("List the available Clara older-adult personas (with their impairment settings) "
                   "and benchmark tasks. Call this first before running episodes.")
    inputs = {}
    output_type = "string"

    def forward(self):
        return json.dumps({"personas": {k: asdict(v) for k, v in PROFILES.items()},
                           "tasks": {k: v["persona_goal"] for k, v in TASKS.items()}}, indent=2)


class ClaraEpisodeTool(Tool):
    name = "clara_run_episode"
    description = (
        "Run one benchmark episode: an assistant whose communication style is `sut_style` tries to help "
        "a Clara persona finish a task. Returns a short JSON score (success, abandoned, turns, "
        "repeat_requests, overlong_sut_replies) and saves the full transcript to lab/episodes/. "
        "To compare designs, change ONE thing in sut_style and rerun on the same persona and task.")
    inputs = {
        "persona": {"type": "string", "description": "Persona key, e.g. 'clara-moderate'."},
        "task": {"type": "string", "description": "Task key, e.g. 'pharmacy-refill'."},
        "sut_style": {"type": "string", "description": "Communication instructions for the assistant being "
                      "tested, e.g. 'One step per message, confirm before moving on.'"},
        "label": {"type": "string", "description": "Short name for this variant, used in the filename."},
    }
    output_type = "string"

    def forward(self, persona, task, sut_style, label):
        if persona not in PROFILES or task not in TASKS:
            return f"Unknown persona or task. Personas: {list(PROFILES)}. Tasks: {list(TASKS)}."
        return json.dumps(run_episode(persona, task, sut_style, label))


class ClaraReportTool(Tool):
    name = "clara_summarize_results"
    description = ("Summarize every saved episode in lab/episodes/ as one line per "
                   "(task, persona, variant) with its scores. Use instead of reading transcripts one by one.")
    inputs = {}
    output_type = "string"

    def forward(self):
        rows = [f"{e['_file']}: {json.dumps(e['score'])}" for e in storage.load_episodes()]
        return "\n".join(rows) or "No episodes yet."


def new_agent(max_steps: int = 25) -> CodeAgent:
    return CodeAgent(
        model=get_model(),
        tools=[read_file, write_file, list_files, ClaraListTool(), ClaraEpisodeTool(), ClaraReportTool()],
        max_steps=max_steps,
        step_callbacks=[trace],
        instructions=f"""Current time: {datetime.now(timezone.utc).isoformat()}.
You are an accessibility research lead running the Cognitive Accessibility Benchmark with Clara personas.
Before starting, read skills/clara-accessibility-review/SKILL.md and follow it. Check lab/ for earlier work.
Personas are simulations, not real people; findings are hypotheses until validated with older adults.
Save a findings note to lab/clara-findings.md that cites the episode files it relies on.""",
    )
