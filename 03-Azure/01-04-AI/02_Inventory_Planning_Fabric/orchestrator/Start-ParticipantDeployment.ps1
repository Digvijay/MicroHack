<#
.SYNOPSIS
Prepare tools inside Azure Cloud Shell and deploy into the participant's existing project.
.DESCRIPTION
Requires Cloud Shell PowerShell and its existing Azure CLI/Python sign-in.
Does not install software on the participant's computer, assign roles, or provision infrastructure.
#>
#Requires -Version 7.2
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$SubscriptionId,
    [Parameter(Mandatory)][string]$ResourceGroupName,
    [Parameter(Mandatory)][uri]$ProjectEndpoint,
    [Parameter(Mandatory)][string]$FabricIQConnectionName,
    [string]$DemandAgentName = 'demand-sensing-agent',
    [string]$OptimisationAgentName = 'inventory-optimisation-agent',
    [string]$ReplenishmentAgentName = 'replenishment-action-agent',
    [string]$EnvironmentName = 'inventory-hosted',
    [switch]$VerifyHosted,
    [switch]$ConfigureOnly
)
$ErrorActionPreference = 'Stop'
if (-not $IsLinux) { throw 'Run this bootstrap in Azure Cloud Shell (PowerShell), not on your computer.' }
if ($VerifyHosted -and $ConfigureOnly) { throw '-VerifyHosted cannot be combined with -ConfigureOnly.' }
if ($ProjectEndpoint.AbsoluteUri.TrimEnd('/') -notmatch '^https://(?<Account>[a-z0-9-]+)\.services\.ai\.azure\.com/api/projects/(?<Project>[a-zA-Z0-9_-]+)$') {
    throw 'Use the FoundryProjectEndpoint supplied by the lab dashboard.'
}
$accountName, $projectName = $Matches.Account, $Matches.Project
foreach ($tool in @('az', 'python3', 'bash')) {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        throw "$tool is missing from this Cloud Shell. Use a supported Azure Cloud Shell session."
    }
}
function Invoke-Checked([string]$Program, [string[]]$Arguments) {
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Program failed (exit $LASTEXITCODE)." }
}
$subscription = az account show --query id -o tsv
if ($LASTEXITCODE -ne 0 -or $subscription -ne $SubscriptionId) {
    throw 'Select the assigned lab subscription with az account set before continuing.'
}
$accountId = az resource list --resource-group $ResourceGroupName `
    --resource-type Microsoft.CognitiveServices/accounts --query "[?name=='$accountName'].id | [0]" -o tsv
if ($LASTEXITCODE -ne 0 -or -not $accountId) {
    throw 'The dashboard project account was not found in the supplied lab resource group.'
}
$projectId = az resource show --ids "$accountId/projects/$projectName" --query id -o tsv
if ($LASTEXITCODE -ne 0 -or -not $projectId) { throw 'Cannot read the existing lab Foundry project.' }

$bootstrap = Join-Path $PSScriptRoot '.azure/bootstrap'
$bin = Join-Path $bootstrap 'bin'
New-Item -ItemType Directory -Path $bin -Force | Out-Null
$env:PATH = "$bin$([IO.Path]::PathSeparator)$env:PATH"
$env:AZD_CONFIG_DIR = Join-Path $bootstrap 'azd-config'
$azd = Get-Command azd -ErrorAction SilentlyContinue
$version = if ($azd) { azd version } else { '' }
if ($azd -and $LASTEXITCODE -ne 0) { throw 'Cannot read the installed azd version.' }
$match = [regex]::Match(($version -join "`n"), '\d+\.\d+\.\d+')
if (-not $match.Success -or [version]$match.Value -lt [version]'1.34.2') {
    $installer = Join-Path $bootstrap 'install-azd.sh'
    Invoke-WebRequest 'https://aka.ms/install-azd.sh' -OutFile $installer
    Invoke-Checked 'bash' @($installer, '--version', '1.34.2', '--install-folder', $bin, '--symlink-folder', $bin)
}
Invoke-Checked 'azd' @('config', 'set', 'auth.useAzCliAuth', 'true')
$extensions = azd extension list --output json
if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect azd extensions.' }
$installed = $extensions | ConvertFrom-Json
foreach ($required in @(
    @{ Id = 'azure.ai.agents'; Version = '1.0.0-beta.19' },
    @{ Id = 'azure.ai.projects'; Version = '1.0.0-beta.13' }
)) {
    $current = ($installed | Where-Object id -eq $required.Id).installedVersion
    if (-not $current -or [System.Management.Automation.SemanticVersion]$current -lt [System.Management.Automation.SemanticVersion]$required.Version) {
        Invoke-Checked 'azd' @('extension', 'install', $required.Id, '--version', $required.Version)
    }
}
azd auth login --check-status
if ($LASTEXITCODE -ne 0) {
    throw 'Cloud Shell Azure CLI authentication is unavailable. Reopen Cloud Shell under the assigned lab account and refresh its sign-in, then rerun. No TAP belongs in this script or terminal.'
}

Invoke-Checked 'python3' @('-c', 'import sys; assert sys.version_info >= (3, 10), "Cloud Shell Python 3.10+ is required"')
$venv = Join-Path $PSScriptRoot '.venv-tools'
$python = Join-Path $venv 'bin/python'
if (-not (Test-Path -LiteralPath $python)) { Invoke-Checked 'python3' @('-m', 'venv', $venv) }
$requirements = Join-Path $PSScriptRoot 'requirements-tools.txt'
$marker = Join-Path $venv 'requirements.sha256'
$hash = (Get-FileHash -LiteralPath $requirements -Algorithm SHA256).Hash
if (-not (Test-Path -LiteralPath $marker) -or (Get-Content -LiteralPath $marker -Raw).Trim() -ne $hash) {
    Invoke-Checked $python @('-m', 'pip', 'install', '-r', $requirements)
    Set-Content -LiteralPath $marker -Value $hash
}
$env:FOUNDRY_PROJECT_ENDPOINT = $ProjectEndpoint.AbsoluteUri.TrimEnd('/')
$env:DEMAND_AGENT_NAME = $DemandAgentName
$env:OPTIMISATION_AGENT_NAME = $OptimisationAgentName
$env:REPLENISHMENT_AGENT_NAME = $ReplenishmentAgentName
$raw = & $python (Join-Path $PSScriptRoot 'configure_specialists.py') --resolve-only
if ($LASTEXITCODE -ne 0) { throw 'Cannot resolve the latest saved specialist versions.' }
$pins = ($raw -join "`n") | ConvertFrom-Json
$parameters = @{
    SubscriptionId = $SubscriptionId
    ProjectResourceId = $projectId.Trim()
    ProjectEndpoint = $ProjectEndpoint
    FabricIQConnectionName = $FabricIQConnectionName
    PythonExecutable = $python
    EnvironmentName = $EnvironmentName
    DemandAgentName = $DemandAgentName
    DemandAgentVersion = $pins.DEMAND_AGENT_VERSION
    OptimisationAgentName = $OptimisationAgentName
    OptimisationAgentVersion = $pins.OPTIMISATION_AGENT_VERSION
    ReplenishmentAgentName = $ReplenishmentAgentName
    ReplenishmentAgentVersion = $pins.REPLENISHMENT_AGENT_VERSION
    Deploy = -not $ConfigureOnly
    VerifyHosted = $VerifyHosted
}
Write-Host "Using saved specialist versions: demand $($pins.DEMAND_AGENT_VERSION), optimisation $($pins.OPTIMISATION_AGENT_VERSION), replenishment $($pins.REPLENISHMENT_AGENT_VERSION)."
& (Join-Path $PSScriptRoot 'Deploy-Orchestrator.ps1') @parameters
