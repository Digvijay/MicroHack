"""Re-run the four copilot scenarios N times and report how often the right tool was chosen first."""
import sys

import agent
import fault_tool
import fl
import retrieval

CASES = [
    ("What is the status of machine CNC-07?", "get_machine_status"),
    ("Predict the most likely fault for CNC-07 from its sensor readings.", "predict_fault"),
    ("At what vibration level must a CNC spindle be stopped?", "search_sops"),
    ("Open a high priority ticket for CNC-07: spindle vibration above the stop limit.", "create_maintenance_ticket"),
]

first_tool = []  # the tool the model picked first in the current run
_original = agent.first_tool_call


def _spy(reply):
    call = _original(reply)
    if call and not first_tool:
        first_tool.append(call[1])
    return call


agent.first_tool_call = _spy

if __name__ == "__main__":
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    client = fl.client()
    chat, emb = fl.load(retrieval.CHAT_MODEL), fl.load(retrieval.EMBED_MODEL)
    chunks, vectors = retrieval.load_index() if retrieval.INDEX.exists() else retrieval.build_index(client, emb)
    tools = [(fault_tool.SCHEMA, fault_tool.predict_fault), retrieval.search_tool(client, chat, emb, chunks, vectors)]
    total = ok = 0
    for question, expected in CASES:
        hits = 0
        for _ in range(runs):
            first_tool.clear()
            agent.run_agent(client, chat, question, extra_tools=tools, approve=lambda *_: False, verbose=False)
            hits += first_tool[:1] == [expected]
        total += runs
        ok += hits
        print(f"{hits}/{runs}  {expected:<26} {question[:60]}")
    print(f"\nfirst tool correct: {ok}/{total}")
