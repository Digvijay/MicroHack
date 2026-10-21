# Lab automation

Deploys the per-participant resources for the **Offline Industrial Copilot** MicroHack.

## What it deploys

| Resource | Why |
|----------|-----|
| Azure Machine Learning workspace (with storage account, key vault, Log Analytics and Application Insights) | Challenge 5, full path: train the fault classifier in the cloud |
| Windows 11 Pro VM with Python 3.12, a public IP and RDP (optional) | For participants who do not bring a laptop that can run Foundry Local |

Foundry Local itself is **not** installed by the automation. Installing it is part of challenge 1.

## Files

| File | Purpose |
|------|---------|
| `deploy-lab.ps1` | Platform entry point, one run per participant |
| `shared-deploy-lab.ps1` | Registers resource providers once per subscription |
| `main.bicep` | The resources above |
| `lab-defaults.json` | Platform configuration |

## Decisions

- **`deploymentType: resourcegroup`**: the platform creates the resource group and the participant is its owner. Nothing in the lab needs subscription-level rights.
- **`preferredLocation: swedencentral, westeurope, norwayeast`**: regions with Azure Machine Learning and the `Standard_D8s_v5` VM size. The platform falls back to the next region if a deployment fails.
- **`labsPerSubscription: 4`**: each lab uses one 8-vCPU VM, so four labs use 32 vCPUs of the DSv5 family.
- **`estimatedDailyCostsUsd: 8`**: about 6 USD for the VM (8 hours), plus the disk, the public IP and a small Azure Machine Learning compute for challenge 5. The workspace itself costs nothing while idle.
- **VM is Windows, not Linux**: the Foundry Local command-line tool is supported on Windows and macOS. The VM runs the models on its CPU, so answers are slower than on a laptop with a GPU or NPU. Choose a GPU `vmSize` in `main.bicep` for faster answers.
- **Set `$deployVm = $false`** in `deploy-lab.ps1` if every participant brings a suitable laptop.

## Credentials returned to the participant

Resource group, Azure Machine Learning workspace, region, and (with a VM) the VM address, user name and a random password.

## Assumptions and checks

- `Invoke-MhhDeploymentWithRegionFallback` and `Get-MhhStablehash` exist only inside the MicroHack platform, so `deploy-lab.ps1` cannot be run on its own.
- `main.bicep` was validated with `az deployment group validate`. A full deployment of the VM and the installation of Foundry Local on it still needs a dry run before the first event.
- The VM is open for Remote Desktop from the internet and carries the `SecurityControl: Ignore` tag, like other labs on the platform. Do not use it for anything except this lab.
