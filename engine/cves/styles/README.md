# Styles

The schema, the merge order and every key are documented in [docs/STYLE.md](../../../docs/STYLE.md).

- `default.yaml`: neutral defaults. Every key the engine reads is here, with a comment.
- `<preset>.yaml`: a reusable look holding only the keys it changes. `edit.yaml` names it: `style: {preset: profitcast-dark}`.
- `viral.yaml`: retention-first defaults for organic posts. `edit.yaml goal: viral` layers it right after `default.yaml` (docs/VIRAL.md).
- `platforms.yaml`: not a preset. The platform profiles (UI safe zones as fractions of the frame, duration bands, loudness)
  picked with `platform.target` (docs/VIRAL.md).

**Per client:** run `cves inspire` on the client's reference edits (`PROJECT/Inspirations/`): it measures pacing, grade,
palette, captions, transitions and sound bed and writes `PROJECT/Edit/style.yaml` with evidence for every key. Then
- drop a `PROJECT/Brand/style.yaml` with the brand tokens to force, e.g.
  ```yaml
  colors: {accent: "#FF7A00", accent_dark: "#A34E00"}
  stage:  {glow_bottom: "#5A2A00", dot_grid: "#FFB070"}
  ```
- or create `styles/<client>.yaml` (copy `profitcast-dark.yaml`, change values) and set `style.preset`.

Fonts must be in `assets/fonts/` (check their licence allows embedding in video) or given as absolute paths.
`cves validate` warns on any style key that `default.yaml` does not know, with a did-you-mean suggestion.
