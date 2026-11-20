# Treatments (read when the brief is open or creative; step 5b)
Use `docs/TREATMENTS.md`. When the brief leaves the look open ("make it pop", "try something", a launch, a new client with
no inspirations or brand look), offer 2-3 treatments as proxies instead of one finished cut:
1. `cves treatments list`: the built-ins (`punchy`, `cinematic`, `minimal`) and any `PROJECT/treatments/*.yaml`; a learned
   `treatments.prefer` for this client or goal comes first. Pick 2-3 that serve `DIRECTION.md` (a quiet brand film does
   not need `punchy`). For a client-specific take, write `PROJECT/treatments/<name>.yaml` (style keys of `default.yaml`
   only + `structure:` hints).
2. `cves treatments make [a,b,c]`; read the printed changes and metrics (cuts, caption style, transitions, punch-ins).
3. `cves treatments render` (proxies: half size, fast encode, plates reused), then `cves treatments compare`.
4. Look at `Edit/treatments/compare/sheet.jpg` once. The rows must read as clearly different and each must be tasteful
   (legible captions, nothing cramped, no effect soup). Fix a weak one in its treatment file and `make` / `render` it again.
5. Show the user the sheet and `compare.mp4` with one line per treatment (its label + summary). On their choice:
   `cves treatments pick <name>` (backs up `edit.yaml`, sets the treatment style layer, journals the choice for
   `cves learn`), then continue at step 6 (`cves build`).
Skip it when the brief, the inspirations or the brand already fix the look: build one plan well.
