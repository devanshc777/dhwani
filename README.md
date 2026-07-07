# dhwani <sub>ध्वनि · "sound"</sub>

Local push-to-talk dictation for Windows. Press **Tab+Q**, speak, press
**Tab+Q** again — clean text lands wherever your cursor is. Whisper on CPU,
zero cloud, zero LLM, zero subscription.

A minimal open-source take on the [Wispr Flow](https://wisprflow.ai) idea:
the transcription-to-typed-text loop, built from six dependencies and the
Python standard library.

## How it works

```
Tab+Q ──▶ mic capture ──▶ faster-whisper ──▶ rule cleanup ──▶ Ctrl+V inject
          (sounddevice)   (base, int8, CPU)  (fillers, cmds)   (clipboard)
               │                                    │
        waveform overlay                       SQLite history
        (tkinter, no-focus)               web UI @ 127.0.0.1:8770
```

Every stage exchanges plain data (float32 audio in, `str` out). Swap any
stage — OpenVINO whisper on the NPU, an LLM cleanup pass — without touching
the others. The data contract is the architecture.

## Features

- **Tab+Q toggle** anywhere in Windows (configurable), debounced against key
  auto-repeat; utterances process strictly in order
- **Floating waveform pill** — a small transparent glow-waveform while
  recording that never steals focus from the app you're dictating into
- **Tuned transcription** — language pinned (auto-detect misfires on short
  clips), in-clip silence filtering (kills "You You… Hi. Hi." hallucinations),
  `initial_prompt` bias so your name and jargon spell correctly
- **Context words** — add names, products, and jargon from the web UI; they
  feed the decoder before every utterance and take effect immediately
- **Filler stripping** (um / uh / erm…) + voice commands: say
  *"new line"* / *"new paragraph"* and get exactly that
- **Transcript history** — local web UI at `http://127.0.0.1:8770` with
  cleaned + raw versions and one-click copy
- **Light when idle** — model weights (~300 MB) unload after 30 quiet
  minutes and reload transparently (~2 s) on the next hotkey press
- **Fully offline** after the one-time model download (~74 MB for `base`)

## Install & run

Requires Python 3.10+ on Windows. With [uv](https://docs.astral.sh/uv/):

```powershell
git clone https://github.com/devanshc777/dhwani.git
cd dhwani
.\run.ps1                              # creates .venv, installs, launches
.\scripts\install-autostart.ps1        # optional: start with Windows (hidden)
```

## Configuration (env vars)

| Variable | Default | Notes |
|---|---|---|
| `DHWANI_MODEL` | `base` | `tiny` (fastest) / `base` / `small` (most accurate) |
| `DHWANI_LANGUAGE` | `en` | any whisper code, or `auto` (unreliable on short clips) |
| `DHWANI_PROMPT` | your names/jargon | words the decoder should spell correctly |
| `DHWANI_HOTKEY` | `tab+q` | any [`keyboard`](https://github.com/boppreh/keyboard) combo |
| `DHWANI_IDLE_UNLOAD_MIN` | `30` | minutes before model unloads (0 = never) |
| `DHWANI_PORT` | `8770` | web UI port |
| `DHWANI_DB` | `~/.dhwani/transcripts.db` | history location |

## Measuring quality (eval harness)

```powershell
# grab any talking-head video's audio + captions as a test set
yt-dlp -x --audio-format mp3 --write-auto-subs --sub-langs en --sub-format vtt -o "sample.%(ext)s" <URL>

# score one config, or compare tiny/base/small x en/auto:
python eval\run.py sample.mp3 --reference sample.en.vtt
python eval\run.py sample.mp3 --reference sample.en.vtt --grid
```

Prints WER (word error rate) + substitution/deletion/insertion breakdown.
Remember auto-captions are themselves ASR — trust the *relative* numbers.
The best reference is you recording yourself reading a known paragraph.

## Design notes

- **No utterance-delimiting VAD.** Push-to-talk toggle means you delimit
  speech. (faster-whisper's *in-clip* `vad_filter` is used though — different
  job: it stops whisper hallucinating text over silent stretches.)
- **No LLM at inference.** Output is a *cleaner transcript of what you said*,
  not a rewrite of what you meant. Instant, private, free.
- **Clipboard paste over synthetic typing.** Survives Electron apps, IMEs and
  RDP; previous clipboard contents are restored afterward.
- **Modifier-release before paste.** The hotkey keys are often still held
  when injection runs; without force-releasing them, Ctrl+V silently becomes
  something else. The kind of bug that costs an evening — see `inject.py`.

## Troubleshooting

- **Output in the wrong language/script** — you're on `DHWANI_LANGUAGE=auto`;
  pin it (`en`). Short clips give detection a coin toss.
- **Names spelled wrong** — add them to `DHWANI_PROMPT`.
- **Hotkey doesn't fire in elevated apps** — Windows blocks input hooks across
  privilege levels; run dhwani as admin for those.
- **Native wheel blocked by Application Control** — pin one major version
  back (aged wheels have reputation; see `docs/BUILD_LOG.md`).
- **Slow first transcription** — model download/warm-up, or idle reload (~2 s).

## Roadmap

- OpenVINO / NPU path for Intel Core Ultra machines (same transcriber
  contract, lower power)
- optional local-LLM restructuring pass (opt-in, still offline)
- tray icon

## License

MIT © [Devansh Chowdhary](https://github.com/devanshc777)
