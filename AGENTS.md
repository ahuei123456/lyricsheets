# lyricsheets — agent notes

Generates karaoke effects (KFX) in `.ass` subtitle files from song data in
Google Sheets, or from local karaoke-timed `.ass` files (`local_songs` config
key). Python 3.14, managed with `uv` (`uv sync`, `uv run lyricsheets-populate ...`).

## Skills

Skills live in `.agents/skills/` (Agent Skills / SKILL.md open standard):

- **lua-to-python-kfx** — migrating Aegisub Lua karaoke templates to Python
  `TemplateEffect` scripts and generating karaoke without a Google Sheets DB.
  If your tool does not auto-discover skills, read
  `.agents/skills/lua-to-python-kfx/SKILL.md` (workflow) and its
  `reference.md` (Lua→lyricsheets translation table, quirks) when working on
  KFX migrations or `local_songs` setups.

`.claude/skills/` contains only shims for Claude Code, which discovers skills
from there; the `.agents/skills/` copies are canonical.
