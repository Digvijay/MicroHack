# Walkthrough Challenge 1 - Get set up

**[Home](../../Readme.md)** - [Next Challenge Solution](../challenge-02/solution-02.md)

Duration: 20 minutes

## Prerequisites

Please ensure that you successfully verified the [General prerequisites](../../Readme.md#general-prerequisites) before continuing with this challenge.

### **Task 1: Install Foundry Local**

Windows (x64 or ARM64):

```powershell
winget install Microsoft.FoundryLocal
```

macOS on Apple silicon:

```bash
brew tap microsoft/foundrylocal
brew install foundrylocal
```

Open a **new** terminal and check the installation:

```powershell
foundry --version
foundry model list
```

`foundry model list` shows the catalog. The *Device* column says where each model runs (NPU, GPU or CPU) and the *Tools* column shows which models support tool calling.

### **Task 2: Download a model and chat with it**

```powershell
foundry model download phi-4-mini
foundry run phi-4-mini
```

Type a question, then leave the chat with `exit`. The model files are stored in `~/.foundry/cache/models`.

### **Task 3: Call the model from Python**

```powershell
cd 10_Offline_Industrial_Copilot
mkdir work
cd work
python -m venv .venv
.venv\Scripts\activate
pip install -r ..\resources\starter\requirements.txt
copy ..\resources\starter\fl.py .
```

[fl.py](../code/fl.py) finds the local service, loads a model and returns the **model ID** that the service expects. Then call the model with the normal OpenAI library ([hello.py](../code/hello.py)):

```python
import fl

model = fl.load("phi-4-mini")
client = fl.client()
reply = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": "In one sentence: what does a technician check first when a CNC spindle vibrates?"}],
    max_tokens=80,
)
print(reply.choices[0].message.content)
```

Expected: one sentence about the spindle, in 1 to 3 seconds on a laptop with a GPU or NPU.

### **Task 4: Find the address of the local service**

```powershell
foundry server status
```

The address is `http://127.0.0.1:<port>`. `127.0.0.1` is the **loopback** address: only programs on the same computer can reach it, so no other device and no one on the internet can call your model. The port is chosen when the service starts. `foundry server start --port 5273` pins it, and the `FOUNDRY_LOCAL_URL` environment variable tells `fl.py` where to look.

You successfully completed challenge 1! 🚀🚀🚀

## Coach notes

- **Pre-cache the models.** `phi-4-mini` is 3.7 GB (4.8 GB for the CPU variant), `qwen2.5-1.5b` 1.1 GB, `qwen3-1.7b` 1.4 GB and `qwen3-embedding-0.6b` 0.5 GB. Ask the teams to start all four downloads in the first minutes (`foundry model download <alias>`). The models are stored in the folder that `foundry cache location` shows. *Not yet validated:* whether that folder can be pre-filled on a VM image or copied between machines. Test this in the dry run.
- **The service needs the model ID, not the alias.** A raw REST call with `phi-4-mini` returns *404 Model not found*. The service expects an ID such as `Phi-4-mini-instruct-generic-gpu:5`. `fl.load()` looks it up with `foundry model list --loaded -o json`. The OpenAI library and the CLI hide this until a team writes its own REST call.
- **Foundry Local picks the variant for the hardware.** The same alias is a GPU variant on one laptop, an NPU variant on a Snapdragon laptop and a CPU variant on the VM. This is why the numbers in challenge 2 differ between teams.
- **Linux is not supported by the command-line tool.** Foundry Local has a Linux SDK, but not the `foundry` command that this MicroHack uses. Use Windows or macOS.
- **The VM from the lab automation** is Windows 11 with Python installed. The participant installs Foundry Local with `winget` in a Remote Desktop session. *Not yet validated on the VM image:* that `winget` works there and which variant (CPU) Foundry Local picks. Test this in the dry run.
- **Teams that finish early:** stream the answer (`stream=True`) and measure the time to the first token.
