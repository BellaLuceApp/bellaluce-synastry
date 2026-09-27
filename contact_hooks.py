"""
Curated "why this matters" hook text for the free teaser snapshot.

The synastry engine tells us WHICH contact is tightest (e.g. "Selena
conjunction North Node"). On its own that's just jargon to a visitor who
isn't a tarot/astrology nerd. This module turns that jargon into the kind
of one-line hook that makes someone want to unlock the full reading --
without ever calling an AI (so it's instant, free, and always on-brand,
the same way BellaLuce's tarot card meanings are hand-curated rather than
AI-generated).

Design: a pairing's MEANING (what these two points represent together,
independent of aspect) is curated for the ~25 highest-signal pairs.
An aspect's TONE (how intensely/favorably that meaning plays out) is
curated for all 5 aspects. The two combine into one sentence. Any pair
not explicitly curated still gets a full sentence, built from each
point's individual flavor text -- so nothing ever falls through blank
or generic-sounding.
"""

# What each point represents in a relational/synastry context.
POINT_FLAVOR = {
    "Sun":         "core identity and sense of self",
    "Moon":        "emotional instincts and what makes you feel at home",
    "Mercury":     "how you think and communicate",
    "Venus":       "attraction, affection, and what you find lovable",
    "Mars":        "desire, drive, and how you go after what you want",
    "Jupiter":     "growth, optimism, and shared possibility",
    "Saturn":      "commitment, structure, and staying power",
    "North Node":  "the direction you're being pulled to grow toward",
    "Selena":      "primal magnetism and instinctive pull",
}

# How each aspect colors the meaning: a connecting verb + an intensity label.
ASPECT_TONE = {
    "conjunction": {"verb": "fuses directly with", "label": "an intense, all-in blend"},
    "trine":       {"verb": "flows easily into",   "label": "an effortless, naturally supportive link"},
    "sextile":     {"verb": "opens a doorway to",   "label": "a light, easy-to-build-on opportunity"},
    "square":      {"verb": "rubs up against",      "label": "a live-wire tension that demands attention"},
    "opposition":  {"verb": "pulls against",        "label": "a magnetic push-pull -- opposites that complete each other"},
}

# Curated, hand-written meaning for the highest-signal point pairs.
# Keyed by a frozenset of the two point names (direction doesn't matter for
# the underlying MEANING -- the aspect tone above is what carries the charge).
PAIR_MEANING = {
    frozenset({"Selena", "North Node"}):
        "This is one of the strongest destiny-style signatures in synastry -- "
        "one person's raw magnetism lining up with the other's growth path, "
        "the kind of pull people often describe as instant recognition.",
    frozenset({"Sun", "Moon"}):
        "This links one person's core identity with the other's emotional "
        "instincts -- classic \"you get me\" territory, often felt as an "
        "easy sense of being truly seen.",
    frozenset({"Venus", "Mars"}):
        "This is the classic chemistry signature: one person's sense of "
        "attraction meeting the other's desire and drive.",
    frozenset({"Sun", "Venus"}):
        "One person's core identity meets the other's sense of affection -- "
        "a sign that just being yourself is what draws them in.",
    frozenset({"Moon", "Venus"}):
        "Emotional comfort meets affection here -- often felt as warmth and "
        "ease rather than fireworks.",
    frozenset({"Sun", "Sun"}):
        "Two core identities lining up directly -- a strong sense of being "
        "cut from similar cloth.",
    frozenset({"Moon", "Moon"}):
        "Two emotional worlds resonating with each other -- a sense of "
        "shared instinct about what feels safe and familiar.",
    frozenset({"Venus", "Venus"}):
        "Two people's sense of what's attractive and lovable lining up "
        "directly with each other.",
    frozenset({"Selena", "Selena"}):
        "A shared instinctive, almost gravitational pull between you both.",
    frozenset({"North Node", "North Node"}):
        "Your growth paths are pointed in a strikingly similar direction.",
    frozenset({"Sun", "North Node"}):
        "One person's core identity lines up with the other's growth path -- "
        "often felt as this relationship pushing you toward who you're "
        "becoming.",
    frozenset({"Moon", "North Node"}):
        "Emotional instinct meeting a growth path -- this relationship can "
        "feel like where you're emotionally headed, not just where you are.",
    frozenset({"Venus", "North Node"}):
        "Attraction lining up with a growth path -- the kind of connection "
        "that can feel like it's meant to teach you something about love.",
    frozenset({"Mars", "North Node"}):
        "Drive and desire lining up with a growth path -- this connection "
        "can feel like it pushes you into motion.",
    frozenset({"Sun", "Selena"}):
        "Core identity meeting raw magnetism -- a strong, instinctive draw "
        "toward who this person simply is.",
    frozenset({"Moon", "Selena"}):
        "Emotional instinct tangled up with magnetism -- feelings that run "
        "deep and are hard to fully explain.",
    frozenset({"Venus", "Selena"}):
        "Attraction amplified by primal pull -- often felt as a chemistry "
        "that's a little hard to rationalize.",
    frozenset({"Mars", "Selena"}):
        "Desire meeting magnetism -- a charge that tends to be felt "
        "immediately, before either of you has said much at all.",
    frozenset({"Saturn", "Sun"}):
        "Structure and commitment meeting core identity -- a bond that "
        "tends to feel serious and built-to-last rather than casual.",
    frozenset({"Saturn", "Venus"}):
        "Commitment meeting affection -- often a sign of relationships that "
        "settle into something steady and long-term.",
    frozenset({"Saturn", "Moon"}):
        "Structure meeting emotional instinct -- can feel like real "
        "stability, or like real work, depending on how it's handled.",
    frozenset({"Mercury", "Venus"}):
        "Communication style meeting affection -- a strong sign you'll "
        "simply enjoy talking to each other.",
    frozenset({"Mercury", "Moon"}):
        "Thought meeting feeling -- a sign of being able to actually talk "
        "through what you're each feeling, not just feel it.",
    frozenset({"Jupiter", "Venus"}):
        "Growth and generosity meeting affection -- a connection that tends "
        "to feel expansive, warm, and encouraging.",
    frozenset({"Jupiter", "Sun"}):
        "Growth meeting core identity -- often felt as this person bringing "
        "out a bigger, more confident version of you.",
}


def contact_hook(a_point, b_point, aspect):
    """One curated marketing-ready sentence explaining why the tightest
    contact between two people is worth paying attention to. Never returns
    blank or bare jargon -- always a full, on-brand sentence."""
    tone = ASPECT_TONE.get(aspect, ASPECT_TONE["conjunction"])
    pair_key = frozenset({a_point, b_point})
    meaning = PAIR_MEANING.get(pair_key)
    if meaning is None:
        a_flavor = POINT_FLAVOR.get(a_point, "an important part of who you are")
        b_flavor = POINT_FLAVOR.get(b_point, "an important part of who they are")
        meaning = (f"This links {a_flavor} with {b_flavor} -- "
                   f"a real point of connection worth understanding.")
    return f"{meaning} With this exact aspect, it plays out as {tone['label']}."
