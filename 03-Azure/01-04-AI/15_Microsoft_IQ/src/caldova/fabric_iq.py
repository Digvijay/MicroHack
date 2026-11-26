"""Fabric IQ: a lakehouse with Caldova's business data, a data agent (GA) and an ontology (preview)."""

from __future__ import annotations

import base64
import csv
import json
import time
import uuid

from .azure import AzureError, arm, fabric, onelake_upload, save_state, load_state
from .config import CONNECTIONS_API, DATA_DIR, settings

LAKEHOUSE = "caldova_lakehouse"
DATA_AGENT = "CaldovaOperations"
ONTOLOGY = "CaldovaSupply"
TABLE_DIR = DATA_DIR / "lakehouse"

AGENT_INSTRUCTIONS = """You answer questions about Caldova Components AB: suppliers, components, products,
bill of materials, customers, open sales orders, purchase orders and their history.
- A product depends on a supplier when one of its components (bill_of_materials) has that supplier as
  primary_supplier_id in components.
- order_value_eur is revenue. finished_goods_on_hand and on_hand_boras are stock in Boras.
- PV-400 that can be built from stock = finished_goods_on_hand + the smallest on_hand_boras of its components.
- Always show the numbers and the tables you used."""

SOURCE_INSTRUCTIONS = ("Tables: suppliers, components, products, bill_of_materials, customers, sales_orders "
                       "(open orders), purchase_orders (open POs), sales_orders_history, supplier_deliveries_history. "
                       "Join components.primary_supplier_id to suppliers.supplier_id. sales_orders holds OPEN orders "
                       "only: quantity is the full open quantity not yet shipped, and order_value_eur is its value. "
                       "Delayed units of an order = quantity minus the units that can ship. Codes starting with HX, "
                       "SL, ST, FX or AC are components (components.component_id, stock in on_hand_boras). Codes "
                       "starting with PV, CV or BV are products (products.product_id). Products and components are "
                       "identified by codes such as PV-400 and HX-220: filter on product_id or component_id, never on "
                       "the name column. Match company names with LIKE '%<short name>%' (for example LIKE '%Brennmark%').")

# Example questions with the SQL that answers them. Fabric data agents use these as few-shot examples.
FEW_SHOTS = [
    ("How many HX-220 do we have on hand in Boras?",
     "SELECT component_id, name, on_hand_boras FROM dbo.components WHERE component_id = 'HX-220'"),
    ("Show the open orders of Solvik.",
     "SELECT so.order_id, c.name AS customer, so.product_id, so.quantity, so.due_date, so.order_value_eur "
     "FROM dbo.sales_orders so JOIN dbo.customers c ON c.customer_id = so.customer_id WHERE c.name LIKE '%Solvik%'"),
    ("Which open orders depend on parts from Kvarnby Polymers?",
     "SELECT DISTINCT so.order_id, c.name AS customer, so.product_id, so.quantity, so.order_value_eur "
     "FROM dbo.sales_orders so JOIN dbo.customers c ON c.customer_id = so.customer_id "
     "JOIN dbo.bill_of_materials b ON b.product_id = so.product_id "
     "JOIN dbo.components co ON co.component_id = b.component_id "
     "JOIN dbo.suppliers s ON s.supplier_id = co.primary_supplier_id WHERE s.name LIKE '%Kvarnby%'"),
    ("How many BV-200 can we have ready from stock without new deliveries?",
     "SELECT p.product_id, p.finished_goods_on_hand, MIN(co.on_hand_boras / b.qty_per_unit) AS buildable_from_parts, "
     "p.finished_goods_on_hand + MIN(co.on_hand_boras / b.qty_per_unit) AS ready_total "
     "FROM dbo.products p JOIN dbo.bill_of_materials b ON b.product_id = p.product_id "
     "JOIN dbo.components co ON co.component_id = b.component_id WHERE p.product_id = 'BV-200' "
     "GROUP BY p.product_id, p.finished_goods_on_hand"),
]


def few_shots() -> dict:
    return {"$schema": "1.0.0", "fewShots": [
        {"id": str(uuid.uuid5(uuid.NAMESPACE_URL, q)), "question": q, "query": sql} for q, sql in FEW_SHOTS]}


def _b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode()


def _capacity_id() -> str:
    caps = fabric("GET", "/capacities").get("value", [])
    active = [c for c in caps if c.get("state") == "Active" and c.get("sku", "").startswith("F")]
    if settings.fabric_capacity:
        active = [c for c in active if c["displayName"] == settings.fabric_capacity] or active
    if not active:
        raise SystemExit("No active Fabric F-SKU capacity found. Check FABRIC_CAPACITY_NAME in src/.env and that "
                         "the capacity is running (Azure portal > your resource group > Fabric capacity > Resume).")
    return active[0]["id"]


def workspace() -> str:
    ws = next((w for w in fabric("GET", "/workspaces").get("value", [])
               if w["displayName"] == settings.fabric_workspace), None)
    if not ws:
        ws = fabric("POST", "/workspaces", {"displayName": settings.fabric_workspace, "capacityId": _capacity_id()})
    elif not ws.get("capacityId"):
        fabric("POST", f"/workspaces/{ws['id']}/assignToCapacity", {"capacityId": _capacity_id()})
    return ws["id"]


def _item(ws: str, kind: str, name: str) -> dict | None:
    return next((i for i in fabric("GET", f"/workspaces/{ws}/{kind}").get("value", [])
                 if i["displayName"] == name), None)


def load_lakehouse() -> dict:
    """Create the lakehouse and load every CSV in data/lakehouse as a Delta table."""
    ws = workspace()
    lh = _item(ws, "lakehouses", LAKEHOUSE) or fabric("POST", f"/workspaces/{ws}/lakehouses", {"displayName": LAKEHOUSE})
    lh_id = lh["id"]
    tables = []
    for f in sorted(TABLE_DIR.glob("*.csv")):
        onelake_upload(ws, lh_id, f"Files/caldova/{f.name}", f.read_bytes())
        body = {"relativePath": f"Files/caldova/{f.name}", "pathType": "File", "mode": "Overwrite",
                "formatOptions": {"format": "Csv", "header": True, "delimiter": ","}}
        for attempt in range(12):
            try:
                fabric("POST", f"/workspaces/{ws}/lakehouses/{lh_id}/tables/{f.stem}/load", body)
                break
            except AzureError as e:
                # An F2 capacity runs few Spark jobs at a time (HTTP 430). Wait for the previous load.
                if "TooManyRequestsForCapacity" not in str(e) or attempt == 11:
                    raise
                print(f"  capacity busy, waiting before loading {f.stem}...")
                time.sleep(20)
        tables.append(f.stem)
    props = fabric("GET", f"/workspaces/{ws}/lakehouses/{lh_id}")["properties"]
    sql = props.get("sqlEndpointProperties") or {}
    if sql.get("id"):
        # New Delta tables reach the SQL analytics endpoint after a metadata sync. The data agent reads
        # its schema from that endpoint, so sync now instead of waiting for the background refresh.
        try:
            fabric("POST", f"/workspaces/{ws}/sqlEndpoints/{sql['id']}/refreshMetadata", {})
        except AzureError as e:
            print(f"  SQL endpoint refresh skipped ({str(e)[:120]}). Wait 2 minutes before creating the data agent.")
    save_state(fabric_workspace_id=ws, lakehouse_id=lh_id, sql_endpoint=props.get("sqlEndpointProperties"),
               lakehouse_tables=tables)
    return {"workspace": ws, "lakehouse": lh_id, "tables": tables}


def create_data_agent(source: str = "lakehouse", examples: bool = True) -> dict:
    """Create and publish the Fabric data agent over the lakehouse tables (or the ontology).

    examples=True adds the few-shot example queries in FEW_SHOTS (Challenge 3 shows the difference)."""
    st = load_state()
    ws, lh = st.get("fabric_workspace_id"), st.get("lakehouse_id")
    if not lh:
        raise SystemExit("Load the lakehouse first: caldova fabric-iq load")
    if source == "ontology":
        onto = st.get("ontology_id")
        if not onto:
            raise SystemExit("Create the ontology first: caldova fabric-iq ontology")
        folder = f"ontology-{ONTOLOGY}"
        ds = {"$schema": "1.0.0", "artifactId": onto, "workspaceId": ws, "displayName": ONTOLOGY, "type": "graph",
              "dataSourceInstructions": "Use the ontology entities and relationships.", "elements": []}
    else:
        folder = f"lakehouse-tables-{LAKEHOUSE}"
        tables = []
        for t in st.get("lakehouse_tables", []):
            cols = [{"id": str(uuid.uuid4()), "display_name": c, "type": "lakehouse_tables.column", "is_selected": True,
                     "data_type": dt} for c, dt in _columns(t)]
            tables.append({"id": str(uuid.uuid4()), "display_name": t, "type": "lakehouse_tables.table",
                           "is_selected": True, "children": cols})
        ds = {"$schema": "1.0.0", "artifactId": lh, "workspaceId": ws, "displayName": LAKEHOUSE,
              "type": "lakehouse_tables", "dataSourceInstructions": SOURCE_INSTRUCTIONS,
              "userDescription": "Caldova master data and orders.",
              "elements": [{"id": str(uuid.uuid4()), "display_name": "dbo", "type": "lakehouse_tables.schema",
                            "is_selected": True, "children": tables}]}
    stage = {"$schema": "1.0.0", "aiInstructions": AGENT_INSTRUCTIONS}
    parts = {"Files/Config/data_agent.json": {"$schema": "2.1.0"},
             "Files/Config/draft/stage_config.json": stage, f"Files/Config/draft/{folder}/datasource.json": ds,
             "Files/Config/published/stage_config.json": stage, f"Files/Config/published/{folder}/datasource.json": ds,
             "Files/Config/publish_info.json": {"$schema": "1.0.0", "description": "Caldova operations data"}}
    if examples and source == "lakehouse":
        for stage_name in ("draft", "published"):
            parts[f"Files/Config/{stage_name}/{folder}/fewshots.json"] = few_shots()
    definition = {"parts": [{"path": p, "payload": _b64(json.dumps(c)), "payloadType": "InlineBase64"}
                            for p, c in parts.items()]}
    agent = _item(ws, "dataAgents", DATA_AGENT)
    if agent:
        fabric("POST", f"/workspaces/{ws}/dataAgents/{agent['id']}/updateDefinition", {"definition": definition})
    else:
        fabric("POST", f"/workspaces/{ws}/dataAgents", {"displayName": DATA_AGENT, "definition": definition})
        agent = _item(ws, "dataAgents", DATA_AGENT)
    url = f"https://api.fabric.microsoft.com/v1/mcp/workspaces/{ws}/dataagents/{agent['id']}/agent"
    save_state(data_agent_id=agent["id"], data_agent_mcp=url)
    connect_fabric_iq(url)
    return {"data_agent": agent["id"], "mcp_url": url, "source": source}


def connect_fabric_iq(server_url: str) -> str:
    """Project connection for the Fabric IQ tool. Uses the signed-in user's identity (on-behalf-of)."""
    settings.require("subscription_id", "resource_group", "project_endpoint")
    name = "caldova-fabric-iq"
    arm("PUT", f"{settings.project_arm_id}/connections/{name}?api-version={CONNECTIONS_API}", {"properties": {
        "category": "RemoteTool", "authType": "UserEntraToken", "target": server_url,
        "audience": "https://analysis.windows.net/powerbi/api", "isSharedToAll": True}})
    save_state(fabric_connection=name)
    return name


# ---------------- Ontology (preview): generated from the lakehouse tables ----------------

COLTYPES = {"int": "int64", "float": "double", "bool": "boolean", "str": "string"}
ENTITIES = {  # entity -> (table, key, description)
    "Supplier": ("suppliers", "supplier_id", "A company that supplies parts to Caldova."),
    "Component": ("components", "component_id", "A part used to build Caldova products, for example HX-220."),
    "Product": ("products", "product_id", "A finished Caldova product, for example PV-400."),
    "Customer": ("customers", "customer_id", "A company that buys Caldova products."),
    "SalesOrder": ("sales_orders", "order_id", "An open customer order."),
    "PurchaseOrder": ("purchase_orders", "po_id", "An open purchase order to a supplier."),
}
RELATIONSHIPS = {  # name -> (from entity, to entity, from column, to column)
    "Component Supplied By": ("Component", "Supplier", "components.primary_supplier_id", "suppliers.supplier_id"),
    "Order By Customer": ("SalesOrder", "Customer", "sales_orders.customer_id", "customers.customer_id"),
    "Order For Product": ("SalesOrder", "Product", "sales_orders.product_id", "products.product_id"),
    "PO For Component": ("PurchaseOrder", "Component", "purchase_orders.component_id", "components.component_id"),
    "PO To Supplier": ("PurchaseOrder", "Supplier", "purchase_orders.supplier_id", "suppliers.supplier_id"),
}


def _columns(table: str) -> list[tuple[str, str]]:
    with open(TABLE_DIR / f"{table}.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = []
    for col in rows[0]:
        vals = [r[col] for r in rows if r[col] != ""]
        kind = "str"
        if vals and all(v.lower() in ("true", "false") for v in vals):
            kind = "bool"
        elif vals and all(v.lstrip("-").isdigit() for v in vals):
            kind = "int"
        elif vals and all(v.replace(".", "", 1).lstrip("-").isdigit() for v in vals):
            kind = "float"
        out.append((col, COLTYPES[kind]))
    return out


def ontology_definition(sql_endpoint: dict) -> dict:
    tag = lambda: str(uuid.uuid4())  # noqa: E731
    parts = {
        ".platform": json.dumps({"$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/"
                                            "platformProperties/2.0.0/schema.json",
                                 "metadata": {"type": "Ontology", "displayName": ONTOLOGY},
                                 "config": {"version": "2.0", "logicalId": "00000000-0000-0000-0000-000000000000"}}),
        "database.tmdl": "database\n\tcompatibilityLevel: 1000000\n",
        "expressions.tmdl": ("expression DatabaseQuery =\n\t\tlet\n\t\t    database = Sql.Database(\""
                             + sql_endpoint["connectionString"] + "\", \"" + sql_endpoint["id"]
                             + "\")\n\t\tin\n\t\t    database\n\tlineageTag: " + tag() + "\n"),
    }
    model = ["model Model", ""]
    tables = sorted({t for t, _, _ in ENTITIES.values()})
    for t in tables:
        lines = [f"table {t}", f"\tlineageTag: {tag()}", ""]
        for col, dt in _columns(t):
            lines += [f"\tcolumn {col}", f"\t\tdataType: {dt}", f"\t\tlineageTag: {tag()}", f"\t\tsourceColumn: {col}", ""]
        lines += [f"\tpartition {t} = entity", "\t\tmode: directLake", "\t\tsource", f"\t\t\tentityName: {t}",
                  "\t\t\tschemaName: dbo", "\t\t\texpressionSource: DatabaseQuery", ""]
        parts[f"tables/{t}.tmdl"] = "\n".join(lines)
        model.append(f"ref table {t}")
    model.append("")
    for ent, (t, key, desc) in ENTITIES.items():
        lines = [f"/// {desc}", f"entity {ent}", f"\tlineageTag: {tag()}", f"\tbackingTable: {t}", f"\tkeyProperty: {key}", ""]
        for col, dt in _columns(t):
            lines += [f"\tproperty {col}", f"\t\tdataType: {dt}", f"\t\tlineageTag: {tag()}", "",
                      "\t\tbackingConfiguration", f"\t\t\tvalueColumn: {t}.{col}", ""]
        parts[f"entities/{ent}.tmdl"] = "\n".join(lines)
        model.append(f"ref entity {ent}")
    model += ["", "ref namespace default", ""]
    parts["model.tmdl"] = "\n".join(model)
    rels, erels = [], []
    for i, (name, (fe, te, fc, tc)) in enumerate(RELATIONSHIPS.items()):
        rels += [f"relationship rel_{i}", f"\tfromColumn: {fc}", f"\ttoColumn: {tc}", ""]
        erels += [f"entityRelationship '{name}'", f"\tlineageTag: {tag()}", f"\tfromEntity: {fe}", f"\ttoEntity: {te}",
                  "", "\tbackingConfiguration", f"\t\trelationship: rel_{i}", ""]
    parts["relationships.tmdl"] = "\n".join(rels)
    parts["entityRelationships.tmdl"] = "\n".join(erels)
    return {"parts": [{"path": p, "payload": _b64(c), "payloadType": "InlineBase64"} for p, c in parts.items()]}


def create_ontology() -> dict:
    st = load_state()
    ws, sql = st.get("fabric_workspace_id"), st.get("sql_endpoint")
    if not sql:
        raise SystemExit("Load the lakehouse first: caldova fabric-iq load")
    definition = ontology_definition(sql)
    try:
        existing = _item(ws, "ontologies", ONTOLOGY)
        if existing:
            fabric("POST", f"/workspaces/{ws}/ontologies/{existing['id']}/updateDefinition", {"definition": definition})
        else:
            fabric("POST", f"/workspaces/{ws}/ontologies", {"displayName": ONTOLOGY, "definition": definition})
            existing = _item(ws, "ontologies", ONTOLOGY)
    except AzureError as e:
        if "FeatureNotAvailable" in str(e):
            raise SystemExit("Ontology (preview) is turned off in this tenant. Ask your coach: a Fabric admin must "
                             "enable 'Users can create ontology (preview) items'. Continue with the data agent.")
        raise
    url = f"https://api.fabric.microsoft.com/v1/mcp/dataPlane/workspaces/{ws}/items/{existing['id']}/ontologyEndpoint"
    save_state(ontology_id=existing["id"], ontology_mcp=url)
    return {"ontology": existing["id"], "mcp_url": url, "entities": list(ENTITIES), "relationships": list(RELATIONSHIPS)}
