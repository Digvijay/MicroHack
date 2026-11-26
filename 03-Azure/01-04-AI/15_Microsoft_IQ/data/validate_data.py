"""Validate the Caldova data against walkthrough/scenario-facts.md.

Stdlib only. Usage: python validate_data.py
Exits with code 1 if any check fails.
"""

import csv
import importlib.util
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

DATA = Path(__file__).resolve().parent
LAKE = DATA / "lakehouse"
DOCS = DATA / "documents"
EVAL = DATA / "eval"
NOW = date(2026, 12, 7)
FRIDAY = date(2026, 12, 11)

CODES = ["PV-400", "CV-90", "BV-200", "HX-220", "SL-12", "ST-50", "FX-8", "AC-3"]
COMPANIES = ["Caldova Components AB", "Nordhavn Castings A/S", "Teglbruk Metall AS",
             "Kvarnby Polymers AB", "Rhein Präzision GmbH", "Baltic Fasteners UAB",
             "Brennmark Industries GmbH", "Solvik Marine AS", "Østerdal Pumps AS",
             "Ferrovia Systems S.p.A."]

DOC_REQUIREMENTS = {
    "supplier-agreement-nordhavn.md": ["SA-2025-014", "Nordhavn Castings A/S", "HX-220", "PV-400", "CV-90",
                                       "Esbjerg", "21 days", "Teglbruk Metall AS", "SQP-04", "Supply Planner"],
    "supplier-agreement-teglbruk.md": ["Teglbruk Metall AS", "HX-220", "backup supplier for HX-220", "10 days",
                                       "incoming inspection", "SQP-04"],
    "customer-agreement-brennmark.md": ["FA-2024-007", "Brennmark Industries GmbH", "PV-400", "Hamburg",
                                        "compressor line", "agrees in writing", "2% of the late value per week",
                                        "capped at 10%", "port closures declared by a public authority",
                                        "within 48 hours", "Purchasing Manager"],
    "customer-agreement-solvik.md": ["FA-2025-002", "Solvik Marine AS", "CV-90", "ballast", "Bergen",
                                     "No partial deliveries", "1% of the order value per week",
                                     "capped at 10%", "within 48 hours"],
    "customer-agreement-osterdal.md": ["Østerdal Pumps AS", "PV-400", "municipal water", "Oslo",
                                       "Partial deliveries are allowed", "No penalty"],
    "customer-agreement-ferrovia.md": ["Ferrovia Systems S.p.A.", "BV-200", "rail braking"],
    "supplier-quality-policy-sqp-04.md": ["SQP-04", "No component from a supplier with status \"quality hold\" may be used without a written deviation approved by the Quality Head",
                                          "Deviations are not granted for pressure-bearing parts", "HX-220 is pressure-bearing"],
    "allocation-policy-ap-02.md": ["AP-02", "Strategic customers", "Key customers", "Standard customers",
                                   "by due date", "Plant Manager may override this allocation order in writing"],
    "quality-report-qr-2026-118.md": ["QR-2026-118", "L-7731", "HX-220", "Teglbruk Metall AS",
                                      "4 December 2026", "quality hold", "16 December 2026", "corrective action"],
    "product-catalogue.md": ["PV-400 contains HX-220, SL-12, ST-50 and FX-8", "CV-90 contains HX-220, AC-3 and FX-8",
                             "BV-200 contains ST-50, SL-12 and FX-8"] + CODES,
}
HEADER_FIELDS = ["Document id", "Title", "Owner role", "Effective date", "Version"]
PERSONAS = {"supply-planner", "sales-lead", "quality-head", "plant-manager"}
IQS = {"web", "fabric", "foundry", "work"}
CHALLENGE_COUNTS = {1: 2, 2: 3, 3: 4, 4: 4, 5: 4, 6: 2}

failures = []
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


def expect_rows(name, header, rows):
    data = read(name)
    with open(LAKE / name, encoding="utf-8") as f:
        actual_header = f.readline().strip().split(",")
    check(actual_header == header, f"{name}: header {actual_header} != {header}")
    actual = [[r[h] for h in header] for r in data]
    check(actual == rows, f"{name}: rows do not match scenario-facts.md")
    return data


def check_master_data():
    expect_rows("suppliers.csv", ["supplier_id", "name", "country", "port", "status"], [
        ["SUP-01", "Nordhavn Castings A/S", "Denmark", "Esbjerg", "active"],
        ["SUP-02", "Teglbruk Metall AS", "Norway", "Bergen", "quality_hold"],
        ["SUP-03", "Kvarnby Polymers AB", "Sweden", "Malmö", "active"],
        ["SUP-04", "Rhein Präzision GmbH", "Germany", "Duisburg", "active"],
        ["SUP-05", "Baltic Fasteners UAB", "Lithuania", "Klaipėda", "active"],
    ])
    expect_rows("components.csv", ["component_id", "name", "primary_supplier_id", "backup_supplier_id",
                                   "on_hand_boras", "unit_cost_eur", "pressure_bearing"], [
        ["HX-220", "Aluminium valve housing", "SUP-01", "SUP-02", "1200", "38", "true"],
        ["SL-12", "Seal kit", "SUP-03", "", "9000", "4", "false"],
        ["ST-50", "Valve stem", "SUP-04", "", "7000", "11", "false"],
        ["FX-8", "Fastener kit", "SUP-05", "", "20000", "1.5", "false"],
        ["AC-3", "Electric actuator", "SUP-04", "", "2500", "95", "false"],
    ])
    expect_rows("products.csv", ["product_id", "name", "unit_price_eur", "finished_goods_on_hand"], [
        ["PV-400", "Pump valve", "410", "600"],
        ["CV-90", "Control valve", "265", "0"],
        ["BV-200", "Ball valve", "120", "2500"],
    ])
    expect_rows("bill_of_materials.csv", ["product_id", "component_id", "qty_per_unit"], [
        [p, c, "1"] for p, cs in [("PV-400", ["HX-220", "SL-12", "ST-50", "FX-8"]),
                                   ("CV-90", ["HX-220", "AC-3", "FX-8"]),
                                   ("BV-200", ["ST-50", "SL-12", "FX-8"])] for c in cs
    ])
    expect_rows("customers.csv", ["customer_id", "name", "country", "tier"], [
        ["CUS-01", "Brennmark Industries GmbH", "Germany", "strategic"],
        ["CUS-02", "Solvik Marine AS", "Norway", "key"],
        ["CUS-03", "Østerdal Pumps AS", "Norway", "standard"],
        ["CUS-04", "Ferrovia Systems S.p.A.", "Italy", "key"],
    ])
    expect_rows("sales_orders.csv", ["order_id", "customer_id", "product_id", "quantity", "due_date",
                                     "order_value_eur"], [
        ["SO-9001", "CUS-01", "PV-400", "4000", "2026-12-11", "1640000"],
        ["SO-9002", "CUS-02", "CV-90", "800", "2026-12-18", "212000"],
        ["SO-9003", "CUS-03", "PV-400", "300", "2027-01-08", "123000"],
        ["SO-9004", "CUS-04", "BV-200", "1500", "2026-12-15", "180000"],
    ])
    expect_rows("purchase_orders.csv", ["po_id", "supplier_id", "component_id", "quantity", "port",
                                        "original_eta", "status"], [
        ["PO-7781", "SUP-01", "HX-220", "3500", "Esbjerg", "2026-12-08", "held_at_port"],
        ["PO-7790", "SUP-04", "ST-50", "4000", "Duisburg", "2026-12-10", "in_transit"],
        ["PO-7795", "SUP-03", "SL-12", "5000", "Malmö", "2026-12-09", "in_transit"],
    ])


def check_references_and_totals():
    suppliers = {r["supplier_id"]: r for r in read("suppliers.csv")}
    components = {r["component_id"]: r for r in read("components.csv")}
    products = {r["product_id"]: r for r in read("products.csv")}
    customers = {r["customer_id"]: r for r in read("customers.csv")}
    bom = defaultdict(dict)
    for r in read("bill_of_materials.csv"):
        check(r["product_id"] in products, f"BOM product {r['product_id']} unknown")
        check(r["component_id"] in components, f"BOM component {r['component_id']} unknown")
        bom[r["product_id"]][r["component_id"]] = int(r["qty_per_unit"])
    for c in components.values():
        check(c["primary_supplier_id"] in suppliers, f"{c['component_id']} primary supplier unknown")
        check(not c["backup_supplier_id"] or c["backup_supplier_id"] in suppliers,
              f"{c['component_id']} backup supplier unknown")
    orders = read("sales_orders.csv")
    for o in orders:
        check(o["customer_id"] in customers, f"{o['order_id']} customer unknown")
        check(o["product_id"] in products, f"{o['order_id']} product unknown")
        check(int(o["quantity"]) * int(products[o["product_id"]]["unit_price_eur"]) == int(o["order_value_eur"]),
              f"{o['order_id']} value != quantity x price")
    pos = read("purchase_orders.csv")
    for p in pos:
        check(p["supplier_id"] in suppliers, f"{p['po_id']} supplier unknown")
        check(p["component_id"] in components, f"{p['po_id']} component unknown")
        check(p["port"] == suppliers[p["supplier_id"]]["port"], f"{p['po_id']} port != supplier port")

    hx_value = sum(int(o["order_value_eur"]) for o in orders if "HX-220" in bom[o["product_id"]])
    check(hx_value == 1975000, f"orders depending on HX-220 = {hx_value}, expected 1975000")
    nordhavn_parts = {c for c, r in components.items() if r["primary_supplier_id"] == "SUP-01"}
    nordhavn_customers = sorted(customers[o["customer_id"]]["name"] for o in orders
                                if nordhavn_parts & set(bom[o["product_id"]]))
    check(nordhavn_customers == ["Brennmark Industries GmbH", "Solvik Marine AS", "Østerdal Pumps AS"],
          f"Nordhavn-dependent customers = {nordhavn_customers}")

    available = {c: int(r["on_hand_boras"]) for c, r in components.items()}
    for p in pos:
        if p["status"] != "held_at_port" and date.fromisoformat(p["original_eta"]) <= FRIDAY:
            available[p["component_id"]] += int(p["quantity"])
    buildable = min(available[c] // q for c, q in bom["PV-400"].items())
    capacity = 400 * 5
    ready = int(products["PV-400"]["finished_goods_on_hand"]) + min(buildable, capacity)
    check(buildable == 1200, f"PV-400 buildable from parts = {buildable}, expected 1200")
    check(ready == 1800, f"PV-400 ready by Friday = {ready}, expected 1800")
    delayed_value = (4000 - ready) * int(products["PV-400"]["unit_price_eur"])
    check(delayed_value == 902000, f"Brennmark delayed value = {delayed_value}, expected 902000")
    check(delayed_value * 2 // 100 == 18040, "weekly penalty != 18040")
    return customers, products, suppliers, components


def check_history(customers, products, suppliers, components):
    open_orders = {r["order_id"] for r in read("sales_orders.csv")}
    open_pos = {r["po_id"] for r in read("purchase_orders.csv")}
    sales = read("sales_orders_history.csv")
    check(350 <= len(sales) <= 450, f"sales history rows = {len(sales)}")
    check(len({r["order_id"] for r in sales}) == len(sales), "duplicate order ids in sales history")
    revenue = Counter()
    for r in sales:
        check(r["order_id"] not in open_orders, f"open order {r['order_id']} in history")
        check(r["customer_id"] in customers and r["product_id"] in products, f"{r['order_id']} bad reference")
        od, sd, pd = (date.fromisoformat(r[k]) for k in ("order_date", "ship_date", "promised_date"))
        check(date(2025, 12, 7) <= od <= sd < NOW, f"{r['order_id']} dates out of range")
        check(int(r["quantity"]) * int(products[r["product_id"]]["unit_price_eur"]) == int(r["order_value_eur"]),
              f"{r['order_id']} value != quantity x price")
        check(r["on_time"] == ("true" if sd <= pd else "false"), f"{r['order_id']} on_time flag wrong")
        revenue[r["customer_id"]] += int(r["order_value_eur"])
    check(set(revenue) == set(customers), "not all customers in sales history")
    check({r["product_id"] for r in sales} == set(products), "not all products in sales history")
    check(revenue.most_common(1)[0][0] == "CUS-01", "Brennmark is not the largest customer")
    check(6300000 <= revenue["CUS-01"] <= 6700000, f"Brennmark yearly revenue = {revenue['CUS-01']}")

    deliveries = read("supplier_deliveries_history.csv")
    check(120 <= len(deliveries) <= 180, f"delivery history rows = {len(deliveries)}")
    for r in deliveries:
        check(r["po_id"] not in open_pos, f"open PO {r['po_id']} in delivery history")
        check(r["supplier_id"] in suppliers and r["component_id"] in components, f"{r['delivery_id']} bad reference")
        check(r["port"] == suppliers[r["supplier_id"]]["port"], f"{r['delivery_id']} port mismatch")
        check(date.fromisoformat(r["actual_date"]) < NOW, f"{r['delivery_id']} in the future")
    nordhavn_late = [r for r in deliveries if r["supplier_id"] == "SUP-01" and r["on_time"] == "false"]
    check(len(nordhavn_late) == 2 and all(date.fromisoformat(r["promised_date"]).month in (12, 1, 2)
                                          and "weather" in r["delay_reason"] for r in nordhavn_late),
          "Nordhavn must have exactly 2 winter weather delays")
    lot = [r for r in deliveries if r["lot_id"] == "L-7731"]
    check(len(lot) == 1 and lot[0]["supplier_id"] == "SUP-02" and lot[0]["component_id"] == "HX-220"
          and lot[0]["actual_date"] == "2026-12-04" and lot[0]["quality_result"] == "failed",
          "Teglbruk lot L-7731 failed on 2026-12-04 missing")
    check(sum(r["quality_result"] == "failed" for r in deliveries) == 1, "only L-7731 may fail")
    return len(sales), len(deliveries)


def check_reproducible():
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("generate_history", DATA / "generate_history.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name, text in module.build().items():
        check((LAKE / name).read_bytes() == text.encode("utf-8"), f"{name} differs from generate_history.py output")


def check_documents():
    files = sorted(p.name for p in DOCS.glob("*.md"))
    check(files == sorted(DOC_REQUIREMENTS), f"documents = {files}")
    corpus = ""
    for name, required in DOC_REQUIREMENTS.items():
        path = DOCS / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        corpus += text
        words = len(re.findall(r"\S+", text))
        check(300 <= words <= 900, f"{name}: {words} words, expected 300 to 900")
        for field in HEADER_FIELDS:
            check(re.search(rf"^\| {field} \| .+ \|$", text, re.M) is not None, f"{name}: header field {field} missing")
        for term in required:
            check(term in text, f"{name}: missing '{term}'")
        check(not re.search(r"\b(?:Mr|Mrs|Ms)\.? [A-Z]", text), f"{name}: named person found")
    for term in CODES + COMPANIES:
        check(term in corpus, f"corpus never mentions {term}")


def check_questions():
    items = json.loads((EVAL / "questions.json").read_text(encoding="utf-8"))
    check(14 <= len(items) <= 19, f"{len(items)} questions, expected 14 to 19")
    check(len({q.get("id") for q in items}) == len(items), "duplicate question ids")
    counts = Counter()
    rubric = (EVAL / "rubric.md").read_text(encoding="utf-8")
    required = {"id", "challenge", "persona", "iqs", "question", "gold", "must_include",
                "must_not_include", "web_citation_required"}
    for q in items:
        qid = q.get("id", "?")
        check(required <= set(q), f"{qid}: missing fields {required - set(q)}")
        check(set(q) <= required | {"expect_no_access", "follows"}, f"{qid}: unknown fields")
        if "follows" in q:
            check(q["follows"] in {x["id"] for x in items} and q["follows"] < qid,
                  f"{qid}: follows must name an earlier question")
        check(q["challenge"] in CHALLENGE_COUNTS, f"{qid}: bad challenge")
        counts[q["challenge"]] += 1
        check(q["persona"] in PERSONAS, f"{qid}: bad persona")
        check(set(q["iqs"]) <= IQS, f"{qid}: bad iqs")
        check(q["web_citation_required"] == (q["challenge"] == 2), f"{qid}: web_citation_required wrong")
        expected_iqs = {1: set(), 2: {"web"}, 3: {"fabric"}, 4: {"foundry"}, 5: {"work"}, 6: IQS}[q["challenge"]]
        check(set(q["iqs"]) == expected_iqs, f"{qid}: iqs do not match challenge")
        gold = q["gold"].lower()
        check(isinstance(q["must_include"], list) and q["must_include"], f"{qid}: must_include empty")
        for group in q["must_include"]:
            check(isinstance(group, list) and group and all(isinstance(a, str) for a in group),
                  f"{qid}: bad must_include group")
            check(any(a.lower() in gold for a in group), f"{qid}: gold does not contain any of {group}")
        for phrase in q["must_not_include"]:
            check(phrase.lower() not in gold, f"{qid}: gold contains forbidden '{phrase}'")
        check(f"| {qid} |" in rubric, f"rubric.md has no row for {qid}")
    check(dict(counts) == CHALLENGE_COUNTS, f"questions per challenge = {dict(counts)}")
    check(all(q["persona"] == "plant-manager" for q in items if q["challenge"] == 6),
          "capstone questions must use persona plant-manager")
    no_access = [q for q in items if q.get("expect_no_access")]
    check(len(no_access) == 1 and no_access[0]["persona"] == "sales-lead"
          and "16 December" in no_access[0]["must_not_include"], "persona trimming question wrong")
    return len(items)


def check_no_dashes():
    for path in DATA.rglob("*"):
        if path.is_file() and path.suffix in {".csv", ".md", ".json", ".py"}:
            text = path.read_text(encoding="utf-8")
            check("\u2014" not in text and "\u2013" not in text, f"{path.relative_to(DATA)}: em or en dash found")


def main():
    check_master_data()
    refs = check_references_and_totals()
    n_sales, n_deliveries = check_history(*refs)
    check_reproducible()
    check_documents()
    n_questions = check_questions()
    check_no_dashes()
    print(f"sales_orders_history rows: {n_sales}")
    print(f"supplier_deliveries_history rows: {n_deliveries}")
    print(f"questions: {n_questions}")
    print(f"checks passed: {passes}, failed: {len(failures)}")
    for f in failures:
        print(f"FAIL: {f}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
