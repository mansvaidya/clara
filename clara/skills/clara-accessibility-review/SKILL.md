---
name: clara-accessibility-review
description: Evaluate whether an assistant's replies can be understood and acted on by older adults with reduced working memory or processing speed, using Clara persona episodes. Use when asked to test, compare, or improve an AI assistant, agent, or app flow for cognitive accessibility or aging users.
metadata:
  author: fluid-interfaces
  version: "0.1"
---

# Clara accessibility review

## Steps
1. Call `clara_list_setup` to see personas and tasks.
2. Run a baseline: same task, the SUT's current style, on `clara-mild` (control) and the target persona.
3. Form one hypothesis about what broke (read at most two transcripts from lab/episodes/).
   Common culprits: several steps in one message, option lists longer than 3, references
   to things said earlier ("as I mentioned"), unconfirmed assumptions.
4. Change ONE thing in `sut_style` and rerun on the same persona and task. Label the variant.
5. Repeat up to the budget you were given, then call `clara_summarize_results`.
6. Write lab/clara-findings.md: what changed, which episodes support it, and what still
   needs checking with real older adults.

## Rules
- Personas are simulations. Say "the persona abandoned", never "older adults can't".
- Never contact real people or send messages during a review.
- Prefer the smallest style change that fixes the failure.
