# Sound (read when planning music / SFX, or before describing the mix; `docs/SOUND.md`)
The engine places the sounds; the user's instructions and the style choose them.
- **Story beats drive the music.** Tag clips `beat:` with the structure's beats in `selects.yaml` (or set
  `music.hook_cut` / `turn_cut` / `drop_cut`). The hook / turn / drop beats default per `grammar.structure`: problem turn
  P/A, drop PR/O; offer turn M, drop PR; story turn T, drop PR. With `music.sync: drop` (or cuts / full), the drop lands
  on the payoff, and the drop whose build starts on the turn is preferred. `cves beats` prints the music sections (intro /
  build / drop / body / break / outro) against the hook, the turn and the payoff.
- **Accents are automatic.** `cves mix` adds a riser that resolves on the payoff; a riser into or out of the hook; a
  downbeat hit on the payoff; impacts on reveals that have no low hit of their own, only on picture events. Read
  `Edit/mix.json accents` to see what was placed or skipped and why. Off per video with `sfx: {auto: false}`, or style
  `sound.accents.enabled: false`.
- **Choose sounds by role, not by file.** In `sfx.extra`, write `@impact:hard`, `@whoosh:soft`, `@riser`, `@pop`, `@ui`,
  `@transition` or `@ambience`. `cves sfx list` shows the bank. When a hero moment needs a real recording, run
  `cves sfx fetch "<query>" --category <c> --to project` (CC0, credited automatically); `earshot describe` to hear it.
- **Ducking follows the voice** (`mix.duck_mode: envelope`): the bed breathes between phrases; `gate` gives the old fixed
  dips. The vocal guard (`mix.vmr_guard`) trims the bed's speech band wherever a word would sit under the music.
- Describe the mix only from a measurement: `Edit/mix.json`, or `earshot timeline Edit/mix.wav` when installed.
