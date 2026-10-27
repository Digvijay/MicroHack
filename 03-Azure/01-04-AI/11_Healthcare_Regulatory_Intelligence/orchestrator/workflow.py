"""Chain the saved Foundry prompt agents: citation -> impact -> briefing.

This is the finished version. The same file with the three steps left as TODOs
is in starter/workflow.py.
"""
from __future__ import annotations

from typing import Dict

from agent_framework import AgentExecutor, WorkflowBuilder
from agent_framework.foundry import FoundryAgent
from azure.ai.projects import AIProjectClient

from configuration import Configuration


def resolve_versions(config: Configuration, credential) -> Dict[str, str]:
    """Use pinned versions when given, otherwise the latest saved version of each agent."""
    resolved = {}
    with AIProjectClient(endpoint=config.endpoint, credential=credential) as project:
        for role, name in config.names.items():
            if config.versions.get(role):
                resolved[role] = config.versions[role]
                continue
            try:
                resolved[role] = str(project.agents.get(name).versions.latest.version)
            except Exception as error:
                raise RuntimeError(f"Agent '{name}' was not found in your Foundry project. "
                                   f"Create and save it first (see the challenge for this agent).") from error
    return resolved


def build_workflow(config: Configuration, credential, versions: Dict[str, str]):
    # Step 1: one executor per saved agent. FoundryAgent calls the agent you built in the portal;
    # "last_agent" passes only the previous agent's answer on, so each agent gets a focused input.
    executors = {
        role: AgentExecutor(
            FoundryAgent(project_endpoint=config.endpoint, credential=credential,
                         agent_name=name, agent_version=versions[role]),
            context_mode="last_agent",
        )
        for role, name in config.names.items()
    }
    # Step 2: start at the citation agent and return what the briefing agent writes.
    builder = WorkflowBuilder(start_executor=executors["CITATION"], output_from=[executors["BRIEFING"]])
    # Step 3: connect the agents in order.
    builder.add_edge(executors["CITATION"], executors["IMPACT"])
    builder.add_edge(executors["IMPACT"], executors["BRIEFING"])
    return builder.build().as_agent(name="regulatory-intelligence-assistant")
