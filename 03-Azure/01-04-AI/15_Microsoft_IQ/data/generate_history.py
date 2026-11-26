"""Generate the Caldova history tables for the Fabric IQ lakehouse.

Writes two files next to the other lakehouse tables:
  lakehouse/sales_orders_history.csv
  lakehouse/supplier_deliveries_history.csv

The output is deterministic: a fixed seed, no clock reads, and "\n" line
endings, so running the script again reproduces the files byte for byte.
History covers the 12 months before Monday 7 December 2026 and never contains
the open orders (SO-9001 to SO-9004) or open POs (PO-7781, PO-7790, PO-7795).
Usage: python generate_history.py
"""

import csv
import io
import random
from datetime import date, timedelta
from pathlib import Path

SEED = 20261207
START = date(2025, 12, 7)
CUTOFF = date(2026, 12, 4)  # last day with any shipped or received history

LAKEHOUSE = Path(__file__).resolve().parent / "lakehouse"

UNIT_PRICE = {"PV-400": 410, "CV-90": 265, "BV-200": 120}

# customer_id, product_id, number of orders, total units for the year,
# promised lead time in days, on-time probability
CUSTOMER_PLAN = [
    ("CUS-01", "PV-400", 100, 15860, 14, 0.95),  # Brennmark, about 6.5 M EUR
    ("CUS-02", "CV-90", 80, 7200, 21, 0.92),     # Solvik, about 1.9 M EUR
    ("CUS-03", "PV-400", 90, 2250, 21, 0.90),    # Osterdal, about 0.9 M EUR
    ("CUS-04", "BV-200", 130, 13000, 10, 0.93),  # Ferrovia, about 1.6 M EUR
]

# supplier_id, component_id, port, deliveries per year, min qty, max qty
SUPPLY_PLAN = [
    ("SUP-01", "HX-220", "Esbjerg", 26, 800, 1200),
    ("SUP-03", "SL-12", "Malmö", 26, 1000, 1600),
    ("SUP-04", "ST-50", "Duisburg", 26, 900, 1400),
    ("SUP-04", "AC-3", "Duisburg", 26, 250, 400),
    ("SUP-05", "FX-8", "Klaipėda", 40, 600, 1000),
]

# Teglbruk Metall AS is the backup supplier for HX-220. It delivered small
# qualification lots only. Lot L-7731 failed the pressure test (QR-2026-118).
TEGLBRUK_LOTS = [
    ("PO-6214", "L-7310", 300, date(2026, 3, 12), date(2026, 3, 12), "passed"),
    ("PO-6538", "L-7522", 300, date(2026, 7, 9), date(2026, 7, 9), "passed"),
    ("PO-7702", "L-7731", 500, date(2026, 12, 4), date(2026, 12, 4), "failed"),
]

# The only two late Nordhavn deliveries: winter weather at Esbjerg.
NORDHAVN_WEATHER_DELAYS = {date(2025, 12, 18): 3, date(2026, 2, 12): 4}


def to_weekday(d):
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def split_units(rng, total, parts, step=10):
    weights = [rng.uniform(0.6, 1.4) for _ in range(parts)]
    scale = total / sum(weights)
    qty = [max(step, int(round(w * scale / step)) * step) for w in weights]
    qty[-1] += total - sum(qty)
    return qty


def write_csv(header, rows):
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return buf.getvalue()


def sales_history(rng):
    last_order_day = CUTOFF - timedelta(days=30)
    span = (last_order_day - START).days
    orders = []
    for customer, product, count, units, lead, p_on_time in CUSTOMER_PLAN:
        quantities = split_units(rng, units, count)
        for i, qty in enumerate(quantities):
            order_date = to_weekday(START + timedelta(days=int(span * (i + rng.random()) / count)))
            promised = to_weekday(order_date + timedelta(days=lead))
            if rng.random() < p_on_time:
                ship = to_weekday(promised - timedelta(days=rng.randint(0, 3)))
                if ship < order_date:
                    ship = order_date
            else:
                ship = to_weekday(promised + timedelta(days=rng.randint(1, 6)))
            orders.append((order_date, customer, product, qty, ship, promised))
    orders.sort(key=lambda o: (o[0], o[1]))
    rows = []
    for n, (order_date, customer, product, qty, ship, promised) in enumerate(orders, start=1):
        rows.append([
            f"SO-{8000 + n}", customer, product, qty,
            order_date.isoformat(), ship.isoformat(), promised.isoformat(),
            qty * UNIT_PRICE[product], "true" if ship <= promised else "false",
        ])
    header = ["order_id", "customer_id", "product_id", "quantity", "order_date",
              "ship_date", "promised_date", "order_value_eur", "on_time"]
    return write_csv(header, rows)


def delivery_history(rng):
    span = (CUTOFF - timedelta(days=7) - START).days
    deliveries = []
    for supplier, component, port, count, q_min, q_max in SUPPLY_PLAN:
        dates = [to_weekday(START + timedelta(days=int(span * (i + 0.5) / count))) for i in range(count)]
        weather = {}
        if supplier == "SUP-01":
            for weather_day, days in NORDHAVN_WEATHER_DELAYS.items():
                nearest = min(range(count), key=lambda i: abs((dates[i] - weather_day).days))
                dates[nearest] = weather_day
                weather[nearest] = days
        for i, promised in enumerate(dates):
            qty = rng.randint(q_min // 50, q_max // 50) * 50
            delay, reason = 0, ""
            if i in weather:
                delay, reason = weather[i], "storm weather at the port of Esbjerg"
            elif supplier != "SUP-01" and rng.random() < 0.08:
                delay = rng.randint(1, 2)
                reason = "carrier delay"
            actual = promised + timedelta(days=delay)
            deliveries.append([promised, actual, supplier, component, port, qty, delay, reason, "passed", None, None])
    for po, lot, qty, promised, actual, result in TEGLBRUK_LOTS:
        deliveries.append([promised, actual, "SUP-02", "HX-220", "Bergen", qty, 0, "", result, po, lot])
    deliveries.sort(key=lambda d: (d[0], d[2], d[3]))
    rows = []
    po_seq = 6000
    lot_seq = 7000
    for n, (promised, actual, supplier, component, port, qty, delay, reason, result, po, lot) in enumerate(deliveries, start=1):
        if po is None:
            po_seq += 1
            lot_seq += 1
            if po_seq in (6214, 6538):
                po_seq += 1
            if lot_seq in (7310, 7522, 7731):
                lot_seq += 1
            po, lot = f"PO-{po_seq}", f"L-{lot_seq}"
        rows.append([
            f"DL-{n:04d}", po, supplier, component, lot, qty, port,
            promised.isoformat(), actual.isoformat(), delay,
            "true" if delay == 0 else "false", result, reason,
        ])
    header = ["delivery_id", "po_id", "supplier_id", "component_id", "lot_id", "quantity",
              "port", "promised_date", "actual_date", "delay_days", "on_time",
              "quality_result", "delay_reason"]
    return write_csv(header, rows)


def build():
    rng = random.Random(SEED)
    return {
        "sales_orders_history.csv": sales_history(rng),
        "supplier_deliveries_history.csv": delivery_history(rng),
    }


def main():
    LAKEHOUSE.mkdir(parents=True, exist_ok=True)
    for name, text in build().items():
        (LAKEHOUSE / name).write_bytes(text.encode("utf-8"))
        print(f"wrote {name}: {text.count(chr(10)) - 1} rows")


if __name__ == "__main__":
    main()
