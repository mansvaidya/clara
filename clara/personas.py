"""Clara personas. The values are placeholders until replaced with interview and literature data."""
from dataclasses import dataclass, asdict  # noqa: F401  (asdict re-exported for convenience)


@dataclass
class ClaraProfile:
    name: str
    age: int
    memory_turns: int        # how many past assistant replies she can still see
    sentences_absorbed: int  # how many sentences of each reply get through
    patience_turns: int      # turns before she gives up
    speech_style: str
    background: str


PROFILES = {
    "clara-mild": ClaraProfile(
        "clara-mild", 72, memory_turns=4, sentences_absorbed=5, patience_turns=10,
        speech_style="fluent, occasionally asks to confirm details",
        background="Retired teacher, uses a smartphone daily, some trouble with dense menus."),
    "clara-moderate": ClaraProfile(
        "clara-moderate", 81, memory_turns=2, sentences_absorbed=3, patience_turns=7,
        speech_style="hesitant, loses track of multi-part instructions",
        background="Lives alone, relies on a daughter for tech help, wears hearing aids."),
    "clara-fragmented": ClaraProfile(
        "clara-fragmented", 85, memory_turns=1, sentences_absorbed=2, patience_turns=6,
        speech_style="fragmented phrases, word-finding pauses, may drift off topic",
        background="Early-stage dementia; wants to stay independent."),
}

# Presets offered in the designer studio.
PRESETS = {
    "Typical aging": dict(memory_turns=6, sentences_absorbed=8, patience_turns=12,
                          speech_style="fluent and direct; asks a question only when something is genuinely unclear"),
    "Mild decline": dict(memory_turns=4, sentences_absorbed=5, patience_turns=10,
                         speech_style=PROFILES["clara-mild"].speech_style),
    "Moderate decline": dict(memory_turns=2, sentences_absorbed=3, patience_turns=7,
                             speech_style=PROFILES["clara-moderate"].speech_style),
    "Significant decline": dict(memory_turns=1, sentences_absorbed=2, patience_turns=6,
                                speech_style=PROFILES["clara-fragmented"].speech_style),
}

CONTEXT = {
    "Wears hearing aids": "Wears hearing aids.",
    "Rarely uses smartphones or apps": "Rarely uses smartphones or apps.",
    "A family member usually helps": "A family member usually helps with paperwork and technology.",
    "Lives alone": "Lives alone and wants to manage on her own.",
}
