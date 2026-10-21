"""User-approved visual codes, 2026-10-05; keep existing page prefixes."""

REVIEWED_SHAPE_CODES = {
    "᳀": "sncx", "᳁": "sncg", "᳂": "snoi",
    "◯": "gsoe", "◎": "gsoi", "◉": "gsoi",
    "⊙": "mtoi", "⊚": "mtoi", "⊕": "mtox", "⊗": "mtox",
    "◐": "gsol", "◑": "gsor", "◒": "gsod", "◓": "gsou",
    "◠": "gscu", "◡": "gscd", "∩": "mtcu", "∪": "mtcd",
    "≈": "mtwp", "≋": "mtwm", "∼": "mtwh", "∽": "mtwh",
    "+": "blxs", "×": "lsxs", "✕": "dixs", "✖": "dixf",
    "✚": "dixf", "✟": "dixe", "▣": "gssi", "◇": "gsse", "◆": "gssf",
}

# Only approved common visual families receive the ten-candidate exception.
CANDIDATE_LIMITS = {code: 10 for code in REVIEWED_SHAPE_CODES.values()}


def candidate_limit(code: str) -> int:
    return CANDIDATE_LIMITS.get(code, 5)
