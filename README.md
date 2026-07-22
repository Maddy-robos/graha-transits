# Graha Transits — Sidereal (Lahiri)

A standalone tool to look up **transits (gochara), retrogression, and combustion**
for the nine grahas, computed with the **Swiss Ephemeris** (the same engine
Jagannatha Hora uses) in the **sidereal zodiac with standard Lahiri (Chitrapaksha)
ayanamsa** and **mean nodes**.

## Files

| File | Purpose |
|------|---------|
| `generate_transits.py` | Computes all events from the ephemeris → `transits.json` |
| `transits.json` | Pre-computed events, 2026–2126 |
| `index.html` | The viewer UI — loads `transits.json` at runtime (or drop it in). Has a `__DATA__` slot the build fills. |
| `build_site.py` | Bakes `transits.json` into `index.html` → self-contained `graha-transits.html` |
| `graha-transits.html` | The finished, double-clickable site (data embedded) |
| `viewer_template.html` | Legacy viewer, superseded by `index.html`; no longer used by the build |

## Just use it

Two ways to view:

- **Double-click `graha-transits.html`** — self-contained, data embedded, no server or internet needed.
- **Open `index.html`** — same viewer, but it loads `transits.json` separately: it auto-loads when served over HTTP (e.g. a static host), and when opened straight from disk it shows a drop zone so you can pick `transits.json` manually.

Either way, filter by year and month, toggle grahas on/off, switch timezone (default IST),
toggle rasi names between Sanskrit and English, and flip light / dark.

The **Gochara** panel shows where the slow grahas (Guru, Shani, Rahu, Ketu) sit and the rasis
they aspect by drishti, plus the **double transit** — rasis influenced by *both* Guru and Shani
at once (whether by sitting or by aspect):

- **Guru (Jupiter):** drishti on the 5th / 7th / 9th rasi from where it sits.
- **Shani (Saturn):** 3rd / 7th / 10th when direct; reversed to the 11th / 7th / 4th when retrograde.
- **Rahu / Ketu:** three aspects — the 5th, the 9th, and one rasi *behind* (odd signs) / *ahead*
  (even signs). E.g. Rahu in Aries aspects Leo (5th), Sagittarius (9th), Pisces (one behind).

("Nth from" counts inclusively, Jyotish-style: the 1st rasi from a graha is its own rasi.)

The double transit is **recomputed per sub-period**, not once for the whole view: it changes
whenever Guru or Shani changes sign, or Shani turns retrograde/direct (which reverses its drishti),
so each stable period is listed with its own date range and triggering event.

## Rebuild from scratch

```
pip install pyswisseph
python generate_transits.py --start 2026 --end 2126   # ~1 minute, writes transits.json
python build_site.py                                    # writes graha-transits.html
```

## Change settings

Edit `generate_transits.py`:

- **Ayanamsa** — `swe.set_sid_mode(swe.SIDM_LAHIRI)`. Swap for `SIDM_TRUE_CITRA`,
  `SIDM_KRISHNAMURTI`, etc. to match a different JHora setting.
- **Nodes** — `swe.MEAN_NODE` → `swe.TRUE_NODE` for true Rahu/Ketu.
- **Combustion orbs** — the `COMBUST_ORB` table (degrees, direct / retrograde).
  Classical values are used; Mercury and Venus have tighter orbs while retrograde.

## How events are found

For each graha the year range is scanned in small time steps, then each detected
crossing is refined to the second by bisection:

- **Ingress** — the sidereal sign index `floor(lon / 30)` changes.
- **Station** — the longitude *speed* crosses zero (retrograde ↔ direct).
- **Combustion** — the angular gap to the Sun crosses the graha's orb.

All times are stored in **UTC**; the viewer converts to the selected timezone.

## Validation notes

- Sun → Capricorn lands on 14–16 Jan every year (Makara Sankranti) — confirms
  Lahiri is configured correctly.
- Combustion counts match each planet's synodic period (e.g. Venus ≈ 125 windows
  per century = one superior + one inferior conjunction per 584-day cycle).

Always spot-check a few dates against your own Jagannatha Hora settings before
relying on results — combustion conventions in particular vary between software.
