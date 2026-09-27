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
from engine import build_chart, pair_payload
from birth_cards import birth_cards, pair_links
from contact_hooks import contact_hook
import datetime as dt

app = Flask(__name__)

REQUIRED = ("year", "month", "day", "timezone")


def _bad(msg, code=400):
    return jsonify({"error": msg}), code


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


@app.route("/healthz", methods=["GET"])
def healthz():
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
