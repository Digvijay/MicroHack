<#
.SYNOPSIS
Runs once per subscription before any deploy-lab.ps1 run starts.
.DESCRIPTION
Registers the resource providers used by the Offline Industrial Copilot lab so the per-participant deployments do not race each other.
.PARAMETER SubscriptionId
Specifies the Azure subscription that contains the lab resources.
.PARAMETER PreferredLocation
Specifies the preferred Azure regions (ordered by preference) for resource deployment.
.PARAMETER AllowedEntraUserIds
Entra user object IDs of every participant holding a lab in this subscription.
#>
param(
    [Parameter(Mandatory=$true)]
    [string]$SubscriptionId,

    [Parameter(Mandatory=$true)]
    [string[]]$PreferredLocation = @(),

    [Parameter(Mandatory=$false)]
    [string[]]$AllowedEntraUserIds = @()
)

$requiredProviders = @(
    "Microsoft.Compute",
    "Microsoft.Network",
    "Microsoft.Storage",
    "Microsoft.KeyVault",
    "Microsoft.OperationalInsights",
    "Microsoft.Insights",
    "Microsoft.MachineLearningServices"
)
foreach($provider in $requiredProviders) {
    $state = (Get-AzResourceProvider -ProviderNamespace $provider -ErrorAction SilentlyContinue | Select-Object -First 1).RegistrationState
    if($state -ne "Registered") {
        Write-Host "[$SubscriptionId] Registering resource provider: $provider"
        Register-AzResourceProvider -ProviderNamespace $provider -ErrorAction Stop | Out-Null
    }
}
