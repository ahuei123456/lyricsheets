---
name: lua-to-python-kfx
description: Migrate Aegisub Lua karaoke templates (karaoke templater or 0x/The0x539 templater) to lyricsheets Python KFX effects, or generate karaoke from a karaoke-timed .ass file without a Google Sheets database. Use when asked to port/convert inline Lua "code once"/"template"/"mixin" lines from an .ass file to Python, to set up local_songs generation, or to write a new TemplateEffect fx script.
---

# Lua → Python KFX migration (lyricsheets)

Full reference: `reference.md` in this skill's directory (read it for the
Lua→lyricsheets translation table and quirks). Worked examples:
`hanasakebafx.py` / `hikarifx.py` in the Onibe-Subs repo (`Hasu Stuff/Movie/Actual/`).

## Workflow

Work through these steps in order; verify at each checkpoint before moving on.

### 1. Understand the Lua

Read the `Comment` lines in the source `.ass`:
- `code once` → constants; `code line` → per-line mutable state (order-dependent).
- Each `template`/`mixin` Comment's **Layer field** is the output layer.
- Note actor filters (`actor X`, `noactor X`, `t_actor`), `retime(...)` calls,
  and whether templates are per-line, per-syl, or per-char (0x `mixin char`).
- Actors live in each Dialogue line's Name field; a `2` token (e.g. `blue 2`)
  or a style ending in `2` means a secondary (backing vocal) line.

### 2. Build the Song source

The adapter (`lyricsheets/service/assfile.py`) reads romaji lines (style
containing `romaji`, `{\k}` timed) and English lines (style containing
`english`), paired 1:1 in file order, Effect field containing `karaoke`,
Dialogue or Comment. Config:

```json
{"local_songs": {"Exact Song Title": "song.kfx.ass"}}
```

**Checkpoint:** load the file with `song_from_ass()` in a throwaway script and
verify line count, actors, secondary flags, and that per-line syllable
durations sum to the line duration.

### 3. Prepare the .kfx.ass file (never overwrite the Lua original)

Copy the original to `<name>.kfx.ass`, then in the copy:
1. Delete all Lua template/code/mixin Comment lines.
2. Convert source karaoke `Dialogue:` lines to `Comment:` (keep Effect
   `karaoke`).
3. Add output styles — names **must start with `Song`** (e.g. `Song - X JP`)
   so regeneration cleans them up.
4. Add the Song comment (start time = first syllable, text = local_songs key):
   `Comment: 0,<t>,<t>,Song,,0,0,0,,{\lyricsmodify(import,-,myfx;kfx,-,my_effect)}Title`

### 4. Port the effect

Write `myfx.py` next to the `.kfx.ass`: subclass `TemplateEffect`, one
`Template.compile(text, style, layer)` per Lua template, helpers in
`globals_dict = globals()`. Key rules:

- Helpers are called as `helper(kObject, event, *args)`; do all real math in
  helpers and return tag strings — the `!...!` evaluator has no builtins.
- Template bodies must not contain `:` and times in `\t()` should be ints.
- `kSyl.center` is absolute; Lua's `syl.center` is line-relative — subtract
  `kLine.left`.
- Replace Lua actor-filtered template variants with one template + a helper
  branching on `kLine.startActor` / `kLine.isSecondary`.
- Port 0x `mixin char`/`mixin syl` as a `template line notext` whose helper
  builds the whole text as per-char `{tags}c{tags}h…` blocks (per-char
  *events* double-blend overlapping glows; per-char blocks in one event don't).
- `code line` sequential state → helper caching per
  `(kLine.isEN, kLine.idxInSong)`; lines process in order, romaji then EN.
- The Aegisub `$li` counter runs across romaji+EN blocks; `idxInSong` restarts
  per language — offset by the romaji line count if colors key off `$li`.

### 5. Generate and verify

```powershell
uv run lyricsheets-populate --no-title --config <config.json> <song.kfx.ass>
```

- Fonts must be **installed system-wide** (wx measures them); a missing font
  silently falls back and skews every position. Check with
  `wx.FontEnumerator().GetFacenames()` if positions look wrong.
- Run populate **twice**; generated Dialogue counts must not change
  (idempotency).
- Hand-check one line's generated tags against the Lua arithmetic (transform
  times, sweep colors, lead-ins), then eyeball in Aegisub vs the old effect.
