# Treatments (read when the user asks for options or treatments)
Use `docs/TREATMENTS.md`. Treatments are 2-3 versions of one plan as fast proxies, compared side by side:
1. `cves treatments list`: the built-ins (`punchy`, `cinematic`, `minimal`) and any `PROJECT/treatments/*.yaml`; a learned
   `treatments.prefer` for this client or goal comes first. Use the ones the user names, else 2-3 that fit the brief. For a client-specific take, write `PROJECT/treatments/<name>.yaml` (style keys of `default.yaml`
   only + `structure:` hints).
2. `cves treatments make [a,b,c]`; read the printed changes and metrics (cuts, caption style, transitions, punch-ins).
3. `cves treatments render` (proxies: half size, fast encode, plates reused), then `cves treatments compare`.
4. Show the user `Edit/treatments/compare/sheet.jpg` and `compare.mp4` with one line per treatment (its label + summary).
   On their choice: `cves treatments pick <name>` (backs up `edit.yaml`, sets the treatment style layer, journals the
   choice for `cves learn`), then `cves build`.
