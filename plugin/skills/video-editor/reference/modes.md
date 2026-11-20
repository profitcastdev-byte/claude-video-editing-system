# Modes (read when the user picks control mode, or asks to open the edit in an editor)
Ask once per project which mode the user wants, if they haven't said. The default is **vibe**.
- **Vibe mode (prompts only).** The user gives notes in words ("the price card is too fast"). You map each note to
  `edit.yaml` changes, re-render only what changed, re-run `cves qc` to 0 FAILs, and send the MP4 with a one-line change
  log per note. See `/cves:notes`.
- **Control mode (hands on).** You export a layered project (`cves export resolve` or `cves export kdenlive`) and drive the
  editor: DaVinci Resolve live through the `davinci-resolve-mcp` bridge (Workspace > Scripts > CursorBridge, works on
  Resolve Free), or Kdenlive through its MCP server by editing the `.kdenlive` file. The user then edits by hand. Baked
  graphics (text inside a card) still change through `edit.yaml` → `cves render --only <id>` → relink. Anything that
  leaves Resolve or Kdenlive must pass the same final-file gates. See `/cves:resolve` and `/cves:kdenlive`.
