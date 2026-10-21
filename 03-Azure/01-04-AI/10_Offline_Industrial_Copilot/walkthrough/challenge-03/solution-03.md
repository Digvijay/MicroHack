# Walkthrough Challenge 3 - Build your first local agent

[Previous Challenge Solution](../challenge-02/solution-02.md) - **[Home](../../Readme.md)** - [Next Challenge Solution](../challenge-04/solution-04.md)

Duration: 60 minutes

## Prerequisites

Please ensure that you successfully completed [Challenge 2](../../challenges/challenge-02.md) before continuing with this challenge. The reference code uses `phi-4-mini`.

### **Task 1: Write the tools**

[tools.py](../code/tools.py) has two plain Python functions and their JSON schemas:

```python
def get_machine_status(machine_id: str) -> dict:
    machines = json.loads((DATA / "machines.json").read_text(encoding="utf-8"))["machines"]
    for m in machines:
        if m["id"].lower() == machine_id.strip().lower():
            return m
    return {"error": f"Unknown machine '{machine_id}'", "known_machines": [m["id"] for m in machines]}


def create_maintenance_ticket(machine_id: str, summary: str, priority: str) -> dict:
    if priority not in ("low", "medium", "high"):
        return {"error": "priority must be low, medium or high"}
    ...  # append one JSON line to tickets.jsonl and return the ticket
```

💡 The tools **validate their own input** and return an error the model can read. A small model sometimes sends a machine ID that does not exist (for a question about the cafeteria it sent `cafeteria_menu`). A tool that returns `{"error": ...}` lets the agent recover. A tool that raises an exception ends the conversation.

### **Task 2: The system prompt**

```text
You are a maintenance assistant for technicians at Contoso Precision Machining.
Machine data and tickets are only available through your tools: never guess a machine reading.
After you receive tool results, answer in at most three short sentences and then stop.
```

Short and specific works best with small models. "Never guess" matters: without it, `phi-4-mini` answers *"I do not have real-time data"* instead of calling the tool.

### **Task 3: The tool-call loop**

The loop in [agent.py](../code/agent.py) does this:

1. Send the conversation and the tool schemas to the model.
2. If the model asks for a tool, run it and add the result to the conversation.
3. Send the conversation again. Stop when the model answers in text.

```python
choice = "required" if step == 0 else "none"
reply = client.chat.completions.create(
    model=model, messages=messages, tools=schemas, tool_choice=choice, temperature=0, max_tokens=500,
).choices[0].message
```

Three details make it work with a small model:

- **The first step uses `tool_choice="required"`.** With `"auto"` the model usually describes the tool call in words (challenge 2: 1 of 8). With `"required"` it makes a proper call (7 of 8). The next step uses `"none"`, so the model has to write the answer.
- **One tool call per step.** Models like `qwen3-1.7b` call several tools at once, including tools nobody asked for. The loop runs the first call and ignores the rest.
- **A step limit.** `max_steps` guarantees that the loop ends.

### **Task 4: Test it**

```powershell
python agent.py "What is the status of machine CNC-07?"
```

```text
  -> get_machine_status({'machine_id': 'CNC-07'})
The CNC-07 machine is currently in a FAULT state due to high spindle vibration (E-SPN-214).
The vibration measurement is 9.4 mm/s and the temperature is 78.0°C. Service is needed.
```

A question that needs no tool, such as *"Why is the sky blue?"*, still gets a forced tool call in this simple loop. The model then picks the closest tool or answers that it has no data. That is a real limit of `"required"`, and challenge 4 shows one way around it.

### **Task 5: The confirmation step**

Writing a ticket changes something, so a person must approve it:

```python
WRITE_TOOLS = {"create_maintenance_ticket"}

if name in WRITE_TOOLS and not approve(name, args):
    result = {"error": "The technician did not approve this action."}
```

```text
  -> create_maintenance_ticket({'machine_id': 'CNC-07', 'priority': 'high', 'summary': 'Spindle vibration above stop limit'})
  The assistant wants to run create_maintenance_ticket(...). Allow? [y/N]
```

The model is told what happened when the technician says no, so it can answer sensibly.

💡 This is not only for show. In the model comparison, `qwen3-1.7b` created a ticket with an invented summary for a plain status question. **A person in the loop is what makes a small model safe enough to give write access.**

You successfully completed challenge 3! 🚀🚀🚀

## Coach notes

- If a team's model handles tool calls badly, send it back to [challenge 2](../../challenges/challenge-02.md): switch to a model that passes more tool cases, or use `tool_choice="required"`.
- `phi-4-mini` sometimes writes the call as text, for example `<|tool_call|>[{...}]`. The loop in challenge 4 parses that form as well.
- Give teams that are new to function calling the loop skeleton in Task 3 and let them write the tools themselves.
- **Stretch:** log every tool call and its arguments to a file, so a technician can see afterwards what the agent did.
