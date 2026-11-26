"""Foundry IQ: knowledge bases over Caldova's documents, with and without a knowledge graph."""

from __future__ import annotations

import json
import time
from pathlib import Path

from .azure import blob_container, blob_upload, save_state, search, load_state, arm
from .config import CONNECTIONS_API, DATA_DIR, SEARCH_PREVIEW_API, settings

DOCS_DIR = DATA_DIR / "documents"
ONTOLOGY_DIR = DATA_DIR / "foundry-iq"
RAG_SOURCE, RAG_KB = "caldova-docs", "caldova-docs-kb"


def _models() -> dict:
    def m(deployment: str) -> dict:
        return {"kind": "azureOpenAI", "azureOpenAIParameters": {
            "resourceUri": settings.openai_endpoint, "deploymentId": deployment, "modelName": deployment}}
    return {"chat": m(settings.graph_model), "emb": m(settings.embedding_model)}


def upload_documents() -> int:
    settings.require("storage_account")
    blob_container(settings.storage_account, settings.storage_container)
    files = sorted(DOCS_DIR.glob("*.md"))
    for f in files:
        blob_upload(settings.storage_account, settings.storage_container, f.name, f.read_bytes(), "text/markdown")
    return len(files)


def _source_body(name: str, ontology_file: Path | None) -> dict:
    mdl = _models()
    ingestion = {"contentExtractionMode": "minimal", "disableImageVerbalization": True, "embeddingModel": mdl["emb"]}
    params = {"connectionString": f"ResourceId={settings.storage_arm_id};", "containerName": settings.storage_container,
              "ingestionParameters": ingestion}
    body = {"name": name, "kind": "azureBlob", "azureBlobParameters": params,
            "description": "Caldova contracts, policies, quality reports and the product catalogue."}
    if ontology_file:
        ontology = json.loads(ontology_file.read_text(encoding="utf-8"))
        ingestion["chatCompletionModel"] = mdl["chat"]  # graph extraction model
        params["graphExtraction"] = {"graphName": name, "pageDegreeOfParallelism": 2, "ontology": {
            "kind": "inline", "name": ontology_file.stem, "value": json.dumps(ontology, separators=(",", ":"))}}
        body["resultsProcessing"] = "none"
    return body


def wait_for_source(name: str, timeout: int = 1200) -> dict:
    start = time.time()
    while time.time() - start < timeout:
        s = search("GET", settings.search_endpoint, f"knowledgesources('{name}')/status", SEARCH_PREVIEW_API)
        last = s.get("lastSynchronizationState") or {}
        if last.get("endTime") and not s.get("currentSynchronizationState"):
            if last.get("itemsUpdatesFailed"):
                raise RuntimeError(f"{name}: {last['itemsUpdatesFailed']} documents failed: {last.get('errors')}")
            return last
        time.sleep(10)
    raise TimeoutError(f"Knowledge source {name} did not finish ingesting in {timeout}s.")


def create_knowledge_base(kb: str, source: str, graph: bool) -> None:
    instructions = ("Use graph_search for relationship questions between suppliers, components, products, "
                    "customers and policies. Traverse the graph rather than using text search." if graph else
                    "Answer from Caldova's contracts, policies, quality reports and catalogue. Quote clause numbers.")
    search("PUT", settings.search_endpoint, f"knowledgebases('{kb}')", SEARCH_PREVIEW_API, {
        "name": kb, "knowledgeSources": [{"name": source}], "models": [_models()["chat"]],
        "retrievalReasoningEffort": {"kind": "low"},
        "outputMode": "extractiveData" if graph else "answerSynthesis",
        "retrievalInstructions": instructions})


def create_documents_kb() -> dict:
    """Challenge 4, part A: plain agentic retrieval (GA) over the documents."""
    settings.require("search_endpoint", "storage_account", "subscription_id", "resource_group")
    n = upload_documents()
    search("PUT", settings.search_endpoint, f"knowledgesources('{RAG_SOURCE}')", SEARCH_PREVIEW_API,
           _source_body(RAG_SOURCE, None))
    last = wait_for_source(RAG_SOURCE)
    create_knowledge_base(RAG_KB, RAG_SOURCE, graph=False)
    connect_kb(RAG_KB)
    save_state(documents_kb=RAG_KB)
    return {"documents": n, "knowledge_source": RAG_SOURCE, "knowledge_base": RAG_KB, "sync": last}


def create_graph_kb(ontology: str = "caldova-supply-v1") -> dict:
    """Challenge 4, part B: entity graph (preview) extracted with your ontology.

    The ontology is fixed when a graph source is created, so each ontology version gets its own
    source and knowledge base (caldova-graph-<ontology>)."""
    settings.require("search_endpoint", "storage_account", "subscription_id", "resource_group")
    ontology_file = ONTOLOGY_DIR / f"{ontology}.jsonld"
    if not ontology_file.exists():
        raise SystemExit(f"Ontology file not found: {ontology_file}")
    upload_documents()
    source, kb = f"caldova-graph-{ontology}", f"caldova-graph-{ontology}-kb"
    search("PUT", settings.search_endpoint, f"knowledgesources('{source}')", SEARCH_PREVIEW_API,
           _source_body(source, ontology_file))
    last = wait_for_source(source)
    time.sleep(15)  # graph writes finish shortly after the indexer run
    create_knowledge_base(kb, source, graph=True)
    connect_kb(kb)
    created = search("GET", settings.search_endpoint, f"knowledgesources('{source}')", SEARCH_PREVIEW_API)
    graph_index = created["azureBlobParameters"].get("createdResources", {}).get("graphIndex")
    save_state(graph_kb=kb, graph_source=source, graph_index=graph_index)
    return {"knowledge_source": source, "knowledge_base": kb, "graph_index": graph_index, "sync": last}


def retrieve(kb: str, question: str) -> dict:
    graph = kb.startswith("caldova-graph")
    src = load_state().get("graph_source") if graph else RAG_SOURCE
    params = {"kind": "azureBlob", "knowledgeSourceName": src, "includeReferences": True}
    if graph:
        params["graphParameters"] = {"includeQuery": True}
    return search("POST", settings.search_endpoint, f"knowledgebases('{kb}')/retrieve", SEARCH_PREVIEW_API, {
        "messages": [{"role": "user", "content": [{"type": "text", "text": question}]}],
        "includeActivity": True, "maxRuntimeInSeconds": 90, "knowledgeSourceParams": [params]})


def gql(query: str) -> dict:
    index = load_state().get("graph_index")
    if not index:
        raise SystemExit("No knowledge graph yet. Run: caldova foundry-iq graph")
    return search("POST", settings.search_endpoint, f"indexes('{index}')/docs/search.graph", SEARCH_PREVIEW_API,
                  {"gql": query, "includeStatistics": True})


def connect_kb(kb: str) -> str:
    """Register the knowledge base MCP endpoint as a project connection (project managed identity)."""
    name = kb
    arm("PUT", f"{settings.project_arm_id}/connections/{name}?api-version={CONNECTIONS_API}", {"properties": {
        "category": "RemoteTool", "authType": "ProjectManagedIdentity", "audience": "https://search.azure.com/",
        "target": f"{settings.search_endpoint}/knowledgebases/{kb}/mcp?api-version={SEARCH_PREVIEW_API}",
        "isSharedToAll": True, "metadata": {"type": "knowledgeBase_MCP"}}})
    return name
