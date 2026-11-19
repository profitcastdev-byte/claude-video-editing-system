# goal: viral (read for an organic post: Reels, TikTok, Shorts, YouTube, not a paid ad)
Set `goal: viral` in `edit.yaml` and read `knowledge-base/modules/viral-playbook.md` (RULEBOOK §12, `docs/VIRAL.md`). The
workflow and both approvals stay; the goal layer (`styles/viral.yaml`) changes the defaults and `cves qc` adds the
retention gates RET-24 to RET-32.
- **Brief (step 1):** ask, in the same single message, for the **hook type** (curiosity gap, pattern break, bold claim,
  visual question, in media res, "wait for it" shown), the **structure** (loop, list, story arc, before/after, tutorial),
  the **platform** (`platform.target`: reels, tiktok, shorts, youtube, meta_feed, meta_stories), whether it **loops**, and
  the **trending sound** if one will be added in the app. Write them in `Edit/NOTES.md`.
- **Story (step 3):** design the hook first: the first second as picture and words, with a visual change and text or a
  strong subject by 1 s. Then the payoff (it lands in the last 20 %), then the middle as a chain of re-hooks. Re-order
  takes to put the hook line first. Show the hook and the payoff at the top of the cut list.
- **Plan (step 4):** budget the pattern interrupts before placing graphics: one every ≤ `rhythm.interrupt_max_s` (2.5 s),
  never a sustained run closer than `rhythm.interrupt_min_s` (no effect soup). List the interrupts with their times in the
  plan summary. Set `style: {structure: {loop: true}}` for a loop.
- **Music:** licensed music in the file as usual, or, for a trending sound, `music: {slot: platform, guide: <reference
  track or tempo>, sound: "<name>"}`: cut to the guide (`cves beats --sync cuts --apply`), deliver a music-free master
  with the guide stem and POSTING.md. **Never** use the slot for an ad.
