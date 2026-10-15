"""The episode runner and scoring (notebook section 4) plus the improved persona turn
used by the designer studio (Week 3)."""
import re

from .llm import _llm
from .personas import ClaraProfile, PROFILES
from .tasks import TASKS
from . import storage

CONFUSION = ["again", "repeat", "what was", "forgot", "say that", "too fast", "lost track",
             "confus", "didn't catch", "not sure", "slow down"]


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", text.lower()).strip("-") or "variant"


def _sentences(text: str) -> list:
    return [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]


def _first_sentences(text: str, n: int) -> str:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    kept = " ".join(parts[:n])
    return kept + (" [...the rest went by too fast]" if len(parts) > n else "")


def persona_reply(p: ClaraProfile, goal: str, sut_history: list) -> str:
    """One Clara turn. She only sees the last `memory_turns` replies, each cut to
    `sentences_absorbed` sentences. Guards against invented details and overplayed confusion."""
    visible = [_first_sentences(r, p.sentences_absorbed) for r in sut_history[-p.memory_turns:]]
    system = (
        f"You are role-playing {p.name}, age {p.age}. {p.background} Speech: {p.speech_style}.\n"
        f"Your goal: {goal}\n"
        "You ONLY know what appears below; anything else you have forgotten. Never invent names, places "
        "or details you were not shown. Text marked '[...the rest went by too fast]' is lost to you.\n"
        "Show confusion only when what you were shown is actually unclear, incomplete or missing. If it is "
        "clear, respond the way a capable adult would. Do not exaggerate age or frailty. Keep replies short.\n"
        "When you believe the task is finished, end with a line 'DONE: <what you think was arranged>'. "
        "If you give up, end with 'GIVE UP'."
    )
    shown = "\n---\n".join(visible) or "(the assistant has not said anything yet)"
    return _llm(system, f"What the assistant said recently:\n{shown}\n\nYour reply:")


def sut_reply(task: dict, sut_style: str, transcript: list) -> str:
    sut_system = f"{task['sut_context']}\nCommunication style: {sut_style}"
    convo = "\n".join(f"{m['role']}: {m['text']}" for m in transcript)
    return _llm(sut_system, f"Conversation so far:\n{convo}\n\nYour next reply:")


def score(task: dict, transcript: list, outcome: str, turns: int) -> dict:
    final = outcome.lower()
    success = outcome.startswith("DONE") and all(v in final for v in task["expected"])
    persona_text = " ".join(t["text"].lower() for t in transcript if t["role"] == "persona")
    repeats = len(re.findall(r"\b(again|repeat|what was|i forgot|say that)\b", persona_text))
    long_replies = sum(1 for t in transcript if t["role"] == "sut"
                       and len([s for s in re.split(r"[.!?]+", t["text"]) if s.strip()]) > 4)
    return {"success": success, "abandoned": outcome == "GIVE UP", "turns": turns,
            "repeat_requests": repeats, "overlong_sut_replies": long_replies}


def iter_episode(p: ClaraProfile, task_key: str, sut_style: str):
    """Run one conversation, yielding (event, transcript, turn) after every message so a UI
    can stream it. The final yield is ("end", transcript, turn, outcome)."""
    t = TASKS[task_key]
    transcript, sut_history, outcome, turn = [], [], "GIVE UP", 0
    yield ("start", transcript, 0)
    persona_msg = persona_reply(p, t["persona_goal"], [])
    for turn in range(1, p.patience_turns + 1):
        transcript.append({"role": "persona", "text": persona_msg})
        yield ("persona", transcript, turn)
        if "GIVE UP" in persona_msg:
            outcome = "GIVE UP"; break
        if "DONE:" in persona_msg:
            outcome = "DONE: " + persona_msg.split("DONE:", 1)[1].strip(); break
        reply = sut_reply(t, sut_style, transcript)
        transcript.append({"role": "sut", "text": reply})
        sut_history.append(reply)
        yield ("sut", transcript, turn)
        persona_msg = persona_reply(p, t["persona_goal"], sut_history)
    yield ("end", transcript, turn, outcome)


def run_episode(persona, task: str, sut_style: str, label: str, verbose: bool = False) -> dict:
    """Run a full episode and save it. `persona` is a key in PROFILES or a ClaraProfile."""
    p = PROFILES[persona] if isinstance(persona, str) else persona
    *_, last = iter_episode(p, task, sut_style)
    _, transcript, turn, outcome = last
    if verbose:
        for m in transcript:
            print(("\n👵 " + p.name if m["role"] == "persona" else "🤖 assistant") + ": " + m["text"])
    s = score(TASKS[task], transcript, outcome, turn)
    path = storage.save_episode(f"{task}__{p.name}__{_slug(label)}.json", {
        "persona": p.name, "task": task, "label": label, "sut_style": sut_style,
        "outcome": outcome, "score": s, "transcript": transcript})
    return {"score": s, "outcome": outcome, "saved": str(path)}
