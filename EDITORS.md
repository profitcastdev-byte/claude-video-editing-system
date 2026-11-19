# CVES for editors: quick start

CVES edits short-form videos (ads and organic posts) with Claude. You give it footage and a brief, approve two checkpoints, and review the result. It never delivers a file that fails its quality checks.

## 1. Install (once per computer, about 30–45 min)
Requirements: a Mac with Apple Silicon, and Claude Code (desktop or CLI).

In Claude Code:
```
/plugin marketplace add profitcastdev-byte/claude-video-editing-system
/plugin install cves@cves
```
Restart Claude Code, then run `/cves:install`. It installs the tools and models and finishes with `cves doctor`; everything should read OK.

**Team setup (recommended).** Edit `~/.cves/config.yaml` so everyone shares projects and learned taste:
```yaml
clients_root: ~/Google Drive/CVES Projects     # shared client folders (styles, brand files, past edits)
team_taste: ~/Google Drive/CVES Team/taste     # lessons the team approves (cves learn promote --team)
```
Keep git repos out of iCloud-synced folders such as `~/Documents` and `~/Desktop`: when the disk fills up, iCloud evicts files and breaks them.

## 2. Every video: the 7 steps
| # | You say / run | What happens | You approve? |
|---|---|---|---|
| 1 | `/cves:new-edit "Client" "Video name" /path/to/footage` | Creates the folder. Drop 2–5 reference videos in `Inspirations/` and the logo in `Brand/`. Say whether it's an **ad** or a **viral** post, and for which platform. | – |
| 2 | (automatic) | Claude picks the best takes, aligns them to the words, removes retakes and checks every chosen word is heard. You get a **cut list**. | ✋ **Yes: "approved"** or ask for changes |
| 3 | (automatic) | Claude plans the graphics, captions, music and SFX. For an open brief, ask for **treatments**: 2–3 different looks to pick from. | – |
| 4 | `cves review-plan` opens the **edit plan** in your browser | Every shot with its frames. Under each shot: **Approve**, quick buttons (Bigger / Smaller / Earlier / Later / Swap / Remove / Fix caption) and a **note box**. Press **Send to Claude**. | ✋ **Approve all** when happy |
| 5 | (automatic) | Render, then 96 quality checks, then Claude watches its own cut and fixes problems (up to 3 rounds). | – |
| 6 | Watch the draft on your phone | Give notes in plain words. Rate it 1–10 (`/cves:notes`): this teaches the system your taste. | ✋ |
| 7 | `/cves:deliver` | `Export/vNNN/`: master, captions (SRT), cover, 4:5 / 1:1 / 16:9 versions and 15 s / 30 s cut-downs. Everything passes QC. | – |

## 3. Daily rules
- **One video = one folder.** Always spell the client name the same way, so CVES reuses that client's style.
- **One Claude session per video at a time.** Different videos in parallel sessions are fine, just slower.
- **To resume tomorrow,** say *"continue the [video] edit for [client]"*, or run `cves status` in the project folder.
- **Never ask Claude to skip a failing check.** Ask it to fix the cause.
- **Ads use licensed music only.** CVES finds licence-checked tracks and writes the credit line into `Music/CREDITS.md`; put it in the post caption.
- **Don't delete `Raw/`.** Re-cuts need the original footage.

## 4. Fast commands
| Command | Use it for |
|---|---|
| `cves status` | Where this video is and what to do next |
| `cves build --draft` | A fast half-size preview while iterating (can never be delivered) |
| `cves build` | The full-quality render. It re-renders only what changed since last time |
| `cves qc --draft` | A quick check while iterating; `cves qc` is the full check that delivery needs |
| `cves review-plan` | Open the edit plan with note boxes |
| `cves templates NAME` | What one graphic template can do |
| `cves learn promote ID --team` | Share an approved lesson with the whole team |

## 5. When something goes wrong
| Problem | What to do |
|---|---|
| QC says FAIL | "Fix the QC fails." Claude fixes the cause; checks are never loosened. |
| A caption word is wrong | Use **Fix caption** in the edit plan, or say "caption: X should be Y". |
| It looks wrong but QC passed | Tell Claude what's wrong. It becomes a rule or a check, so it never comes back. |
| Want to edit by hand | Ask for **control mode**: you get a DaVinci Resolve / Kdenlive project, and your changes come back into CVES. |
| Lost track | Run `cves status`. |

More detail: `README.md`, `docs/PLAN-REVIEW.md`, `docs/LEARNING.md`, `docs/QC.md`.
