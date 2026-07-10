# Stock Aegisub Karaoke Templater

The templater that ships with Aegisub (`kara-templater.lua`, the "Apply karaoke
template" macro).

## Sources

- Reference docs (complete and reliable for this templater):
  https://aegisub.org/docs/latest/automation/karaoke_templater/ — subpages
  `declaring_template_and_code_lines`, `template_modifiers`,
  `inline_variables`, `code_lines_and_blocks`, `code_execution_environment`,
  `template_execution_rules_and_order`.
- Source of truth: `automation/autoload/kara-templater.lua` in the
  `TypesettingTools/Aegisub` GitHub repo (fetch via GitHub MCP
  `get_file_contents` if the docs are ambiguous).

## Recognizing it

- Effect fields like `template pre-line`, `template line`, `template syl`,
  `template furi`, `code once`, `code line`, `code syl`.
- Modifiers `all`, `fx <name>`, `fxgroup <name>`, `loop n` (numeric, unnamed).
- **No** `mixin` components (that's 0x) and **no** `lsyl`/`lword`/`lchar`
  keywords (those are karaOK). `template pre-line` appearing anywhere is a
  strong stock signal — karaOK removed that keyword.
- A `code once` line doing `ln = _G.require "ln.kara"` only means the karaOK
  *library* is loaded; the templater may still be stock. Check the keywords.

## Input selection and file lifecycle

- Processes non-comment lines with a **blank or `karaoke`** Effect, plus
  Comment lines with `karaoke` in the Effect. Everything else is skipped.
- After applying: each input line is turned into a Comment with Effect
  `karaoke`; generated lines get Effect `fx`. Reruns delete `fx` lines and
  regenerate.
- A stock-templated file therefore usually already has its source as
  `Comment` + `karaoke` — exactly what the lyricsheets adapter wants. Delete
  the old `fx` lines along with the template/code comments when preparing the
  `.kfx.ass`.

## Classes — the `pre-line` vs `line` trap

| Stock class | Behavior | lyricsheets equivalent |
|---|---|---|
| `code once` | run once, before everything | module-level constants |
| `code line` / `code syl` / `code furi` | run per matching line / syl / furi | captured state or helpers (see reference.md on `code line` order) |
| `template pre-line [name]` | runs **once per line**, one output event, template text prepended, line text kept | `template line` |
| `template line [name]` | runs **once per syllable** but emits **one output event**, with the evaluated template text inserted before each syllable; named variants concatenate in file order | `template line notext` + a helper that builds the whole text as `{tags}syl{tags}syl…` blocks |
| `template syl` | one output event per syllable | `template syl` |
| `template syl` + `char` modifier | per-character pseudo-syllables | `template char`, or per-char blocks in one event |
| `template furi` / `syl furi` | furigana events | **no lyricsheets support** — port manually or record as an intentional deviation |

Do not skim past this: stock `template line` is *not* a per-line template.
Reading it as one silently drops every per-syllable tag.

## Modifiers

- `all` — match any style (default: template's own Style must equal the
  input line's style). Map to one lyricsheets `Template` per output style.
- `char` — per-character instead of per-syllable.
- `multi` — per-highlight in multi-highlight (`#`) timed karaoke.
- `fx <name>` — only syls whose inline-fx matches → branch on `kSyl.inlineFx`.
- `fxgroup <name>` — template belongs to a group; a `code` line can gate it
  with `fxgroup.name = <bool>`. Port as a helper condition; capture what the
  gating code computed if it is stateful.
- `keeptags` — keep the source line's override tags in the output. The
  lyricsheets adapter does not carry source tags through; capture any needed
  tag values into migration data.
- `noblank` / `notext` — same meanings as lyricsheets' modifiers.
- `repeat n` / `loop n` — run the template n times (`$j`, `$maxj`;
  `maxloop(newmax)` to change dynamically). lyricsheets has **no loops**:
  unroll into n `Template` entries, or compute the combined output (e.g. a
  full `\t` chain) inside one helper.

## Inline variables

Case-insensitive. Line: `$layer`, `$lstart`, `$lend`, `$ldur`, `$lmid`,
`$style`, `$actor`, `$margin_*`, `$syln`, `$li`, `$lleft`, `$lcenter`,
`$lright`, `$ltop`, `$lmiddle`, `$lbottom`, `$lx`, `$ly`, `$lwidth`,
`$lheight`. Syllable: `$sstart`, `$send`, `$smid` (line-relative), `$sdur`
(ms), `$skdur` (cs), `$si`, `$sleft`, `$scenter`, `$sright`, `$stop`,
`$smiddle`, `$sbottom`, `$sx`, `$sy`, `$swidth`, `$sheight` (absolute).
"Automatic" variants (`$start`, `$end`, `$dur`, `$kdur`, `$i`, `$x`, `$y`,
`$center`, …) resolve to the line or syl flavor depending on template class.
Loop: `$j`, `$maxj`.

- Most names carry over directly to lyricsheets inline variables
  (`KObject.inline_var` in `lyricsheets/models/karaoke.py`).
- Stock rounds position variables to whole pixels; lyricsheets keeps float
  precision. Harmless, but list it as an intentional deviation.
- `$li` counts input lines *in processing order for that run* — it depends on
  which lines the templater accepted. Capture `$li`-derived values from an
  untouched copy (see reference.md quirks); never infer them.
- Note the karaskel struct vs inline-var mismatch: the Lua field
  `syl.center` is line-relative, while `$scenter` is absolute. lyricsheets
  `kSyl.center` is absolute.

## tenv functions

- `retime(mode, startadjust, endadjust)` — modes `abs`/`set`, `preline`,
  `line`, `start2syl`, `presyl`, `syl`, `postsyl`, `syl2end`, `postline`,
  `sylpct`. The lyricsheets `retime` helper supports **all** of these (plus
  char modes), same names.
- `relayer(n)` — layer is per-`Template` in lyricsheets; give each variant its
  own `Template.compile(..., layer)`.
- `restyle(name)` — no lyricsheets equivalent; use one `Template` per output
  style.
- `maxloop(n)` / `loopctl(j, maxj)` — see loop note above.
- `remember(name, value)` / `remember_if(name, value, cond)` /
  `recall.name` or `recall(name, default)` — cross-template state, usually
  used to compute something in an early template and reuse it in a later one
  (e.g. randomized values shared between layers). Port as a Python dict cached
  by a stable song-local key, and check what order the templates ran in before
  assuming which one "writes" first.

## Execution order

1. All `code once` lines, in file order.
2. For each accepted input line, in file order: matching `code line` +
   `template line`/`pre-line` components, then per-syl `code syl` +
   `template syl`, then furi.
3. Style matching: a component runs only for input whose Style equals the
   component line's Style, unless `all` is set. (Exact match — not the
   substring matching karaOK's `style` modifier does.)
