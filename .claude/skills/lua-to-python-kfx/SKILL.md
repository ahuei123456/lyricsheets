---
name: lua-to-python-kfx
description: Migrate Aegisub Lua karaoke templates (karaoke templater or 0x/The0x539 templater) to lyricsheets Python KFX effects, or generate karaoke from a karaoke-timed .ass file without a Google Sheets database. Use when asked to port/convert inline Lua "code once"/"template"/"mixin" lines from an .ass file to Python, to set up local_songs generation, or to write a new TemplateEffect fx script.
---

# Lua → Python KFX migration (lyricsheets)

This is a shim for Claude Code, which does not yet discover skills from the
cross-tool `.agents/skills/` directory.

The canonical skill lives at `.agents/skills/lua-to-python-kfx/` in this repo:
read its `SKILL.md` now and follow the workflow there. The detailed
Lua→lyricsheets translation table and quirks are in `reference.md` alongside
it.
