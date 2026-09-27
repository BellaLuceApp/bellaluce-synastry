"""Tests the web service exactly the way Bubble's API Connector will call it:
real HTTP-shaped JSON in, JSON out. Uses Flask's test client (no network
needed), and checks against the same known values we've verified by hand
throughout this conversation."""
import json
from app import app

client = app.test_client()
fails = []


def check(label, got, want):
    ok = got == want
    print(("  ok   " if ok else "  FAIL ") + label + ": " + str(got) + ("" if ok else "  (expected %s)" % (want,)))
    if not ok:
        fails.append(label)


def call(a, b):
    r = client.post("/synastry", json={"person_a": a, "person_b": b})
    return r.status_code, r.get_json()


me = {"name": "You", "year": 1978, "month": 5, "day": 24, "timezone": "America/Sao_Paulo"}
m1 = {"name": "Man 1", "year": 1991, "month": 10, "day": 7, "timezone": "America/Los_Angeles"}
m3 = {"name": "Man 3", "year": 1977, "month": 11, "day": 10, "timezone": "Europe/Madrid"}

print("== /synastry: You + Man 1 ==")
code, data = call(me, m1)
check("HTTP 200", code, 200)
check("Sun signs", (data["teaser"]["person_a_sun_sign"], data["teaser"]["person_b_sun_sign"]), ("Gemini", "Libra"))
check("Tightest contact is the Selena/Node conjunction",
      (data["teaser"]["tightest_contact"]["a_point"], data["teaser"]["tightest_contact"]["b_point"],
       data["teaser"]["tightest_contact"]["aspect"]),
      ("Selena", "North Node", "conjunction"))
check("Birth cards", (data["teaser"]["person_a_birth_card"], data["teaser"]["person_b_birth_card"]),
      ("The Hermit", "Wheel of Fortune"))
check("No shared birth card with Man 1", data["teaser"]["shared_birth_card"], False)
check("Selena -> Node link still present in full payload",
      data["selena_north_node"]["A_selena_to_B_node"]["aspect"], "conjunction")

print("\n== /synastry: You + Man 3 (shared Hermit) ==")
code, data = call(me, m3)
check("HTTP 200", code, 200)
check("Shared birth card flag", data["teaser"]["shared_birth_card"], True)
check("Shared card is The Hermit", data["shared_birth_cards"][0]["card"], "The Hermit")

print("\n== Error handling ==")
code, data = call({"year": 1978, "month": 5, "day": 24}, m1)  # missing timezone
check("Missing timezone -> 400", code, 400)
code, data = call({"name": "x", "year": 1978, "month": 5, "day": 24, "timezone": "Not/AZone"}, m1)
check("Bad timezone name -> 400", code, 400)

print("\n== /healthz ==")
code, data = client.get("/healthz").status_code, client.get("/healthz").get_json()
check("health check", (code, data["ok"]), (200, True))

print("\nRESULT:", "all checks passed" if not fails else "FAILED: %s" % fails)
