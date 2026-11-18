"""Writing systems: which bundled font draws a language's script. Independent of cves.gfx (no PIL import at module load).
The map lives in the style (`font_files.script_fallback: {lang: file}`); files are in assets/fonts/ (Noto Sans, OFL).
  font_for_language("ta")              -> /.../assets/fonts/NotoSansTamil-SemiBold.ttf
  font_for_language("hi", "bold")      -> /.../assets/fonts/NotoSansDevanagari-Bold.ttf
  font_for_language("en")              -> None (use the brand font)
Indic scripts need complex shaping: PIL must have libraqm (`shaping_available()`), else conjuncts and vowel signs render wrong."""
import os, re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FONTS = os.path.join(ROOT, "assets", "fonts")
WEIGHTS = {"m": "Medium", "medium": "Medium", "sb": "SemiBold", "semibold": "SemiBold", "b": "Bold", "bold": "Bold",
           "xb": "ExtraBold", "extrabold": "ExtraBold", "regular": "Regular"}
# Unicode block -> (script, a representative language code)
BLOCKS = [(0x0900, 0x097F, "Devanagari", "hi"), (0x0980, 0x09FF, "Bengali", "bn"), (0x0A80, 0x0AFF, "Gujarati", "gu"),
          (0x0B80, 0x0BFF, "Tamil", "ta"), (0x0C00, 0x0C7F, "Telugu", "te"), (0x0C80, 0x0CFF, "Kannada", "kn"),
          (0x0D00, 0x0D7F, "Malayalam", "ml")]
LANG_SCRIPT = {"hi": "Devanagari", "mr": "Devanagari", "ne": "Devanagari", "sa": "Devanagari", "ta": "Tamil", "te": "Telugu",
               "kn": "Kannada", "ml": "Malayalam", "bn": "Bengali", "as": "Bengali", "gu": "Gujarati"}

def _fallback_map(S=None):
    if S is None:
        from . import style as STY; S = STY.load()
    return (S.get("font_files.script_fallback") if hasattr(S, "get") else None) or {}

def _path(f): return f if os.path.isabs(f) else os.path.join(FONTS, f)

def font_for_language(lang, weight="semibold", S=None):
    """absolute font file for a language code (en, hi, ta, ... or 'ta-IN'), in the requested weight when that file exists;
    None when the language needs no fallback (Latin) or none is configured. S = style.load(pr) (default style if None)."""
    if not lang: return None
    code = str(lang).lower().replace("_", "-").split("-")[0]
    fb = _fallback_map(S); v = fb.get(code) or fb.get(LANG_SCRIPT.get(code, ""))
    if isinstance(v, dict): v = v.get(weight) or next(iter(v.values()), None)
    if not v: return None
    want = WEIGHTS.get(str(weight).lower())
    if want:
        alt = re.sub(r"-(Regular|Medium|SemiBold|Bold|ExtraBold)\.(ttf|otf)$", rf"-{want}.\2", str(v))
        if os.path.exists(_path(alt)): return _path(alt)
    return _path(v) if os.path.exists(_path(v)) else None

def script_of(text):
    """(script, language code) of the first Indic letter in text, else (None, None)"""
    for ch in str(text or ""):
        o = ord(ch)
        for a, b, name, code in BLOCKS:
            if a <= o <= b: return name, code
    return None, None

def font_for_text(text, weight="semibold", S=None, lang=None):
    """font for a string: its script's fallback, else the language's, else None (brand font)"""
    _, code = script_of(text)
    return font_for_language(code, weight, S) if code else (font_for_language(lang, weight, S) if lang and lang in LANG_SCRIPT else None)

def shaping_available():
    """True when PIL can shape complex scripts (libraqm + fribidi). Without it Indic text renders unshaped."""
    try:
        from PIL import features; return bool(features.check("raqm"))
    except Exception: return False
