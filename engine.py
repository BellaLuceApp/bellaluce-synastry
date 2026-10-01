"""
BellaLuce synastry engine: birth DATE + birth PLACE only (no birth time).

Nothing here is guessed. The birth place gives a time zone, which gives the exact
24-hour window (in universal time) that the birth date covers. Every point is
calculated across that whole window, so each result carries a certainty label:

  certain   holds at every moment of the birth date
  possible  holds only at some moments (depends on the unknown birth time)

Not calculated (they need a birth time): Rising sign, houses, Midheaven/IC,
Part of Fortune, sect, Moon degree, progressed Moon, astrocartography.

Requires:  pip install pyswisseph tzdata
"""
import datetime as dt
import itertools
import math
from zoneinfo import ZoneInfo

import swisseph as swe

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
ELEMENTS = ["Fire", "Earth", "Air", "Water"]          # sign index % 4
MODES = ["Cardinal", "Fixed", "Mutable"]              # sign index % 3

BODIES = {
    "Sun": swe.SUN, "Moon": swe.MOON, "Mercury": swe.MERCURY, "Venus": swe.VENUS,
    "Mars": swe.MARS, "Jupiter": swe.JUPITER, "Saturn": swe.SATURN,
    "Uranus": swe.URANUS, "Neptune": swe.NEPTUNE, "Pluto": swe.PLUTO,
    "North Node": swe.MEAN_NODE,      # mean node
    "Lilith": swe.MEAN_APOG,          # mean Black Moon Lilith
}
# Selena = Lilith + 180 and South Node = North Node + 180 are derived below.
# Chiron/Ceres/Pallas/Juno/Vesta need extra Swiss Ephemeris data files, so they
# are added only if the files are installed.
OPTIONAL = {"Chiron": swe.CHIRON}

PLANETS_10 = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn",
              "Uranus", "Neptune", "Pluto"]
SYNASTRY_POINTS = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter",
                   "Saturn", "North Node", "Selena", "Lilith"]
ASPECTS = [(0, "conjunction"), (60, "sextile"), (90, "square"),
           (120, "trine"), (180, "opposition")]

ORB_DEFAULT = 6.0   # degrees
ORB_NODE = 3.0      # any contact involving North Node or Selena
ORB_AXIS_ECHO = 5.0 # the Lilith/Selena mutual axis-mirror pattern (see below)
SAMPLES = 97        # every 15 minutes across a 24-hour window
FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED

DOMICILE = {"Sun": ["Leo"], "Moon": ["Cancer"], "Mercury": ["Gemini", "Virgo"],
            "Venus": ["Taurus", "Libra"], "Mars": ["Aries", "Scorpio"],
            "Jupiter": ["Sagittarius", "Pisces"], "Saturn": ["Capricorn", "Aquarius"]}
EXALT = {"Sun": "Aries", "Moon": "Taurus", "Mercury": "Virgo", "Venus": "Pisces",
         "Mars": "Capricorn", "Jupiter": "Cancer", "Saturn": "Libra"}


# ---------------------------------------------------------------- basics
def fmt(lon):
    lon %= 360
    return "%d°%02d' %s" % (int(lon % 30), int((lon % 1) * 60), SIGNS[int(lon // 30)])


def _jd(d_utc):
    return swe.julday(d_utc.year, d_utc.month, d_utc.day,
                      d_utc.hour + d_utc.minute / 60 + d_utc.second / 3600)


def birth_window(year, month, day, tzname):
    """Exact UT window of the birth date at the birth place, plus local noon.
    Uses the historical time zone rules (including daylight saving)."""
    tz = ZoneInfo(tzname)
    nxt = dt.date(year, month, day) + dt.timedelta(days=1)
    start = dt.datetime(year, month, day, tzinfo=tz)
    end = dt.datetime(nxt.year, nxt.month, nxt.day, tzinfo=tz)
    noon = dt.datetime(year, month, day, 12, tzinfo=tz)
    utc = dt.timezone.utc
    j0, jn, j1 = (_jd(x.astimezone(utc)) for x in (start, noon, end))
    return j0, jn, j1


def _lon_speed(body, jd):
    r = swe.calc_ut(jd, body, FLAGS)[0]
    return r[0] % 360, r[3]


def _point(body, jds, jd_noon):
    lon_n, spd_n = _lon_speed(body, jd_noon)
    lons, spds = [], []
    for j in jds:
        l, s = _lon_speed(body, j)
        lons.append(l)
        spds.append(s)
    deltas = [((l - lon_n + 180) % 360) - 180 for l in lons] + [0.0]
    samples = [lon_n + d for d in deltas]
    sign_opts = sorted({int((x % 360) // 30) for x in samples})
    retro_opts = {s < 0 for s in spds} | {spd_n < 0}
    return {"lon": lon_n, "lo": min(samples), "hi": max(samples),
            "sign": SIGNS[int(lon_n // 30)], "sign_idx": int(lon_n // 30),
            "sign_certain": len(sign_opts) == 1,
            "sign_options": [SIGNS[i] for i in sign_opts],
            "retrograde": spd_n < 0, "retro_certain": len(retro_opts) == 1,
            "speed": spd_n, "samples": samples}


def _shift(p, deg):
    q = dict(p)
    q["lon"] = (p["lon"] + deg) % 360
    q["lo"], q["hi"] = p["lo"] + deg, p["hi"] + deg
    q["sign_idx"] = int(q["lon"] // 30)
    q["sign"] = SIGNS[q["sign_idx"]]
    q["samples"] = [s + deg for s in p["samples"]]
    opts = sorted({int((s % 360) // 30) for s in q["samples"]})
    q["sign_options"] = [SIGNS[i] for i in opts]
    q["sign_certain"] = len(opts) == 1
    return q


def build_chart(name, year, month, day, tzname, place=""):
    j0, jn, j1 = birth_window(year, month, day, tzname)
    jds = [j0 + (j1 - j0) * i / (SAMPLES - 1) for i in range(SAMPLES)]
    pts = {n: _point(b, jds, jn) for n, b in BODIES.items()}
    pts["Selena"] = _shift(pts["Lilith"], 180)
    pts["South Node"] = _shift(pts["North Node"], 180)
    for n, b in OPTIONAL.items():
        try:
            pts[n] = _point(b, jds, jn)
        except Exception:
            pass  # needs the extra ephemeris files
    return {"name": name, "date": "%04d-%02d-%02d" % (year, month, day),
            "place": place, "timezone": tzname, "window_hours": round((j1 - j0) * 24, 2),
            "jd_noon": jn, "points": pts}


# ------------------------------------------------------- aspects between charts
def _orb_range(dlo, dhi, angle, n=121):
    vals = []
    for i in range(n):
        d = dlo + (dhi - dlo) * i / (n - 1)
        sep = abs((d + 180) % 360 - 180)
        vals.append(abs(sep - angle))
    return min(vals), max(vals)


def _limit(a, b):
    return ORB_NODE if ({a, b} & {"North Node", "Selena", "South Node", "Lilith"}) else ORB_DEFAULT


def contacts(A, B, names=SYNASTRY_POINTS):
    """Every aspect between A's points and B's points. Labeled certain/possible."""
    out = []
    for na, nb in itertools.product(names, names):
        pa, pb = A["points"][na], B["points"][nb]
        lim = _limit(na, nb)
        dlo, dhi = pa["lo"] - pb["hi"], pa["hi"] - pb["lo"]
        sep_noon = abs((pa["lon"] - pb["lon"] + 180) % 360 - 180)
        best = None
        for ang, aname in ASPECTS:
            mn, mx = _orb_range(dlo, dhi, ang)
            if mn > lim:
                continue
            status = "certain" if mx <= lim else "possible"
            row = {"a_point": na, "b_point": nb, "aspect": aname,
                   "orb_at_noon": round(abs(sep_noon - ang), 2),
                   "orb_best": round(mn, 2), "orb_worst": round(mx, 2),
                   "status": status}
            if best is None or mn < best["orb_best"]:
                best = row
        if best:
            out.append(best)
    out.sort(key=lambda r: (r["status"] != "certain", r["orb_at_noon"]))
    return out


def selena_node_links(A, B):
    """Selena on North Node in each direction, and whether the link is mutual."""
    c = contacts(A, B, names=["North Node", "Selena"])
    ab = [r for r in c if r["a_point"] == "Selena" and r["b_point"] == "North Node"]
    ba = [r for r in c if r["a_point"] == "North Node" and r["b_point"] == "Selena"]
    return {"A_selena_to_B_node": ab[0] if ab else None,
            "B_selena_to_A_node": ba[0] if ba else None,
            "mutual": bool(ab and ba)}


def lilith_selena_axis_echo(A, B):
    """Whether A and B's Lilith/Selena axes nearly mirror each other:
    A's Lilith landing close to B's Selena. Since Selena = Lilith + 180 for
    both people, this is mathematically the SAME fact as A's Selena landing
    close to B's Lilith -- not two independent confirmations, just the same
    axis-overlap seen from both ends. So this returns ONE finding, not two,
    to avoid it reading as double evidence.

    Uses a wider orb (ORB_AXIS_ECHO) than ordinary point contacts (ORB_NODE),
    since this is a broader "do these two axes roughly line up" pattern
    rather than a precise point-to-point aspect -- and because it's fairly
    rare at a tight orb (two independent slow points landing within a few
    degrees of each other), making it worth catching a bit more generously.

    Returns None if the axes aren't close enough to count.
    """
    a_lil, b_sel = A["points"]["Lilith"], B["points"]["Selena"]
    a_sel, b_lil = A["points"]["Selena"], B["points"]["Lilith"]

    dlo, dhi = a_lil["lo"] - b_sel["hi"], a_lil["hi"] - b_sel["lo"]
    sep_noon = abs((a_lil["lon"] - b_sel["lon"] + 180) % 360 - 180)
    mn, mx = _orb_range(dlo, dhi, 0)  # 0 deg = conjunction/overlap target
    if mn > ORB_AXIS_ECHO:
        return None

    return {
        "orb_at_noon": round(sep_noon, 2),
        "orb_best": round(mn, 2),
        "orb_worst": round(mx, 2),
        "status": "certain" if mx <= ORB_AXIS_ECHO else "possible",
        "a_lilith": {"sign": a_lil["sign"], "text": fmt(a_lil["lon"])},
        "b_selena": {"sign": b_sel["sign"], "text": fmt(b_sel["lon"])},
        "a_selena": {"sign": a_sel["sign"], "text": fmt(a_sel["lon"])},
        "b_lilith": {"sign": b_lil["sign"], "text": fmt(b_lil["lon"])},
    }


# ------------------------------------------------------------- composite
def composite(A, B, names=SYNASTRY_POINTS):
    """Midpoint (shorter arc) of each point, checked across both birth windows."""
    def mid(a, b):
        d = ((b - a + 180) % 360) - 180
        return (a + d / 2) % 360
    out = {}
    for n in names:
        pa, pb = A["points"][n], B["points"][n]
        m0 = mid(pa["lon"], pb["lon"])
        span = []
        for x, y in itertools.product(pa["samples"][::8], pb["samples"][::8]):
            span.append(((mid(x, y) - m0 + 180) % 360) - 180)
        signs = sorted({int(((m0 + s) % 360) // 30) for s in span + [0]})
        out[n] = {"lon": round(m0, 4), "text": fmt(m0),
                  "sign_certain": len(signs) == 1,
                  "sign_options": [SIGNS[i] for i in signs]}
    return out


# ----------------------------------------------------- one-person derived data
def dignity(chart):
    out = {}
    for n, doms in DOMICILE.items():
        p = chart["points"][n]
        if not p["sign_certain"]:
            out[n] = "uncertain (sign changes that day)"
            continue
        s = p["sign"]
        opp = [SIGNS[(SIGNS.index(d) + 6) % 12] for d in doms]
        if s in doms:
            out[n] = "domicile"
        elif s == EXALT[n]:
            out[n] = "exaltation"
        elif s in opp:
            out[n] = "detriment"
        elif s == SIGNS[(SIGNS.index(EXALT[n]) + 6) % 12]:
            out[n] = "fall"
        else:
            out[n] = "neutral"
    return out


def element_counts(chart):
    el, mo, skipped = dict.fromkeys(ELEMENTS, 0), dict.fromkeys(MODES, 0), []
    for n in PLANETS_10:
        p = chart["points"][n]
        if not p["sign_certain"]:
            skipped.append(n)
            continue
        el[ELEMENTS[p["sign_idx"] % 4]] += 1
        mo[MODES[p["sign_idx"] % 3]] += 1
    return {"elements": el, "modalities": mo, "excluded_uncertain": skipped}


def patterns(chart):
    names = [n for n in PLANETS_10 if n != "Moon"]
    pos = {n: chart["points"][n]["lon"] for n in names}
    sep = lambda a, b: abs((pos[a] - pos[b] + 180) % 360 - 180)
    near = lambda a, b, ang: abs(sep(a, b) - ang) <= ORB_DEFAULT
    out = {"stelliums": [], "grand_trines": [], "t_squares": []}
    by_sign = {}
    for n in names:
        by_sign.setdefault(chart["points"][n]["sign"], []).append(n)
    out["stelliums"] = [{"sign": s, "points": v} for s, v in by_sign.items() if len(v) >= 3]
    for a, b, c in itertools.combinations(names, 3):
        if near(a, b, 120) and near(b, c, 120) and near(a, c, 120):
            out["grand_trines"].append([a, b, c])
        for x, y, z in ((a, b, c), (b, c, a), (c, a, b)):  # z is the apex
            if near(x, y, 180) and near(x, z, 90) and near(y, z, 90):
                out["t_squares"].append({"apex": z, "opposition": [x, y]})
    out["note"] = "Moon excluded; based on noon positions (moving points shift up to about a degree)."
    return out


# ------------------------------------------------------------ returns, transits
def _f(body, jd, natal):
    return ((_lon_speed(body, jd)[0] - natal + 180) % 360) - 180


def next_return(body, natal_lon, jd_from, years, step=5.0, group_days=400):
    """First return period after jd_from (retrograde loops give up to 3 exact hits)."""
    hits, j = [], jd_from
    end = jd_from + years * 365.25
    prev = _f(body, j, natal_lon)
    while j < end:
        j2 = j + step
        cur = _f(body, j2, natal_lon)
        if prev * cur <= 0 and abs(prev) < 90 and abs(cur) < 90:
            a, b, fa = j, j2, prev
            for _ in range(40):
                m = (a + b) / 2
                fm = _f(body, m, natal_lon)
                if fa * fm <= 0:
                    b = m
                else:
                    a, fa = m, fm
            hits.append((a + b) / 2)
        j, prev = j2, cur
        if hits and j - hits[0] > group_days:
            break
    if not hits:
        return None
    grp = [h for h in hits if h - hits[0] <= group_days]
    date = lambda h: "%04d-%02d-%02d" % swe.revjul(h)[:3]
    return {"exact_dates": [date(h) for h in grp]}


def returns(chart, today):
    jd_now = swe.julday(today.year, today.month, today.day, 12)
    out = {}
    for label, body, yrs in (("Saturn", swe.SATURN, 32), ("Jupiter", swe.JUPITER, 13),
                             ("North Node", swe.MEAN_NODE, 19)):
        nat = chart["points"][label]["lon"]
        out[label] = next_return(body, nat, jd_now, yrs)
    return out


TRANSIT_ASPECTS = ASPECTS


def transits(chart, today, orb=3.0, top=8):
    jd = swe.julday(today.year, today.month, today.day, 12)
    rows = []
    for tname in ("Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"):
        t = _lon_speed(BODIES[tname], jd)[0]
        for n in ("Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn",
                  "North Node", "Selena"):
            p = chart["points"][n]
            for ang, an in TRANSIT_ASPECTS:
                mn, mx = _orb_range(t - p["hi"], t - p["lo"], ang)
                if mn <= orb:
                    rows.append({"transit": tname, "natal": n, "aspect": an,
                                 "orb_best": round(mn, 2),
                                 "status": "certain" if mx <= orb else "possible"})
    rows.sort(key=lambda r: (r["status"] != "certain", r["orb_best"]))
    return rows[:top]


# ------------------------------------------------------------------ payload
def person_summary(chart, today=None):
    today = today or dt.date.today()
    pts = {}
    for n, p in chart["points"].items():
        pts[n] = {"text": fmt(p["lon"]), "sign": p["sign"],
                  "sign_certain": p["sign_certain"], "sign_options": p["sign_options"],
                  "retrograde": p["retrograde"], "retro_certain": p["retro_certain"]}
        if n == "Moon":
            pts[n]["degree_range"] = "%s to %s" % (fmt(p["lo"]), fmt(p["hi"]))
    return {"name": chart["name"], "date": chart["date"], "place": chart["place"],
            "timezone": chart["timezone"], "window_hours": chart["window_hours"],
            "points": pts, "dignities": dignity(chart),
            "balance": element_counts(chart), "patterns": patterns(chart),
            "next_returns": returns(chart, today),
            "current_transits": transits(chart, today)}


def pair_payload(A, B, today=None):
    return {"person_a": person_summary(A, today), "person_b": person_summary(B, today),
            "contacts": contacts(A, B)[:12], "selena_north_node": selena_node_links(A, B),
            "lilith_selena_axis_echo": lilith_selena_axis_echo(A, B),
            "composite": composite(A, B),
            "not_available": ["Rising sign", "houses", "Midheaven/IC", "Part of Fortune",
                              "sect", "Moon degree", "progressed Moon"]}
