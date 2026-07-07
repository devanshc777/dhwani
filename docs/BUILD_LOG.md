# Build log

## 2026-07-07 — v0.1 built end-to-end (Cowork session)

**Research phase (before any code, per directive):**
- Surveyed existing OSS Wispr Flow clones: drajb/whisper-local (faster-whisper
  push-to-talk — closest prior art), OpenWhispr, voicetypr, PinW/whisper-key-local.
  Conclusion: category is well-trodden; build the minimal personal version, own
  the code, keep it teachable.
- Prior-session research (Meteor Lake capabilities, discriminative-vs-generative
  split for cleanup) folded into SPEC.md. Two of its recommendations were
  *dropped on closer look*: Silero VAD (obsoleted by toggle UX) and a
  punctuation-restoration model (whisper already punctuates). Lesson: re-derive
  the dependency list from the actual UX, not from the generic pipeline.
- Name: `whisperkey` taken (whisperkey.org), `altvoice` collides with alt:V
  gaming ecosystem + altvoice.io → **dhwani** (ध्वनि, "sound"; near-collision
  with defunct "dhvani" TTS accepted, different spelling).

**Build decisions logged in SPEC.md.** Ponytail skill (DietrichGebert) actively
applied: 6 deps, stdlib tkinter/sqlite/ctypes, no VAD, no punctuation model,
polling over WebSocket, cleanup self-check instead of a test framework.

**Gotchas hit & handled:**
- Alt still held during injection → Ctrl+V becomes Ctrl+Alt+V. Fixed:
  force-release modifiers + 150 ms settle in `inject.py`.
- Overlay stealing focus would redirect the paste → `WS_EX_NOACTIVATE` +
  `WS_EX_TOOLWINDOW` via ctypes in `overlay.py`.
- tkinter is single-thread — all overlay ops routed through a queue pumped by
  `root.after` on the main thread.
- Cowork's folder mount corrupts git lock/config writes (`bad config line 1`,
  blocked unlinks) → repo history created in the sandbox FS and `.git` copied
  onto the mount afterward.

**Verification:** `py_compile` on all 9 modules · `python -m dhwani.cleanup`
self-check green · FastAPI app imports and routes registered (fastapi+uvicorn
installed in sandbox; faster-whisper/sounddevice are Windows-runtime-only here,
so first live run happens on the host machine).

**Not done yet (honest):** no live end-to-end run on the host (sandbox has no
mic/display); OpenVINO path unstarted; no tray icon; hotkey conflicts with any
app that binds Alt+V locally.
