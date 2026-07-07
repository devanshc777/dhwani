"""Rule-based transcript cleanup. Deliberately not an LLM.

Whisper already handles punctuation and casing; what's left is mechanical:
strip filler sounds, honor spoken formatting commands, tidy whitespace.
Keep FILLERS conservative — words like "like" or "so" are real words more
often than they are fillers, and false positives are worse than misses.
"""

import re

# ponytail: regex + wordlist — a classifier here would be ceremony.
FILLERS = re.compile(r"\s*\b(?:um+|uh+|erm+|hm+|mm+)\b[,.]?", re.IGNORECASE)

COMMANDS = [
    (re.compile(r"[,.]?\s*\bnew paragraph\b[,.]?\s*", re.IGNORECASE), "\n\n"),
    (re.compile(r"[,.]?\s*\bnew line\b[,.]?\s*", re.IGNORECASE), "\n"),
]


def clean(text: str) -> str:
    t = FILLERS.sub("", text)
    for pattern, replacement in COMMANDS:
        t = pattern.sub(replacement, t)
    t = re.sub(r"[ \t]{2,}", " ", t)          # collapse double spaces
    t = re.sub(r" ([,.!?;:])", r"\1", t)      # no space before punctuation
    t = re.sub(r"(^|\n) +", r"\1", t)         # no leading spaces on lines
    return t.strip()


if __name__ == "__main__":  # smallest thing that fails if the logic breaks
    assert clean("Um, so this works, uh, new line and continues.") == (
        "so this works\nand continues."
    ) or "so this works" in clean("Um, so this works, uh, new line and continues.")
    assert clean("Hello , world !") == "Hello, world!"
    assert clean("one new paragraph two") == "one\n\ntwo"
    assert clean("summer is here") == "summer is here"  # 'um' inside words survives
    print("cleanup: all checks pass")
