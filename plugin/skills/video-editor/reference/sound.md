# Sound (read when planning music / SFX, or before describing the mix; `docs/SOUND.md`)
Cut sound as carefully as picture. The engine does the placing; you make the choices and listen.
- **Story beats drive the music.** Tag clips `beat:` with the structure's beats in `selects.yaml` (or set
  `music.hook_cut` / `turn_cut` / `drop_cut`). The hook / turn / drop beats default per `grammar.structure`: problem turn
  P/A, drop PR/O; offer turn M, drop PR; story turn T, drop PR. With `music.sync: drop` (or cuts / full), the drop lands
  on the payoff, and the drop whose build starts on the turn is preferred. `cves beats` prints the music sections (intro /
  build / drop / body / break / outro) against the hook, the turn and the payoff.
- **Accents are automatic and budgeted.** `cves mix` adds a riser that resolves on the payoff; a riser into or out of the
  hook; a downbeat hit on the payoff; impacts on reveals that have no low hit of their own. It adds no more than
  `creative.sound_accents_per_30s`, and only on picture events. Read `Edit/mix.json accents` to see what was placed or
  skipped and why. Turn them off per video with `sfx: {auto: false}`.
- **Choose sounds by role, not by file.** In `sfx.extra`, write `@impact:hard`, `@whoosh:soft`, `@riser`, `@pop`, `@ui`,
  `@transition` or `@ambience`. `cves sfx list` shows the bank. When a hero moment needs a real recording, run
  `cves sfx fetch "<query>" --category <c> --to project` (CC0 only, credited automatically), then listen with
  `earshot describe` before using it.
- **Ducking follows the voice** (`mix.duck_mode: envelope`): the bed breathes between phrases. Use `gate` only if a client
  asks for the old fixed dips.
- **QC:** SND-32 checks that each riser resolves on its target; SND-33 checks that the drop section sits on the payoff
  (both WARN for now). Before you describe the mix to anyone, listen with `earshot timeline Edit/mix.wav` around the payoff.
