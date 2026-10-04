"""
BellaLuce synastry service.

A small web service wrapping the tested engine (engine.py) and the tarot
birth cards (birth_cards.py), so Bubble can call it over the internet
instead of trying to reproduce the astronomy in JavaScript.

ONE ENDPOINT: POST /synastry
INPUT (JSON):
{
  "person_a": {"name": "You", "year": 1978, "month": 5, "day": 24, "timezone": "America/Sao_Paulo"},
  "person_b": {"name": "Man 1", "year": 1991, "month": 10, "day": 7, "timezone": "America/Los_Angeles"}
}
"timezone" must be an IANA name (e.g. "America/Sao_Paulo"), exactly what
Google's Time Zone API returns as "timeZoneId". Do NOT send a raw UTC
offset in minutes -- the IANA name lets the engine work out the correct
historical daylight-saving rule for that exact date, which manual offset
math cannot do reliably.

OUTPUT: the full pair_payload (person summaries, contacts, Selena/Node
links, composite), plus each person's tarot birth cards, plus a ready-made
"teaser" object for the free landing-page snapshot.
"""
from flask import Flask, request, jsonify
from engine import build_chart, pair_payload, transits
from birth_cards import birth_cards, pair_links
from contact_hooks import contact_hook
from transit_hooks import daily_transit_hook, find_activated_contact, activated_contact_hook
import datetime as dt

app = Flask(__name__)

REQUIRED = ("year", "month", "day", "timezone")


def _bad(msg, code=400):
    return jsonify({"error": msg}), code


def _contact_line(c):
    """One plain-English line for a single contact, ready to drop straight
    into an AI prompt -- so Bubble never has to assemble it from five
    separate fields."""
    if not c:
        return ""
    return (f"{c['a_point']} {c['aspect']} {c['b_point']} -- {c['status']} "
            f"(orb {c['orb_best']}°)")


def build_prompt_data(payload, a_name, b_name, today):
    """Flat, pre-formatted fields meant to be dropped straight into a
    {{placeholder}}-style AI prompt template -- so the Bubble side only
    needs one find/replace per field instead of reassembling nested JSON
    (point names, aspect, orb, status...) by hand for every contact."""
    contacts = payload["contacts"]
    certain = [c for c in contacts if c["status"] == "certain"]
    possible = [c for c in contacts if c["status"] == "possible"]

    axis = payload["lilith_selena_axis_echo"]
    if axis:
        axis_summary = (
            f"{a_name}'s Lilith in {axis['a_lilith']['sign']} mirrors {b_name}'s "
            f"Selena in {axis['b_selena']['sign']} (and {b_name}'s Lilith in "
            f"{axis['b_lilith']['sign']} mirrors {a_name}'s Selena in "
            f"{axis['a_selena']['sign']}) -- orb {axis['orb_best']}°, "
            f"{axis['status']}."
        )
    else:
        axis_summary = "No Lilith/Selena axis echo present in this pairing."

    sn = payload["selena_north_node"]
    if sn["mutual"]:
        ab, ba = sn["A_selena_to_B_node"], sn["B_selena_to_A_node"]
        sn_summary = (
            f"Mutual: {a_name}'s Selena {ab['aspect']} {b_name}'s North Node "
            f"({ab['status']}), and {b_name}'s Selena {ba['aspect']} "
            f"{a_name}'s North Node ({ba['status']})."
        )
    elif sn["A_selena_to_B_node"]:
        c = sn["A_selena_to_B_node"]
        sn_summary = f"{a_name}'s Selena {c['aspect']} {b_name}'s North Node -- {c['status']}."
    elif sn["B_selena_to_A_node"]:
        c = sn["B_selena_to_A_node"]
        sn_summary = f"{b_name}'s Selena {c['aspect']} {a_name}'s North Node -- {c['status']}."
    else:
        sn_summary = "No direct Selena-North Node contact between you."

    shared = payload["shared_birth_cards"]
    if shared:
        names = ", ".join(sorted({s["card"] for s in shared}))
        shared_summary = f"You share a birth card: {names}."
    else:
        shared_summary = "No shared birth card between you."

    data = {
        "person_a_name": a_name, "person_b_name": b_name,
        "reading_date": today.isoformat(),
        "person_a_sun_sign": payload["person_a"]["points"]["Sun"]["sign"],
        "person_b_sun_sign": payload["person_b"]["points"]["Sun"]["sign"],
        "person_a_birth_card": payload["person_a"]["birth_card"]["personality"]["name"],
        "person_b_birth_card": payload["person_b"]["birth_card"]["personality"]["name"],
        "shared_birth_card_summary": shared_summary,
        "certain_count": len(certain), "possible_count": len(possible),
        "axis_echo_summary": axis_summary,
        "selena_node_summary": sn_summary,
    }
    for i in range(12):
        data[f"contact_{i + 1}"] = _contact_line(contacts[i]) if i < len(contacts) else ""
    return data


def _transit_line(t):
    """One plain-English line for a single transit, e.g.
    'Transiting Jupiter trine your natal Venus -- certain (orb 1.2°)'."""
    return (f"Transiting {t['transit']} {t['aspect']} your natal {t['natal']} -- "
            f"{t['status']} (orb {t['orb_best']}°)")


def build_daily_prompt_data(today, a_name, a_chart, a_rows, b_name=None, b_chart=None, b_rows=None,
                             shared_contacts=None):
    """Flat, pre-formatted fields for the DailyAlignment {{placeholder}} prompt
    template. If no second person was given, the person_b_* fields are filled
    with harmless placeholder text ('(not included today)') and empty transit
    lines -- the system message is written to recognize that and talk about
    Person A only, the same way certain/possible is handled by instruction
    rather than by hiding fields.

    shared_contacts, when given (paired mode only), is the synastry contact
    list between the two people -- this is what lets the AI write a genuinely
    relational full reading instead of two solo horoscopes stapled together:
    it can see not just what's transiting today, but what's already
    connecting these two charts, and tie the two together itself."""
    a_certain = [t for t in a_rows if t["status"] == "certain"]
    a_possible = [t for t in a_rows if t["status"] == "possible"]
    data = {
        "today_date": today.isoformat(),
        "person_a_name": a_name,
        "person_a_sun_sign": a_chart["points"]["Sun"]["sign"],
        "person_a_certain_count": len(a_certain),
        "person_a_possible_count": len(a_possible),
    }
    for i in range(8):
        data[f"person_a_transit_{i + 1}"] = _transit_line(a_rows[i]) if i < len(a_rows) else ""

    if b_chart is not None:
        b_rows = b_rows or []
        b_certain = [t for t in b_rows if t["status"] == "certain"]
        b_possible = [t for t in b_rows if t["status"] == "possible"]
        data["person_b_name"] = b_name
        data["person_b_sun_sign"] = b_chart["points"]["Sun"]["sign"]
        data["person_b_certain_count"] = len(b_certain)
        data["person_b_possible_count"] = len(b_possible)
        for i in range(8):
            data[f"person_b_transit_{i + 1}"] = _transit_line(b_rows[i]) if i < len(b_rows) else ""
    else:
        data["person_b_name"] = "(not included today)"
        data["person_b_sun_sign"] = ""
        data["person_b_certain_count"] = 0
        data["person_b_possible_count"] = 0
        for i in range(8):
            data[f"person_b_transit_{i + 1}"] = ""

    shared_contacts = shared_contacts or []
    for i in range(6):
        data[f"shared_contact_{i + 1}"] = (
            _contact_line(shared_contacts[i]) if i < len(shared_contacts) else "")
    return data


def _parse_person(p, label):
    if not isinstance(p, dict):
        raise ValueError(f"{label} must be an object")
    for k in REQUIRED:
        if k not in p:
            raise ValueError(f"{label}.{k} is required")
    return p


@app.route("/synastry", methods=["POST"])
def synastry():
    body = request.get_json(silent=True) or {}
    try:
        a = _parse_person(body.get("person_a"), "person_a")
        b = _parse_person(body.get("person_b"), "person_b")
    except ValueError as e:
        return _bad(str(e))

    try:
        chart_a = build_chart(a.get("name", "Person A"), a["year"], a["month"], a["day"],
                              a["timezone"], a.get("place", ""))
        chart_b = build_chart(b.get("name", "Person B"), b["year"], b["month"], b["day"],
                              b["timezone"], b.get("place", ""))
    except Exception as e:
        return _bad(f"Could not calculate a chart -- check the timezone name and date. ({e})")

    today = dt.date.today()
    payload = pair_payload(chart_a, chart_b, today)

    cards_a = birth_cards(a["year"], a["month"], a["day"], today)
    cards_b = birth_cards(b["year"], b["month"], b["day"], today)
    payload["person_a"]["birth_card"] = cards_a
    payload["person_b"]["birth_card"] = cards_b
    payload["shared_birth_cards"] = pair_links(cards_a, cards_b)
    payload["prompt_data"] = build_prompt_data(
        payload, a.get("name", "Person A"), b.get("name", "Person B"), today)

    # A ready-made teaser for the free landing-page snapshot: the single
    # tightest CERTAIN contact (so the free hook never shows an "it depends
    # on birth time" result), plus each person's Sun sign and birth card.
    certain = [c for c in payload["contacts"] if c["status"] == "certain"]
    tightest = certain[0] if certain else None
    tightest_hook = None
    if tightest:
        tightest_hook = contact_hook(tightest["a_point"], tightest["b_point"], tightest["aspect"])
    payload["teaser"] = {
        "person_a_sun_sign": payload["person_a"]["points"]["Sun"]["sign"],
        "person_b_sun_sign": payload["person_b"]["points"]["Sun"]["sign"],
        "person_a_birth_card": cards_a["personality"]["name"],
        "person_b_birth_card": cards_b["personality"]["name"],
        "tightest_contact": tightest,
        "tightest_contact_hook": tightest_hook,
        "shared_birth_card": bool(payload["shared_birth_cards"]),
    }
    return jsonify(payload)


@app.route("/daily-alignment", methods=["POST"])
def daily_alignment():
    body = request.get_json(silent=True) or {}
    try:
        a = _parse_person(body.get("person_a"), "person_a")
    except ValueError as e:
        return _bad(str(e))

    b = body.get("person_b")
    if b is not None:
        try:
            b = _parse_person(b, "person_b")
        except ValueError as e:
            return _bad(str(e))

    try:
        chart_a = build_chart(a.get("name", "Person A"), a["year"], a["month"], a["day"],
                              a["timezone"], a.get("place", ""))
        chart_b = None
        if b is not None:
            chart_b = build_chart(b.get("name", "Person B"), b["year"], b["month"], b["day"],
                                  b["timezone"], b.get("place", ""))
    except Exception as e:
        return _bad(f"Could not calculate a chart -- check the timezone name and date. ({e})")

    today = dt.date.today()
    rows_a = transits(chart_a, today)
    rows_b = transits(chart_b, today) if chart_b is not None else None

    # Paired mode only: the synastry contacts between the two charts. This is
    # what lets today's transits be tied back to something that already
    # connects these two people, instead of just reporting two solo
    # horoscopes side by side.
    contacts = []
    if chart_b is not None:
        synastry_payload = pair_payload(chart_a, chart_b, today)
        contacts = synastry_payload["contacts"]

    payload = {
        "today": today.isoformat(),
        "person_a": {"name": a.get("name", "Person A"),
                     "sun_sign": chart_a["points"]["Sun"]["sign"],
                     "transits": rows_a},
    }
    if chart_b is not None:
        payload["person_b"] = {"name": b.get("name", "Person B"),
                                "sun_sign": chart_b["points"]["Sun"]["sign"],
                                "transits": rows_b}
    else:
        payload["person_b"] = None

    # Free teaser: the single tightest transit for each person given, with a
    # curated one-line hook -- no AI call, same pattern as /synastry's teaser.
    def _teaser_for(name, chart, rows):
        if not rows:
            return {"name": name, "sun_sign": chart["points"]["Sun"]["sign"],
                    "tightest_transit": None, "tightest_transit_hook": None}
        top = rows[0]
        hook = daily_transit_hook(top["transit"], top["natal"], top["aspect"])
        return {"name": name, "sun_sign": chart["points"]["Sun"]["sign"],
                "tightest_transit": top, "tightest_transit_hook": hook}

    payload["teaser"] = {
        "person_a": _teaser_for(a.get("name", "Person A"), chart_a, rows_a),
        "person_b": (_teaser_for(b.get("name", "Person B"), chart_b, rows_b)
                     if chart_b is not None else None),
    }

    # Paired mode: if today's tightest transit for either person is landing
    # on a point that's already part of a contact BETWEEN them, surface that
    # as the headline instead of two disconnected snapshots -- this is the
    # actual "alignment" the feature is named for.
    payload["teaser"]["shared_hook"] = None
    if chart_b is not None and rows_a and rows_b:
        activated = find_activated_contact(rows_a, rows_b, contacts)
        if activated:
            transit_row, who, contact = activated
            payload["teaser"]["shared_hook"] = activated_contact_hook(
                a.get("name", "Person A"), b.get("name", "Person B"),
                transit_row, who, contact)

    payload["prompt_data"] = build_daily_prompt_data(
        today, a.get("name", "Person A"), chart_a, rows_a,
        b.get("name", "Person B") if b else None, chart_b, rows_b,
        shared_contacts=contacts)
    return jsonify(payload)


@app.route("/healthz", methods=["GET"])
def healthz():
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
