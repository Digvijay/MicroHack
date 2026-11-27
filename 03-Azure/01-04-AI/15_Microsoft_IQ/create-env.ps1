<#
.SYNOPSIS
    create-env.ps1: fill .env from your Microsoft IQ lab (Strandvik Drives). Windows twin
    of create-env.sh, same result.

.DESCRIPTION
    Used by both roles (business and builder). Signs you in once with the Azure CLI
    (device code) if needed, finds your lab resource group, reads the resource names and
    endpoints and writes them to .env in this folder. It only reads; it changes nothing.

.EXAMPLE
    ./create-env.ps1
    ./create-env.ps1 -ResourceGroup rg-my-lab
#>
param([string]$ResourceGroup = $env:AZURE_RESOURCE_GROUP)

$ErrorActionPreference = "Stop"
$env:AZURE_CORE_ONLY_SHOW_ERRORS = "1"
$envFile = Join-Path $PSScriptRoot ".env"
$labTag = "15_Microsoft_IQ"

if (-not (Get-Command az -ErrorAction SilentlyContinue)) { throw "Azure CLI (az) is not installed: https://aka.ms/installazurecliwindows" }

function Invoke-Az {
    # Returns parsed JSON, or $null when the command fails.
    $out = & az @args -o json 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $out) { return $null }
    return ($out | Out-String | ConvertFrom-Json)
}

Write-Host "==> Checking your Azure sign-in"
$account = Invoke-Az account show
if (-not $account) {
    Write-Host "    Not signed in. Sign in with your LAB user (one device code login)."
    az login --use-device-code --output none
    if ($LASTEXITCODE -ne 0) { throw "az login failed." }
    $account = Invoke-Az account show
}
$subId = $account.id; $tenantId = $account.tenantId
Write-Host "    Signed in as $($account.user.name)"

function Find-LabAccount {
    $all = @(Invoke-Az resource list --resource-type Microsoft.CognitiveServices/accounts)
    $tagged = @($all | Where-Object { $_.tags.microhack -eq $labTag -and (-not $ResourceGroup -or $_.resourceGroup -eq $ResourceGroup) })
    if ($tagged.Count -gt 0) { return $tagged[0] }
    return @($all | Where-Object { $_.name -like 'iq-*' -and (-not $ResourceGroup -or $_.resourceGroup -eq $ResourceGroup) }) | Select-Object -First 1
}

Write-Host "==> Looking for your lab"
$acct = Find-LabAccount
if (-not $acct) {
    foreach ($s in @(Invoke-Az account list | Where-Object { $_.state -eq 'Enabled' -and $_.id -ne $subId })) {
        az account set --subscription $s.id | Out-Null
        $acct = Find-LabAccount
        if ($acct) { $subId = $s.id; break }
    }
}
if (-not $acct) { throw "No Microsoft IQ lab found. Sign in with your lab user, or pass -ResourceGroup <name>." }
$foundry = $acct.name; $rg = $acct.resourceGroup
Write-Host "    Lab resource group: $rg (Foundry resource $foundry)"

$resources = @(Invoke-Az resource list -g $rg)
function First-OfType([string]$Type, [string]$Prefix = "") {
    ($resources | Where-Object { $_.type -eq $Type -and $_.name -like "$Prefix*" } | Select-Object -First 1).name
}

$hostBase = "https://$foundry.services.ai.azure.com"
$searchName = First-OfType "Microsoft.Search/searchServices"
$deployments = @((Invoke-Az cognitiveservices account deployment list -g $rg -n $foundry) | ForEach-Object { $_.name })
function Pick-Model([string]$Name) {
    if ($deployments -notcontains $Name) { Write-Warning "Model deployment '$Name' not found in $foundry." }
    return $Name
}

Write-Host "==> Reading the Work IQ emulator"
$funcName = First-OfType "Microsoft.Web/sites" "iq-wiq-"
$wiq = @{ mcp = ""; viewer = ""; board = ""; key = ""; sam = "" }
if ($funcName) {
    $funcHost = (Invoke-Az resource show -g $rg -n $funcName --resource-type Microsoft.Web/sites).properties.defaultHostName
    $wiq.mcp = "https://$funcHost/mcp"; $wiq.viewer = "https://$funcHost/viewer"; $wiq.board = "https://$funcHost/board"
    $settings = @(Invoke-Az functionapp config appsettings list -g $rg -n $funcName)
    # The participant key is Alex's persona key. The admin key is never written to .env.
    $wiq.key = ($settings | Where-Object name -eq 'WORKIQ_KEY_ALEX').value
    $wiq.sam = ($settings | Where-Object name -eq 'WORKIQ_KEY_SAM').value
} else {
    Write-Warning "No Work IQ emulator found in $rg."
}

Write-Host "==> Looking for your Fabric workspace"
$fabricCapacity = First-OfType "Microsoft.Fabric/capacities"
$ws = Invoke-Az rest --method get --url "https://api.fabric.microsoft.com/v1/workspaces" --resource "https://api.fabric.microsoft.com"
$fabricWorkspaceId = (@($ws.value) | Where-Object { $_.displayName -like 'strandvik*' } | Select-Object -First 1).id
if (-not $fabricWorkspaceId) {
    Write-Host "    No 'strandvik-...' Fabric workspace yet. Create one on capacity '$fabricCapacity', then run this again."
}

$values = [ordered]@{
    AZURE_SUBSCRIPTION_ID       = $subId
    AZURE_TENANT_ID             = $tenantId
    AZURE_RESOURCE_GROUP        = $rg
    FOUNDRY_ACCOUNT             = $foundry
    PROJECT_ENDPOINT_STRANDVIK  = "$hostBase/api/projects/strandvik"
    PROJECT_ENDPOINT_KOLVO      = "$hostBase/api/projects/kolvo"
    MODEL_DEPLOYMENT_NAME       = Pick-Model "gpt-5.4-mini"
    JUDGE_MODEL_DEPLOYMENT_NAME = Pick-Model "gpt-5.6-luna"
    EMBEDDING_DEPLOYMENT_NAME   = Pick-Model "text-embedding-3-large"
    SEARCH_ENDPOINT             = $(if ($searchName) { "https://$searchName.search.windows.net" } else { "" })
    STORAGE_ACCOUNT             = First-OfType "Microsoft.Storage/storageAccounts" "iqst"
    DOCUMENTS_CONTAINER         = "documents"
    APPINSIGHTS_NAME            = First-OfType "Microsoft.Insights/components"
    FABRIC_CAPACITY_NAME        = $fabricCapacity
    FABRIC_WORKSPACE_ID         = $fabricWorkspaceId
    WORKIQ_MCP_URL              = $wiq.mcp
    WORKIQ_VIEWER_URL           = $wiq.viewer
    WORKIQ_BOARD_URL            = $wiq.board
    WORKIQ_KEY                  = $wiq.key
    WORKIQ_KEY_SAM              = $wiq.sam
}

# Keep any lines you added yourself; replace the managed keys.
$keep = @()
if (Test-Path $envFile) {
    $keep = @(Get-Content $envFile | Where-Object {
        $k = ($_ -split '=', 2)[0]
        -not $values.Contains($k) -and $_ -notmatch '^# (Written by create-env|Lab:)'
    })
}
$lines = @("# Written by create-env.ps1 on $((Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mmZ')). Do not commit: it holds your Work IQ keys.", "# Lab: $rg")
$lines += $values.Keys | ForEach-Object { "$_=$($values[$_])" }
$lines += $keep
# LF line endings so the same file works in bash and Python.
[IO.File]::WriteAllText($envFile, (($lines -join "`n") + "`n"))

$hex = $subId -replace '-', ''
$bytes = for ($i = 0; $i -lt $hex.Length; $i += 2) { [Convert]::ToByte($hex.Substring($i, 2), 16) }
$subToken = [Convert]::ToBase64String([byte[]]$bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
function Project-Url([string]$p) { "https://ai.azure.com/nextgen/r/$subToken,$rg,,$foundry,$p/home?tid=$tenantId" }
$fabricUrl = if ($fabricWorkspaceId) { "https://app.fabric.microsoft.com/groups/$fabricWorkspaceId/list?tid=$tenantId" } else { "https://app.fabric.microsoft.com/home?tid=$tenantId (create your workspace)" }

Write-Host ""
Write-Host "============================================================"
Write-Host " Your lab is ready. Wrote $envFile"
Write-Host ""
Write-Host " Foundry (ai.azure.com)"
Write-Host "   Strandvik project (build here): $(Project-Url 'strandvik')"
Write-Host "   Kolvo project (pre-built):       $(Project-Url 'kolvo')"
Write-Host " Azure portal, your resource group:"
Write-Host "   https://portal.azure.com/#@$tenantId/resource/subscriptions/$subId/resourceGroups/$rg/overview"
Write-Host " Fabric workspace:"
Write-Host "   $fabricUrl"
Write-Host " Work IQ viewer (play Sam here): $($wiq.viewer)"
Write-Host " Kolvo procurement board:        $($wiq.board)"
Write-Host "   Sign in to both with your WORKIQ_KEY (in .env)."
Write-Host "============================================================"
$missing = @($values.Keys | Where-Object { -not $values[$_] })
if ($missing.Count -gt 0) {
    Write-Host " Still empty: $($missing -join ', ')"
    Write-Host " (FABRIC_WORKSPACE_ID stays empty until you create your Fabric workspace.)"
}
