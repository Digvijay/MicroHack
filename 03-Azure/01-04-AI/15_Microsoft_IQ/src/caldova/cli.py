"""Command line for the hack: `uv run caldova --help`."""

from __future__ import annotations

import json
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import agent, evals, fabric_iq, foundry_iq, work_iq
from .azure import load_state
from .config import IQS, PERSONAS, settings

app = typer.Typer(add_completion=False, no_args_is_help=True, help="Caldova: one agent, four IQs.")
fabric_app = typer.Typer(no_args_is_help=True, help="Fabric IQ: lakehouse, data agent, ontology.")
foundry_app = typer.Typer(no_args_is_help=True, help="Foundry IQ: knowledge bases and the knowledge graph.")
work_app = typer.Typer(no_args_is_help=True, help="Work IQ: call the Work IQ MCP server directly.")
app.add_typer(fabric_app, name="fabric-iq")
app.add_typer(foundry_app, name="foundry-iq")
app.add_typer(work_app, name="work-iq")
con = Console()


def _iqs(value: str) -> set[str]:
    chosen = {v.strip().lower() for v in value.split(",") if v.strip() and v.strip().lower() != "none"}
    bad = chosen - set(IQS)
    if bad:
        raise typer.BadParameter(f"Unknown IQ: {', '.join(bad)}. Use: {', '.join(IQS)} or none")
    return chosen


IQ_OPT = typer.Option("none", "--iqs", help="Comma list of IQs: web,fabric,foundry,work (or none).")
PERSONA_OPT = typer.Option("supply-planner", "--persona", help=f"Who is asking: {', '.join(PERSONAS)}.")


@app.command()
def check() -> None:
    """Check src/.env and your sign-in."""
    t = Table("Setting", "Value")
    for k in ("project_endpoint", "subscription_id", "resource_group", "model", "search_endpoint", "storage_account",
              "fabric_capacity", "workiq_endpoint"):
        t.add_row(k, getattr(settings, k) or "[red]missing[/red]")
    for p in PERSONAS:
        t.add_row(f"workiq key {p}", "set" if settings.workiq_key(p) else "[red]missing[/red]")
    con.print(t)
    with agent.project() as p:
        con.print(f"[green]Signed in. Foundry project reachable:[/green] {len(list(p.agents.list()))} agents")


@app.command()
def build(iqs: str = IQ_OPT, persona: str = PERSONA_OPT) -> None:
    """Create a new version of the Caldova agent with the IQs you choose."""
    con.print(f"[green]Agent version[/green] {agent.build(_iqs(iqs), persona)}")


@app.command()
def ask(question: str, persona: str = PERSONA_OPT,
        iqs: Optional[str] = typer.Option(None, "--iqs", help="Rebuild the agent with these IQs first.")) -> None:
    """Ask the Caldova agent a question."""
    if iqs is not None:
        agent.build(_iqs(iqs), persona)
    a = agent.ask(question, persona)
    con.print(Panel(a.text or "(no answer)", title=f"Caldova agent as {persona}"))
    con.print("[dim]Tools used:[/dim] " + (", ".join(a.tool_calls) or "none"))
    for c in a.citations[:8]:
        con.print(f"[dim]  {c}[/dim]")


@app.command("eval")
def eval_(iqs: str = IQ_OPT, label: str = typer.Option(..., "--label", help="Name of this run, e.g. 'challenge 3'."),
          upto: int = typer.Option(6, "--upto", help="Only questions up to this challenge."),
          only: Optional[str] = typer.Option(None, "--only", help="Only these question ids, e.g. q16,q18."),
          workers: int = typer.Option(4, "--workers")) -> None:
    """Score the agent on the evaluation questions and add the run to the leaderboard."""
    ids = {i.strip() for i in only.split(",")} if only else None
    entry = evals.run(_iqs(iqs), upto, label, workers, ids)
    t = Table("Q", "Ch", "Persona", "Needs", "Score", "Judge", "Tools", "Why")
    for r in entry["results"]:
        color = "green" if r["score"] >= 8 else "yellow" if r["score"] >= 5 else "red"
        t.add_row(r["id"], str(r["challenge"]), r["persona"], ",".join(r["iqs_needed"]) or "-",
                  f"[{color}]{r['score']}[/{color}]", str(r["judge"]), ", ".join(r["tools"])[:40], r["reason"][:60])
    con.print(t)
    con.print(f"[bold]{label}: {entry['score']} / {entry['max']}[/bold]")


@app.command()
def leaderboard() -> None:
    """Show how your agent's score changed run by run."""
    t = Table("Run", "IQs", "Score", "Max", "%", "When (UTC)")
    for e in evals.board():
        pct = 100 * e["score"] / e["max"] if e["max"] else 0
        bar = "█" * int(pct / 5)
        t.add_row(e["label"], ",".join(e["iqs"]) or "none", str(e["score"]), str(e["max"]), f"{pct:4.0f} {bar}", e["at"])
    con.print(t)


@fabric_app.command("load")
def fabric_load() -> None:
    """Create the workspace and lakehouse, and load data/lakehouse/*.csv as tables."""
    con.print_json(json.dumps(fabric_iq.load_lakehouse()))


@fabric_app.command("agent")
def fabric_agent(source: str = typer.Option("lakehouse", help="lakehouse or ontology"),
                 examples: bool = typer.Option(True, "--examples/--no-examples",
                                               help="Teach the data agent with example queries.")) -> None:
    """Create and publish the Fabric data agent, and connect it to Foundry as a Fabric IQ tool."""
    con.print_json(json.dumps(fabric_iq.create_data_agent(source, examples)))


@fabric_app.command("ontology")
def fabric_ontology() -> None:
    """Create the Fabric IQ ontology (preview) from the lakehouse tables."""
    con.print_json(json.dumps(fabric_iq.create_ontology()))


@foundry_app.command("documents")
def foundry_documents() -> None:
    """Upload the documents and create the documents knowledge base (agentic retrieval)."""
    con.print_json(json.dumps(foundry_iq.create_documents_kb()))


@foundry_app.command("graph")
def foundry_graph(ontology: str = typer.Option("caldova-supply-v1", help="Ontology file in data/foundry-iq")) -> None:
    """Extract a knowledge graph (preview) from the documents with your ontology."""
    con.print_json(json.dumps(foundry_iq.create_graph_kb(ontology)))


@foundry_app.command("retrieve")
def foundry_retrieve(question: str, kb: str = typer.Option("documents", help="documents or graph")) -> None:
    """Query a knowledge base directly, without the agent."""
    st = load_state()
    name = st.get("graph_kb") if kb == "graph" else st.get("documents_kb")
    r = foundry_iq.retrieve(name, question)
    for m in r.get("response", []):
        for c in m.get("content", []):
            con.print(Panel(c.get("text", "")[:4000], title=name))
    for a in r.get("activity", []):
        if a.get("type") == "graphSearch":
            con.print("[dim]GQL:[/dim] " + a.get("graphSearchArguments", {}).get("gql", ""))


@foundry_app.command("gql")
def foundry_gql(query: str) -> None:
    """Run a GQL query on the knowledge graph."""
    con.print_json(json.dumps(foundry_iq.gql(query).get("value", [])))


@work_app.command("retrieve")
def work_retrieve(query: str, persona: str = PERSONA_OPT,
                  capability: Optional[list[str]] = typer.Option(None, "--capability",
                                                                 help="Email, TeamsMessages, Meetings, OneDriveAndSharePoint, People")) -> None:
    """Call the Work IQ retrieve tool as a persona."""
    args: dict = {"query": query}
    if capability:
        args["capabilities"] = [{"name": c} for c in capability]
    res = work_iq.call(persona, "retrieve", args)
    payload = res.get("structuredContent", {}).get("application/vnd.ms-workiq.retrieval", {})
    con.print(f"[bold]{payload.get('resultCount', 0)} results for {persona}[/bold]")
    for hit in payload.get("results", []):
        con.print(Panel(hit.get("markdown", "")[:800], title=f"{hit.get('id')} {hit.get('entityType')}"))


@work_app.command("connect")
def work_connect(persona: str = PERSONA_OPT) -> None:
    """Register the Work IQ server for a persona as a Foundry project connection."""
    con.print(f"[green]Connection[/green] {work_iq.connect(persona)}")


if __name__ == "__main__":
    app()
