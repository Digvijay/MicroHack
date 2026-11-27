#!/usr/bin/env python3
"""Switch on incoming A2A for a Strandvik agent and let one caller agent in.

Run it in Azure Cloud Shell (Bash): it is already signed in and has `az` and Python.
No install, no .env. It finds your lab by the resource group tag microhack=15_Microsoft_IQ.

    python3 enable-a2a.py --agent strandvik-customer-service --caller kolvo/maria-procurement
    python3 enable-a2a.py --agent strandvik-parts --caller strandvik/alex-agent

What it does (the same REST calls a portal would make):
  1. Publishes the agent card and switches on the agent's incoming A2A endpoint.
  2. Gives the caller agent's identity the Foundry Agent Consumer role on that one agent
     (or on the whole strandvik project with --scope project). Safe to run twice.
The Foundry portal cannot do either step yet: it cannot switch on incoming A2A, and its
role dialog cannot pick an agent identity.
"""
import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

LAB_TAG = "15_Microsoft_IQ"
CONSUMER_ROLE = "eed3b665-ab3a-47b6-8f48-c9382fb1dad6"  # Foundry Agent Consumer (built-in)
FOUNDRY = "https://ai.azure.com"
ARM = "https://management.azure.com"

CARDS = {
    "strandvik-customer-service": (
        "Strandvik Drives customer service. Receives requests from approved customers' agents, checks who is "
        "asking, opens a case and hands it to the account owner. Never quotes, orders or commits.",
        [("request-quote", "Request price and delivery",
          "An approved customer's agent asks for price and delivery of a drive unit. Opens a case."),
         ("case-status", "Case status", "An approved customer's agent asks about an open case.")]),
    "strandvik-parts": (
        "Strandvik Drives internal Parts agent. Read-only view of the ERP: drive units, stock, replacement "
        "candidates, reservations and their owners. Never sells, reserves or moves a unit.",
        [("find-replacement", "Find replacement units",
          "Given a machine or a failing unit, lists the in-stock units of the required model, with reservations and owners."),
         ("reservation-owner", "Reservation and owner",
          "Given a unit or reservation id, returns the reservation, the reserved customer, the needed-by day and the owner.")]),
    "strandvik-logistics": (
        "Strandvik Drives internal Logistics agent. Routes, transit times, costs and flight holds for drive units "
        "(LOG-03). Places holds, never books: bookings need the key account manager's approval.",
        [("route-options", "Route options",
          "Compares routes from a site to a customer: departure, arrival, transit time, cost, approval needed, risk."),
         ("hold-flight", "Hold a flight", "Places a free 6-hour flight hold and reports until when it runs. Not a booking.")]),
    "strandvik-service": (
        "Strandvik Drives internal Service agent. Contracts, policies and technician slots, with citations "
        "(SC-KOL-2024, SC-POL-2025, RES-02, EAP-01, FS-04). Never changes a contract or books a technician.",
        [("contract-terms", "Contract terms", "Replacement targets, uptime credits, who may order, how changes are confirmed."),
         ("policy-check", "Policy check", "What a policy allows, for example whether a reserved unit may be reallocated."),
         ("technician-slots", "Technician slots", "Free certified technician slots at a customer site and the notice they need.")]),
    "alex-agent": (
        "Strandvik Drives internal: Alex's agent, prepares proposals for Kolvo cases. Never commits.",
        [("prepare-proposal", "Prepare a proposal",
          "Given a Kolvo case, gathers parts, service and logistics facts and drafts a proposal pending Alex.")]),
}


def say(msg=""):
    print(msg, flush=True)


def fail(msg):
    say(f"\nERROR: {msg}")
    sys.exit(1)


def az(*args):
    try:
        r = subprocess.run(["az", *args, "-o", "json"], capture_output=True, text=True, shell=sys.platform == "win32")
    except FileNotFoundError:
        fail("The Azure CLI (az) is not installed. Use Azure Cloud Shell, where it is ready.")
    if r.returncode != 0:
        fail(f"az {' '.join(args[:3])} failed: {r.stderr.strip()[:400]}\n"
             "In Cloud Shell you are signed in already; elsewhere run `az login` first.")
    return json.loads(r.stdout or "null")


_tokens = {}


def token(resource):
    if resource not in _tokens:
        _tokens[resource] = az("account", "get-access-token", "--resource", resource)["accessToken"]
    return _tokens[resource]


def call(method, url, resource, body=None):
    data = json.dumps(body).encode() if body is not None else None
    for attempt in range(6):
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", "Bearer " + token(resource))
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                text = r.read().decode().strip()
                return json.loads(text) if text.startswith(("{", "[")) else {}
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < 5:
                time.sleep(5 + 5 * attempt)
                continue
            fail(f"{method} {url.split('?')[0]} returned HTTP {e.code}: {e.read().decode()[:600]}")


def find_lab(rg_hint):
    accounts = az("cognitiveservices", "account", "list") or []
    lab = [x for x in accounts if (x.get("tags") or {}).get("microhack") == LAB_TAG] or \
          [x for x in accounts if x["name"].startswith("iq-")]
    if rg_hint:
        lab = [x for x in lab if x["resourceGroup"].lower() == rg_hint.lower()]
    if not lab:
        fail("No lab found: no Foundry resource tagged microhack=15_Microsoft_IQ in this subscription.\n"
             "Check the subscription with `az account show` (switch with `az account set -s <id>`).")
    if len(lab) > 1:
        names = ", ".join(f"{x['name']} ({x['resourceGroup']})" for x in lab)
        fail(f"More than one lab found: {names}. Add --resource-group <name>.")
    return lab[0]


def principal_of(agent_json):
    latest = (agent_json.get("versions") or {}).get("latest") or {}
    return ((latest.get("instance_identity") or agent_json.get("instance_identity")) or {}).get("principal_id")


def main():
    p = argparse.ArgumentParser(description="Switch on incoming A2A for a Strandvik agent and let a caller agent in.")
    p.add_argument("--agent", required=True, help="the Strandvik agent to open, for example strandvik-customer-service")
    p.add_argument("--caller", required=True, help="project/agent that may call it, for example kolvo/maria-procurement")
    p.add_argument("--scope", choices=["agent", "project"], default="agent",
                   help="role on this one agent (default, least privilege) or on every agent in the strandvik project")
    p.add_argument("--description", help="your own agent card description (default: the hack's card for this agent)")
    p.add_argument("--resource-group", help="only needed if you have more than one lab")
    a = p.parse_args()

    caller_project, _, caller_agent = a.caller.partition("/")
    if caller_project not in ("kolvo", "strandvik") or not caller_agent:
        fail("--caller must look like kolvo/maria-procurement or strandvik/alex-agent")

    say("==> Finding your lab")
    acct = find_lab(a.resource_group)
    sub = acct["id"].split("/")[2]
    host = f"https://{acct['name']}.services.ai.azure.com/api/projects"
    say(f"    Foundry resource {acct['name']} in resource group {acct['resourceGroup']}")

    say(f"==> Reading agent {a.agent} (project strandvik)")
    agent = call("GET", f"{host}/strandvik/agents/{a.agent}?api-version=v1", FOUNDRY)
    say(f"    found, latest version {((agent.get('versions') or {}).get('latest') or {}).get('version')}")

    desc, skills = CARDS.get(a.agent, (f"Strandvik Drives agent {a.agent}.", []))
    if a.description:
        desc = a.description
    say("==> Publishing the agent card and switching on incoming A2A")
    call("PATCH", f"{host}/strandvik/agents/{a.agent}?api-version=v1", FOUNDRY, {
        "agent_card": {"description": desc, "version": "1.0",
                       "skills": [{"id": i, "name": n, "description": d} for i, n, d in skills]},
        "agent_endpoint": {"protocol_configuration": {"responses": {}, "a2a": {}}},
    })
    a2a_url = f"{host}/strandvik/agents/{a.agent}/endpoint/protocols/a2a"
    card = call("GET", f"{a2a_url}/agentCard/v1.0?api-version=v1", FOUNDRY)
    say(f"    card: {card.get('name', a.agent)}: {card.get('description', desc)[:110]}")

    say(f"==> Finding the caller's agent identity ({caller_agent}, project {caller_project})")
    caller = principal_of(call("GET", f"{host}/{caller_project}/agents/{caller_agent}?api-version=v1", FOUNDRY))
    if not caller:
        fail(f"{caller_agent} has no agent identity yet. Open it once in the Foundry portal and Save, then run again.")
    say(f"    agent identity {caller}")

    project_id = f"{acct['id']}/projects/strandvik"
    scope_id = f"{project_id}/agents/{a.agent}" if a.scope == "agent" else project_id
    where = f"agent {a.agent}" if a.scope == "agent" else "the strandvik project"
    say(f"==> Foundry Agent Consumer for {caller_agent} on {where}")
    existing = call("GET", f"{ARM}{scope_id}/providers/Microsoft.Authorization/roleAssignments"
                           f"?api-version=2022-04-01&$filter=assignedTo('{caller}')", ARM).get("value", [])
    if any(x["properties"]["roleDefinitionId"].endswith(CONSUMER_ROLE) for x in existing):
        say("    already granted, nothing to do")
    else:
        call("PUT", f"{ARM}{scope_id}/providers/Microsoft.Authorization/roleAssignments/{uuid.uuid4()}"
                    "?api-version=2022-04-01", ARM, {"properties": {
                        "roleDefinitionId": f"/subscriptions/{sub}/providers/Microsoft.Authorization/roleDefinitions/{CONSUMER_ROLE}",
                        "principalId": caller, "principalType": "ServicePrincipal",
                        "description": f"{caller_agent} may call {a.agent} over A2A"}})
        say("    granted")

    say()
    say("Done. The A2A endpoint (the caller's A2A tool points here):")
    say(f"    {a2a_url}")
    say("Wait 3 to 6 minutes before testing: until the role is active, the caller's run fails with a vague")
    say(f"\"tool_user_error\". Then test in the Foundry portal: project {caller_project} > Agents > {caller_agent} > Playground.")


if __name__ == "__main__":
    main()
