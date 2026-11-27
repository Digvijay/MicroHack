"""Validate the Strandvik data against scenario-facts.md (v2).

Stdlib only, Python 3.10+. Usage: python validate_data.py
Exits with code 1 if any check fails.
"""

import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path

DATA = Path(__file__).resolve().parent
HACK = DATA.parent
LAKE = DATA / "lakehouse"
DOCS = DATA / "documents"
EVAL = DATA / "eval"
SEED = DATA / "workiq" / "strandvik-seed.json"
SEED_COPY = HACK / "labautomation" / "workiq-emulator" / "seed" / "strandvik.json"
ONTOLOGY = DATA / "foundry-iq" / "strandvik-ontology.jsonld"

SCHEMAS = {
    "sites.csv": ["site_id", "site_name", "site_type", "operator", "customer_id", "city", "country", "time_zone"],
    "customers.csv": ["customer_id", "customer_name", "industry", "country", "tier", "main_site_id", "service_contract_id"],
    "people.csv": ["person_id", "first_name", "company", "role", "email", "base_location", "current_location", "time_zone"],
    "account_owners.csv": ["customer_id", "owner_person_id", "owner_role", "backup_person_id", "owner_since"],
    "approved_external_agents.csv": ["agent_id", "agent_name", "customer_id", "acts_for_person_id", "allowed_requests",
                                     "may_place_orders", "approved_date", "policy_id"],
    "machines.csv": ["machine_id", "machine_name", "customer_id", "site_id", "machine_type", "criticality",
                     "required_model", "drive_unit_serial", "status"],
    "drive_units.csv": ["serial", "model", "status", "condition", "site_id", "machine_id", "customer_id",
                        "manufactured_date", "last_test_date", "notes"],
    "reservations.csv": ["reservation_id", "serial", "customer_id", "machine_id", "purpose", "needed_by_date",
                         "owner_person_id", "status", "created_date", "policy_id"],
    "technicians.csv": ["technician_id", "first_name", "base_site_id", "certified_models", "email"],
    "technician_schedule.csv": ["slot_id", "technician_id", "site_id", "customer_id", "start_time", "end_time",
                                "shift", "status", "booking_ref"],
    "transport_options.csv": ["option_id", "origin_site_id", "destination_site_id", "mode", "route", "carrier",
                              "transit_hours_min", "transit_hours_max", "cost_eur", "earliest_departure",
                              "earliest_arrival", "needs_kam_approval", "notes"],
    "price_list.csv": ["item_code", "description", "model", "list_price_eur", "unit", "valid_from", "valid_to"],
    "service_contracts.csv": ["contract_id", "customer_id", "document_name", "start_date", "end_date",
                              "annual_value_eur", "replacement_target_hours", "uptime_credit_pct_per_day",
                              "covered_machines"],
    "service_cases.csv": ["case_id", "opened_at", "customer_id", "machine_id", "drive_unit_serial", "channel",
                          "requested_by", "owner_person_id", "status", "summary", "closed_at"],
}

DOC_REQUIREMENTS = {
    "external-agent-access-policy-eap-01.md": [
        "EAP-01", "must be identified", "the company it works for **and** the person it acts for",
        "may request **price and delivery** (a quote)", "**They may not place orders.**",
        "Every external request opens a case", "goes to the account owner", "Quotes are valid for 24 hours",
        "**Only the key account manager can commit** a delivery date or a price", "maria-procurement"],
    "reservation-policy-res-02.md": [
        "RES-02", "belongs to its reservation until the **owner** releases it", "is **not** a release",
        "**A note is a reason to ask.**", "owner's approval in writing (a chat message counts)",
        "must still get an equal unit in time", "accountable for the cost risk"],
    "service-contract-kolvo-sc-kol-2024.md": [
        "SC-KOL-2024", "press lines 1 to 3", "**replacement target of 48 hours** from the request",
        "Strandvik installs", "0.5% of the annual contract value per day of downtime beyond the target",
        "Kolvo's agent may request quotes on Maria's behalf. Orders need Maria's approval.", "1,240,000 EUR"],
    "service-contract-poliden-sc-pol-2025.md": [
        "SC-POL-2025", "reserved at least 5 working days ahead",
        "Poliden must confirm date changes in writing from its maintenance planner", "C3"],
    "logistics-rules-log-03.md": [
        "LOG-03", "truck and ferry (Kiel to Gothenburg) takes about 25 hours", "about 2,800 EUR",
        "30 to 36 hours door to door", "about 40,000 EUR", "A flight hold can be kept for 6 hours without cost",
        "Bookings above 10,000 EUR need KAM approval"],
    "sd-900-product-sheet.md": [
        "replaces SD-900s only (not SD-700)", "Installation takes 6 to 8 hours and needs a certified technician"],
    "technician-scheduling-fs-04.md": [
        "FS-04", "available at Kolvo on **Wednesday night (22:00 to 06:00)**",
        "A night install needs 24 hours' notice", "FS-5101", "Wednesday from 22:00 to Thursday at 06:00"],
}
CALENDAR_DATE = re.compile(r"\b\d{1,2} (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\b"
                           r"|\b(January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}\b"
                           r"|\b20\d\d\b")
DATE_IDS = re.compile(r"\bSC-(KOL|POL)-20\d\d\b", re.I)


def calendar_dates(text):
    return [m.group(0) for m in CALENDAR_DATE.finditer(DATE_IDS.sub("", text))]


HEADER_FIELDS = ["Document id", "Title", "Owner role", "Effective date", "Version"]

failures: list[str] = []
passes = 0


def check(condition, message):
    global passes
    if condition:
        passes += 1
    else:
        failures.append(message)


def read(name):
    with open(LAKE / name, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def by_key(rows, key):
    return {r[key]: r for r in rows}


def dt(value):
    return datetime.fromisoformat(value)


def check_lakehouse():
    files = sorted(p.name for p in LAKE.glob("*.csv"))
    check(files == sorted(SCHEMAS), f"lakehouse files = {files}")
    t = {}
    for name, header in SCHEMAS.items():
        with open(LAKE / name, encoding="utf-8") as f:
            actual = f.readline().rstrip("\r\n").split(",")
        check(actual == header, f"{name}: header {actual} != {header}")
        rows = read(name)
        check(len(rows) > 0, f"{name}: no rows")
        for i, r in enumerate(rows):
            check(None not in r and all(v is not None for v in r.values()), f"{name} row {i + 2}: wrong column count")
        key = header[0]
        check(len({r[key] for r in rows}) == len(rows), f"{name}: duplicate {key}")
        t[name[:-4]] = rows
    return t


def check_integrity(t):
    sites = by_key(t["sites"], "site_id")
    customers = by_key(t["customers"], "customer_id")
    people = by_key(t["people"], "person_id")
    machines = by_key(t["machines"], "machine_id")
    units = by_key(t["drive_units"], "serial")
    techs = by_key(t["technicians"], "technician_id")
    contracts = by_key(t["service_contracts"], "contract_id")

    for s in sites.values():
        check(not s["customer_id"] or s["customer_id"] in customers, f"site {s['site_id']}: unknown customer")
    for c in customers.values():
        check(c["main_site_id"] in sites, f"customer {c['customer_id']}: unknown site")
        check(c["service_contract_id"] in contracts, f"customer {c['customer_id']}: unknown contract")
    for o in t["account_owners"]:
        check(o["customer_id"] in customers, f"account owner: unknown customer {o['customer_id']}")
        check(o["owner_person_id"] in people and o["backup_person_id"] in people, f"account owner {o['customer_id']}: unknown person")
    check(set(customers) == {o["customer_id"] for o in t["account_owners"]}, "every customer needs exactly one owner")
    for a in t["approved_external_agents"]:
        check(a["customer_id"] in customers and a["acts_for_person_id"] in people, f"agent {a['agent_id']}: bad reference")
        check(a["may_place_orders"] == "false", f"agent {a['agent_id']}: external agents may not place orders")
    for m in machines.values():
        check(m["customer_id"] in customers and m["site_id"] in sites, f"machine {m['machine_id']}: bad reference")
        check(sites[m["site_id"]]["customer_id"] == m["customer_id"], f"machine {m['machine_id']}: site of another customer")
        u = units.get(m["drive_unit_serial"])
        check(u is not None, f"machine {m['machine_id']}: unknown drive unit")
        if u:
            check(u["machine_id"] == m["machine_id"] and u["status"] == "installed", f"machine {m['machine_id']}: unit not installed on it")
            check(u["model"] == m["required_model"], f"machine {m['machine_id']}: model mismatch")
            check(u["site_id"] == m["site_id"], f"machine {m['machine_id']}: unit at another site")
    for u in units.values():
        check(u["model"] in ("SD-900", "SD-700"), f"{u['serial']}: bad model")
        check(u["serial"].startswith({"SD-900": "SD9-", "SD-700": "SD7-"}.get(u["model"], "?")), f"{u['serial']}: serial prefix != model")
        check(u["status"] in ("installed", "in_stock", "in_repair", "sold"), f"{u['serial']}: bad status")
        check(u["site_id"] in sites, f"{u['serial']}: unknown site")
        check(not u["customer_id"] or u["customer_id"] in customers, f"{u['serial']}: unknown customer")
        if u["status"] == "installed":
            check(u["machine_id"] in machines and machines[u["machine_id"]]["drive_unit_serial"] == u["serial"],
                  f"{u['serial']}: installed but machine does not run on it")
        else:
            check(not u["machine_id"], f"{u['serial']}: not installed but has a machine")
    for r in t["reservations"]:
        check(r["serial"] in units and r["customer_id"] in customers and r["machine_id"] in machines
              and r["owner_person_id"] in people, f"{r['reservation_id']}: bad reference")
        if r["machine_id"] in machines:
            check(machines[r["machine_id"]]["customer_id"] == r["customer_id"], f"{r['reservation_id']}: machine of another customer")
            if r["serial"] in units:
                check(units[r["serial"]]["model"] == machines[r["machine_id"]]["required_model"], f"{r['reservation_id']}: model mismatch")
        owner = next((o for o in t["account_owners"] if o["customer_id"] == r["customer_id"]), None)
        check(owner is not None and owner["owner_person_id"] == r["owner_person_id"], f"{r['reservation_id']}: owner is not the account owner")
    for tech in techs.values():
        check(tech["base_site_id"] in sites, f"{tech['technician_id']}: unknown site")
    for s in t["technician_schedule"]:
        check(s["technician_id"] in techs and s["site_id"] in sites and s["customer_id"] in customers, f"{s['slot_id']}: bad reference")
        check(dt(s["end_time"]) > dt(s["start_time"]), f"{s['slot_id']}: end before start")
    for o in t["transport_options"]:
        check(o["origin_site_id"] in sites and o["destination_site_id"] in sites, f"{o['option_id']}: bad site")
        check(o["needs_kam_approval"] == ("true" if int(o["cost_eur"]) > 10000 else "false"), f"{o['option_id']}: KAM approval flag != cost > 10,000 EUR")
        check(dt(o["earliest_arrival"]) > dt(o["earliest_departure"]), f"{o['option_id']}: arrival before departure")
    for c in contracts.values():
        check(c["customer_id"] in customers, f"{c['contract_id']}: unknown customer")
        check(not c["document_name"] or (DOCS / c["document_name"]).exists(), f"{c['contract_id']}: document missing")
        for m in c["covered_machines"].split(";"):
            check(m in machines and machines[m]["customer_id"] == c["customer_id"], f"{c['contract_id']}: bad machine {m}")
    for k in t["service_cases"]:
        check(re.fullmatch(r"CS-\d{5}", k["case_id"]) is not None, f"{k['case_id']}: bad format")
        check(k["customer_id"] in customers and k["machine_id"] in machines and k["drive_unit_serial"] in units
              and k["owner_person_id"] in people, f"{k['case_id']}: bad reference")
        check(not k["requested_by"] or k["requested_by"] in people, f"{k['case_id']}: unknown requester")
        check(dt(k["opened_at"]) < dt("2026-12-15T02:13:00+01:00"), f"{k['case_id']}: opened after 02:13")
    return sites, customers, people, machines, units


def check_facts(t, people, machines, units):
    get = lambda name, key, val: next((r for r in t[name] if r[key] == val), {})
    first = lambda pid: people.get(pid, {}).get("first_name")
    kol, pol = get("customers", "customer_name", "Kolvo AB"), get("customers", "customer_name", "Poliden AB")
    check(kol.get("main_site_id") == "SITE-KOL-HIS" and pol.get("main_site_id") == "SITE-POL-SKE", "Kolvo or Poliden site wrong")
    check(get("sites", "site_id", "SITE-PUN-FAC").get("city") == "Pune", "Pune factory missing")
    check(get("sites", "site_id", "SITE-RTM-WH").get("city") == "Rotterdam", "Rotterdam warehouse missing")
    check(get("sites", "site_id", "SITE-GOT-HQ").get("city") == "Gothenburg", "Gothenburg HQ missing")
    check(first(get("account_owners", "customer_id", kol.get("customer_id")).get("owner_person_id")) == "Alex", "Alex must own Kolvo")
    check(first(get("account_owners", "customer_id", pol.get("customer_id")).get("owner_person_id")) == "Sam", "Sam must own Poliden")
    check("Singapore" in people.get("P-SAM", {}).get("current_location", ""), "Sam must be in Singapore")
    check(get("approved_external_agents", "customer_id", "CUST-KOL").get("acts_for_person_id") == "P-MARIA", "Kolvo agent must act for Maria")
    check(get("approved_external_agents", "customer_id", "CUST-KOL").get("allowed_requests") == "price;delivery", "Kolvo agent: price and delivery only")

    pl2 = next((m for m in machines.values() if m["machine_name"] == "Press line 2" and m["customer_id"] == "CUST-KOL"), {})
    check(pl2.get("drive_unit_serial") == "SD9-K-0412" and pl2.get("required_model") == "SD-900", "Kolvo press line 2 must run on SD9-K-0412 (SD-900)")
    check({m["machine_name"] for m in machines.values() if m["customer_id"] == "CUST-KOL" and m["criticality"] == "critical"}
          == {"Press line 1", "Press line 2", "Press line 3"}, "Kolvo critical machines must be press lines 1 to 3")
    c3 = next((m for m in machines.values() if m["machine_name"] == "Crusher line C3"), {})
    check(c3.get("customer_id") == "CUST-POL" and c3.get("required_model") == "SD-900", "Poliden crusher C3 must run an SD-900")

    candidates = sorted(u["serial"] for u in units.values() if u["model"] == "SD-900" and u["status"] == "in_stock")
    check(candidates == ["SD9-P-0981", "SD9-R-0733"], f"in-stock SD-900 units = {candidates}")
    check(units.get("SD9-P-0981", {}).get("site_id") == "SITE-PUN-FAC" and units["SD9-P-0981"]["condition"] == "new_tested", "SD9-P-0981 must be new and tested at Pune")
    check(units.get("SD9-R-0733", {}).get("site_id") == "SITE-RTM-WH", "SD9-R-0733 must be in Rotterdam")
    check(any(u["model"] == "SD-700" and u["status"] == "in_stock" and u["site_id"] == "SITE-RTM-WH" for u in units.values()),
          "need an SD-700 distractor in stock in Rotterdam")

    rsv = get("reservations", "reservation_id", "RSV-2291")
    check(rsv.get("serial") == "SD9-R-0733" and rsv.get("customer_id") == "CUST-POL" and rsv.get("machine_id") == c3.get("machine_id")
          and rsv.get("needed_by_date") == "2026-12-21" and first(rsv.get("owner_person_id")) == "Sam" and rsv.get("status") == "active",
          "RSV-2291 must reserve SD9-R-0733 for Poliden C3 for next Monday's stop, owner Sam, active")
    check(not any(r["serial"] == "SD9-P-0981" for r in t["reservations"]), "SD9-P-0981 must be unreserved")
    active = [r["serial"] for r in t["reservations"] if r["status"] == "active"]
    check(len(active) == len(set(active)), "a unit has two active reservations")

    slot = [s for s in t["technician_schedule"] if s["site_id"] == "SITE-KOL-HIS" and s["status"] == "available"]
    check(len(slot) == 1 and slot[0]["start_time"] == "2026-12-16T22:00:00+01:00" and slot[0]["end_time"] == "2026-12-17T06:00:00+01:00"
          and slot[0]["shift"] == "night", "Kolvo needs exactly one available slot: Wednesday 22:00 to Thursday 06:00")
    if slot:
        tech = get("technicians", "technician_id", slot[0]["technician_id"])
        check("SD-900" in tech.get("certified_models", ""), "Kolvo slot technician must be SD-900 certified")

    road = next((o for o in t["transport_options"] if o["origin_site_id"] == "SITE-RTM-WH" and o["destination_site_id"] == "SITE-KOL-HIS"), {})
    check(road.get("transit_hours_min") == "25" and road.get("cost_eur") == "2800" and "ferry" in road.get("route", "")
          and road.get("earliest_departure") == "2026-12-15T08:00:00+01:00" and road.get("earliest_arrival") == "2026-12-16T09:00:00+01:00",
          "Rotterdam to Kolvo must be truck and ferry, 25 h, 2,800 EUR, 08:00 Tue to 09:00 Wed")
    air = next((o for o in t["transport_options"] if o["origin_site_id"] == "SITE-PUN-FAC" and o["destination_site_id"] == "SITE-KOL-HIS"), {})
    check(air.get("mode") == "air" and air.get("transit_hours_min") == "30" and air.get("transit_hours_max") == "36"
          and air.get("cost_eur") == "40000" and air.get("earliest_arrival") == "2026-12-16T19:00:00+01:00" and "17:30" in air.get("notes", ""),
          "Pune to Kolvo must be air, 30 to 36 h, 40,000 EUR, Landvetter 17:30, Kolvo 19:00 Wed")

    sc = get("service_contracts", "contract_id", "SC-KOL-2024")
    check(sc.get("replacement_target_hours") == "48" and sc.get("uptime_credit_pct_per_day") == "0.5" and sc.get("annual_value_eur") == "1240000",
          "SC-KOL-2024: 48 h, 0.5% per day, 1,240,000 EUR")
    check(get("service_contracts", "contract_id", "SC-POL-2025").get("customer_id") == "CUST-POL", "SC-POL-2025 missing")
    check(not any(k["case_id"] == "CS-88412" for k in t["service_cases"]), "CS-88412 must not exist yet (opened live)")


def check_documents():
    files = sorted(p.name for p in DOCS.glob("*.md"))
    check(files == sorted(DOC_REQUIREMENTS), f"documents = {files}")
    for name, required in DOC_REQUIREMENTS.items():
        path = DOCS / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        words = len(re.findall(r"\S+", text))
        check(250 <= words <= 1500, f"{name}: {words} words, expected 250 to 1500")
        for field in HEADER_FIELDS:
            check(re.search(rf"^\| {field} \| .+ \|$", text, re.M) is not None, f"{name}: header field {field} missing")
        for term in required:
            check(term in text, f"{name}: missing '{term}'")
        found = calendar_dates(text)
        check(not found, f"{name}: calendar dates {found}, use weekday and clock time")


def check_seed():
    raw = SEED.read_text(encoding="utf-8")
    pack = json.loads(raw)
    check(SEED_COPY.exists() and SEED_COPY.read_text(encoding="utf-8") == raw, "emulator seed copy differs from data/workiq/strandvik-seed.json")
    check(pack.get("schemaVersion") == 1 and pack.get("scenario") == "strandvik", "seed schemaVersion/scenario wrong")
    personas = {p["id"]: p for p in pack["personas"]}
    check(personas.get("alex", {}).get("mail") == "alex@strandvik.example", "persona alex missing")
    check(personas.get("sam", {}).get("mail") == "sam@strandvik.example", "persona sam missing")
    check(personas.get("maria", {}).get("mail", "").endswith("@kolvo.example"), "persona maria must be @kolvo.example")
    check(personas.get("poliden-planner", {}).get("mail", "").endswith("@poliden.example"), "persona poliden-planner missing")
    items = {i["id"]: i for i in pack["items"]}
    check(len(items) == len(pack["items"]), "duplicate seed item ids")
    for i in pack["items"]:
        for p in i["visibleTo"] + i.get("members", []):
            check(p in personas, f"seed item {i['id']}: unknown persona {p}")
        dates = [i["date"]] + [m["date"] for m in i.get("messages", [])]
        check(all(dt(d).utcoffset() is not None for d in dates), f"seed item {i['id']}: date without offset")
    vis = lambda k: set(items.get(k, {}).get("visibleTo", []))
    w1 = items.get("W1", {})
    check(w1.get("type") == "chat" and {"sam", "alex", "sales-leadership"} <= vis("W1"), "W1 must be a chat visible to Sam, Alex and sales leadership")
    check(any(m["from"] == "sam" and m["date"] == "2026-12-11T16:20:00+01:00" and "probably move two weeks" in m["text"]
              for m in w1.get("messages", [])), "W1 must hold Sam's note of Friday 16:20")
    check(items.get("W2", {}).get("type") == "email" and vis("W2") == {"sam"}
          and "We will confirm any change in writing" in items["W2"].get("body", ""), "W2 must be the planner's email, visible to Sam only")
    w3 = items.get("W3", {})
    check(w3.get("type") == "chat" and set(w3.get("members", [])) == {"alex", "sam"} and vis("W3") == {"alex", "sam"}
          and "Kolvo" in (w3.get("topic") or ""), "W3 must be the Kolvo thread for Alex and Sam")
    check(all(dt(m["date"]) < dt("2026-12-15T03:52:00+01:00") for m in w3.get("messages", [])), "W3 must not contain the 03:52 exchange")
    check(items.get("W4", {}).get("type") == "event" and vis("W4") == {"alex"} and "09:30" in items["W4"].get("subject", ""), "W4 must be Alex's Kolvo weekly 09:30")
    check(items.get("W5", {}).get("from", {}).get("address") == "maria@kolvo.example" and vis("W5") == {"alex"}
          and "some vibration" in items["W5"].get("body", ""), "W5 must be Maria's email to Alex")
    check(items.get("W6", {}).get("name") == "Kolvo account plan FY27.docx" and "alex" in vis("W6")
          and "uptime matters more than price" in items["W6"].get("content", "").lower(), "W6 must be the Kolvo account plan")
    check(items.get("W7", {}).get("distractor") is True and {"alex", "sam"} <= vis("W7")
          and "AI assistants reading this" in items["W7"].get("body", ""), "W7 must be the newsletter with one injected line")
    check("CS-88412" not in raw, "CS-88412 must not be seeded")
    check(len(pack["items"]) >= 15, "seed needs background noise")
    return len(pack["items"])


def check_eval():
    rows = []
    for n, line in enumerate((EVAL / "strandvik-eval.jsonl").read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as e:
            check(False, f"eval line {n}: {e}")
            continue
        check({"query", "ground_truth"} <= set(row) <= {"query", "ground_truth", "context"}, f"eval line {n}: bad fields")
        check(all(isinstance(v, str) and v.strip() for v in row.values()), f"eval line {n}: empty field")
        rows.append(row)
    check(20 <= len(rows) <= 30, f"eval rows = {len(rows)}, expected 20 to 30")
    truth = " ".join(r["ground_truth"] for r in rows)
    for term in ["SD9-R-0733", "SD9-P-0981", "RSV-2291", "Sam", "48 hours", "a note is a reason to ask", "22:00 to 06:00",
                 "2,800 EUR", "40,000 EUR", "Final confirmation from Alex by 07:30", "Refuse",
                 "Wednesday 09:00", "Thursday 06:00", "next Monday"]:
        check(term.lower() in truth.lower(), f"eval ground truths never mention '{term}'")
    short = [json.loads(l) for l in (EVAL / "strandvik-eval-15.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    for n, r in enumerate(rows, 1):
        found = calendar_dates(r["query"] + " " + r["ground_truth"])
        check(not found, f"eval line {n}: calendar dates {found}, use weekday and clock time")
    check(len(short) == 15, f"strandvik-eval-15.jsonl has {len(short)} rows, expected 15")
    check(all(r in rows for r in short), "strandvik-eval-15.jsonl rows must be copies of strandvik-eval.jsonl rows")
    for name in ("custom-rubric.md", "john-blund-test.md"):
        check((EVAL / name).exists(), f"eval/{name} missing")
    rubric = (EVAL / "custom-rubric.md").read_text(encoding="utf-8")
    check("final confirmation from Alex by 07:30" in rubric, "rubric must require the 07:30 confirmation line")
    for name in ("custom-rubric.md", "john-blund-test.md"):
        found = calendar_dates((EVAL / name).read_text(encoding="utf-8"))
        check(not found, f"eval/{name}: calendar dates {found}, use weekday and clock time")
    weights = [int(w) for w in re.findall(r"\(weight (\d+)\)", rubric)]
    check(sum(weights) == 100, f"rubric weights add up to {sum(weights)}")
    return len(rows)


def check_ontology():
    onto = json.loads(ONTOLOGY.read_text(encoding="utf-8"))
    ids = {n["@id"] for n in onto["@graph"]}
    for c in ["DriveUnit", "Machine", "Site", "Customer", "Reservation", "Person", "Owner", "ServiceContract", "Policy", "Transport"]:
        check(f"sv:{c}" in ids, f"ontology class {c} missing")
    for p in ["runsOn", "locatedAt", "reservedFor", "ownedBy", "coveredBy", "governs"]:
        check(f"sv:{p}" in ids, f"ontology relation {p} missing")
    check(all(n.get("rdfs:comment") for n in onto["@graph"]), "every ontology node needs an rdfs:comment")


def check_no_dashes():
    targets = [p for p in DATA.rglob("*") if p.is_file() and p.suffix in {".csv", ".md", ".json", ".jsonl", ".jsonld", ".py"}]
    targets.append(SEED_COPY)
    for path in targets:
        if path.exists():
            text = path.read_text(encoding="utf-8")
            check("\u2014" not in text and "\u2013" not in text, f"{path.name}: em or en dash found")


def main():
    t = check_lakehouse()
    _, _, people, machines, units = check_integrity(t)
    check_facts(t, people, machines, units)
    check_documents()
    n_items = check_seed()
    n_eval = check_eval()
    check_ontology()
    check_no_dashes()
    print("lakehouse rows: " + ", ".join(f"{k} {len(v)}" for k, v in t.items()))
    print(f"seed items: {n_items}")
    print(f"eval rows: {n_eval}")
    print(f"checks passed: {passes}, failed: {len(failures)}")
    for f in failures:
        print(f"FAIL: {f}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
