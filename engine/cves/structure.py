"""Named story structures (style `grammar.structure`): the beat order the story gates expect, the beat labels shown in
`cves story`, the moodboard and the edit plan, and the music hook / turn / drop beats each structure implies.

  problem  H P A PR O C   problem-led ad: hook, problem, agitation, proof, offer, CTA (the default)
  offer    H M PR R C     offer-led ad: hook / promise, mechanism (how it works), proof, risk reversal (guarantee), CTA
  story    H S T PR C     story-led piece: hook, setup (the before), turn (the moment it changed), proof (the after), CTA
  custom   grammar.beats  any order you write in grammar.beats (labels for unknown tags are the tags themselves)

`grammar.beats`, when set, always overrides the structure's order. X tags a clip that is cut (never in the order)."""

STRUCTURES = {
    "problem": ["H", "P", "A", "PR", "O", "C"],
    "offer": ["H", "M", "PR", "R", "C"],
    "story": ["H", "S", "T", "PR", "C"],
}
LABELS = {"H": "Hook", "P": "Problem", "A": "Agitation", "PR": "Proof", "O": "Offer", "C": "CTA",
          "M": "Mechanism", "R": "Risk reversal", "S": "Setup", "T": "Turn", "X": "Cut"}
# moodboard / edit-plan lane colours per beat (a fixed legend, not part of the client look)
COLORS = {"H": "#ff9f43", "P": "#ff6b6b", "A": "#c56cf0", "PR": "#19e6a0", "O": "#54a0ff", "C": "#feca57",
          "M": "#48dbfb", "R": "#1dd1a1", "S": "#a29bfe", "T": "#fd79a8"}
# music.hook_beats / turn_beats / drop_beats defaults per structure (docs/SOUND.md): the build starts on the turn,
# the drop lands on the payoff
MUSIC = {
    "problem": {"hook_beats": ["H"], "turn_beats": ["P", "A"], "drop_beats": ["PR", "O"]},
    "offer": {"hook_beats": ["H"], "turn_beats": ["M"], "drop_beats": ["PR"]},
    "story": {"hook_beats": ["H"], "turn_beats": ["T"], "drop_beats": ["PR"]},
}
NAMES = ("problem", "offer", "story", "custom")
DEFAULT = "problem"


def name_of(S):
    """the structure name from a style (grammar.structure); unknown values fall back to the default"""
    n = str((S.get("grammar.structure") if S is not None else None) or DEFAULT).strip().lower()
    return n if n in NAMES else DEFAULT


def beats_of(S):
    """the beat order the story gates expect: grammar.beats if set, else the structure's preset order"""
    b = S.get("grammar.beats") if S is not None else None
    if isinstance(b, (list, tuple)) and b: return [str(x) for x in b]
    n = name_of(S)
    return list(STRUCTURES.get(n) or STRUCTURES[DEFAULT])


def preset_for(order):
    """the preset whose order equals `order` (None when it is a custom order)"""
    return next((n for n, o in STRUCTURES.items() if list(o) == list(order)), None)


def music_beats(S):
    """{hook_beats, turn_beats, drop_beats} implied by the structure. A preset order (also one written out in
    grammar.beats) maps to its preset; a custom order: hook = H (else the first beat), turn = its problem / mechanism /
    setup / turn beats (else the second beat), drop = its proof / offer beats (else the middle beat)."""
    order = beats_of(S)
    n = preset_for(order)
    if n in MUSIC: return {k: list(v) for k, v in MUSIC[n].items()}
    hook = ["H"] if "H" in order else order[:1]
    turn = [b for b in order if b in ("P", "A", "M", "S", "T")][:2] or order[1:2]
    drop = [b for b in order if b in ("PR", "O")] or ([order[len(order) // 2]] if order else [])
    return {"hook_beats": hook, "turn_beats": turn, "drop_beats": drop}


def label(b):
    return LABELS.get(str(b), str(b)) if b else ""


def legend(S):
    """'H Hook > M Mechanism > PR Proof > R Risk reversal > C CTA' for the active order"""
    return " > ".join(f"{b} {label(b)}" for b in beats_of(S))
