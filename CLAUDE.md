# CLAUDE.md — Graha Transits

Guidance for Claude Code (and humans) working in this repo.

## What this is
A standalone, **static** Vedic-astrology tool: sidereal (Lahiri) transits, retrogression,
combustion, **drishti** (graha aspects), and the **Guru+Shani double transit** for the nine
grahas, 2026–2126. Computed with the Swiss Ephemeris. No backend — pure HTML + JS + one JSON.

## Pipeline / architecture
```
generate_transits.py --(Swiss Ephemeris)--> transits.json  (all events, stored UTC)
transits.json + index.html --(build_site.py)--> graha-transits.html  (data embedded)
```
- `generate_transits.py` — ephemeris scan → `transits.json`. Lahiri ayanamsa, mean nodes.
- `transits.json` — precomputed `ingresses` / `stations` / `combustions` per graha (UTC ISO).
- `index.html` — **the viewer and the source of truth for UI**. Single file, inline CSS/JS.
  Loads `transits.json` at runtime (`fetch`), with a drag-drop fallback. Has an inert
  `#embedded-data` slot + a bootstrap that uses baked-in data if present, else fetches.
- `build_site.py` — bakes `transits.json` into index.html's `#embedded-data` slot →
  `graha-transits.html` (self-contained, double-clickable, offline).
- `graha-transits.html` — generated offline build. **Never hand-edit** — run `build_site.py`.
- `viewer_template.html` — LEGACY, superseded by index.html; not used by the build.
- `backup/` — snapshots of prior versions (e.g. `v1-pre-ux-redesign/`).

**Edit `index.html`, then rebuild:** `python build_site.py`.

## Rebuild from scratch
```
pip install pyswisseph
python generate_transits.py --start 2026 --end 2126   # ~40s → transits.json
python build_site.py                                   # → graha-transits.html
```

## Jyotish calculation rules (verified — DO NOT regress)
Drishti = graha aspects, as **inclusive** sign-offsets (1st = same rasi = +0; Nth = +(N−1)).
Code: `drishtiOffsets(pl, s, retro)`, `s` = 0-based sign index (Aries=0 → rasi 1).
- **Jupiter (Guru):** 5th/7th/9th → `+4,+6,+8`. Motion-independent.
- **Saturn (Shani):** direct 3rd/7th/10th → `+2,+6,+9`; **retrograde reversed** to 11th/7th/4th
  → `+10,+6,+3`. Needs `motionAtMs()` for retro state.
- **Rahu/Ketu:** THREE aspects — 5th(`+4`), 9th(`+8`), **plus** one rasi behind in odd signs
  (`+11`) / ahead in even signs (`+1`). Odd sign = odd rasi number = `s` even (Aries=1).
  e.g. Rahu in Aries → Leo(5th), Sagittarius(9th), Pisces(1 behind).

**Double transit** = rasis under BOTH Guru and Shani, where each graha's influence set =
{its rasi} ∪ {its drishti rasis}; the double transit is the intersection. Nodes NOT involved.
It is **time-varying**: recomputed/segmented at every Guru sign change, Shani sign change, and
Shani station (retro/direct). Code: `doubleTransitSegments(winStart, winEnd)`. (Guru stations
are not cut points — Guru's drishti is motion-independent.)

**NEVER sample one instant to describe a period.** Every graha state shown for a *window*
(sign, motion, drishti, combustion) must be segmented, not sampled — the window midpoint was
used once and silently misreported Shani's drishti for weeks after each station. Two clocks,
deliberately kept apart:
- Hero (`renderHero`) — the real clock, `Date.now()`. One instant, filter-independent.
- Gochara cards (`grahaSegments(pl, s, en)`) — cuts the window at that graha's OWN ingresses
  and stations, so sign/motion/drishti are exact inside every row. Neighbouring rows fold when
  they'd render identically (same rasi + same drishti); folding across a station sets
  `mixed`, which suppresses the motion pill and moves the dates to a `retroWindows()`
  footnote (this is why Guru shows 3 rows by rasi, not 5). Combustion is a footnote with real
  dates, never a pill. A window with nothing changing renders the plain one-state card.
- Both agree by construction: the row containing `Date.now()` is chipped `now` and must match
  the hero on rasi, motion and drishti.
- The same rule binds the phala layer: **bhava** is safe to show for a period (it follows only
  the graha's own rasi, constant within a `grahaSegments` row), but **vedha is not** — it turns
  on and off with the other grahas. So period rows use `bhChipsSign()` (bhava only) while
  instant readouts (`renderHero`, `renderPhala`) use `bhChips()` (bhava + live vedha), and the
  phala calendar draws vedha as its own time-segmented underbar.

### Gochara phala — bhava favourability + vedha (verified — DO NOT regress)
Reckoned from the user's **natal Moon rasi** (classical Chandra gochara) and, as a second
reading, from the **Lagna**. `bhava(signIdx, refIdx)` — the reference rasi itself is the 1st.
- `FAV[graha]` — auspicious bhavas. Everything else is inauspicious.
  Sun `3,6,10,11` · Moon `1,3,6,7,10,11` · Mars `3,6,11` · Mercury `2,4,6,8,10,11` ·
  Jupiter `2,5,7,9,11` · Venus `1,2,3,4,5,8,9,11,12` · Saturn `3,6,11` · Rahu/Ketu `3,6,10,11`.
- `FAVQ` — **qualified** favourables from the node texts: Rahu `2,7` (if well-aspected),
  Ketu `12` (moksha). Rendered amber, never counted as plain auspicious.
- `VEDHA[graha]` — maps each auspicious bhava → the bhava that **obstructs** it. If any other
  graha occupies that bhava the good result is blocked (red dot / red underbar). Positionally
  paired with `FAV`, e.g. Venus `1→6, 2→7, 3→10, 4→9, 5→3, 8→5, 9→1, 11→8, 12→2`.
- Exceptions: **Surya ↔ Shani** and **Chandra ↔ Budha** never obstruct each other (`NOVEDHA`);
  **Rahu/Ketu neither cause nor suffer vedha** (`BLOCKERS` excludes the nodes, `VEDHA` empty).
- Vedha applies **only to an otherwise-auspicious** bhava — it blocks good, it does not add bad.

Code: `phalaAt(pl, ms, refIdx, pos)` → `{si, b, state, note, vedhaHouse, block}` where `state`
is `fav | blocked | qual | unfav`. `refs()` returns the reference rasis the user has set
(`state.moon` / `state.lagna`, `-1` = unset, persisted in `localStorage` as `gt.moon`/`gt.lagna`).
Verified: the shipped tables were diffed against the source tables cell-by-cell (all 1296
graha×reference×position combinations), plus synthetic tests for both exception pairs and the
node rules, plus a 100-year invariant sweep.

### Touch / narrow-screen handling (DO NOT regress)
`title` tooltips never fire on touch, and the wide grids get squeezed to a smear on a phone.
Both are handled generically:
- **Tap-for-details.** Anything carrying a `title` also carries `data-tip` with the same text —
  use `setTip(el, s)` for created elements and `tipAttr(s)` inside innerHTML (it escapes and
  emits both attributes). One delegated click listener drives the `#tip` popover; it flips
  above/below the target, clamps to the viewport, and closes on outside click / Escape /
  scroll. Native hover still works on desktop. Newlines in the text are real newlines
  (`white-space:pre-line`).
- **Content-driven horizontal pan.** `#grid` and `#pcgrid` sit inside `.gscroll`.
  `renderBoard` / `renderPhalaCal` set `--panw` from the densest selected row (~22px per board
  mark, ~15px per phala segment, capped at 3000px); CSS applies it as `min-width`, so a grid
  pans **only** when squeezing would make it unreadable — at any viewport width. The graha
  column is `position:sticky` so it stays pinned while panning. Phones additionally get a
  760px floor. `.swipehint` is toggled on by `syncPanHints()` from real overflow, never by a
  media query. `.mk::before` grows the marker hit area to finger size on mobile.
- **Segment labels are measured, not guessed.** `labelPhalaSegs()` reads one band's pixel
  width after layout and labels only segments ≥13px (all reads before any writes). It must be
  re-run whenever the section becomes visible — hence the `onOpen` callback on `mkToggle` and
  the `resize` listener. A percentage threshold does NOT work here: `--panw` changes the band
  width by up to 10×.

**Performance:** `signAtMs` and `ingressesIn` are binary searches over a per-graha index
(`SIDX`, built in `buildEvents`); `Intl.DateTimeFormat` instances are memoised per timezone in
`dtf()`. Both matter — the phala calendar asks for thousands of positions and tooltip dates per
render (a full-year, all-9-graha render went 1075 ms → ~70 ms). Keep them.

## Product decisions
- **Claude Design** (claude.ai/design project `d9b41938-…`) is **design reference ONLY**, never
  the source of math. Its index.html carries outdated/buggy calc — don't re-import blindly.
- `index.html` fetches `transits.json`; `graha-transits.html` is the embedded offline build.
- Fonts (Caprasimo, Figtree) load from Google Fonts with system fallbacks (works offline).
- **Defaults on load:** current year (from the clock, clamped to data range), whole-year view,
  only the slow grahas selected (Jupiter, Saturn, Rahu, Ketu). Sanskrit rasi names; light theme.
  **Timezone auto-detected from the browser** (`detectTZ` via `Intl` — free, no permission, offline;
  legacy aliases like `Asia/Calcutta`→`Asia/Kolkata` canonicalized; falls back to IST), with a
  curated ~33-zone worldwide picker (`TZS`) that pins the detected zone; IST always available.
  Times use `tzAbbr(ms)` (DST-correct via `Intl`, with an `IST` override for India). Location is
  NOT otherwise used — gochara is geocentric, so transits are identical worldwide; only the display
  clock changes. Users can toggle any of these.
- **Natal chart input** (Moon rasi + Lagna) sits at the very top, above the hero. Both are
  optional and independent: set only the Moon and every phala reading shows one row/band; set
  both and everything shows two (☾ Moon first — it is the classical basis — then ↑ Lagna). With
  neither set the phala section shows a call-to-action and the phala calendar hides itself.
  Stored in `localStorage` only; nothing leaves the browser.
- **Hosting: LIVE on GitHub Pages** → https://maddy-robos.github.io/graha-transits/
  Serves `main` at root path, HTTPS enforced, no custom domain. **Any push to `main` redeploys
  the public site** — so `main` is production; commit there deliberately.

## Status
**Done:** ephemeris generator; transits.json (2026–2126); runtime-fetch viewer + offline build
pipeline; Sanskrit/English rasi toggle; drishti + time-segmented double-transit engine (verified
against user edge cases); sensible defaults.

**UX redesign — DONE** (lower the learning curve, usable at a glance):
- [x] "Right now" hero (`renderHero` + `dtAt`/`nextSlowChange`) — today's positions, each graha's
  motion (direct/retrograde) & combustion status (`statusTags`/`combustAt`/`motionLabel`; Rahu/Ketu
  are always retrograde), the current double transit, and the next-change date. Always reflects the
  real clock, independent of filters.
- [x] Plain-language notation — "sits" / "aspects" instead of `ʘ`.
- [x] "How to read this" collapsible panel — glyph key + Vedic glossary.
- [x] Clearer hierarchy — hero → help → explore controls → Gochara/double-transit (primary) →
  Transit calendar board (collapsible, open) → Timeline (collapsible, closed).
- [x] Labelled board marks (destination rasi # for transits, R/D for stations).
- [x] Backup of the previous version at `backup/v1-pre-ux-redesign/`.
- [x] Period-accurate Gochara cards (`grahaSegments`/`retroWindows`) — replaced midpoint
  sampling, which showed Shani direct while the hero showed it retrograde. See the calc rules.

**Gochara phala — DONE, shipped:**
- [x] Natal **Moon rasi + Lagna** input bar at the top (`#moonrasi` / `#lagnarasi`, persisted).
- [x] **Gochara Phala · right now** — a card per graha: current rasi, the bhava from each
  reference, the verdict (`✔ auspicious` / `⊘ blocked` / `~ qualified` / `✕ inauspicious`), a
  red dot when a vedha is active, and a sentence naming the blocking graha and its bhava.
  Above it, a score strip per reference (`renderPhala`).
- [x] **Phala calendar** — collapsible band per graha across the selected period, one segment
  per sign held, coloured by verdict, labelled with the bhava; vedha drawn separately as a red
  underbar because it switches on/off with the other grahas (the Moon can block for two days).
  `bhavaSegments` / `vedhaSegments` / `renderPhalaCal`.
- [x] Bhava chips in the hero (`bhChips`, with live vedha) and on every `grahaSegments` row of
  the gochara cards (`bhChipsSign`, bhava only); verdict chips on every timeline ingress
  (`ingressPhala`).
- [x] Reference table of all `FAV`/`VEDHA` pairs in the "How to read this" panel (`renderRefTable`).
- [x] Desktop reviewed and signed off by the user.
- [x] **Mobile pass** (user feedback: hover tooltips dead on touch, wide grids squeezed) —
  tap-for-details popover + content-driven horizontal pan with a pinned graha column.
  See "Touch / narrow-screen handling" above.

**Deployed:** live on GitHub Pages (see Hosting above). The live site needs only
`index.html` + `transits.json`; `graha-transits.html` is the offline single-file copy.

## Verifying UI changes
The in-app browser preview **caps proxied responses at ~1 MB**, so it can't fetch the full
1.9 MB `transits.json` (real browsers handle it fine). To test locally, generate a SMALL
dataset and serve it:
```
python generate_transits.py --start 2026 --end 2029 --out <scratch>/transits.json
cp index.html <scratch>/ ; python -m http.server 8100 --directory <scratch>
```
Load `http://localhost:8100/index.html`. Verify calc by calling the page's own functions
(`drishtiOffsets`, `doubleTransitSegments`, `signAtMs`, `motionAtMs`) via the console/JS tool.
