# Ratings, results and learned taste (read after a delivery, or when asked what CVES learned; `docs/LEARNING.md`, `/cves:learn`)
- After every delivery, ask the user for a 1-10 rating and one line why, and log it: `cves learn rate vNNN <score> --why
  "<their words>"` (`--by client` for the client's verdict; `cves learn approve|reject vNNN` for a sign-off or refusal).
  When they share platform numbers, log them with `cves learn results vNNN --platform .. --hook-rate .. --hold ..`.
- Every few deliveries (or when the user asks what CVES has learned), run `cves learn mine` and present the new candidates
  in plain words: the pattern, the proposed change, the scope, n and the effect. Promote only what the user approves
  (`cves learn promote <id>`, `--share` for the team, never with client names); record refusals with
  `cves learn reject <id> --why`. Never promote on your own: learning must never change the look silently.
