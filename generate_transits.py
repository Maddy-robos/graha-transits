#!/usr/bin/env python3
"""
Vedic transit / retrogression / combustion generator.

Engine : Swiss Ephemeris (pyswisseph)  -- same engine Jagannatha Hora uses.
Zodiac : Sidereal, standard Lahiri (Chitrapaksha) ayanamsa.
Output : transits.json  (all times stored as UTC ISO-8601; the viewer converts
         to a chosen timezone, default IST +05:30).

Events produced per graha:
  - ingresses    : sign changes (gochara), refined to the second
  - stations     : retrograde / direct turns (where speed crosses zero)
  - combustions  : intervals when the graha is within its classical orb of the Sun
                   (Mercury & Venus use the tighter orb while retrograde)

Setup:
  pip install pyswisseph

Usage:
  python3 generate_transits.py --start 2026 --end 2126 --out transits.json
"""

import argparse
import datetime as dt
import json

import swisseph as swe

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
         "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

# graha -> (swisseph id, coarse scan step in HOURS)
# Step is chosen well below the boundary-crossing time so we never skip an event.
PLANETS = {
    "Sun":     (swe.SUN,       6),
    "Moon":    (swe.MOON,      6),
    "Mars":    (swe.MARS,      12),
    "Mercury": (swe.MERCURY,   6),
    "Jupiter": (swe.JUPITER,   24),
    "Venus":   (swe.VENUS,     6),
    "Saturn":  (swe.SATURN,    24),
    "Rahu":    (swe.MEAN_NODE, 24),   # mean node: always retrograde, no stations
    # Ketu is derived from Rahu (Rahu + 180) after the run.
}

# Classical combustion orbs in degrees: (direct, retrograde)
COMBUST_ORB = {
    "Moon":    (12.0, 12.0),
    "Mars":    (17.0, 17.0),
    "Mercury": (14.0, 12.0),
    "Jupiter": (11.0, 11.0),
    "Venus":   (10.0,  8.0),
    "Saturn":  (15.0, 15.0),
}

FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED | swe.FLG_SIDEREAL


# ---------------------------------------------------------------------------
# Ephemeris helpers
# ---------------------------------------------------------------------------

def jd_to_iso(jd):
    """Julian day (UT) -> UTC ISO-8601 string to the second."""
    y, m, d, h = swe.revjul(jd, swe.GREG_CAL)
    hour = int(h)
    minute = int((h - hour) * 60)
    second = int(round(((h - hour) * 60 - minute) * 60))
    # normalise possible rounding overflow
    base = dt.datetime(y, m, d) + dt.timedelta(hours=hour, minutes=minute, seconds=second)
    return base.strftime("%Y-%m-%dT%H:%M:%SZ")


def lon_speed(jd, pid):
    r, _ = swe.calc_ut(jd, pid, FLAGS)
    return r[0], r[3]          # longitude, longitude speed (deg/day)


def sign_index(lon):
    return int(lon // 30) % 12


def sun_lon(jd):
    r, _ = swe.calc_ut(jd, swe.SUN, FLAGS)
    return r[0]


def sep_from_sun(lon, slon):
    """Shortest angular separation in longitude, 0..180."""
    d = abs(lon - slon) % 360.0
    return 360.0 - d if d > 180.0 else d


def bisect(f, t0, t1, iters=45):
    """Return t in [t0,t1] where f changes sign (f(t0) and f(t1) differ)."""
    a, b = t0, t1
    fa = f(a)
    for _ in range(iters):
        m = 0.5 * (a + b)
        fm = f(m)
        if (fm > 0) == (fa > 0):
            a, fa = m, fm
        else:
            b = m
    return 0.5 * (a + b)


# ---------------------------------------------------------------------------
# Per-planet event scan
# ---------------------------------------------------------------------------

def scan_planet(name, pid, step_hours, jd_start, jd_end):
    ingresses, stations, combustions = [], [], []
    step = step_hours / 24.0

    orb = COMBUST_ORB.get(name)  # None for Sun and Rahu

    # initial sample
    jd = jd_start
    lon0, spd0 = lon_speed(jd, pid)
    sign0 = sign_index(lon0)
    in_combust = False
    combust_start = None
    if orb is not None:
        slon = sun_lon(jd)
        cur_orb = orb[1] if spd0 < 0 else orb[0]
        in_combust = sep_from_sun(lon0, slon) < cur_orb
        if in_combust:
            combust_start = jd

    while jd < jd_end:
        jd_next = min(jd + step, jd_end)
        lon1, spd1 = lon_speed(jd_next, pid)
        sign1 = sign_index(lon1)

        # ---- ingress (sign change) --------------------------------------
        if sign1 != sign0:
            target_sign = sign1

            # refine: find first instant the new sign holds
            a, b = jd, jd_next
            for _ in range(45):
                m = 0.5 * (a + b)
                lm, _ = lon_speed(m, pid)
                if sign_index(lm) == target_sign:
                    b = m
                else:
                    a = m
            tc = b
            lc, sc = lon_speed(tc, pid)
            ingresses.append({
                "utc": jd_to_iso(tc),
                "from": SIGNS[sign0],
                "to": SIGNS[target_sign],
                "retrograde": sc < 0,
            })

        # ---- station (speed sign change) --------------------------------
        if name != "Rahu" and (spd0 < 0) != (spd1 < 0):
            def f_spd(t):
                _, s = lon_speed(t, pid)
                return s
            tc = bisect(f_spd, jd, jd_next)
            lc, _ = lon_speed(tc, pid)
            kind = "direct" if spd1 >= 0 else "retrograde"  # sign we turn INTO
            stations.append({
                "utc": jd_to_iso(tc),
                "type": kind,       # 'retrograde' = begins retro, 'direct' = resumes direct
                "sign": SIGNS[sign_index(lc)],
                "deg": round(lc % 30, 3),
            })

        # ---- combustion -------------------------------------------------
        if orb is not None:
            slon1 = sun_lon(jd_next)
            cur_orb1 = orb[1] if spd1 < 0 else orb[0]
            now_combust = sep_from_sun(lon1, slon1) < cur_orb1

            if now_combust != in_combust:
                # refine crossing of (orb - separation)
                def f_comb(t):
                    l, s = lon_speed(t, pid)
                    o = orb[1] if s < 0 else orb[0]
                    return o - sep_from_sun(l, sun_lon(t))
                tc = bisect(f_comb, jd, jd_next)
                if now_combust:                 # entering combustion
                    combust_start = tc
                else:                           # leaving combustion
                    if combust_start is not None:
                        lm, _ = lon_speed(0.5 * (combust_start + tc), pid)
                        combustions.append({
                            "start_utc": jd_to_iso(combust_start),
                            "end_utc": jd_to_iso(tc),
                            "sign": SIGNS[sign_index(lm)],
                        })
                    combust_start = None
                in_combust = now_combust

        jd, lon0, spd0, sign0 = jd_next, lon1, spd1, sign1

    # close an open combustion window at the range edge
    if orb is not None and in_combust and combust_start is not None:
        combustions.append({
            "start_utc": jd_to_iso(combust_start),
            "end_utc": jd_to_iso(jd_end),
            "sign": SIGNS[sign_index(lon0)],
        })

    return ingresses, stations, combustions


def derive_ketu(rahu_ingresses):
    """Ketu = Rahu opposite. Sign index + 6."""
    out = []
    for ev in rahu_ingresses:
        fi = (SIGNS.index(ev["from"]) + 6) % 12
        ti = (SIGNS.index(ev["to"]) + 6) % 12
        out.append({"utc": ev["utc"], "from": SIGNS[fi], "to": SIGNS[ti],
                    "retrograde": ev["retrograde"]})
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=2026)
    ap.add_argument("--end", type=int, default=2126)
    ap.add_argument("--out", default="transits.json")
    args = ap.parse_args()

    swe.set_sid_mode(swe.SIDM_LAHIRI)

    jd_start = swe.julday(args.start, 1, 1, 0.0)
    jd_end = swe.julday(args.end, 1, 1, 0.0)

    data = {
        "meta": {
            "engine": "Swiss Ephemeris (pyswisseph)",
            "ayanamsa": "Lahiri (Chitrapaksha)",
            "zodiac": "sidereal",
            "node": "mean",
            "time_zone_of_storage": "UTC",
            "range": {"start": args.start, "end": args.end},
            "combustion_orbs_deg": COMBUST_ORB,
            "generated_utc": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "planets": {},
    }

    rahu_ing = None
    for name, (pid, step) in PLANETS.items():
        ing, sta, com = scan_planet(name, pid, step, jd_start, jd_end)
        data["planets"][name] = {"ingresses": ing, "stations": sta, "combustions": com}
        if name == "Rahu":
            rahu_ing = ing
        print(f"{name:8s}  ingresses={len(ing):4d}  stations={len(sta):4d}  combustions={len(com):4d}")

    # Ketu derived from Rahu
    data["planets"]["Ketu"] = {
        "ingresses": derive_ketu(rahu_ing),
        "stations": [],
        "combustions": [],
    }
    print(f"{'Ketu':8s}  ingresses={len(data['planets']['Ketu']['ingresses']):4d}  (derived from Rahu)")

    with open(args.out, "w") as fh:
        json.dump(data, fh, separators=(",", ":"))
    print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
