---
name: lua-to-python-kfx
description: Migrate Aegisub Lua karaoke templates (stock karaoke templater, karaOK, or The0x539's 0x.KaraTemplater) to lyricsheets Python KFX effects, or generate karaoke from a karaoke-timed .ass file without a Google Sheets database. Use when asked to port/convert inline Lua "code once"/"template"/"mixin" lines from an .ass file to Python, to set up local_songs generation, or to write a new TemplateEffect fx script.
---

# Lua → Python KFX migration (lyricsheets)

Full reference: `reference.md` in this skill's directory (Lua→lyricsheets
translation table and quirks). Templater-dialect docs: `templaters/`.
Worked examples: `hanasakebafx.py` / `hikarifx.py` in the Onibe-Subs repo
(`Hasu Stuff/Movie/Actual/`).

## Workflow

Work through these steps in order; verify at each checkpoint before moving on.

### 1. Identify the templater, then read the Lua

Three mutually incompatible templaters exist, and identical Effect strings
mean different things in each (`template line` is per-syllable in stock but
per-line in karaOK). Identify the dialect **before** interpreting any
template, and read its doc:

- **Stock Aegisub templater** (`template pre-line`, `fx`/`fxgroup`, numeric
  `loop n`) → `templaters/stock-kara-templater.md`
- **karaOK** (`lsyl`/`lword`/`lchar`/`word` classes, `k_retime`, `ci`) →
  `templaters/karaok.md` (also covers the `ln.kara` library, which all three
  templaters can use — `ln.` calls alone identify nothing)
- **0x / The0x539's KaraTemplater** (`mixin` components, named loops,
  `if`/`unless`, `actor`/`t_actor`) → `templaters/the0x-karatemplater.md`

Then read the `Comment` lines in the source `.ass`:
- `code once` → constants; `code line` → filtered per-line mutable state.
- Each `template`/`mixin` Comment's **Layer field** is the output layer.
- Note style/actor filters, `retime(...)` calls, loops, and whether templates
  are per-line, per-syl, per-word, or per-char — using the *dialect's*
  semantics, not another templater's.
- Actors live in each Dialogue line's Name field; a `2` token (e.g. `blue 2`)
  or a style ending in `2` means a secondary (backing vocal) line.
- Treat `$li` as source-dependent. It has no general `idxInSong` equivalent.
  Before deleting or reordering Lua rows, use the original templater or a
  throwaway Aegisub macro to capture any `$li`-derived values from an
  untouched copy. Encode the results as immutable, song-local migration data.
- `code line` runs are filter-sensitive and stateful in every dialect:
  components execute in original subtitle order only when their filters match
  and mutate a shared environment. Preserve that filtered ordering explicitly
  when porting stateful code.

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
durations sum to the line duration. lyricsheets deliberately uses
case-insensitive `karaoke` *substring* matching for the Effect field — looser
than every templater's own input matching (each templater doc states its exact
rule) — so audit any extra lines it retains, such as `karaoke too long`.

### 3. Prepare the .kfx.ass file (never overwrite the Lua original)

Copy the original to `<name>.kfx.ass`, then in the copy:
1. Delete all Lua template/code/mixin Comment lines and stale generated lines
   (Effect `fx`).
2. Convert source karaoke `Dialogue:` lines to `Comment:` (keep Effect
   `karaoke`).
3. Add output styles — names **must start with `Song`** (e.g. `Song - X JP`)
   so regeneration cleans them up.
4. Add the Song comment (start time = first syllable, text = local_songs key):
   `Comment: 0,<t>,<t>,Song,,0,0,0,,{\lyricsmodify(import,-,myfx;kfx,-,my_effect)}Title`

### 4. Port the effect

Write `myfx.py` next to the `.kfx.ass`: subclass `TemplateEffect`, one
`Template.compile(text, style, layer)` per Lua template, helpers in
`globals_dict = globals()`. Key rules (dialect-specific mappings are in the
`templaters/` docs):

- Helpers are called as `helper(kObject, event, *args)`; do all real math in
  helpers and return tag strings — the `!...!` evaluator has no builtins.
- Template bodies must not contain `:` and times in `\t()` should be ints.
- `kSyl.center` is absolute; Lua's `syl.center` is line-relative — subtract
  `kLine.left`.
- Replace actor/style-filtered template variants with one template + a helper
  branching on `kLine.startActor` / `kLine.isSecondary`.
- lyricsheets has only `line|syl|char` templates, no loops, no mixins: fold
  mixins into their templates, unroll loops into helpers or multiple
  `Template`s, and port per-word/one-event-per-syl-block classes (0x `mixin
  char`, stock `template line`, karaOK `lsyl`) as `template line notext`
  whose helper builds the whole text as per-char/per-syl `{tags}c{tags}h…`
  blocks (per-char *events* double-blend overlapping glows; blocks in one
  event don't).
- Reproduce `code line` mutations using captured source order and the original
  component filters. Cache results by `(kLine.isEN, kLine.idxInSong)` when that
  is a stable song-local lookup key; do not assume runtime generation order is
  equivalent to the Lua source walk.
- Reproduce `$li`-derived behavior from captured song-local data, not an
  inferred line offset. Fail loudly when a required mapping is missing.
- Port randomness with deterministic per-line/per-syl seeding, or generation
  stops being idempotent.
- Keep migration-only indexing and captured data inside the effect module. Do
  not add `sourceLineIndex` or other migration-only fields to `SongLine` or
  `KLine`.

**Intentional-deviations checkpoint:** compare the port with the source and
list every deliberate difference before generation. Check English auto-fit,
`noblank` cleanup, extra ASS tags, sub-pixel positions, and source lines the
original templater would have skipped (see the templater doc's input rules).
Keep only reviewed improvements.

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
