# dhwani <sub>ध्वनि · "sound"</sub>

Local push-to-talk dictation for Windows. Press **Alt+V**, speak, press
**Alt+V** again — clean text lands wherever your cursor is. Whisper on CPU,
zero cloud, zero LLM, zero subscription.

A minimal open-source take on the [Wispr Flow](https://wisprflow.ai) idea:
the transcription-to-typed-text loop, built from six dependencies and the
Python standard library.

## How it works

```
 Alt+V ──▶ mic capture ──▶ faster-whisper ──▶ rule cleanup ──▶ Ctrl+V inject
           (sounddevice)   (base, int8, CPU)  (fillers, cmds)   (clipboard)
                │                                    │
           overlay pill                         SQLite history
           (tkinter bars)                  web UI @ 127.0.0.1:8770
```

Every stage exchanges plain data (float32 audio in, `str` out). Swap any
stage — OpenVINO whisper on the NPU, an LLM cleanup pass — without touching
the others. The data contract is the architecture.

## Features

- **Alt+V toggle** anywhere in Windows (configurable)
- **Recording pill** — a small always-on-top strip of live level bars that
  never steals focus from the app you're dictating into
- **Filler stripping** (um / uh / erm…) + voice commands: say
  *"new line"* / *"new paragraph"* and get exactly that
- **Transcript history** — local web UI at `http://127.0.0.1:8770` with
  cleaned + raw versions and one-click copy
- **Fully offline** after the one-time model download (~74 MB for `base`).
  Audio never leaves the machine. History lives in `~/.dhwani/transcripts.db`.

## Install & run

Requires Python 3.10+ on Windows. With [uv](https://docs.astral.sh/uv/):

```powershell
git clone https://github.com/devanshc777/dhwani.git
cd dhwani
.\run.ps1        # creates .venv, installs, launches
```

or manually: `uv venv && .venv\Scripts\activate && uv pip install -e . && dhwani`

First run downloads the whisper model to the Hugging Face cache, then you're
offline for good.

## Configuration (env vars)

| Variable | Default | Notes |
|---|---|---|
| `DHWANI_MODEL` | `base` | `tiny` (fastest) / `base` / `small` (most accurate) |
| `DHWANI_LANGUAGE` | auto | set `en` to pin English (faster, more accurate) |
| `DHWANI_HOTKEY` | `alt+v` | any [`keyboard`](https://github.com/boppreh/keyboard) combo |
| `DHWANI_PORT` | `8770` | web UI port |
| `DHWANI_DB` | `~/.dhwani/transcripts.db` | history location |

## Design notes

- **No VAD, on purpose.** Push-to-talk toggle means the user delimits speech —
  a voice-activity model would be a dependency solving a problem the UX
  already solved.
- **No punctuation model.** Whisper outputs punctuated, capitalized text
  natively; the cleanup layer only strips fillers and applies spoken commands.
- **No LLM at inference.** Output is a *cleaner transcript of what you said*,
  not a rewrite of what you meant. That's the honest ceiling of a rule-based
  cleanup — and it keeps the tool instant, private, and free.
- **Clipboard paste over synthetic typing.** Survives Electron apps, IMEs and
  RDP; previous clipboard contents are restored afterward.
- **Alt-release before paste.** The hotkey leaves Alt physically held; without
  force-releasing modifiers, Ctrl+V silently becomes Ctrl+Alt+V. The kind of
  bug that costs an evening — handled in `inject.py`.

## Troubleshooting

- **Hotkey doesn't fire in elevated apps** — Windows blocks input hooks across
  privilege levels; run dhwani as admin if you dictate into admin windows.
- **Nothing pastes** — the target app must accept Ctrl+V; check the web UI,
  the transcript is saved there regardless.
- **Slow first transcription** — model warm-up or first-time download; watch
  the status dot on the web UI turn green.

## Roadmap

- OpenVINO / NPU path for Intel Core Ultra machines (same transcriber
  contract, lower power)
- optional local-LLM restructuring pass (opt-in, still offline)
- tray icon + autostart

## License

MIT © [Devansh Chowdhary](https://github.com/devanshc777)
