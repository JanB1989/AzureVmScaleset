# Azure VM Scale Set (Demo / Showcase)

This repository contains a Python 3.11-driven deployment that uses the Azure SDK to deploy an ARM template for a simple Azure Virtual Machine Scale Set (VMSS) with basic horizontal autoscale rules. It is intended for testing and as a showcase.

## What gets deployed
- Virtual Machine Scale Set
- Autoscale rules for horizontal scaling (e.g., by average CPU)

## Prerequisites
- Azure subscription with permissions to create resources
- Windows 10/11 with Python 3.11 installed
- Azure CLI installed and signed in

## Quick start (Windows, Python 3.11)

1. Sign in and pick a subscription (device code works well on locked-down PCs):
   ```powershell
   az login --use-device-code
   az account set --subscription "<subscription-id-or-name>"
   ```

2. Set up environment:
   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   Copy-Item env.example .env
   # Edit .env and set AZURE_SUBSCRIPTION_ID, optional overrides
   ```

3. Provide an SSH public key in `infra/parameters/dev.json` under `adminPublicKey`.

4. Deploy via Python (template creates the resource group and all resources):
   ```powershell
   python deploy.py
   ```

Notes:
- The Python script authenticates with `DefaultAzureCredential`. On Windows, ensure `az login` is complete, or configure environment credentials.
- Parameters are loaded from `infra/parameters/dev.json` and passed to the ARM template.

## Clean up
Delete the resource group (created by the template) to remove all resources:
```powershell
az group delete --name rg-vmss-demo --yes
```

### Generate load (optional)
To see autoscaling in action, start/stop CPU load on all VMSS instances using Azure Run Command (no redeploy). The VMSS is provisioned with `stress-ng` pre-installed.

- Set names and gather instance IDs:
  ```powershell
  $rg = 'rg-vmss-demo'; $vmss = 'vmss-demo'
  $ids = az vmss list-instances -g $rg -n $vmss --query "[].instanceId" -o tsv
  ```

- Start load for 5 minutes (300s) on each instance:
  ```powershell
  foreach ($id in $ids) {
    az vmss run-command invoke -g $rg -n $vmss --instance-id $id `
      --command-id RunShellScript `
      --scripts "nohup stress-ng --cpu 0 --timeout 300s --metrics-brief >/tmp/stress.log 2>&1 &"
  }
  ```

#### Stop or check load
- Auto-stop: load stops automatically after the duration you set.
- Stop early on each instance:
  ```powershell
  foreach ($id in $ids) {
    az vmss run-command invoke -g $rg -n $vmss --instance-id $id `
      --command-id RunShellScript `
      --scripts "sudo pkill -f stress-ng || true"
  }
  ```
- Check logs on each instance:
  ```powershell
  foreach ($id in $ids) {
    az vmss run-command invoke -g $rg -n $vmss --instance-id $id `
      --command-id RunShellScript `
      --scripts "tail -n 50 /tmp/stress.log || true"
  }
  ```

## Autoscale parameters
Parameters are supplied via `infra/parameters/dev.json` and passed to the autoscale settings. Terminology follows the Azure portal. Reference: [Microsoft Learn: Automatically scale a Virtual Machine Scale Set in the Azure portal](https://learn.microsoft.com/en-us/azure/virtual-machine-scale-sets/virtual-machine-scale-sets-autoscale-portal).

| Portal parameter | Our parameter(s) | Explanation | Example |
| --- | --- | --- | --- |
| Time Aggregation | `autoscaleTimeAggregation` | Aggregation across samples in the evaluation window. | `Average` |
| Metric Name | `autoscaleMetricName` | Metric to monitor. | `Percentage CPU` |
| Time grain statistic | `autoscaleStatistic` | Aggregation applied per time grain. | `Average` |
| Operator | `autoscaleOperatorScaleOut`, `autoscaleOperatorScaleIn` | Comparison operator to trigger scaling. | `GreaterThan` / `LessThan` |
| Threshold | `autoscaleThresholdScaleOut`, `autoscaleThresholdScaleIn` | Metric value to trigger scaling. | `70` / `30` |
| Duration | `autoscaleTimeWindow` | Evaluation window length (ISO 8601). | `PT10M` (10 minutes) |
| Operation | `ChangeCount` via `autoscaleChangeCountScaleOut`, `autoscaleChangeCountScaleIn` | Action type and amount for scaling. | Increase count by `1` |
| Instance count | `autoscaleChangeCountScaleOut`, `autoscaleChangeCountScaleIn` | Number of instances to change when rule triggers. | `1` |
| Cool down (minutes) | `autoscaleCooldownScaleOut`, `autoscaleCooldownScaleIn` | Wait time before the rule applies again (ISO 8601). | `PT5M` |
| Instance limits | `autoscaleMin`, `autoscaleMax`, `autoscaleDefault` | Min/Max/Default instance counts for the autoscale profile. | `1` / `3` / `1` |
| Enable autoscale | `autoscaleEnabled` | Toggle to enable/disable autoscale rules. | `true` |

