# Walkthrough Challenge 6 - Cut the cord

[Previous Challenge Solution](../challenge-05/solution-05.md) - **[Home](../../Readme.md)** - [Finish](../../challenges/finish.md)

Duration: 30 minutes

## Prerequisites

Please ensure that you successfully completed [Challenge 5](../../challenges/challenge-05.md) before continuing with this challenge. The reference copilot is [copilot.py](../code/copilot.py): one agent with four tools (machine status, tickets, fault prediction, SOP search).

### **Task 1: Run it while connected and write down the timings**

```powershell
python copilot.py "What is the status of machine CNC-07?" "Predict the most likely fault for CNC-07 from its sensor readings." "At what vibration level must a CNC spindle be stopped?" "Open a high priority ticket for CNC-07: spindle vibration above the stop limit."
```

Reference timings on a Snapdragon X Elite laptop (`phi-4-mini` on the GPU), **connected**:

| Step | Time |
|------|------|
| Machine status (one tool call and answer) | 6.6 s |
| Fault prediction (ONNX model and answer) | 5.6 s |
| SOP question (decompose, embed, search, answer) | 15.7 s |
| Ticket (tool call, confirmation, answer) | 9.5 s |

The ticket time includes the seconds the technician needs to type `y`. Your numbers will differ with your hardware.

### **Task 2: Disconnect**

**Laptop**, in a terminal started as administrator. This blocks outbound traffic to the internet and leaves the loopback address that Foundry Local uses alone:

```powershell
New-NetFirewallRule -DisplayName "Offline copilot test" -Direction Outbound -Action Block -RemoteAddress Internet
```

Remove it afterwards with `Remove-NetFirewallRule -DisplayName "Offline copilot test"`. Turning Wi-Fi off or unplugging the cable works as well.

**VM**: add an outbound rule to the network security group of the VM. The rule stops traffic to the internet and does not stop your Remote Desktop session, because replies to an incoming connection are allowed:

```powershell
az network nsg rule create -g <resource-group> --nsg-name <nsg-name> -n deny-internet-out `
  --priority 100 --direction Outbound --access Deny --protocol '*' `
  --source-address-prefixes '*' --source-port-ranges '*' `
  --destination-address-prefixes Internet --destination-port-ranges '*'
```

### **Task 3: Check that you are really offline**

[offline_check.py](../code/offline_check.py) checks three things: the model service is on a loopback address, the internet is **not** reachable, and a local answer still comes back.

```powershell
python offline_check.py
```

Expected output when the block works (the first two lines and the timings are real output from a connected run, the `Internet` line is what the script prints when the internet is unreachable):

```text
Model service : http://127.0.0.1:54794/v1
Runs locally  : yes
Internet      : not reachable (offline)
Local answers : [2.67, 0.63] s
```

If it says `REACHABLE`, the block does not work yet. Do not continue until it says `not reachable`.

### **Task 4: Run the whole scenario again**

Repeat the four questions from task 1 and write down the timings. Every capability from challenges 3 to 5 must work: the tools, the SOP search with sources, the ONNX model and the ticket.

### **Task 5: What still needs the cloud?**

Go through the copilot and the Foundry Local service and ask *"does this need the internet?"* A good list:

| Needs the internet | When |
|--------------------|------|
| Downloading a model or a model update | Once, and when a model is refreshed |
| Updating Foundry Local itself and the Python packages | On a schedule, from a controlled place |
| Syncing the maintenance tickets to the central system | When the device is back online |
| Retraining the fault classifier with new sensor history | Periodically, in the cloud (challenge 5) |
| Monitoring and logs to a central place | When connected |

💡 A good routine for the stretch goal: when the device reconnects, it uploads the new tickets, then checks for a newer model, downloads it, tests it with the evaluation set from challenge 4, and only then switches to it.

You successfully completed challenge 6! 🚀🚀🚀

## Coach notes

- **Not yet verified with the network blocked.** The timings above were measured while connected. Before the first event, run this challenge on a laptop and on a VM with the block in place, and check `offline_check.py` and the four questions. Fill in the offline timings from that run.
- **Check for silent internet dependencies.** During a normal run the Foundry Local service held an outbound HTTPS connection to an Azure address while it answered. This is probably a catalog or telemetry check and not part of the inference, but **confirm it** by running with the block in place. Look at `foundry server logs` for errors. Python packages must be installed **before** the disconnect.
- **On Azure VMs keep a management path.** The outbound deny rule does not affect Remote Desktop. Do not add an inbound deny rule.
- **The block must not stop the loopback address.** `127.0.0.1` is not "Internet" for the firewall rule above. If a team blocks "all" outbound traffic and the copilot stops, this is why.
- **Stretch:** design the reconnection routine from task 5 and write the ticket-sync part.
