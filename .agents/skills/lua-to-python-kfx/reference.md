# Migrating Aegisub Lua karaoke templates to Python KFX

This guide covers taking a song that only exists as a karaoke-timed `.ass` file
with inline Lua (karaoke templater or 0x-templater style) and regenerating the
same effect with lyricsheets — **no Google Sheets database required**. It is
based on the migration of two Hasunosora movie songs (`hanasakebafx.py`,
`hikarifx.py` in the Onibe-Subs repo), which are good worked examples.

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
out so they don't render) whose Effect field contains `karaoke`:

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
   `template ...`, `mixin ...`).
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
- The third `Template.compile` argument is the **layer**. In karaoke-templater
  files the layer lives on each template's Comment line; in 0x files too.
  One `Template` = one Lua template line.
- `!helper()!` calls a function from `globals_dict`; it is always invoked as
  `helper(kObject, event, *args)`. Return a tag string (or a number). The
  expression evaluator only supports arithmetic, calls, names and indexing —
  no keywords, no builtins like `int()` — so do any real math inside helpers.
- `$sstart`, `$sdur`, `$skdur`, `$ldur`, `$li`, `$center`, … are inline
  variables (see `KObject.inline_var` in `lyricsheets/models/karaoke.py`).
- **Template bodies must not contain `:`** — `Template.compile` splits on it.

### Lua → lyricsheets translation table

| Lua (karaskel / 0x templater) | lyricsheets equivalent |
|---|---|
| `syl.start_time` / `syl.end_time` (ms, line-relative) | `$sstart` / `$send`, or `ms(kObject.kSyl.start)` in a helper |
| `syl.kdur` (centiseconds) | `$skdur`, or `ms(duration) // 10` |
| `syl.i`, `line.li` (1-based) | `kSyl.i`, `kLine.idxInSong` (both 1-based) |
| `syl.center` (relative to the line's left edge) | `kSyl.center` is **absolute** — use `kSyl.center - kLine.left` |
| `orgline.center - orgline.left` | `kLine.width / 2` |
| `$ldur`, `$lstart`, `$lmid` | same names |
| `retime("line", a, b)` | `retime(kObject, event, "line", a, b)` via a helper (all modes supported) |
| `code once` globals | module-level constants |
| `code line` per-line state | helper caching per `(kLine.isEN, kLine.idxInSong)`; lines are processed in order (all romaji, then all English), so sequential state like "previous line's end time" chains naturally |
| `template syl actor green` / actor filters | one template + a helper branching on `kLine.startActor` / `kLine.isSecondary` |
| 0x `mixin char` / `mixin syl` on a line template | `template line notext` + a helper that builds the whole text as per-char `{tags}c{tags}h…` blocks. Keeps borders/blur contiguous — per-char *events* double-blend where glows overlap |
| 0x `util.xf()` | `(kChar.i - 1) / (len(kLine.chars) - 1)` |
| `inline_fx` | `kSyl.inlineFx` (from per-line actors/breakpoints) |

### Quirks worth knowing

- **`$li` counts differently.** The Aegisub templater's `li` keeps counting
  across every karaoke line in the file (romaji *and* English), while
  `idxInSong` restarts per language. If a color cycle keys off `$li` for
  English lines, add the romaji line count as an offset to reproduce the
  original colors (see `EN_LINE_INDEX_OFFSET` in `hanasakebafx.py`).
- **English `KLine` syllable times are absolute**, not line-relative like
  romaji (see `to_en_k_line`). Avoid syllable-time math on English lines.
- **Positions come from real font metrics.** `FontScaler` measures with wx
  using *installed system fonts*. If a font is only shipped per-release (mkv
  attachment), install it first — otherwise wx silently falls back to a
  default font and every position is subtly wrong.
- Times fed to `\t(...)` should be ints — round in your helpers.

## 4. Verifying the port

- Run populate **twice** and diff/count events — output must be identical
  (idempotency also proves the `Song`-style cleanup works).
- Pick one line and hand-check the generated tags against the Lua arithmetic
  (transform times, sweep colors, lead-ins).
- Eyeball it in Aegisub next to a render of the old Lua effect.

Remember that the migrated file's commented-out source lines are now the
database: retiming or rewording means editing those comments (or the sheet, if
the song later graduates to one) and re-running populate.
