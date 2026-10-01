"""
Curated "why this matters" hook text for the free teaser snapshot.

The synastry engine tells us WHICH contact is tightest (e.g. "Selena
conjunction North Node"). On its own that's just jargon to a visitor who
isn't a tarot/astrology nerd. This module turns that jargon into the kind
of one-line hook that makes someone want to unlock the full reading --
without ever calling an AI (so it's instant, free, and always on-brand,
the same way BellaLuce's tarot card meanings are hand-curated rather than
AI-generated).

Design: a pairing's MEANING (what these two points represent together) can
be curated two ways:

  1. ASPECT-SPECIFIC (preferred, for the highest-exposure pairs): a dict of
     {aspect_name: full curated sentence}. Each aspect gets its own
     fully-written sentence, so two users who both hit this pairing but with
     a different aspect get genuinely different text, not a shared opening
     line with a different last clause tacked on. This matters because a
     repeated opening sentence reads as templated/generic to a paying user,
     even when the underlying result is accurate.

  2. GENERIC (fallback, for pairs not yet given the aspect-specific
     treatment): a single string describing the pairing regardless of
     aspect, combined with a generic ASPECT_TONE closing clause. Lower
     curation cost, but more prone to feeling repetitive across users.

Any pair with neither gets a full sentence built from each point's
individual flavor text -- so nothing ever falls through blank or
generic-sounding.
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

# Fallback tone for any pairing that only has a GENERIC meaning (see above):
# a connecting verb + an intensity label, appended as a closing clause.
ASPECT_TONE = {
    "conjunction": {"verb": "fuses directly with", "label": "an intense, all-in blend"},
    "trine":       {"verb": "flows easily into",   "label": "an effortless, naturally supportive link"},
    "sextile":     {"verb": "opens a doorway to",   "label": "a light, easy-to-build-on opportunity"},
    "square":      {"verb": "rubs up against",      "label": "a live-wire tension that demands attention"},
    "opposition":  {"verb": "pulls against",        "label": "a magnetic push-pull -- opposites that complete each other"},
}

# Curated, hand-written meaning for the highest-signal point pairs.
# Keyed by a frozenset of the two point names (direction doesn't matter).
# Value is EITHER:
#   - a dict of {aspect_name: full sentence}      (aspect-specific, preferred)
#   - a plain string                               (generic, see ASPECT_TONE)
PAIR_MEANING = {
    frozenset({"Selena", "North Node"}): {
        "conjunction":
            "This is one of the strongest destiny-style signatures in "
            "synastry -- your magnetism and their growth path aren't just "
            "nearby, they're fused together, the kind of pull people "
            "describe as instant recognition.",
        "square":
            "Your magnetism and their growth path are rubbing directly "
            "against each other here -- a live-wire tension that won't let "
            "either of you look away, even when it's uncomfortable.",
        "trine":
            "Your magnetism and their growth path move in sync here, "
            "almost without effort -- the kind of pull that feels less "
            "like chemistry and more like fate quietly doing its job.",
        "sextile":
            "There's an open doorway between your magnetism and their "
            "growth path -- not forced, but there, waiting for either of "
            "you to walk through it.",
        "opposition":
            "Your magnetism and their growth path sit on opposite ends of "
            "the same axis -- a push-pull dynamic where each of you seems "
            "to complete something the other is missing.",
    },
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
    pair_key = frozenset({a_point, b_point})
    meaning = PAIR_MEANING.get(pair_key)

    # Case 1: aspect-specific curated sentences (preferred).
    if isinstance(meaning, dict):
        sentence = meaning.get(aspect)
        if sentence:
            return sentence
        # an aspect without its own variant falls through to the generic path

    # Case 2: a single generic sentence, plus a tone clause keyed by aspect.
    tone = ASPECT_TONE.get(aspect, ASPECT_TONE["conjunction"])
    if isinstance(meaning, str):
        return f"{meaning} With this exact aspect, it plays out as {tone['label']}."

    # Case 3: nothing curated at all -- build from each point's flavor text.
    a_flavor = POINT_FLAVOR.get(a_point, "an important part of who you are")
    b_flavor = POINT_FLAVOR.get(b_point, "an important part of who they are")
    meaning = (f"This links {a_flavor} with {b_flavor} -- "
               f"a real point of connection worth understanding.")
    return f"{meaning} With this exact aspect, it plays out as {tone['label']}."
