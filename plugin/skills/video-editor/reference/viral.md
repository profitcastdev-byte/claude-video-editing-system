# goal: viral (read for an organic post: Reels, TikTok, Shorts, YouTube, not a paid ad)
`goal: viral` in `edit.yaml` layers `styles/viral.yaml` (faster pacing defaults, popped captions, `music.sync: cuts`) right
after `styles/default.yaml` (`docs/VIRAL.md`). Everything else works as for an ad.
- **Platform:** `style: {platform: {target: reels|tiktok|shorts|youtube|meta_feed|meta_stories}}` sets the UI safe zone,
  duration band and loudness (`styles/platforms.yaml`).
- **Loop:** `style: {structure: {loop: true}}` when the user wants the end to flow back into the start.
- **Trending sound added in the app:** `music: {slot: platform, guide: <reference track, beats.json or tempo>, sound:
  "<name>"}`: cut to the guide (`cves beats --sync cuts --apply`); `cves deliver` ships a music-free master with the guide
  stem and POSTING.md (which sound, where to start it, where the drop lands).
