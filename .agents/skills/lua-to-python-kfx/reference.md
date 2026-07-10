# Migrating Aegisub Lua karaoke templates to Python KFX

This guide covers taking a song that only exists as a karaoke-timed `.ass` file
with inline Lua and regenerating the same effect with lyricsheets — **no Google
Sheets database required**. It is based on the migration of two Hasunosora
movie songs (`hanasakebafx.py`, `hikarifx.py` in the Onibe-Subs repo), which
are good worked examples.

## 0. Identify the source templater first

There are (at least) three mutually incompatible Aegisub templaters, and the
same Effect string can mean different things in each (`template line` is
per-syllable in stock, per-line in karaOK). Identify the dialect before
reading a single template, then read the matching doc in `templaters/`:

| Templater | Telltale signs | Doc |
|---|---|---|
| Stock Aegisub karaoke templater | `template pre-line`, `fx`/`fxgroup` modifiers, numeric `loop n`, no mixins | `templaters/stock-kara-templater.md` |
| karaOK (logarithm) | `lsyl`/`lword`/`lchar`/`word`/`furichar` classes, `code word/char`, `k_retime`, `ci` | `templaters/karaok.md` |
| The0x539's KaraTemplater | `mixin` components, named `loop foo 3`, `if`/`unless`, `actor`/`t_actor`, `anystyle` | `templaters/the0x-karatemplater.md` |

`ln.` calls (the karaOK *library*) appear under all three templaters and don't
identify anything; the `ln.kara` → Python mapping lives in
`templaters/karaok.md`. All three templaters share karaskel's `line`/`syl`
data model, so the translation table below applies to all of them; the
per-templater docs cover the dialect-specific classes, modifiers, and
functions.

## Overview

The pipeline after migration looks like this:

```
song.kfx.ass ──┐                       ┌── song.kfx.ass (rewritten in place)
  source lines │──> lyricsheets-populate ──┤     generated "Song - *" events
  Song comment │      + yourfx.py       └──   source lines untouched
```

One `.ass` file is both the database and the output: the original karaoke
timings live in it as `Comment` events, a `Song` comment tells populate what to
generate, and generated events are written back into the same file. Rerunning
populate deletes and regenerates only the events whose style starts with
`Song` — it is idempotent.

## 1. Local songs instead of Google Sheets

`SongServiceByAssFiles` (`lyricsheets/service/assfile.py`) builds a `Song`
directly from a karaoke-timed `.ass` file. Enable it with a `local_songs` key
in your config (`google_credentials` becomes optional; if both are present,
local songs win):

```json
{
    "local_songs": {
        "Hanasakeba Yume Kakeru": "hanasakebayumekakeru.kfx.ass",
        "Hikari no Naka de Hanasaite": "hikarinonakadehanasaite.kfx.ass"
    }
}
```

Relative paths resolve against the config file's directory. A value can also be
an object when the default style detection isn't enough:

```json
"Some Song": {"path": "somesong.ass", "romaji_style": "MyRomaji", "en_style": "MyEnglish"}
```

### What the source file must look like

The adapter reads events (Dialogue **or** Comment — comment your source lines
out so they don't render) whose Effect field contains `karaoke`, using a
case-insensitive substring match. This is intentionally looser than every
templater's own input matching (see each templater doc); audit lines the
adapter picks up that the original templater would have skipped.

- **Romaji lines** — style name containing `romaji` (case-insensitive), or
  matching the `romaji_style` prefix. Must carry `{\k}` syllable timings.
- **English lines** — style name containing `english`, or matching the
  `en_style` prefix. Plain text; paired with romaji lines **1:1 in file
  order** (populate errors out on a count mismatch).
- **Actor** — the Name field (`green`, `blue`, `all`, …) becomes the line's
  actor (`kLine.startActor`).
- **Secondary lines** (backing vocals) — a `2` token in the Name field
  (`blue 2`) or a style name ending in `2` (`MyRomaji2`) sets
  `kLine.isSecondary`.

## 2. Preparing the karaoke file

Starting from the Lua-templated file:

1. **Delete** all the Lua `Comment` lines (`code once`, `code line`,
   `template ...`, `mixin ...`) and any stale generated lines (Effect `fx`).
2. **Convert** every source karaoke `Dialogue` line to `Comment` (keep
   `karaoke` in the Effect field).
3. **Add the styles** your generated events will use. Their names must start
   with `Song` (e.g. `Song - MySong JP`) so that re-running populate cleans
   them up (`filter_old_song_lines` keeps everything else).
4. **Add the `Song` comment.** Style `Song`, start time = the first timed
   syllable, text = the exact `local_songs` key:

   ```ass
   Comment: 0,0:11:09.26,0:11:09.26,Song,,0,0,0,,{\lyricsmodify(import,-,myfx;kfx,-,my_effect)}My Song Title
   ```

   `import,-,myfx` imports `myfx.py` from the same directory as the input
   file; `kfx,-,my_effect` selects the effect it registered.

Then generate (and regenerate after any edit) with:

```powershell
uv run lyricsheets-populate --no-title --config path\to\config.json path\to\song.kfx.ass
```

## 3. Porting the effect itself

Write a `myfx.py` next to the input file, modeled on `TemplateEffect`:

```python
import pyass
from lyricsheets.ass.to_ass import KObject, register_effect
from lyricsheets.effect.template_effect import Template, TemplateEffect, retime

ROMAJI_STYLE = pyass.Style.parse("Style: Song - MySong JP,<font>,<size>,...")
EN_STYLE = pyass.Style.parse("Style: Song - MySong EN,...")

def my_helper(kObject: KObject, event: pyass.Event) -> str:
    return rf"\pos({kObject.center},{50})"

class MyEffect(TemplateEffect):
    romaji_templates = [
        Template.compile(r"template syl noblank: {!my_helper()!\blur1}", ROMAJI_STYLE, 3),
    ]
    en_templates = [
        Template.compile(r"template line: {\pos(21,1020)\blur1}", EN_STYLE, 3),
    ]
    globals_dict = globals()

register_effect("my_effect", MyEffect())
```

Template syntax essentials:

- `template line|syl|char`, plus `noblank` (skip whitespace-only syls/chars)
  and `notext` (don't append the object's text — you supply it yourself).
  There is no `word`, `furi`, mixin, or loop support — the templater docs say
  how to fold each dialect's extras into these three classes.
- The third `Template.compile` argument is the **layer**, taken from each Lua
  template's Comment line. One `Template` = one Lua template line.
- `!helper()!` calls a function from `globals_dict`; it is always invoked as
  `helper(kObject, event, *args)`. Return a tag string (or a number). The
  expression evaluator only supports arithmetic, calls, names and indexing —
  no keywords, no builtins like `int()` — so do any real math inside helpers.
- `$sstart`, `$sdur`, `$skdur`, `$ldur`, `$li`, `$center`, … are inline
  variables (see `KObject.inline_var` in `lyricsheets/models/karaoke.py`).
- **Template bodies must not contain `:`** — `Template.compile` splits on it.

### Lua → lyricsheets translation table

These rows hold for all three templaters (karaskel-shared concepts);
dialect-specific mappings are in the `templaters/` docs.

| Lua (karaskel) | lyricsheets equivalent |
|---|---|
| `syl.start_time` / `syl.end_time` (ms, line-relative) | `$sstart` / `$send`, or `ms(kObject.kSyl.start)` in a helper |
| `syl.kdur` (centiseconds) | `$skdur`, or `ms(duration) // 10` |
| `syl.i`, `line.li` (1-based) | `kSyl.i`, `kLine.idxInSong` (both 1-based) |
| `syl.center` (relative to the line's left edge) | `kSyl.center` is **absolute** — use `kSyl.center - kLine.left` |
| `orgline.center - orgline.left` | `kLine.width / 2` |
| `$ldur`, `$lstart`, `$lmid` | same names |
| `retime("line", a, b)` | `retime(kObject, event, "line", a, b)` via a helper (stock modes + char modes; 0x-only modes need emulation — see the 0x doc) |
| `code once` globals | module-level constants |
| `code line` per-line state | Reproduce the original filtered source-order walk, then cache computed results by a stable song-local key such as `(kLine.isEN, kLine.idxInSong)`. Do not assume lyricsheets runtime order is semantically equivalent. |
| actor-filtered template variants (`actor green`, stock per-style copies) | one template + a helper branching on `kLine.startActor` / `kLine.isSecondary` |
| `inline_fx` | `kSyl.inlineFx` (from per-line actors/breakpoints) |

### Quirks worth knowing

- **`$li` has no general `idxInSong` equivalent.** Its meaning depends on the
  source templater and subtitle state (see each templater doc); deleting or
  reordering rows changes it. On an untouched disposable copy, use the real
  templater or an Automation macro over Aegisub's `subs` indexing to capture
  every required `$li`-derived value first. Store immutable mappings inside
  the song effect and fail on missing entries. Do not add `sourceLineIndex`
  or any other migration-only field to `SongLine` or `KLine`.
- **`code line` execution is filter-sensitive and stateful** in every
  templater: components run only when their style/actor/condition filters
  match and mutate one shared environment, in source order. Capture or
  simulate that exact walk before translating the resulting state to
  lyricsheets keys.
- **English `KLine` syllable times are absolute**, not line-relative like
  romaji (see `to_en_k_line`). Avoid syllable-time math on English lines.
- **Positions come from real font metrics.** `FontScaler` measures with wx
  using *installed system fonts*. If a font is only shipped per-release (mkv
  attachment), install it first — otherwise wx silently falls back to a
  default font and every position is subtly wrong.
- Times fed to `\t(...)` should be ints — round in your helpers.
- **Randomness breaks idempotency.** Any `math.random`/`util.rand`/`ln`
  randomization must be ported with deterministic per-line/per-syl seeding,
  or the run-populate-twice check will fail.

### Intentional deviations

Before accepting a port, compare it against the original source and record all
deliberate behavior changes. In particular, check:

- English auto-fitting added to prevent overflow.
- `noblank` or other harmless blank-syllable cleanup.
- Extra ASS tags that were not emitted by the Lua template.
- Source lines picked up by lyricsheets that the original templater would
  skip — each templater doc describes its exact input matching versus the
  adapter's case-insensitive `karaoke` substring match.
- Sub-pixel precision: lyricsheets keeps float positions where stock rounds
  to ints (karaOK to one decimal).

Keep each divergence only when it is intentional and covered by verification.

## 4. Verifying the port

- Run populate **twice** and diff/count events — output must be identical
  (idempotency also proves the `Song`-style cleanup works).
- Pick one line and hand-check the generated tags against the Lua arithmetic
  (transform times, sweep colors, lead-ins).
- Eyeball it in Aegisub next to a render of the old Lua effect.

Remember that the migrated file's commented-out source lines are now the
database: retiming or rewording means editing those comments (or the sheet, if
the song later graduates to one) and re-running populate.
