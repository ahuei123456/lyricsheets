# The0x539's KaraTemplater (0x.KaraTemplater)

Deliberately **not** compatible with stock/karaOK templates.

## Sources

Fetch via GitHub MCP (`get_file_contents`, owner `The0x539`, repo
`Aegisub-Scripts`) when this doc or the upstream doc is silent:

- `doc/0x.KaraTemplater.md` — upstream docs. **Incomplete**: the "Execution
  Order", "Inline Expressions", and "Inline Variables" sections are TODOs.
- `src/0x.KaraTemplater.moon` — MoonScript source, the real authority.
  Key functions: `eval_inline_var` (the `$` variables), `should_eval`
  (filter semantics), `apply_templates` (execution order), `util` and
  `template_env` (available functions).

The source-derived facts below were extracted at commit `15518cb` (2026-07);
re-check the source if behavior seems off — the script is actively maintained.

## Input selection

Two conditions (see `collect_template_input`):

1. Effect field **exactly** `kara` or `karaoke` (Comment or Dialogue both
   accepted; accepted Dialogue inputs are converted to Comments on run).
2. The line's **style must be one some component is attached to** (or named
   via a `style` modifier, or anything if any component says `anystyle`).
   Input in a style no component cares about is ignored entirely.

Generated output gets Effect `fx` (non-comment); reruns delete those.

The lyricsheets adapter instead matches case-insensitive Effect *substrings*
(`KaRaOkE`, `karaoke too long`, …) and selects by romaji/english style names —
at the intentional-deviations checkpoint, audit lines lyricsheets accepts that
0x skipped.

- The **actor field is a space-separated list of tokens**, mixed and matched
  by `actor`/`noactor` modifiers. lyricsheets gives you the raw Name field as
  `kLine.startActor` (and derives `isSecondary` from a `2` token); replicate
  multi-token matching by splitting `startActor` in a helper.

## Recognizing it

- `mixin` components in Effect fields — 0x's defining feature.
- Named loops (`loop foo 3`), `if`/`unless`/`cond`, `actor`/`noactor`/
  `t_actor`, `anystyle`, `layer`, `sylfx`, `nok0`, `prefix` modifiers.
- Input lines whose Effect is exactly `kara`.
- Auto-loads `ln` (`ln.kara`, see `templaters/karaok.md`) and `colorlib`
  (`0x.color`) without an explicit `require`.

## Components

`code` / `template` / `mixin` × class `once` (code only) / `line` / `syl` /
`word` / `char`.

- `code` — runs its text as Lua. `code line` runs per accepted input line
  *when its filters match* and mutates the shared environment — the classic
  stateful-walk hazard; see reference.md quirks.
- `template` — generates output events. One `Template.compile(text, style,
  layer)` per 0x template. There is no `word` class in lyricsheets: convert
  per-word logic to per-char blocks grouped by whitespace in a helper.
- `mixin` — modifies the output of matching `template`s (selected via
  filters, `t_actor`, `layer`, …), inserting tags before each line/syl/word/
  char *within the template's output event(s)*. lyricsheets has no mixins:
  **fold each mixin into the templates it applied to.** `mixin char`/`mixin
  syl` on a line template becomes `template line notext` + a helper that
  builds the whole text as per-char `{tags}c{tags}h…` blocks (per-char
  *events* would double-blend overlapping glows; blocks in one event don't).
  A `mixin` gated on `layer` folds into exactly the `Template`s compiled with
  that layer.

Execution order (`apply_templates`): `code once` first; then per input line
in file order: `code line` → `template line` → per word (`code word` →
`template word`) → per syl → per char. Within a group, components run in
their file order. Mixins run as part of "running a template", and which
mixin classes a template accepts depends on the template's class:

| Template class | Mixin classes applied |
|---|---|
| `line` | `line`, `word`, `syl`, `char` |
| `word` | `line`, `word`, `char` (**not** `syl`) |
| `syl` | `line`, `syl`, `char` |
| `char` | `line`, `char` |

## Modifiers

| Modifier | Meaning | Porting note |
|---|---|---|
| `style x` | also run for style `x` (default: own style only) | one `Template` per output style |
| `anystyle` | run for any style | like stock `all` |
| `actor x` / `noactor x` | (dis)interested actor tokens, OR within, AND across kinds | helper branching on `kLine.startActor` tokens |
| `t_actor x` / `no_t_actor x` | mixin-only: match the *template's* actor field | resolves statically — decide at fold-in time which templates get the mixin's tags |
| `sylfx x` / `inlinefx x` | match syl's `syl_fx` / `inline_fx` | `kSyl.inlineFx`; see syl_fx note below |
| `layer n` | mixin-only: match output's *current* layer (post-`relayer`) | fold into the matching `Template.compile(..., n)` |
| `if f` / `unless f` / `cond f` | predicate variable/function in tenv | helper branching; see "conditional output" below |
| `noblank` | skip empty *and* whitespace-only text (`is_blank or is_space`) — does **not** skip zero-duration syls | lyricsheets `noblank` |
| `nok0` | skip zero-duration syls/chars | check `kSyl.duration` in the helper |
| `multi` | per-highlight for `#`-timed karaoke (`msyl` = base syl) | port highlight-by-highlight; lyricsheets has no multi-highlight class |
| `keeptags` | keep source override tags (except `\k`) | capture needed tag values as migration data |
| `keepspace` / `nomerge` | whitespace/`}{`-merge output cosmetics | usually irrelevant; note as deviation if diffs matter |
| `notext` | don't append source text | lyricsheets `notext` |
| `loop name n` / `repeat` | named loops, `$loop_name`/`$maxloop_name`, nested in **reverse** order of appearance; mixins have separate `$mloop_*`; `maxloop(var, val)` sets counts dynamically | lyricsheets has no loops: unroll into multiple `Template`s or compute the whole result (e.g. a `\t` chain, gradient segments) in one helper |
| `prefix` | mixin output goes at line start (used for `\t(\clip)` kf-style wipes) | build the prefix tags in the line-level part of your helper |

## Conditional output: `skip()` family

`skip()`/`unskip()` discard the current output line; `mskip()`/`unmskip()`
discard one mixin iteration. lyricsheets templates always emit an event.
Options, in order of preference: restructure so the `Template` only matches
the lines that need it; branch in the helper to emit alternative tags; or
emit a fully transparent event and record it at the intentional-deviations
checkpoint.

## Inline expressions and variables

- `!expr!` is full Lua in 0x and `nil` becomes an empty string (so
  side-effect calls like `retime` are written inline). The lyricsheets `!…!`
  evaluator supports only arithmetic, calls, names, and indexing — no
  keywords or builtins — so move all logic into helpers; helpers returning
  tag strings replicate the nil-for-side-effects idiom by returning `""`.
- Evaluation order (`eval_body`): **`$` variables are text-substituted
  first, then `!expr!` blocks run** — so a `$var` inside an inline
  expression is expanded before the Lua compiles. lyricsheets does the same
  substitution trick differently; re-derive the value in the helper instead
  of relying on textual splicing.
- `syl.syl_fx` is a non-sticky variant of `syl.inline_fx` (set only on the
  syl carrying the `\-fx` tag). lyricsheets only has the sticky
  `kSyl.inlineFx`; recover syl_fx by comparing with the previous syl's value.
- `word`/`char` tables have parents (`char.syl`, `word.line`) — map to
  `kChar.kSyl`-style traversal in helpers.

### The complete `$` variable list (from `eval_inline_var`)

0x's `$` set is **much smaller than stock's** — there are no `$lstart`,
`$start`, `$x`, `$center`, etc.; positions and times come from `!expr!`
instead. Anything not listed here is a hard error. Names are lowercase-only
(matched as `%$[a-z_]+`).

| Variable | Value | lyricsheets |
|---|---|---|
| `$sylstart` / `$sylend` | syl start/end, ms, line-relative | `$sstart` / `$send` |
| `$syldur` | syl duration, ms | `$sdur` |
| `$kdur`, `$sylkdur` | `syl.duration / 10` — **fractional cs, not floored** | `$skdur` floors; use `ms(duration) / 10` in a helper to match |
| `$ldur` | line duration, ms | `$ldur` |
| `$li` | `orgline.li` = the line's **raw index in the subtitle file** at run time | capture, don't infer (see reference.md quirks) |
| `$si` / `$wi` / `$ci` | syl / word / char index of the current (or containing) object | `kSyl.i`; word/char indices via helper counting |
| `$cxf` / `$sxf` / `$wxf` | `util.xf` over chars / syls / words | the xf formula (see Functions) |
| `$loop_x`, `$maxloop_x` | template loop state/max | unrolled — constants per `Template` |
| `$mloop_x`, `$maxmloop_x` | mixin loop state/max | same |
| `$env_x` | reads tenv variable `x` | module-level state |

In a `char` context, syl-level variables resolve through `char.syl`.

## Functions

`retime(mode, s, e)` — lyricsheets `retime` covers `set`/`abs`, `preline`,
`line`, `start2syl`, `presyl`, `syl`, `postsyl`, `syl2end`, `postline` (plus
char modes). 0x-only modes you must emulate by setting `event.start`/
`event.end` in a helper:

| 0x mode | start / end |
|---|---|
| `presyl2postline` | syl start → line end |
| `preline2postsyl` | line start → syl end |
| `delta` | offsets added to the output's *current* times |
| `clamp` / `clampsyl` | clamp current times into line / syl bounds |

- `relayer(n)` — fold into per-`Template` layers.
- `set(k, v)` — tenv global assignment; module-level state in Python (respect
  the captured execution order).
- `print`/`printf` — debugging only; drop.
- `util.tag_or_default(tag, default)` / `util.fad(t_in, t_out)` — reads the
  source line's tags with a fallback: capture per-line values or use the
  default.
- `util.xf(obj, objs, field)` — normalized 0→1 position:
  `(kChar.center - first.center) / (last.center - first.center)` over
  rendered centers; return `0.0` for empty/one-char/zero-span lines.
  (`util.cx` is an old alias.)
- `util.lerp(t, v0, v1)` — plain Python.
- `util.gbc(c1, c2, interp, t)` / `util.multi_gbc(cs, …)` —
  gradient-by-character; port as a helper interpolating per char (default
  color interp is LCh via `colorlib` — match it or note the deviation).
- `util.make_grad`/`util.get_grad`/`util.get_multi_grad` — clip-based
  gradients built on loops; port as one helper emitting all `\clip` segment
  events' worth of tags, or per-char `gbc` if visually equivalent (deviation).
- `util.fbf(...)` — frame-by-frame line splitting via loops. lyricsheets has
  no fbf; prefer expressing the animation as `\t` chains, else flag it.
- `util.rand.*` (`sign`, `item`, `bool`, `choice`) and `ln.math.random` —
  0x calls `math.randomseed(os.time())` on every run, so even the *Lua*
  output differs run to run; there is no exact reference output to diff
  against. In Python, seed deterministically per line/syl (e.g.
  `random.Random((kLine.idxInSong, kSyl.i))`) — randomness breaks populate's
  run-twice idempotency check — and record the frozen randomness as an
  intentional deviation.
- `util.math.round(n)` — Python `round()` (mind banker's rounding if diffing
  outputs exactly).
- `maxloop`/`maxmloop` — see loop row above; `maxloop(var, 0)`-style skips →
  see `skip()` section.
- `colorlib` (`0x.color`): `interp_lch`, `interp_alpha`, etc. — port the
  color math or precompute palettes.
