"""
BellaLuce "My Patterns": counts what really happened across a person's earlier
Cards and Stars readings, so the AI is only ever handed real figures and never
has to count or guess.

INPUT: a block of text, one saved history_line per reading, readings separated
by a line containing only ###. The format Bubble saves looks like:

  10/26/26  Question: <their question> | Energy Lean: Leaning Favorable| Cards: The Star
  Reversed, Two of CupsReversed, ... | Situation (1793023145220x233701192483733500)

The parser accepts that exactly as saved (glued card names, line breaks inside
a line, a two-digit year, a situation id), and also the cleaner forms
("Two of Cups Reversed", "Situation: Job decision", ISO dates).
"""
import datetime as dt
import math
import random
import re
from collections import Counter, defaultdict

from birth_cards import _MAJOR

LEAN_ORDER = ["Favorable", "Leaning Favorable", "Balanced",
              "Leaning Challenging", "Challenging"]
LEAN_SCORE = {"Favorable": 2, "Leaning Favorable": 1, "Balanced": 0,
              "Leaning Challenging": -1, "Challenging": -2}
_LEAN_BY_LOWER = {k.lower(): k for k in LEAN_ORDER}
MAJOR_LOWER = {m.lower() for m in _MAJOR} | {"judgment", "the wheel of fortune"}

MAX_READINGS_FOR_TRANSITS = 200   # most recent; keeps the call fast
TIMELINE_MAX = 20                 # readings listed in the timeline (most recent)
QUESTION_MAX_CHARS = 240
MIN_LINK_READINGS = 3             # a transit must be present in this many readings
MIN_WITHOUT = 2                   # ...and absent in this many, so there is a contrast
PERMUTATIONS = 2000               # shuffles used for the chance check
ALPHA = 0.05                      # report only if luck explains it in under 5 of 100 shuffles
PERM_SEED = 20261026              # fixed, so the same readings always give the same answer


# ------------------------------------------------------------------ parsing
def _last(pattern, text, flags=re.I):
    found = None
    for m in re.finditer(pattern, text, flags):
        found = m
    return found


def _parse_date(text):
    m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", text[:40])
    if m:
        y, mo, d = map(int, m.groups())
    else:
        m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", text[:40])
        if not m:
            return None
        a, b, y = map(int, m.groups())
        mo, d = (a, b) if a <= 12 else (b, a)      # Bubble saves month/day/year
        if y < 100:
            y += 2000
    try:
        return dt.date(y, mo, d)
    except ValueError:
        return None


def parse_line(line):
    """One saved history_line -> dict, or None if it can't be understood."""
    text = re.sub(r"\s+", " ", (line or "").replace("\r", " ")).strip()
    if not text:
        return None
    date = _parse_date(text)
    lean_m = _last(r"Energy Lean:\s*(Leaning Favorable|Leaning Challenging|Favorable|"
                   r"Challenging|Balanced)", text)
    cards_m = _last(r"Cards:\s*", text)
    if not (date and lean_m and cards_m):
        return None
    lean = _LEAN_BY_LOWER[lean_m.group(1).lower()]

    # situation: "Situation (id)" or "Situation: name" at the end of the line
    situation = None
    cards_text = text[cards_m.end():]
    sm = _last(r"\|\s*Situation\s*(?:\(([^)]*)\)|:\s*(.+?))\s*$", text)
    if sm:
        situation = (sm.group(1) or sm.group(2) or "").strip() or None
        cards_text = text[cards_m.end():sm.start()]

    cards = []
    for part in cards_text.split(","):
        part = part.strip().strip("|").strip()
        cm = re.match(r"^(.*?)\s*(Upright|Reversed)$", part, re.I)
        if cm and cm.group(1).strip():
            cards.append((cm.group(1).strip(), cm.group(2).lower() == "reversed"))
    if not cards:
        return None

    q = re.search(r"Question:\s*(.*?)\s*\|\s*Energy Lean:", text, re.I)
    return {"date": date, "lean": lean, "cards": cards, "situation": situation,
            "question": q.group(1) if q else ""}


def parse_block(readings_text):
    lines = (readings_text or "").split("###")
    good, skipped = [], 0
    for ln in lines:
        if not ln.strip():
            continue
        r = parse_line(ln)
        if r:
            good.append(r)
        else:
            skipped += 1
    good.sort(key=lambda r: r["date"])
    return good, skipped


def parse_names(names_text):
    """Optional 'id=Name' pairs, separated by new lines or ;; (a stray space
    between the semicolons, as Bubble can produce, is accepted too)."""
    out = {}
    for part in re.split(r"\n|;\s*;", names_text or ""):
        if "=" in part:
            k, v = part.split("=", 1)
            if k.strip() and v.strip():
                out[k.strip()] = v.strip()
    return out


# -------------------------------------------------------------------- stats
def _is_major(name):
    return name.lower() in MAJOR_LOWER


def _lean_text(readings):
    c = Counter(r["lean"] for r in readings)
    return ", ".join(f"{k}: {c[k]}" for k in LEAN_ORDER if c[k]) or "none"


def _trend(readings):
    n = len(readings)
    if n < 4:
        return "too early to tell (needs at least 4 readings)"
    half = n // 2
    old = sum(LEAN_SCORE[r["lean"]] for r in readings[:half]) / half
    new = sum(LEAN_SCORE[r["lean"]] for r in readings[-half:]) / half
    diff = new - old
    if diff >= 0.5:
        return "the more recent readings lean more favorable than the older ones"
    if diff <= -0.5:
        return "the more recent readings lean more challenging than the older ones"
    return "steady, no clear shift between older and newer readings"


def _card_stats(readings):
    total = sum(len(r["cards"]) for r in readings)
    rev = sum(1 for r in readings for _, x in r["cards"] if x)
    major = sum(1 for r in readings for nme, _ in r["cards"] if _is_major(nme))
    seen = defaultdict(lambda: {"readings": 0, "rev": 0, "up": 0, "name": ""})
    for r in readings:
        per_reading = {}
        for nme, x in r["cards"]:
            per_reading.setdefault(nme.lower(), (nme, x))
        for key, (nme, x) in per_reading.items():
            e = seen[key]
            e["name"] = e["name"] or nme
            e["readings"] += 1
            e["rev" if x else "up"] += 1
    repeat = sorted((e for e in seen.values() if e["readings"] >= 2),
                    key=lambda e: (-e["readings"], e["name"]))[:8]
    return total, rev, major, repeat


def _pct(a, b):
    return 0 if not b else round(100 * a / b)


def _group_stats(readings):
    total, rev, major, repeat = _card_stats(readings)
    return {
        "readings": len(readings),
        "first_date": readings[0]["date"].isoformat(),
        "last_date": readings[-1]["date"].isoformat(),
        "energy_lean_counts": {k: v for k, v in
                               ((k, sum(1 for r in readings if r["lean"] == k))
                                for k in LEAN_ORDER) if v},
        "trend": _trend(readings),
        "cards_drawn": total,
        "reversed_percent": _pct(rev, total),
        "major_arcana_percent": _pct(major, total),
        "repeat_cards": [{"card": e["name"], "in_readings": e["readings"],
                          "upright": e["up"], "reversed": e["rev"]} for e in repeat],
    }


def _group_text(label, readings, st):
    lines = [f"{label}: {st['readings']} readings, {st['first_date']} to {st['last_date']}",
             f"  Energy Lean spread: {_lean_text(readings)}",
             f"  Direction over time: {st['trend']}",
             f"  Cards drawn: {st['cards_drawn']}; reversed {st['reversed_percent']}%; "
             f"Major Arcana {st['major_arcana_percent']}%"]
    if st["repeat_cards"]:
        parts = []
        for e in st["repeat_cards"]:
            side = []
            if e["upright"]:
                side.append(f"{e['upright']} upright")
            if e["reversed"]:
                side.append(f"{e['reversed']} reversed")
            parts.append(f"{e['card']} (in {e['in_readings']} readings: {', '.join(side)})")
        lines.append("  Cards that keep returning: " + "; ".join(parts))
    else:
        lines.append("  Cards that keep returning: none appear in more than one reading yet")
    return "\n".join(lines)


# ---------------------------------------------------------------- transits
FAST = ("Sun", "Mercury", "Venus", "Mars")
KIND = {"square": "hard", "opposition": "hard", "trine": "soft",
        "sextile": "soft", "conjunction": "conjunction"}
KIND_TEXT = {"hard": "in a hard aspect (square or opposition) to something in the chart",
             "soft": "in an easy aspect (trine or sextile) to something in the chart",
             "conjunction": "conjunct something in the chart"}
MIN_EPISODES = 3      # the transit must show up on this many separate occasions
EPISODE_GAP_DAYS = 7  # readings closer together than this count as one occasion


def _episodes(dates):
    dates = sorted(dates)
    n = 1 if dates else 0
    for a, b in zip(dates, dates[1:]):
        if (b - a).days > EPISODE_GAP_DAYS:
            n += 1
    return n


def _transit_links(readings, chart, transits_fn):
    """Which FAST transits were active (certain only, so no birth time is needed)
    on the dates of readings that leaned one way.

    Only the fast planets are tabulated, grouped as (planet, kind of aspect).
    Slow planets last weeks to months, so they would only mirror the direction
    over time, which is reported separately.

    A group is a candidate only if it was active in at least MIN_LINK_READINGS
    readings spread over at least MIN_EPISODES separate occasions, and inactive
    in at least MIN_WITHOUT. Candidates then face a chance check: the Energy
    Lean labels are shuffled PERMUTATIONS times, and the largest standardized
    gap across ALL candidates is recorded each time. A group is reported only if
    its real gap beats that in at least 95% of shuffles. This is what stops
    ordinary luck from looking like a pattern when many groups are compared."""
    used = readings[-MAX_READINGS_FOR_TRANSITS:]
    n = len(used)
    scores = [LEAN_SCORE[r["lean"]] for r in used]
    baseline = sum(scores) / n
    present = defaultdict(list)
    for idx, r in enumerate(used):
        keys = set()
        for row in transits_fn(chart, r["date"], top=80, fast_top=80):
            if row["status"] == "certain" and row["transit"] in FAST:
                keys.add((row["transit"], KIND[row["aspect"]]))
        for k in keys:
            present[k].append(idx)

    cands = {}
    for k, idxs in present.items():
        n_with = len(idxs)
        if n_with < MIN_LINK_READINGS or n - n_with < MIN_WITHOUT:
            continue
        if _episodes([used[i]["date"] for i in idxs]) < MIN_EPISODES:
            continue
        cands[k] = idxs
    var = sum((s - baseline) ** 2 for s in scores) / n
    if not cands or var == 0:
        return [], n, round(baseline, 2)
    sd = math.sqrt(var)
    total = sum(scores)

    def z(vals, idxs):
        nw = len(idxs)
        nwo = n - nw
        s_with = sum(vals[i] for i in idxs)
        gap = s_with / nw - (total - s_with) / nwo
        return gap, gap / (sd * math.sqrt(1 / nw + 1 / nwo))

    real = {k: z(scores, idxs) for k, idxs in cands.items()}
    rng = random.Random(PERM_SEED)
    shuffled = list(scores)
    maxes = []
    for _ in range(PERMUTATIONS):
        rng.shuffle(shuffled)
        maxes.append(max(abs(z(shuffled, idxs)[1]) for idxs in cands.values()))

    found = []
    for k, idxs in cands.items():
        gap, zz = real[k]
        p_adj = (1 + sum(1 for m in maxes if m >= abs(zz))) / (PERMUTATIONS + 1)
        if p_adj > ALPHA:
            continue
        planet, kind = k
        scores_with = [scores[i] for i in idxs]
        found.append({
            "transit": f"{planet} {KIND_TEXT[kind]}",
            "readings_with": len(idxs), "readings_without": n - len(idxs),
            "occasions": _episodes([used[i]["date"] for i in idxs]),
            "favorable_side_with": sum(1 for s in scores_with if s > 0),
            "challenging_side_with": sum(1 for s in scores_with if s < 0),
            "balanced_with": sum(1 for s in scores_with if s == 0),
            "direction": "more favorable" if gap > 0 else "more challenging",
            "gap": round(gap, 2), "chance_p": round(p_adj, 4)})
    found.sort(key=lambda f: (f["chance_p"], -abs(f["gap"])))
    return found[:4], n, round(baseline, 2)


def _links_text(found, n, span_days=None):
    head = (f"Transit links ({n} readings checked). Only the fast planets (Sun, Mercury, "
            "Venus, Mars) are compared, because the slow planets last weeks to months and "
            "would only mirror the direction over time shown above.")
    if not found and span_days is not None and span_days < 28:
        return (f"Transit links ({n} readings checked): these readings cover only "
                f"{span_days + 1} days. Comparing transits with how readings leaned needs "
                "readings spread over several weeks, at least 3 separate occasions more than a "
                "week apart, so this part cannot say anything yet. It fills in as the history grows.")
    if not found:
        return head + ("\nNo fast transit passed the chance check. Nothing here is strong enough "
                       "to call a pattern yet.")
    lines = [head, "These passed a chance check (luck alone would produce a gap this large "
                   "in fewer than 5 of 100 shufflings of the readings). They are tendencies "
                   "in the data so far, not causes:"]
    for f in found:
        lines.append(
            f"  - {f['transit']}, active in {f['readings_with']} readings across "
            f"{f['occasions']} separate occasions (not active in {f['readings_without']}). "
            f"Of the active ones: {f['favorable_side_with']} leaned favorable, "
            f"{f['challenging_side_with']} leaned challenging, {f['balanced_with']} balanced. "
            f"Those readings leaned {f['direction']} than the rest.")
    return "\n".join(lines)


def _timeline_text(readings, label_for):
    """Every reading in scope, oldest to newest, so the AI can see HOW the
    questions and the answers moved, not just the totals."""
    shown = readings[-TIMELINE_MAX:]
    head = "Timeline of readings in this scope, oldest to newest"
    if len(readings) > len(shown):
        head += f" (the most recent {len(shown)} of {len(readings)} are listed)"
    lines = [head + ":"]
    for r in shown:
        q = re.sub(r"\s+", " ", r["question"]).strip()
        if len(q) > QUESTION_MAX_CHARS:
            q = q[:QUESTION_MAX_CHARS].rstrip() + "..."
        cards = ", ".join(f"{n} ({'reversed' if rev else 'upright'})" for n, rev in r["cards"])
        lines.append(f"  - {r['date'].isoformat()} | {label_for(r['situation'])} | "
                     f"Energy Lean: {r['lean']} | Question: {q or '(not saved)'} | Cards: {cards}")
    return "\n".join(lines)


# ------------------------------------------------------------------- driver
def analyze(readings_text, chart, transits_fn, names_text="", min_readings=5):
    readings, skipped = parse_block(readings_text)
    names = parse_names(names_text)
    n = len(readings)
    out = {"reading_count": n, "skipped_lines": skipped, "min_readings": min_readings}

    if n < min_readings:
        out["enough"] = "no"
        out["message"] = (f"Not enough readings yet. There are {n} in this scope and at "
                          f"least {min_readings} are needed before patterns mean anything.")
        out["patterns_block"] = ""
        out["stats"] = {}
        return out

    # group by situation, in order of first appearance
    groups, order = defaultdict(list), []
    for r in readings:
        key = r["situation"]
        if key not in groups:
            order.append(key)
        groups[key].append(r)

    # one readable name per situation: the given name, else "Situation N"
    sit_names, counter = {}, 0
    for key in order:
        if key is None:
            continue
        counter += 1
        sit_names[key] = names.get(key, f"Situation {counter}")

    def label_for(key):
        return "no situation" if key is None else sit_names[key]

    blocks, stats_groups = [], {}
    overall = _group_stats(readings)
    blocks.append(_group_text("All readings in this scope", readings, overall))
    blocks.append(_timeline_text(readings, label_for))
    labelled = [k for k in order if k is not None]
    if labelled:      # break down by situation only when any reading has one
        for key in order:
            if key is None:
                label = "Readings with no situation (one-time readings)"
            else:
                label = f"Situation: {sit_names[key]}"
            grp = groups[key]
            if len(grp) < 2:
                blocks.append(f"{label}: only {len(grp)} reading so far, too early to say anything")
                continue
            st = _group_stats(grp)
            stats_groups[label] = st
            blocks.append(_group_text(label, grp, st))

    found, used_n, baseline = _transit_links(readings, chart, transits_fn)
    span_days = (readings[-1]["date"] - readings[0]["date"]).days
    blocks.append(_links_text(found, used_n, span_days))

    out["enough"] = "yes"
    out["message"] = ""
    out["patterns_block"] = "\n\n".join(blocks)
    out["stats"] = {"overall": overall, "by_situation": stats_groups,
                    "transit_links": found, "average_lean": baseline}
    return out
