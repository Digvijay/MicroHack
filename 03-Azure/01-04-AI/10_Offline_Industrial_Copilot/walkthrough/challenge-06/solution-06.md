# Walkthrough Challenge 6 - Cut the cord

[Previous Challenge Solution](../challenge-05/solution-05.md) - **[Home](../../Readme.md)** - [Finish](../../challenges/finish.md)

Duration: 30 minutes

## Prerequisites

Please ensure that you successfully completed [Challenge 5](../../challenges/challenge-05.md) before continuing with this challenge. The reference copilot is [copilot.py](../code/copilot.py): one agent with four tools (machine status, tickets, fault prediction, SOP search).

### **Task 1: Run it while connected and write down the timings**

```powershell
python copilot.py "What is the status of machine CNC-07?" "Run the fault prediction model for CNC-07." "At what vibration level must a CNC spindle be stopped?" "Open a high priority ticket for CNC-07: spindle vibration above the stop limit."
```

Reference timings, **connected**. Your numbers will differ with your hardware.

| Step | Laptop (Snapdragon X Elite, GPU variant) | Windows VM (8 vCPU, CPU variant) |
|------|------------------------------------------|----------------------------------|
| Machine status (tool call and answer) | 6 s | 18.5 s |
| Fault prediction (ONNX model and answer) | 5 s | n/m |
| SOP question (split, embed, search, answer) | 13 s | 25.7 s |
| Ticket (tool call and confirmation) | 3 s | n/m |

*n/m: not measured on the VM with the final code.* The ticket time includes the seconds the technician needs to type `y`.

### **Task 2: Get ready, then disconnect**

💥 **Start everything before you disconnect, and do not restart the Foundry Local service while you are offline.** The service loads its model catalog from the internet when it starts. A service that is already running, with its models loaded, keeps answering offline. A service that is restarted offline cannot find any model, even a model that is on the disk (see the coach notes).

1. Make sure the service is running and both models are loaded:

   ```powershell
   foundry server status
   foundry model list --loaded
   ```

2. Ask one question of each kind, so every model is warm and the SOP index exists.

### **Task 3: Disconnect**

**Laptop**, in a terminal started as administrator. This blocks outbound traffic to the internet and leaves the loopback address that Foundry Local uses alone:

```powershell
New-NetFirewallRule -DisplayName "Offline copilot test" -Direction Outbound -Action Block -RemoteAddress Internet
```

Remove it afterwards with `Remove-NetFirewallRule -DisplayName "Offline copilot test"`. Turning Wi-Fi off or unplugging the cable works as well.

**VM**: add an outbound rule to the network security group of the VM. It blocks the internet and keeps your Remote Desktop session and the Azure management path:

```powershell
az network nsg rule create -g <resource-group> --nsg-name <nsg-name> -n deny-internet-out `
  --priority 100 --direction Outbound --access Deny --protocol '*' `
  --source-address-prefixes '*' --source-port-ranges '*' `
  --destination-address-prefixes Internet --destination-port-ranges '*'
```

Wait about 30 seconds for the rule to take effect.

### **Task 4: Check that you are really offline**

[offline_check.py](../code/offline_check.py) checks three things: the model service is on a loopback address, the internet is **not** reachable, and a local answer still comes back.

```powershell
python offline_check.py
```

Expected output when the block works (this is the real output from the VM test below):

```text
Model service : http://127.0.0.1:59668/v1
Runs locally  : yes
Internet      : not reachable (offline)
Local answers : [2.48, 1.05] s
```

If it says `REACHABLE`, the block does not work yet. Do not continue until it says `not reachable`.

### **Task 5: Run the whole scenario again**

Repeat the questions from task 1 and write down the timings. Every capability from challenges 3 to 5 must work: the tools, the SOP search with sources, the ONNX model and the ticket.

Offline results on the VM (the same question set, internet blocked at the network level):

| Step | Connected | Offline |
|------|-----------|---------|
| Machine status | 18.5 s | 20.1 s |
| SOP question | 25.7 s | 26.4 s |
| Embedding the 25 SOP chunks | n/m | 36 s |
| One SOP retrieval | n/m | 1.0 s |
| ONNX fault prediction | n/m | 1 ms |
| Short chat answer | 1.4 to 1.8 s | 1.1 s |

The offline and connected times are the same within normal variation. **Nothing in the question path needs the internet.**

### **Task 6: What still needs the cloud?**

Go through the copilot and the Foundry Local service and ask *"does this need the internet?"* A good list:

| Needs the internet | When |
|--------------------|------|
| Starting or restarting the Foundry Local service | Whenever it starts (it fetches the model catalog) |
| Downloading a model or a model update | Once, and when a model is refreshed |
| Updating Foundry Local itself and the Python packages | On a schedule, from a controlled place |
| Syncing the maintenance tickets to the central system | When the device is back online |
| Retraining the fault classifier with new sensor history | Periodically, in the cloud (challenge 5) |
| Monitoring and logs to a central place | When connected |

💡 A good routine for the stretch goal: when the device reconnects, it uploads the new tickets, then checks for a newer model, downloads it, tests it with the evaluation set from challenge 4, and only then switches to it.

You successfully completed challenge 6! 🚀🚀🚀

## Coach notes

### What was verified (on a Windows 11 VM in Azure, 8 vCPU, no GPU)

- The outbound deny rule above blocks the internet (`aka.ms`, `huggingface.co` and `pypi.org` all time out) and the **Azure management path keeps working**: a coach can still run commands on the VM with `az vm run-command`. Do not add an inbound deny rule.
- With the service started and the models loaded **before** the block, the whole copilot works offline, with the same timings as connected.
- Starting the service takes 2 seconds, loading `phi-4-mini` and the embedding model about 17 seconds, and the first chat answer after that 0.6 s.

### What breaks offline: restarting the service

After `foundry server restart` with the internet blocked, `foundry model load` and every other command that names a model failed with `No model matching 'phi-4-mini' was found in the catalog`, **also for a model that was already downloaded** and also when the full variant ID was used. The service log shows why:

```text
GetModelVariant: 'Phi-4-mini-instruct-generic-cpu:5' not in cache, fetching from catalog source.
Region detection probe failed (status 0); defaulting to 'centralus'.
RegionFallback: region 'centralus' unhealthy (transport failure); trying next candidate.
... (7 regions, about 21 seconds each)
```

It tries 7 regions in turn, which is about 2.5 minutes of waiting, and then gives up. Teams that block the network and then restart the service (or reboot the VM) will lose the copilot and will think the network block broke something.

- **Tell teams in the briefing:** start and warm up first, disconnect second, do not restart.
- **For a real shop-floor device** this is a design question: the device needs a way to start the service while disconnected. The Foundry Local SDK has a local catalog (`register_model`) that is meant for model files you already have. We did **not** test it. It is the first thing to try if a customer asks for a device that must survive an offline reboot.

### Other observations

- **The service keeps trying to reach the internet in the background.** Even in a steady state, `Get-NetTCPConnection` shows connections in the `SynSent` state to Azure addresses on port 443 (for example `20.42.73.27`) that never complete. They do not slow the answers. This is useful for the discussion about *"does it phone home?"*: with the network blocked the attempts fail quietly and nothing in the copilot depends on them. We did not find out what the service sends.
- **Python packages must be installed before the disconnect.** `pip` has no internet either.
- **The block must not stop the loopback address.** `127.0.0.1` is not "Internet" for the firewall rule above. If a team blocks "all" outbound traffic and the copilot stops, this is why.

### Not verified

- The Windows Firewall rule on a **laptop**. It needs an administrator terminal, which we did not have. The rule is standard (`New-NetFirewallRule`), and the VM test used the equivalent network rule. Run it once on a laptop before the first event.
- Turning Wi-Fi off or unplugging the cable.

**Stretch:** design the reconnection routine from task 6 and write the ticket-sync part.
