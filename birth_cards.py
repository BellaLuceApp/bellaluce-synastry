"""
Tarot birth cards from a birth DATE (no place or time needed).

Method (one common convention; settings below let you change it):
  1. Add every digit of the full birth date.
  2. While the total is above 22, add its digits again  (method="digits"),
     or subtract 22                                     (method="subtract22").
  3. The result (1-21, with 22 meaning The Fool) is the PERSONALITY card.
  4. If it is 10 or more, add its digits again until a single digit (1-9):
     that is the SOUL card. Any number passed through on the way is the
     "hidden factor". A single digit straight away means one card only.
  5. YEARLY card: digits of birth month + birth day + the year of the person's
     most recent birthday, reduced the same way.

Card numbering: Rider-Waite has Strength = 8 and Justice = 11.
Marseille / Thoth-style decks swap them. Set deck="marseille" to swap.
"""
import datetime as dt

_MAJOR = ["The Fool", "The Magician", "The High Priestess", "The Empress", "The Emperor",
          "The Hierophant", "The Lovers", "The Chariot", "Strength", "The Hermit",
          "Wheel of Fortune", "Justice", "The Hanged Man", "Death", "Temperance",
          "The Devil", "The Tower", "The Star", "The Moon", "The Sun", "Judgement",
          "The World"]


def card_name(n, deck="rider_waite"):
    n = 0 if n == 22 else n
    if deck == "marseille" and n in (8, 11):
        return "Justice" if n == 8 else "Strength"
    return _MAJOR[n]


def digit_sum(n):
    return sum(int(c) for c in str(abs(n)))


def _reduce_to_22(total, method):
    while total > 22:
        total = digit_sum(total) if method == "digits" else total - 22
    return total


def _card(n, deck):
    return {"number": 0 if n == 22 else n, "name": card_name(n, deck)}


def _soul_path(n):
    """From a 10-22 number, the numbers passed through down to a single digit."""
    path = []
    while n >= 10:
        n = digit_sum(n)
        path.append(n)
    return path  # last item is the soul number; earlier items are hidden factors


def birth_cards(year, month, day, today=None, deck="rider_waite", method="digits"):
    today = today or dt.date.today()
    total = digit_sum(year) + digit_sum(month) + digit_sum(day)
    pers = _reduce_to_22(total, method)
    out = {"digit_total": total, "personality": _card(pers, deck),
           "hidden": [], "soul": None, "method": method, "deck": deck}
    if pers >= 10:
        path = _soul_path(pers)
        out["soul"] = _card(path[-1], deck)
        out["hidden"] = [_card(x, deck) for x in path[:-1]]
    else:
        out["soul"] = out["personality"]          # one card only
    out["single_card"] = out["soul"] == out["personality"]

    yr = today.year if (today.month, today.day) >= (month, day) else today.year - 1
    ycard = _reduce_to_22(digit_sum(month) + digit_sum(day) + digit_sum(yr), method)
    out["yearly"] = {"for_year": yr, **_card(ycard, deck)}
    return out


def pair_links(a, b):
    """Cards two people share, in any role."""
    def roles(c):
        if c["single_card"]:                      # one card only: list it once
            return {"birth card": c["personality"]["name"]}
        return {"personality": c["personality"]["name"], "soul": c["soul"]["name"]}
    ra, rb = roles(a), roles(b)
    links = []
    for ka, na in ra.items():
        for kb, nb in rb.items():
            if na == nb:
                links.append({"card": na, "person_a_role": ka, "person_b_role": kb})
    seen, uniq = set(), []
    for l in links:
        k = (l["card"], l["person_a_role"], l["person_b_role"])
        if k not in seen:
            seen.add(k)
            uniq.append(l)
    return uniq
