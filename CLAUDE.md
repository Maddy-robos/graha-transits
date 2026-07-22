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

## Product decisions
- **Claude Design** (claude.ai/design project `d9b41938-…`) is **design reference ONLY**, never
  the source of math. Its index.html carries outdated/buggy calc — don't re-import blindly.
- `index.html` fetches `transits.json`; `graha-transits.html` is the embedded offline build.
- Fonts (Caprasimo, Figtree) load from Google Fonts with system fallbacks (works offline).
- **Defaults on load:** current year (from the clock, clamped to data range), whole-year view,
  only the slow grahas selected (Jupiter, Saturn, Rahu, Ketu). Sanskrit rasi names; light theme;
  IST timezone. Users can toggle any of these.
- **Hosting plan:** free static host (GitHub Pages preferred; Netlify Drop = fastest). No custom
  domain needed, low traffic. HTTPS from the host; app is read-only/static.

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

**Next:** deploy to GitHub Pages (free static hosting) — pending user go-ahead. Only
`index.html` + `transits.json` are needed for the live site (or the single `graha-transits.html`).

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
