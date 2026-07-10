# karaOK (logarithm's templater mod + `ln.kara` library)

https://github.com/logarrhythmic/karaOK — two separate things that often get
conflated:

## Sources

Fetch via GitHub MCP (`get_file_contents`, owner `logarrhythmic`, repo
`karaOK`) when the README is unclear — its author warns "parts of this will
be out of date or outright incorrect":

- `README.md` — library + templater-mod docs (basis for this file).
- `autoload/ln.kara-templater-mod.lua` — the modified templater itself.
- `include/ln/kara.lua` — the `ln` library implementation; the authority for
  exact `ln.*` math when porting (e.g. `ln.tag.pos` anchor handling,
  `ln.wave` sampling, `xerp` acceleration).

The repo is feature-frozen, so these references should stay stable.

1. **The karaOK templater** — a modified copy of the stock templater
   (feature-frozen; its own README recommends 0x for new work).
2. **The `ln.kara` utility library** — loadable from *any* templater: stock
   (`ln = _G.require "ln.kara"; ln.init(tenv)` in a `code once`), karaOK, or
   0x (which auto-loads it as `ln`). Seeing `ln.` calls does **not** identify
   the templater; check the keywords below.

## Recognizing the karaOK templater

- Class keywords `lsyl`, `lword`, `lchar`, `word`, `furichar` in template
  Effects.
- `template line` present but `template pre-line` absent (karaOK renamed it).
- `code word` / `code char` lines (stock doesn't have these).
- `style <name>` modifier, `k_retime(...)` calls, `ci` variable.

## Templater differences vs stock

Everything in `templaters/stock-kara-templater.md` applies except:

**Keyword renames (the critical part).** karaOK shifted the class names:

| karaOK class | Meaning | Stock equivalent | lyricsheets equivalent |
|---|---|---|---|
| `line` | runs once per line, one output event | `pre-line` | `template line` |
| `lsyl` | runs per syllable, **one** output event, output placed before each syl | stock `line` | `template line notext` + helper building `{tags}syl…` blocks |
| `lword` | per word, one output event | — | `template line notext` + helper splitting on whitespace |
| `lchar` | per char, one output event | — | `template line notext` + per-char blocks helper |
| `word` | **one output event per word** | — | no word class in lyricsheets; if word ≠ syl boundaries, restructure (per-word blocks in one event, or one `Template` per case) and record the deviation |
| `syl`, `char` | as stock | same | `template syl` / `template char` |
| `furichar` | one event per furigana char | — | no lyricsheets support |

So the same Effect string `template line` means "once per line" in karaOK but
"per syllable" in stock — identify the templater before reading any template.

**Other behavioral changes:**

- Line splitting is NyuFX-style: `word`, `syll`, `char` objects exist, and
  `syl` aliases *the current smallest unit* (word/syl/char depending on
  class). `syll` is always the true syllable. When porting, resolve which
  object each expression really read.
- `style <name>` modifier: runs on any line whose style name **contains**
  `<name>` (substring, like fxgroup-style gating) — e.g.
  `template line all style romaji`. Closer to lyricsheets' own
  romaji/english style detection than stock's exact matching.
- `ci` — character index of the start of the current unit.
- Expanded tenv: templates can touch the `subtitles` object directly (read
  other lines!), plus `table`, `pairs`, `ipairs`, `tonumber`, `tostring`,
  `type`. If a template reads neighboring lines through `subtitles`, that is
  `$li`-style source-dependent state: capture it from an untouched copy.
- `notext`/`noblank` work on all classes; `line.text` isn't clobbered.
- Inline `$` position variables have one decimal of sub-pixel precision
  (stock rounds to ints; lyricsheets keeps full floats).
- `maxloop(0)` suppresses the output line entirely — a poor man's `skip()`.
  Port as conditional logic; see the intentional-deviations checkpoint.
- `k_retime(...)` — like `retime` but also shifts the current syl timing.
  The lyricsheets `retime` helper does not adjust `kSyl`; do any dependent
  syl-time math explicitly in the helper.

## `ln.kara` library → Python equivalents

Only the functions that commonly appear in templates. `ln.init(tenv)` also
registers shorthands (`st`, `sd`, `gc`, `ga`, `rgb`, `hsl`, `hsy`, `clamp`,
`rnd`, `fl`, `set`, `rset`) — grep for both names.

| Lua | Port as |
|---|---|
| `ln.syltime(p)` / `st(p)` | `ms(kSyl.start) + p * ms(kSyl.duration)` in a helper |
| `ln.syldur(p)` / `sd(p)` | `p * ms(kSyl.duration)` |
| `ln.line.c(n)` / `gc(n)`, `ln.line.a(n)` / `ga(n)` | color/alpha from the source line's tags, falling back to style defaults. The adapter doesn't expose source override tags — read the style you defined in the fx module, or capture per-line values as migration data |
| `ln.line.tag(...)` / `ln.line.tags(...)` | same: capture from the source file; don't try to re-parse at runtime |
| `ln.line.buffers(...)` | lead-in/out from `\fad` or blank edge syllables — compute from `kLine.syls` durations in a helper |
| `ln.line.len()` / `len_stripped()` | `len(kLine.text)` (Python is already unicode-safe) |
| `ln.tag.pos(...)` / `ln.tag.move(...)` | build `\an\pos`/`\move` from `kLine`/`kSyl` geometry (`kObject.center`, `kLine.top`, style alignment) |
| `ln.tag.t(...)` | emit `\t(...)` from a helper with `round()`ed int times |
| `ln.wave.*` (`new`, `addWave`, `transform`, …) | precompute the sampled waveform in Python (`math.sin` etc.) and emit the `\t` chain from a helper — this is *easier* in Python than in Lua |
| `ln.color.byRGB/byHSL/lumaHSL`, `rgb`/`hsl`/`hsy` | Python `colorsys` or manual math; emit `&HBBGGRR&` strings (BGR order!) |
| `ln.color.rgb.get/add`, `ln.color.hsl.get/add` | parse/format the ASS color string in a helper |
| `ln.math.clamp/lerp/xerp/round/modloop/modbounce/log/sgn` | plain Python; `xerp` matches `\t` acceleration: `v0 + (v1 - v0) * t**accel` |
| `ln.math.random(...)` / `rnd(...)`, `ln.randomize` / `rset` | seed deterministically (e.g. `random.Random(kLine.idxInSong)`) or populate stops being idempotent — the run-twice check will catch you |
| `ln.shapes.*` | run the Lua once and paste the resulting drawing strings as constants, or port the small generator functions |
