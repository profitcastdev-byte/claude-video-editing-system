# Modes (read when the user asks to open the edit in an editor)
- **Vibe (prompts only).** The user gives notes in words ("the price card is too fast"). Map each note to `edit.yaml`
  changes, re-render only what changed, and send the MP4 with a one-line change log per note. See `/cves:notes`.
- **Control (hands on).** Export a layered project (`cves export resolve` or `cves export kdenlive`) and drive the editor:
  DaVinci Resolve live through the `davinci-resolve-mcp` bridge (Workspace > Scripts > CursorBridge, works on Resolve
  Free), or Kdenlive through its MCP server by editing the `.kdenlive` file. The user then edits by hand. Baked graphics
  (text inside a card) still change through `edit.yaml` → `cves render --only <id>` → relink. See `/cves:resolve` and
  `/cves:kdenlive`.
