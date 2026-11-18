# Toolchain notes and gotchas

Hard-won facts from building the system on a Mac (Apple Silicon). `INSTALL.md` handles all of this automatically; read this when something breaks.

## Media
- **ffmpeg:** Homebrew's `ffmpeg` lacks `drawtext` and `rubberband`. Use `ffmpeg-full` (`/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg`, symlinked into `~/.cves/bin`).
- **iPhone raw clips** are HEVC 1728×3072 vertical, 23.976 fps, 10-bit SDR BT.709, with extra metadata tracks. Always map only `0:v:0` and `0:a:0`.
- **Encoding:** set the BT.709 matrix *and* tags (`-x264-params colorprim=bt709:transfer=bt709:colormatrix=bt709:range=tv`). Without them phones guess the colours.
- **librosa can't read MP4:** extract a WAV first.
- **OpenCV H.264 seeking is frame-accurate** for our files (checked against ffmpeg `select`).

## Speech
- **whisper.cpp:** `whisper-cli` with `ggml-large-v3-turbo-q5_0.bin`. Feed it 16 kHz mono WAV; `-ml 1 -sow -oj` gives word timings.
- **Whisper word timings can be zero-length:** snap cuts to RMS dips in the audio, not to word boundaries.
- **Whisper skips sentences on long files:** transcribe in about 8 s chunks for any check.
- **It invents words over a music tail** ("we'll be right back"): check the sign-off on the voice stem.
- **It hides disfluencies:** prompt it verbatim ("I, I mean, want, want to") to catch stutters. Proper nouns can make it loop, so re-run unprompted if a word repeats 4 or more times.
- **Resemble Enhance** needs git-lfs to fetch its model and crashes on Apple's GPU (MPS) for one op. More importantly, its generative mode rewrites words: **banned**. Use DeepFilterNet3.

## Vision
- **Robust Video Matting** (resnet50, downsample 0.4) runs at about 10 fps on Apple's GPU (MPS). It can leak wall pixels beside hair, so clean the edge ring (bright and colourless pixels).
- **BiRefNet-portrait** (via rembg) is about 15 s a frame: stills only.
- **YuNet** gives a face box plus 5 landmarks. Sample skin from cheek patches between eye and mouth corner, never the face box (beard, open mouth).
- **NumPy float32 is not a Python float:** any coordinate helper that checks `isinstance(v, float)` must also accept `np.number`.

## Python environments
- Homebrew's default Python can be newer than PyAV / torch wheels support. Use Python 3.12 for the main venv and 3.11 for the voice venv (DeepFilterNet).
- Remotion and HyperFrames install globally under `~/.npm-global/bin`, which may not be on PATH: use `npx remotion` or the full path.

## Claude Code and connectors
- **Magnific:** its MCP exposes exactly 200 tools, and the generate / upload / wait tools fall past that limit, so image generation didn't reach Claude Code. `audio_clean_speech` needs a public URL. Re-test as the connector changes.
- **ElevenLabs creative flows** (Seedream with `background: transparent`) produced the 3D clay and glass assets.
- **Apify:** works for trend research, e.g. scraping Instagram reels (about ₹50 bought 8 reels plus a brief).
- **yt-dlp:** works for Instagram and YouTube. TikTok timed out on this network. YouTube captions rate-limit (HTTP 429) after many fetches, so the knowledge-base tools fall back to downloading the audio and running local Whisper.
- **GitHub:** if `git push` over SSH fails ("check access rights"), switch the remote to HTTPS and run `gh auth setup-git`.

## Apps evaluated
| App | What it is | Verdict |
|---|---|---|
| ReelMimic (`~/apps/reelmimic`) | Clones a reference video's edit, with a web UI | Optional; needs PyAV on Python 3.12 and Node 26 |
| OpenMotion (`~/apps/openmotion`) | Motion graphics studio, built from source | Not registered as an MCP server |
| MotionClone | Motion transfer | Windows / Codex only: not runnable on Mac |
| lemo-opuscar | 99 film-style presets (Claude Code plugin) | Installed by `install_skills.py` (optional) |
