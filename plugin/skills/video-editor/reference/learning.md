# Ratings, results and learned taste (read when the user rates a version, shares results, or asks what CVES learned; `docs/LEARNING.md`, `/cves:learn`)
- A rating or verdict the user gives: `cves learn rate vNNN <score> --why "<their words>"` (`--by client` for the client's);
  `cves learn approve|reject vNNN`. Platform numbers: `cves learn results vNNN --platform .. --hook-rate .. --hold ..`.
- When the user asks what CVES has learned: `cves learn mine`, then present the new candidates in plain words (pattern,
  proposed change, scope, n, effect). Promote only what the user picks (`cves learn promote <id>`, `--share` for the team,
  never with client names); `cves learn reject <id> --why` for the ones they turn down. Learning never changes the look
  until a person promotes it.
