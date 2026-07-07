"""Offline eval: measure the dhwani pipeline against a reference transcript.

Usage (from repo root, venv active):

    python eval/run.py audio.mp3 --reference ref.txt
    python eval/run.py audio.mp3 --reference subs.en.vtt          # vtt ok
    python eval/run.py audio.mp3 --reference ref.txt --grid       # compare configs

Getting test material (any talking-head video with decent captions):

    yt-dlp -x --audio-format mp3 --write-auto-subs --sub-langs en ^
           --sub-format vtt -o "sample.%(ext)s" <URL>

Caveat worth remembering: YouTube auto-captions are themselves ASR (~5-10%
WER), so treat absolute numbers with salt — the *relative* comparison
between configs (base vs small, en-pinned vs auto) is the real signal.
Best reference = a video with human-made captions, or record yourself
reading a paragraph you have the text of.
"""

import argparse
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dhwani.cleanup import clean  # noqa: E402


def load_reference(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() in (".vtt", ".srt"):
        lines = []
        for line in text.splitlines():
            s = line.strip()
            if (not s or "-->" in s or s == "WEBVTT" or s.isdigit()
                    or s.startswith(("Kind:", "Language:", "NOTE"))):
                continue
            s = re.sub(r"<[^>]+>", "", s)  # strip cue tags
            if not lines or lines[-1] != s:  # vtt repeats rolling lines
                lines.append(s)
        text = " ".join(lines)
    return text


def normalize(text: str) -> list[str]:
    """Lowercase, strip punctuation — WER should score words, not commas."""
    return re.sub(r"[^\w\s']", " ", text.lower()).split()


def wer(ref: list[str], hyp: list[str]) -> tuple[float, int, int, int]:
    """Word error rate via edit distance. Returns (wer, subs, dels, ins)."""
    d = [[(j, 0, 0, j) if i == 0 else (i, 0, i, 0) if j == 0 else None
          for j in range(len(hyp) + 1)] for i in range(len(ref) + 1)]
    d[0][0] = (0, 0, 0, 0)
    for i in range(1, len(ref) + 1):
        for j in range(1, len(hyp) + 1):
            if ref[i - 1] == hyp[j - 1]:
                c, s, dl, ins = d[i - 1][j - 1]
                d[i][j] = (c, s, dl, ins)
            else:
                sub = d[i - 1][j - 1]; dele = d[i - 1][j]; inse = d[i][j - 1]
                best = min(sub, dele, inse, key=lambda t: t[0])
                if best is sub:
                    d[i][j] = (best[0] + 1, best[1] + 1, best[2], best[3])
                elif best is dele:
                    d[i][j] = (best[0] + 1, best[1], best[2] + 1, best[3])
                else:
                    d[i][j] = (best[0] + 1, best[1], best[2], best[3] + 1)
    c, s, dl, ins = d[len(ref)][len(hyp)]
    return (c / max(1, len(ref)), s, dl, ins)


def run_config(audio: str, model_size: str, language, prompt: str) -> tuple[str, float]:
    from faster_whisper import WhisperModel  # import here: slow

    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    t0 = time.time()
    segments, _ = model.transcribe(
        audio, language=language, initial_prompt=prompt, beam_size=5,
        vad_filter=True, vad_parameters={"min_silence_duration_ms": 500},
        condition_on_previous_text=False,
    )
    text = clean(" ".join(s.text.strip() for s in segments).strip())
    return text, time.time() - t0


def report(name: str, ref_words: list[str], hyp: str, secs: float) -> None:
    rate, s, dl, ins = wer(ref_words, normalize(hyp))
    print(f"\n== {name} ==  WER {rate:.1%}  (sub {s} · del {dl} · ins {ins})  {secs:.1f}s")
    print(hyp[:400] + ("…" if len(hyp) > 400 else ""))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("audio")
    ap.add_argument("--reference", required=True, help="txt/vtt/srt reference")
    ap.add_argument("--model", default="base")
    ap.add_argument("--language", default="en", help="'auto' for detection")
    ap.add_argument("--prompt", default="", help="initial_prompt bias words")
    ap.add_argument("--grid", action="store_true",
                    help="compare tiny/base/small x en/auto instead of one run")
    args = ap.parse_args()

    ref_words = normalize(load_reference(Path(args.reference)))
    print(f"reference: {len(ref_words)} words")

    if args.grid:
        for m in ("tiny", "base", "small"):
            for lang in ("en", None):
                hyp, secs = run_config(args.audio, m, lang, args.prompt)
                report(f"{m} / {lang or 'auto'}", ref_words, hyp, secs)
    else:
        lang = None if args.language == "auto" else args.language
        hyp, secs = run_config(args.audio, args.model, lang, args.prompt)
        report(f"{args.model} / {args.language}", ref_words, hyp, secs)


if __name__ == "__main__":
    main()
