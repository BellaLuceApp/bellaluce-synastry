"""
Curated "why this matters" hook text for the Daily Alignment free teaser --
the transit equivalent of contact_hooks.py's synastry hooks. Same design
goal: an instant, free, on-brand one-liner with no AI call, so a visitor
gets something worth reading before they ever pay for the full narrative.

A transit is directional (today's sky meeting a fixed natal point), unlike
a synastry contact, so this is keyed by the TRANSITING planet's theme plus
the NATAL point's theme (reusing contact_hooks.POINT_FLAVOR for the natal
side) rather than an unordered pair. A short list of hand-curated
combinations gets a fully written sentence; everything else falls back to
a formula built from each side's flavor text, so nothing ever reads as
bare jargon.
"""
from contact_hooks import POINT_FLAVOR, ASPECT_TONE, contact_hook

# What each transiting (slow-moving) planet represents as a current
# influence, independent of which natal point it's touching.
TRANSIT_FLAVOR = {
    "Jupiter": "a wave of growth, luck, and expansion",
    "Saturn":  "a test of structure, discipline, and staying power",
    "Uranus":  "a jolt of change, disruption, and sudden clarity",
    "Neptune": "a haze of intuition, imagination, and blurred edges",
    "Pluto":   "a slow, deep pressure toward transformation",
}

# A few hand-curated highlights for especially resonant pairings. Keyed by
# (transit_planet, natal_point) -- order matters here, unlike synastry.
TRANSIT_PAIR_MEANING = {
    ("Saturn", "Sun"):
        "Transiting Saturn is pressing directly on your core sense of self "
        "today -- the kind of influence that asks you to prove something "
        "real, not just feel something nice.",
    ("Jupiter", "Sun"):
        "Transiting Jupiter is lighting up your core identity today -- a "
        "genuinely good day to back yourself and take up a little more room.",
    ("Uranus", "Sun"):
        "Transiting Uranus is shaking something loose in your sense of self "
        "today -- expect the unexpected, and don't fight it too hard.",
    ("Saturn", "Venus"):
        "Transiting Saturn is testing what you value and who you love today "
        "-- not a bad day, but an honest one.",
    ("Jupiter", "Venus"):
        "Transiting Jupiter is warming up everything to do with love, "
        "money, and pleasure today -- a genuinely lucky stretch worth "
        "noticing.",
    ("Pluto", "Sun"):
        "Transiting Pluto is working on your core identity at a deep, slow "
        "level today -- not a one-day event, but today is part of it.",
}


def daily_transit_hook(transit_planet, natal_point, aspect):
    """One curated, marketing-ready sentence for the single tightest transit
    in today's reading. Never returns blank or bare jargon."""
    sentence = TRANSIT_PAIR_MEANING.get((transit_planet, natal_point))
    if sentence:
        return sentence

    t_flavor = TRANSIT_FLAVOR.get(transit_planet, "a notable current influence")
    n_flavor = POINT_FLAVOR.get(natal_point, "an important part of who you are")
    tone = ASPECT_TONE.get(aspect, ASPECT_TONE["conjunction"])
    return (f"Transiting {transit_planet} is bringing {t_flavor}, meeting "
            f"{n_flavor} in your own chart. With this exact aspect, it "
            f"plays out as {tone['label']}.")


def find_activated_contact(rows_a, rows_b, contacts):
    """Look for a synastry contact (between two people) that ANY of today's
    transits for EITHER person is landing on -- not just each person's
    single tightest transit. This is what makes a paired Daily Alignment
    teaser actually relational instead of two side-by-side solo horoscopes:
    if a transiting planet is hitting a point that's already part of
    something connecting these two charts, that's the most relevant thing
    to surface today.

    Checks every transit row for both people (up to 8 each from the engine),
    not just the top one, since narrowing to only the tightest transit per
    person made a match too rare to be useful in practice. Prefers, in
    order: a CERTAIN contact matched by a CERTAIN transit, then a CERTAIN
    contact matched by a possible transit, then any remaining match --
    and within each tier, the tightest transit orb wins. Returns
    (transit_row, which, contact) or None if nothing lines up.
    """
    candidates = []
    for row in (rows_a or []):
        candidates.append((row, "A"))
    for row in (rows_b or []):
        candidates.append((row, "B"))

    def rank(row, contact):
        # Lower is better: certain contact + certain transit first, then
        # certain contact + possible transit, then anything else; tightest
        # orb breaks ties within a tier.
        contact_certain = contact["status"] == "certain"
        transit_certain = row["status"] == "certain"
        if contact_certain and transit_certain:
            tier = 0
        elif contact_certain:
            tier = 1
        else:
            tier = 2
        return (tier, row["orb_best"])

    best = None
    for row, who in candidates:
        natal_point = row["natal"]
        for c in contacts:
            if natal_point not in (c["a_point"], c["b_point"]):
                continue
            candidate_rank = rank(row, c)
            if best is None or candidate_rank < best[0]:
                best = (candidate_rank, row, who, c)

    if best is None:
        return None
    _, row, who, c = best
    return row, who, c


def activated_contact_hook(a_name, b_name, transit_row, who, contact):
    """One curated sentence tying today's transit to an existing connection
    between two people -- the relational payoff that makes paired Daily
    Alignment worth more than two separate solo snapshots."""
    transit_planet = transit_row["transit"]
    natal_point = transit_row["natal"]
    owner_name = a_name if who == "A" else b_name
    other_name = b_name if who == "A" else a_name

    t_flavor = TRANSIT_FLAVOR.get(transit_planet, "a notable current influence")
    link_meaning = contact_hook(contact["a_point"], contact["b_point"], contact["aspect"])

    return (f"Transiting {transit_planet} is bringing {t_flavor} right to "
            f"{owner_name}'s {natal_point} today -- and that's exactly the "
            f"point already connecting {owner_name} and {other_name}'s "
            f"charts. {link_meaning}")
