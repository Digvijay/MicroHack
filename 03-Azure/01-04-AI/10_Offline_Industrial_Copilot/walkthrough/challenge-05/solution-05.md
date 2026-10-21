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
python copilot.py "Predict the most likely fault for CMP-01 from its sensor readings."
```

```text
  -> predict_fault({'machine_id': 'CMP-01'})
The most likely fault for CMP-01 is overheating.
```

💡 The wording of the question matters. *"What is the likely fault on CNC-07?"* often makes the model look in the SOPs instead of calling the classifier. Mention the sensor readings, or make the tool description stronger.

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
- **Not yet dry-run:** the Azure Machine Learning studio steps in Task 1 (compute creation time, kernel start). The notebook code itself was run end to end. Do the studio steps once before the first event and adjust the timings.
- **Stretch:** compare the classifier's verdict with what the language model says about the same readings (*"given vibration 9.4 mm/s and 78 °C, what is wrong?"*) and discuss which to trust when.
