"""The designer-facing perspective-taking studio (Week 3 interface), unchanged in behavior.

    from clara.studio import build_demo, launch_kwargs
    build_demo().queue().launch(**launch_kwargs())
"""
import html
import inspect
import json
from dataclasses import asdict
from datetime import datetime

import gradio as gr
import pandas as pd

from . import config, storage
from .episode import CONFUSION, _sentences, _slug, iter_episode, score
from .personas import CONTEXT, PRESETS, ClaraProfile
from .tasks import TASKS

OUTCOMES = ["Finishes smoothly", "Finishes, but struggles", "Ends with the wrong result", "Gives up"]
STAGES = ["Configure", "Predict", "Simulating", "Review", "Revise"]


def _esc(text):
    return html.escape(text).replace("\n", "<br>")


def build_profile(age, level, mem, sent, pat, context):
    background = " ".join(CONTEXT[c] for c in context) or "Lives independently."
    return ClaraProfile(f"clara-{_slug(level)}", int(age), memory_turns=int(mem),
                        sentences_absorbed=int(sent), patience_turns=int(pat),
                        speech_style=PRESETS[level]["speech_style"], background=background)


# ---------------------------------------------------------------- rendering
CSS = """<style>
.cl-chat{font-size:15px;line-height:1.5;color:#111}
.cl-turn{padding:12px 0;border-bottom:1px solid #e4e4e4}
.cl-who{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:#777;margin-bottom:4px}
.cl-sut .cl-text{padding-left:16px;border-left:1px solid #111}
.cl-lost{color:#aaa;text-decoration:line-through}
.cl-note{margin-top:6px;font-size:12px;color:#777}
.cl-tl{font-family:Menlo,Consolas,monospace;font-size:12px;line-height:1.9;color:#111}
.cl-tl .ok{color:#999}.cl-tl .warn{color:#555}.cl-tl .bad,.cl-tl .good{color:#111;font-weight:700}
.cl-tl b{display:inline-block;width:2.5em;font-weight:400;color:#777}
.cl-legend{font-size:12px;color:#777;margin-top:10px;max-width:60ch}
</style>"""


def render_chat(transcript, p):
    rows = []
    for m in transcript:
        if m["role"] == "persona":
            rows.append(f'<div class="cl-turn cl-persona"><div class="cl-who">Clara</div>'
                        f'<div class="cl-text">{_esc(m["text"])}</div></div>')
        else:
            parts = _sentences(m["text"])
            kept, lost = " ".join(parts[:p.sentences_absorbed]), " ".join(parts[p.sentences_absorbed:])
            body = _esc(kept) + (f' <span class="cl-lost">{_esc(lost)}</span>' if lost else "")
            note = (f'<div class="cl-note">Only {p.sentences_absorbed} of {len(parts)} sentences got through '
                    f'(crossed-out text never reached Clara)</div>' if lost else "")
            rows.append(f'<div class="cl-turn cl-sut"><div class="cl-who">Assistant</div>'
                        f'<div class="cl-text">{body}{note}</div></div>')
    return CSS + '<div class="cl-chat">' + "".join(rows) + "</div>"


def friction_events(transcript, p):
    """One event per turn: (who, label, level). Levels: ok / warn / bad / good."""
    events, a, c = [], 0, 0
    for m in transcript:
        if m["role"] == "sut":
            a += 1
            n = len(_sentences(m["text"]))
            if n > p.sentences_absorbed:
                events.append((f"A{a}", f"{p.sentences_absorbed}/{n} sentences absorbed", "warn"))
            else:
                events.append((f"A{a}", f"{n} sentence(s), all absorbed", "ok"))
        else:
            c += 1
            text, low = m["text"], m["text"].lower()
            hits = [w for w in CONFUSION if w in low]
            if "DONE:" in text:
                events.append((f"C{c}", "thinks it's done", "good"))
            elif "GIVE UP" in text:
                events.append((f"C{c}", "gave up", "bad"))
            elif hits:
                events.append((f"C{c}", "confused: " + ", ".join(hits[:2]), "bad"))
            else:
                events.append((f"C{c}", "on track", "ok"))
    return events


def render_timeline(events, p):
    chips = "<br>".join(f'<span class="{lvl}"><b>{who}</b>{html.escape(lbl)}</span>'
                        for who, lbl, lvl in events)
    legend = (f'<div class="cl-legend">A = assistant reply, C = Clara. Clara absorbs the first '
              f'{p.sentences_absorbed} sentences of each reply and keeps only the last {p.memory_turns} '
              f'assistant replies in mind. She gives up after {p.patience_turns} turns.</div>')
    return CSS + f'<div class="cl-tl">{chips}</div>{legend}'


def classify(s, events):
    if s["abandoned"]:
        return "Gives up"
    if not s["success"]:
        return "Ends with the wrong result"
    struggled = s["repeat_requests"] > 0 or any(lvl == "bad" for _, _, lvl in events)
    return "Finishes, but struggles" if struggled else "Finishes smoothly"


def stage(current, note=""):
    bar = "&nbsp;&nbsp;/&nbsp;&nbsp;".join(
        f'<span style="color:#111;border-bottom:1px solid #111">{s}</span>' if s == current
        else f'<span style="color:#aaa">{s}</span>' for s in STAGES)
    msg = f'<div style="margin-top:8px;color:#111">{html.escape(note)}</div>' if note else ""
    return f'<div style="font-size:13px;letter-spacing:.02em">{bar}</div>{msg}'


# ---------------------------------------------------------------- main loop
def run_and_review(age, level, mem, sent, pat, context, task_key, style, label,
                   pred_outcome, pred_where, history):
    keep = gr.update()
    if not style.strip():
        yield stage("Configure", "Describe your assistant's communication style first."), keep, keep, keep, keep, history
        return
    if not pred_outcome or not pred_where.strip():
        yield (stage("Predict", "Make your prediction first: how will Clara do, and where will she struggle?"),
               keep, keep, keep, keep, history)
        return

    p, t = build_profile(age, level, mem, sent, pat, context), TASKS[task_key]
    transcript, turn, outcome = [], 0, "GIVE UP"

    for ev in iter_episode(p, task_key, style):
        kind, transcript, turn = ev[0], ev[1], ev[2]
        if kind == "start":
            yield stage("Simulating", "Clara is reading the first message..."), render_chat(transcript, p), "", "", keep, history
        elif kind == "persona":
            yield (stage("Simulating", f"Turn {turn} of at most {p.patience_turns}"), render_chat(transcript, p),
                   render_timeline(friction_events(transcript, p), p), "", keep, history)
        elif kind == "sut":
            yield (stage("Simulating", f"Turn {turn}: Clara is responding..."), render_chat(transcript, p),
                   render_timeline(friction_events(transcript, p), p), "", keep, history)
        else:
            outcome = ev[3]

    s = score(t, transcript, outcome, turn)
    events = friction_events(transcript, p)
    actual = classify(s, events)
    struggle_turns = [who for who, _, lvl in events if lvl == "bad" and who.startswith("C")]
    match = actual == pred_outcome

    path = storage.save_episode(f"{task_key}__designer-{_slug(level)}__{_slug(label)}.json", {
        "persona": asdict(p), "task": task_key, "label": label, "sut_style": style,
        "prediction": {"outcome": pred_outcome, "where": pred_where},
        "actual": actual, "outcome": outcome, "score": s, "transcript": transcript,
    })

    result = f"""### Your prediction vs. what happened
| | |
|---|---|
| **You predicted** | {pred_outcome} |
| **Clara** | {actual} |
| **Match** | {"Yes" if match else "**No**, your mental model of this user differed from the simulation"} |

**Where you expected trouble:** {pred_where}

**Where Clara struggled:** {", ".join(struggle_turns) if struggle_turns else "nowhere visible"}

**What Clara thinks was arranged:** {outcome[6:] if outcome.startswith("DONE") else "nothing; she gave up or ran out of patience"}

Turns: {s['turns']} · repeat requests: {s['repeat_requests']} · replies over 4 sentences: {s['overlong_sut_replies']} · saved to `{path}`

---
**Before you revise:** which of your assumptions about this user did this run confirm, and which did it challenge? Change *one* thing in the style, give it a new version name, predict again, and rerun. (Clara is a simulation; treat her reactions as prompts, not verdicts.)"""

    history = history + [{
        "run": len(history) + 1, "version": label, "profile": level, "age": int(age), "task": task_key,
        "predicted": pred_outcome, "actual": actual, "match": match, "turns": s["turns"],
        "repeats": s["repeat_requests"], "overlong": s["overlong_sut_replies"], "style": style,
    }]
    yield (stage("Review"), render_chat(transcript, p), render_timeline(events, p), result,
           pd.DataFrame(history).drop(columns=["style"]), history)


def apply_preset(level):
    pr = PRESETS[level]
    return pr["memory_turns"], pr["sentences_absorbed"], pr["patience_turns"]


def export_session(history, notes):
    if not history:
        return None
    ts = datetime.now().strftime("%Y%m%d-%H%M")
    hits = sum(r["match"] for r in history)
    lines = [f"# Clara designer session {ts}", "",
             f"Predictions that matched the simulation: {hits} of {len(history)}", "",
             "| run | version | profile | age | task | predicted | actual | turns | repeats | style |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for r in history:
        lines.append(f"| {r['run']} | {r['version']} | {r['profile']} | {r['age']} | {r['task']} | "
                     f"{r['predicted']} | {r['actual']} | {r['turns']} | {r['repeats']} | {r['style']} |")
    lines += ["", "## Reflection notes", "", notes or "(none)", "",
              "_Clara personas are simulations with placeholder parameters; validate with older adults._"]
    return str(storage.save_text(f"designer-session-{ts}.md", "\n".join(lines)))


# ---------------------------------------------------------------- look
# Black / grey / white, square corners, no card borders.
INK, MID, LINE = "#111111", "#777777", "#d4d4d4"
_look = dict(
    body_background_fill="#ffffff", body_text_color=INK, body_text_color_subdued=MID,
    background_fill_primary="#ffffff", background_fill_secondary="#ffffff",
    block_background_fill="transparent", block_border_width="0px", block_shadow="none",
    block_label_background_fill="transparent", block_label_border_width="0px",
    block_label_text_color=MID, block_title_text_color=MID, block_title_text_weight="400",
    panel_background_fill="transparent", panel_border_width="0px",
    input_background_fill="#ffffff", input_border_color=LINE, input_border_color_focus=INK,
    input_border_width="1px", input_shadow="none", input_shadow_focus="none",
    button_primary_background_fill=INK, button_primary_background_fill_hover="#333333",
    button_primary_text_color="#ffffff", button_primary_border_color=INK, button_primary_shadow="none",
    button_secondary_background_fill="#ffffff", button_secondary_background_fill_hover="#f2f2f2",
    button_secondary_text_color=INK, button_secondary_border_color=INK, button_secondary_shadow="none",
    checkbox_background_color_selected=INK, checkbox_border_color_selected=INK,
    checkbox_border_color=MID, checkbox_label_background_fill="transparent",
    checkbox_label_background_fill_selected="transparent", checkbox_label_border_width="0px",
    checkbox_label_shadow="none", slider_color=INK, color_accent=INK, color_accent_soft="#eeeeee",
    border_color_primary=LINE, border_color_accent=INK, shadow_drop="none", shadow_drop_lg="none",
    table_border_color=LINE, table_even_background_fill="#ffffff", table_odd_background_fill="#ffffff",
)


def _theme():
    base = gr.themes.Base(primary_hue=gr.themes.colors.neutral, secondary_hue=gr.themes.colors.neutral,
                          neutral_hue=gr.themes.colors.neutral, radius_size=gr.themes.sizes.radius_none,
                          font=[gr.themes.Font(f) for f in ("Helvetica Neue", "Helvetica", "Arial", "sans-serif")],
                          font_mono=[gr.themes.Font(f) for f in ("Menlo", "Consolas", "monospace")])
    return base.set(**{k: v for k, v in _look.items() if hasattr(base, k)})


PAGE_CSS = """
.gradio-container{max-width:1080px!important;margin:0 auto!important}
.gradio-container *{border-radius:0!important;box-shadow:none!important}
.gradio-container .block,.gradio-container .form,.gradio-container .panel{border:none!important;background:transparent!important}
.sec{border-top:1px solid #111;padding-top:6px!important;margin-top:28px!important}
.sec p{font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:#111;margin:0}
.title h1{font-weight:400;font-size:32px;letter-spacing:-.01em;margin:0}
.title p{color:#777;margin:4px 0 0}
.gradio-container table{border-collapse:collapse;border:none!important}
.gradio-container th,.gradio-container td{border:none!important;border-bottom:1px solid #e4e4e4!important;background:#fff!important}
footer{display:none!important}
"""
# Keep the page light even when the computer is in dark mode.
FORCE_LIGHT = ("<script>const u=new URL(location.href);"
               "if(u.searchParams.get('__theme')!=='light'){u.searchParams.set('__theme','light');location.replace(u);}</script>")

# Gradio 6 takes theme/css/head in launch(); Gradio 5 takes them in Blocks().
_STYLE_IN_LAUNCH = "theme" in inspect.signature(gr.Blocks.launch).parameters


def _style():
    return dict(theme=_theme(), css=PAGE_CSS, head=FORCE_LIGHT)


def launch_kwargs() -> dict:
    """Keyword arguments for demo.launch(): styling (Gradio 6) and optional login."""
    kwargs = _style() if _STYLE_IN_LAUNCH else {}
    if config.AUTH_USER and config.AUTH_PASS:
        kwargs["auth"] = (config.AUTH_USER, config.AUTH_PASS)
    return kwargs


def sec(text):
    return gr.Markdown(text, elem_classes="sec")


# ---------------------------------------------------------------- layout
def build_demo() -> gr.Blocks:
    with gr.Blocks(title="Clara", **({} if _STYLE_IN_LAUNCH else _style())) as demo:
        gr.Markdown("# Clara\nA perspective-taking studio for designers. See how your assistant's messages reach "
                    "an older adult with cognitive decline. Clara is a simulation with placeholder parameters, "
                    "not a real person.", elem_classes="title")
        stage_md = gr.HTML(stage("Configure"))
        history = gr.State([])

        with gr.Row(equal_height=False):
            with gr.Column(scale=1, min_width=320):
                sec("01  Persona")
                age = gr.Slider(65, 95, value=81, step=1, label="Age")
                level = gr.Radio(list(PRESETS), value="Moderate decline", label="Cognitive profile")
                with gr.Accordion("Parameters", open=False):
                    mem = gr.Slider(1, 8, value=2, step=1, label="Assistant replies she can keep in mind")
                    sent = gr.Slider(1, 10, value=3, step=1, label="Sentences she absorbs per reply")
                    pat = gr.Slider(3, 15, value=7, step=1, label="Turns before she gives up")
                context = gr.CheckboxGroup(list(CONTEXT), value=["Wears hearing aids", "A family member usually helps"],
                                           label="Context")

                sec("02  System under test")
                task = gr.Dropdown(list(TASKS), value="pharmacy-refill", label="Task")
                style = gr.Textbox(lines=3, label="Communication style",
                                   value="Be thorough. Explain every option and all the details in each message.")
                label = gr.Textbox(value="v1-baseline", label="Version name")

                sec("03  Prediction")
                pred_outcome = gr.Radio(OUTCOMES, label="How will Clara do?")
                pred_where = gr.Textbox(lines=2, label="Where will she struggle, and why?")
                run = gr.Button("Run", variant="primary")

            with gr.Column(scale=2):
                sec("04  Conversation, as Clara received it")
                chat = gr.HTML()
                sec("Friction")
                timeline = gr.HTML()
                result = gr.Markdown()

        sec("05  Versions")
        table = gr.Dataframe(interactive=False)
        notes = gr.Textbox(lines=4, label="Notes: what did you learn about this user?")
        export_btn = gr.Button("Export session", variant="secondary")
        export_file = gr.File(label="Session summary")

        level.change(apply_preset, level, [mem, sent, pat])
        run.click(run_and_review,
                  [age, level, mem, sent, pat, context, task, style, label, pred_outcome, pred_where, history],
                  [stage_md, chat, timeline, result, table, history])
        export_btn.click(export_session, [history, notes], export_file)
    return demo
