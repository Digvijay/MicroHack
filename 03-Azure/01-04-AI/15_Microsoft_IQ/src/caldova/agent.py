"""The Caldova agent: one Foundry prompt agent that gains one IQ per challenge."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    FabricIQPreviewTool,
    MCPTool,
    PromptAgentDefinition,
    WebSearchApproximateLocation,
    WebSearchTool,
)

from .azure import credential, load_state
from .config import IQS, SRC_DIR, settings
from . import work_iq

PLAYBOOK = SRC_DIR / "playbook.md"

BASE_INSTRUCTIONS = """You are the operations assistant of Caldova Components AB, a Swedish maker of industrial
valves (plant in Boras). Today is Monday 7 December 2026, 08:00 CET. "Friday" means 11 December 2026.
Answer in short, plain business English. Show the numbers you used.
Never invent facts, names, quantities or dates. If you do not have a source for something, say what you
could not find and which system would know it."""

TOOL_GUIDANCE = {
    "web": "- Web IQ (web search): current public information, such as weather, storms, port closures, public "
           "holidays and exchange rates. Cite the web sources.",
    "fabric": "- Fabric IQ (Caldova data agent): numbers from Caldova's business data: stock, orders, order values, "
              "suppliers, bill of materials, purchase orders. Use it for any quantity or money question. Pass the "
              "user's question to it in their own words, with the codes unchanged (HX-220 is a component, PV-400 "
              "is a product).",
    "foundry": "- Foundry IQ (caldova_documents): contracts, policies, quality reports and the catalogue. Use it for "
               "rules, obligations, penalties and deadlines, and quote the clause. Before you say an action is "
               "allowed (a supplier, a partial delivery, a deviation), check caldova_documents for policies and "
               "quality holds.\n"
               "- Foundry IQ (caldova_graph, if present): relationships between suppliers, components, products and "
               "customers across documents. A relationship in the graph does not mean an action is allowed.",
    "work": "- Work IQ (workiq): what people at Caldova said, promised and decided: emails, Teams chats, meetings "
            "and files the signed-in user can see. It also has the latest news from partners, such as shipment "
            "delays and new arrival dates, which is newer than the business data. Use retrieve first.",
}


def instructions(iqs: set[str]) -> str:
    if not iqs:
        return BASE_INSTRUCTIONS + "\nYou have no tools. Answer only from general knowledge."
    lines = [BASE_INSTRUCTIONS, "", "Your tools:"] + [TOOL_GUIDANCE[i] for i in IQS if i in iqs]
    if len(iqs) > 1:
        lines.append("Combine the tools: check the data, the documents, the people and the outside world before "
                     "recommending an action. Point out conflicts between sources.")
    if PLAYBOOK.exists() and PLAYBOOK.read_text(encoding="utf-8").strip():
        lines += ["", "Team playbook (follow it):", PLAYBOOK.read_text(encoding="utf-8").strip()]
    return "\n".join(lines)


def tools(iqs: set[str], persona: str) -> list:
    st = load_state()
    out: list = []
    if "web" in iqs:
        out.append(WebSearchTool(user_location=WebSearchApproximateLocation(country="SE", city="Boras")))
    if "fabric" in iqs:
        if not st.get("fabric_connection"):
            raise SystemExit("Fabric IQ is not connected yet. Run: caldova fabric-iq agent")
        conn = f"{settings.project_arm_id}/connections/{st['fabric_connection']}"
        out.append(FabricIQPreviewTool(project_connection_id=conn, server_label="caldova-data",
                                       server_url=st["data_agent_mcp"], require_approval="never"))
    if "foundry" in iqs:
        kbs = [("caldova_documents", st.get("documents_kb")), ("caldova_graph", st.get("graph_kb"))]
        if not kbs[0][1]:
            raise SystemExit("Foundry IQ is not set up yet. Run: caldova foundry-iq documents")
        for label, kb in kbs:
            if kb:
                out.append(MCPTool(server_label=label, project_connection_id=kb, require_approval="never",
                                   server_url=f"{settings.search_endpoint}/knowledgebases/{kb}/mcp?api-version=2026-11-01-preview",
                                   allowed_tools=["knowledge_base_retrieve"]))
    if "work" in iqs:
        name = st.get(f"workiq_connection_{persona}") or work_iq.connect(persona)
        out.append(MCPTool(server_label="workiq", server_url=settings.workiq_endpoint, project_connection_id=name,
                           require_approval="never", allowed_tools=["retrieve", "fetch", "ask"],
                           server_description="Work IQ: Caldova's emails, Teams chats, meetings and files, including "
                                              "the latest partner news on shipments, delays and arrival dates."))
    return out


def project() -> AIProjectClient:
    settings.require("project_endpoint")
    return AIProjectClient(endpoint=settings.project_endpoint, credential=credential())


def agent_name(persona: str) -> str:
    return f"{settings.agent_name}-{persona}"


def build(iqs: set[str], persona: str = "supply-planner") -> str:
    with project() as p:
        v = p.agents.create_version(agent_name=agent_name(persona), definition=PromptAgentDefinition(
            model=settings.model, instructions=instructions(iqs), tools=tools(iqs, persona)),
            description=f"Caldova agent with IQs: {', '.join(sorted(iqs)) or 'none'}")
    return f"{v.name}:{v.version}"


@dataclass
class Answer:
    text: str
    tool_calls: list[str] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    response_id: str = ""


def ask(question: str, persona: str = "supply-planner", previous: str | None = None) -> Answer:
    """Ask the agent. Pass previous=<response id> to continue the same conversation."""
    with project() as p, p.get_openai_client(agent_name=agent_name(persona)) as client:
        r = client.responses.create(input=question, **({"previous_response_id": previous} if previous else {}))
    calls, cites = [], []
    for item in r.output:
        kind = getattr(item, "type", "")
        if kind.endswith("_call") or kind in ("mcp_call",):
            label = getattr(item, "server_label", "") or kind.replace("_call", "")
            name = getattr(item, "name", "")
            calls.append(f"{label}.{name}" if name else label)
        for c in getattr(item, "content", None) or []:
            for a in getattr(c, "annotations", None) or []:
                if getattr(a, "url", None):
                    cites.append(a.url)
    return Answer(_CITE.sub("", r.output_text or "").strip(), calls, sorted(set(cites)), r.id)


_CITE = re.compile(r"【[^】]*】")
