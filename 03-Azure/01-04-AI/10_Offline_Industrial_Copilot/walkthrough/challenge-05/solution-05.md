# Walkthrough Challenge 5 - Train in the cloud, deploy at the edge

[Previous Challenge Solution](../challenge-04/solution-04.md) - **[Home](../../Readme.md)** - [Next Challenge Solution](../challenge-06/solution-06.md)

Duration: 60 minutes (shortcut: 25 minutes)

## Prerequisites

Please ensure that you successfully completed [Challenge 4](../../challenges/challenge-04.md) before continuing with this challenge. The full path also needs the Azure Machine Learning workspace from your lab page.

### **Task 1 (full path): Train in Azure Machine Learning**

1. Open [Azure Machine Learning studio](https://ml.azure.com) and select your workspace (`mlw-oic-...`).
2. **Compute** > **Compute instances** > **New**. Choose a small CPU size such as `Standard_DS3_v2`. Training takes a few seconds, so a small size is enough.
3. **Notebooks**: upload `resources/shortcut/train_fault_classifier.ipynb` and `resources/data/sensor_history.csv`, open the notebook and run all cells. You can also paste the code of [train_fault_classifier.py](../code/train_fault_classifier.py).
4. The notebook:
   - loads the 2,400 labelled sensor readings,
   - trains a random forest (about 94 percent accuracy on held-out data),
   - exports it to **ONNX**,
   - loads the ONNX file with ONNX Runtime and checks that it gives the same answers as the training library.
5. Download `fault_classifier.onnx` and `fault_labels.json` and copy them into your `work` folder, in a folder named `artifacts`.
6. **Stop** the compute instance (or delete it). It bills while it runs.

💡 The point of the exercise is the **workflow**: cloud tools for training, a portable file for delivery, a small runtime on the device. This model is tiny, so you could also train it on your laptop with `python train_fault_classifier.py`.

### **Task 1 (shortcut): Read the notebook and use the ready-made model**

Read through `resources/shortcut/train_fault_classifier.ipynb` and copy `fault_classifier.onnx` and `fault_labels.json` from `resources/shortcut`.

### **Task 2: Run the model on the device**

[fault_tool.py](../code/fault_tool.py) loads the ONNX file with ONNX Runtime and **no** training library:

```python
_session = ort.InferenceSession(str(ARTIFACTS / "fault_classifier.onnx"), providers=["CPUExecutionProvider"])

features = np.array([[machine[f] for f in _meta["features"]]], dtype=np.float32)
label_idx, probabilities = _session.run(None, {_session.get_inputs()[0].name: features})
```

The file is 140 KB. A prediction takes a few milliseconds on the CPU: no GPU, no NPU and no network.

### **Task 3: Make it a tool for the agent**

`predict_fault(machine_id)` reads the machine's current readings (the same data as the status tool) and returns the predicted fault with its probability. Add its schema to the agent:

```python
agent.run_agent(client, model, question, extra_tools=[(fault_tool.SCHEMA, fault_tool.predict_fault)])
```

```powershell
python copilot.py "Run the fault prediction model for CNC-07."
```

```text
  -> predict_fault({'machine_id': 'CNC-07'})
The fault prediction model has identified a high likelihood of bearing wear in CNC-07.
```

💥 **The wording of the question decides which tool the model picks, and it is fragile.** We asked the same request in four ways, three times each, with `phi-4-mini` on the laptop (GPU variant) and the final reference code:

| Wording | Calls the classifier |
|---------|----------------------|
| *"Run the fault prediction model for CNC-07."* | 3 of 3 |
| *"Predict the most likely fault for CNC-07 from its sensor readings."* | 0 of 3 |
| *"Use the fault classifier to predict the fault of CNC-07."* | 0 of 3 |
| *"What does the classifier say is wrong with CMP-01?"* | 0 of 3 |

In the other cases the model searched the SOPs instead and gave a plausible answer from the SOP text (*"spindle vibration high, error E-SPN-214"*), which is correct but is **not** the classifier's verdict. The CPU variant on the VM mis-routed the *"Predict the most likely fault..."* wording in the same way. The same prompts also routed correctly in some earlier runs on the laptop and not in later ones, even at temperature 0, so do not promise a team that a wording "always works". [check_routing.py](../code/check_routing.py) re-runs the four canonical requests a few times and counts how often the right tool is chosen first. This is a good discussion: *what would make routing reliable?* Teams can try a stronger tool description, fewer tools per request, or choosing the tool with the embedding model.

### **Task 4: How far do you trust it?**

| Machine | Reading | Predicted fault | Confidence |
|---------|---------|-----------------|------------|
| CNC-07 | vibration 9.4 mm/s, 78 °C | `bearing_wear` | 0.98 |
| CMP-01 | 104 °C, vibration 2.8 mm/s | `overheating` | 1.00 |
| CNC-03 | normal readings | `normal` | 0.99 |
| LATHE-05 | vibration 4.9 mm/s | `bearing_wear` | 0.67 |
| PRESS-02 | oil temperature warning E-HYD-031 | `low_lubrication` | 0.65 |

- **CNC-07, CMP-01 and CNC-03:** high confidence, and they agree with the error codes and the SOPs. Trust them.
- **PRESS-02:** the classifier says low lubrication with 0.65 while the controller says *oil temperature high* (E-HYD-031). The error code and the SOP are facts from the machine. The classifier is advice. **A known error code beats a low-confidence prediction.**
- **LATHE-05:** 0.67 is an early warning at best. Worth a look at the next planned stop, not a ticket.

A rule for the technician: a result below about 0.8 is a hint, not a diagnosis. The agent should show the confidence so the person can decide.

You successfully completed challenge 5! 🚀🚀🚀

## Coach notes

- **Decide the path per team at the start of the day**, based on experience and Azure access. Teams on the shortcut gain about 35 minutes. Give them a longer challenge 4 or the stretch goals.
- **Custom model serving in Foundry Local:** this MicroHack does **not** serve the classifier through Foundry Local. Foundry Local serves the catalog models, and a scikit-learn classifier is not a chat model. What we validated is the fallback from the outline: the ONNX classifier runs as an **agent tool next to** the small language model, with ONNX Runtime. A fine-tuned small language model served by Foundry Local is not covered here.
- **Cost:** the Azure Machine Learning workspace costs nothing while idle. The compute instance costs a few cents per hour. Remind teams to stop it.
- **Verified with the `az ml` command line** against the workspace that the lab automation creates: the compute instance (`Standard_DS3_v2`) was `Running` **3.7 minutes** after the request, and the training job (`pip install skl2onnx onnx`, then `train_fault_classifier.py`) ran in **2.5 minutes** on it. It reproduced the local result exactly: accuracy 0.940, the same confusion matrix, and an ONNX file that is **byte-identical** to `resources/shortcut/fault_classifier.onnx`. So the shortcut file is a faithful stand-in for a team's own result, and a team's file can be checked against it with a file hash.
- **Not verified:** the clicks in the Azure Machine Learning **studio** (notebooks, kernel start-up) were not exercised, only the same steps through the command line. Plan about 4 minutes for the compute instance to start, and do the studio steps once before the first event.
- **Stretch:** compare the classifier's verdict with what the language model says about the same readings (*"given vibration 9.4 mm/s and 78 °C, what is wrong?"*) and discuss which to trust when.
