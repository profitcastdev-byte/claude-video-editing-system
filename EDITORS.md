# CVES for editors: quick start

CVES edits short-form videos (ads and organic posts) with Claude. You give it footage and instructions; it does what you ask, nothing more.

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
team_taste: ~/Google Drive/CVES Team/taste     # taste the team approves (cves learn promote --team)
```
Keep git repos out of iCloud-synced folders such as `~/Documents` and `~/Desktop`: when the disk fills up, iCloud evicts files and breaks them.

## 2. Every video: the 7 steps
| # | You say / run | What happens |
|---|---|---|
| 1 | `/cves:new-edit "Client" "Video name" /path/to/footage` | Creates the folder. Drop reference videos in `Inspirations/` and the logo in `Brand/`. Say whether it's an **ad** or a **viral** post, and for which platform. |
| 2 | "cut it: takes …, in this order" (`/cves:story`) | Claude writes the selects, aligns them to the words and builds the **cut list**. |
| 3 | "add a stat card on …, captions, music …" (`/cves:plan`) | Claude fills the plan with the graphics, captions, music and SFX you ask for. Ask for **treatments** for 2–3 looks to pick from. |
| 4 | `cves review-plan` opens the **edit plan** in your browser | Every shot with its frames. Under each shot: **Approve**, quick buttons (Bigger / Smaller / Earlier / Later / Swap / Remove / Fix caption) and a **note box**. Press **Send to Claude**. |
| 5 | "render it" (`/cves:render`) | Render, mix, encode. |
| 6 | Watch the draft on your phone | Give notes in plain words (`/cves:notes`). Rate it 1–10 if you want the system to learn your taste (`/cves:learn`). |
| 7 | `/cves:deliver` | `Export/vNNN/`: master, captions (SRT), cover, 4:5 / 1:1 / 16:9 versions and 15 s / 30 s cut-downs. |

## 3. Daily rules
- **One video = one folder.** Always spell the client name the same way, so CVES reuses that client's style.
- **One Claude session per video at a time.** Different videos in parallel sessions are fine, just slower.
- **To resume tomorrow,** say *"continue the [video] edit for [client]"*, or run `cves status` in the project folder.
- **Music licences are recorded** in `Music/CREDITS.md` with the credit line; put it in the post caption when the licence asks for one.
- **Don't delete `Raw/`.** Re-cuts need the original footage.

## 4. Fast commands
| Command | Use it for |
|---|---|
| `cves status` | Where this video is and what to do next |
| `cves build --draft` | A fast half-size preview while iterating |
| `cves build` | The full-quality render. It re-renders only what changed since last time |
| `cves review-plan` | Open the edit plan with note boxes |
| `cves templates NAME` | What one graphic template can do |
| `cves learn promote ID --team` | Share an approved taste pattern with the whole team |

## 5. When something goes wrong
| Problem | What to do |
|---|---|
| A caption word is wrong | Use **Fix caption** in the edit plan, or say "caption: X should be Y". |
| It looks wrong | Tell Claude what to change. |
| Want to edit by hand | Ask for **control mode**: you get a DaVinci Resolve / Kdenlive project, and your changes come back into CVES. |
| Lost track | Run `cves status`. |

More detail: `README.md`, `docs/PLAN-REVIEW.md`, `docs/LEARNING.md`.
