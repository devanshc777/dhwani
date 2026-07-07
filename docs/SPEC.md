# dhwani — design spec (v0.1, 2026-07-07)

## Goal

A local Wispr-Flow-style dictation loop for one specific machine and user:
press Alt+V anywhere in Windows, speak, get clean text at the cursor. Hard
constraints set by the owner: **no heavy GPU model, no LLM at inference, no
cloud** — the AI's only role was building the software.

## Target hardware (why every model choice looks the way it does)

Intel Core Ultra 7 155H (Meteor Lake: 6P+8E+2LP, AVX2 no AVX-512) · 32 GB RAM
· Arc iGPU (8 Xe cores, shared memory, no dedicated VRAM) · NPU ~11 TOPS ·
no discrete GPU · Windows 11.

faster-whisper `base` at int8 on this CPU runs faster than real-time, which is
the whole requirement for push-to-talk (transcription happens once, after you
stop talking — not streaming). `small` remains a config flag away for accuracy.
The OpenVINO/NPU path (lower power, same contract) is roadmap, not v0.1:
CPU meets the latency budget, so the extra toolchain wasn't earned yet.

## Decisions & rejected alternatives

| Decision | Rationale | Rejected |
|---|---|---|
| Toggle (press/press) not hold-to-talk | Hands-free while speaking; simpler key handling | Hold: keyup races with paste modifiers |
| **No VAD** | Toggle means the user delimits speech; VAD solves a problem the UX already solved | Silero VAD (recommended earlier in research — obsoleted by the toggle decision) |
| **No punctuation model** | Whisper natively punctuates/capitalizes | 100–500 MB token-classifier (earlier research overcomplicated this) |
| Rule-based cleanup only | Constraint: no generative model. Ceiling accepted: cleans what you *said*, never rewrites to what you *meant* | LanguageTool (Java server for marginal gain), local 1.5B LLM (violates constraint; roadmap opt-in) |
| Clipboard+Ctrl+V injection | Survives Electron/IME/RDP; restore-after-delay keeps clipboard intact | `keyboard.write()` per-char (breaks in Electron/IME), Win32 SendInput via pywin32 (another dep) |
| tkinter overlay | stdlib; one canvas; `WS_EX_NOACTIVATE` via ctypes keeps focus in the target app | PySide/pywebview (30 MB+ dep for 60 lines of bars) |
| FastAPI + one static HTML + polling | No build step; dictation rate makes WebSockets ceremony | React/Vite UI, WebSocket push |
| SQLite stdlib, connection-per-call | Thread-safe by construction at these rates | ORM, server DB |
| 6 pip deps total | Every dep must out-earn its install weight | — |

## Architecture

Pipeline stages exchange **plain data only** (float32 mono 16 kHz in, `str`
out). The governing principle: *everything around the pipeline can change —
model, UI, harness — as long as data crosses stage boundaries clean and
segmented.* This is what makes the roadmap (OpenVINO transcriber, LLM cleaner)
drop-in rather than rewrite.

```
keyboard hook thread ── toggle() ──▶ Recorder (audio cb thread, chunks + RMS deque)
        │ stop                                      │ levels
        ▼                                           ▼
worker thread: transcribe ▶ clean ▶ store ▶ inject   tk main thread: overlay pill
uvicorn daemon thread: GET / · /api/status · /api/transcripts (SQLite)
```

Threading rules that keep this correct:
- tk objects touched **only** on the main thread (hook thread posts to a queue)
- audio callback writes chunks/levels; `deque(maxlen)` makes cross-thread reads safe
- model loads in background at startup; `Event.wait()` guards the race where
  the first hotkey beats the load

## Known limits (accepted, documented)

- No restructuring of rambling speech — that genuinely requires a generative
  model (the discriminative/generative split from the research phase).
- `keyboard` hooks don't reach elevated windows unless dhwani runs elevated.
- Hotkey `suppress=True` eats Alt+V globally — deliberate.
- Windows-first: overlay no-focus trick and paste flow are Win32-specific;
  everything else is portable.

## Verification plan

`python -m dhwani.cleanup` self-check (pure stdlib) · `py_compile` all modules
· manual: dictate into Notepad/VS Code/browser textarea; confirm overlay never
steals focus; confirm clipboard restore; confirm history renders at :8770.
