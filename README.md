---
title: Clara
emoji: 🪞
colorFrom: gray
colorTo: gray
sdk: gradio
sdk_version: 6.30.0
app_file: app.py
pinned: false
---

# Clara

A perspective-taking studio for designers, plus the research harness behind it. Clara is a set of
simulated older-adult personas with adjustable memory, processing speed and patience. You give an
assistant a communication style, predict how Clara will do, and watch the conversation as she
actually received it.

Clara personas are simulations with placeholder parameters, not real people. Treat results as
hypotheses to check with older adults.

## Layout

```
app.py                      entry point for Hugging Face Spaces / `python app.py`
clara/
  config.py                 settings from environment variables
  llm.py                    model setup (Anthropic via LiteLLM, or a mock with no key)
  personas.py               ClaraProfile, PROFILES, studio PRESETS and CONTEXT
  tasks.py                  benchmark tasks with expected end states
  episode.py                persona turn, episode runner, scoring
  storage.py                every save/load goes through here (swap for a DB later)
  studio.py                 the Gradio studio (Week 3 interface)
  agent_tools.py            smolagents tools + new_agent() for autonomous research runs
  skills/clara-accessibility-review/SKILL.md   instructions the research agent follows
notebooks/                  original Week 3 notebook and a slim Colab version
```

## Settings

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | none | Model access. Without it the app uses the scripted mock model. |
| `CLARA_PROVIDER` | `anthropic` | `anthropic`, `openai`, `hf` or `mock` |
| `CLARA_MODEL_ID` | `anthropic/claude-sonnet-4-5` | Any LiteLLM model id |
| `CLARA_DATA_DIR` | `lab` | Where episodes and session exports are saved |
| `CLARA_USERNAME`, `CLARA_PASSWORD` | none | If both are set, the studio asks for a login |

## Run locally

```bash
pip install -e ".[studio]"
export ANTHROPIC_API_KEY=...
python app.py              # opens on http://127.0.0.1:7860
```

## Deploy to Hugging Face Spaces

1. Create a new Space at huggingface.co/new-space, SDK **Gradio**, hardware **CPU basic** (free).
2. Push this folder to the Space's git repo (or connect the Space to your GitHub repo).
3. In the Space's **Settings → Variables and secrets**, add the secret `ANTHROPIC_API_KEY`.
4. Strongly recommended: also add `CLARA_USERNAME` and `CLARA_PASSWORD` as secrets, so a public URL
   can't spend your API credits.
5. Optional: enable persistent storage and set the variable `CLARA_DATA_DIR=/data/lab`. Without it,
   saved episodes are lost whenever the Space restarts. The **Export session** button still lets
   each designer download their summary.

The YAML block at the top of this README is the Space config; keep it there.

## Use from Colab or a notebook

```python
!pip install -q "clara @ git+https://github.com/<you>/clara-studio.git"

import os
os.environ["ANTHROPIC_API_KEY"] = "..."     # or set it in Colab secrets

from clara.episode import run_episode
run_episode("clara-moderate", "pharmacy-refill", "One step per message.", "v2", verbose=True)

from clara.agent_tools import new_agent
new_agent().run("Find a style that lets clara-moderate finish pharmacy-refill. Try at most 4 variants.")
```

To open the studio from Colab with a temporary public link:

```python
from clara.studio import build_demo, launch_kwargs
build_demo().queue().launch(share=True, **launch_kwargs())
```
