<#
.SYNOPSIS
    Deploys the per-attendee lab for the "Microsoft IQ" MicroHack (Caldova Components).

.DESCRIPTION
    Called by the MicroHack platform once per attendee, in parallel. Each run builds
    one complete, isolated lab in the attendee's resource group:

      - Log Analytics workspace + workspace-based Application Insights
      - Foundry account (AIServices, keyless) + Foundry project
      - Model deployments: gpt-5.4-mini (agent chat), gpt-5.6-luna (Foundry IQ
        knowledge graph extraction and query planning), text-embedding-3-small
      - Azure AI Search (Foundry IQ), Basic tier, Entra auth + semantic ranker
      - Storage account + container 'caldova-docs' for the knowledge corpus
        (blob soft delete on, versioning off, as the Foundry IQ entity graph needs)
      - Fabric capacity (default F2) with the attendee as capacity admin
      - Work IQ emulator (Azure Functions Flex Consumption, MCP server) with four
        persona keys and one admin key
      - Data-plane RBAC for the attendee and the service identities

    Everything except Fabric lives in one region: the first region from
    $PreferredLocation that offers Search Basic with semantic ranker and has enough
    model quota. Fabric may fall back to another preferred region on its own.

    The platform pre-sets the Az context and pre-creates the resource group.
    This script never calls Connect-AzAccount, Set-AzContext, az login or az account set.

.PARAMETER DeploymentType
    Deployment scope, passed in by the platform.
.PARAMETER SubscriptionId
    Azure subscription, passed in by the platform.
.PARAMETER ResourceGroupName
    Pre-created resource group, passed in by the platform.
.PARAMETER PreferredLocation
    Ordered list of preferred Azure regions, passed in by the platform.
.PARAMETER AllowedEntraUserIds
    Entra user object IDs for this lab, passed in by the platform.
.PARAMETER FabricSkuName
    Per-attendee Fabric capacity SKU. Default F2. If you change it, also change
    estimatedDailyCostsUsd and labsPerSubscription in lab-defaults.json.
.PARAMETER ChatModelCapacity
    gpt-5.4-mini GlobalStandard capacity in thousands of tokens per minute. Default 100.
.PARAMETER GraphModelCapacity
    gpt-5.6-luna GlobalStandard capacity in thousands of tokens per minute. Default 50.
.PARAMETER EmbeddingModelCapacity
    text-embedding-3-small GlobalStandard capacity in thousands of tokens per minute. Default 50.
#>
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('subscription','resourcegroup','resourcegroup-with-subscriptionowner')]
    [string]$DeploymentType,

    [Parameter(Mandatory=$true)]
    [string]$SubscriptionId,

    [string]$ResourceGroupName = "",

    [string[]]$PreferredLocation = @(),

    [string[]]$AllowedEntraUserIds = @(),

    [ValidateSet('F2','F4','F8','F16','F32','F64')]
    [string]$FabricSkuName = "F2",

    [ValidateRange(10, 1000)]
    [int]$ChatModelCapacity = 100,

    [ValidateRange(10, 1000)]
    [int]$GraphModelCapacity = 50,

    [ValidateRange(10, 1000)]
    [int]$EmbeddingModelCapacity = 50
)

$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
$cogApi      = "2025-06-01"
$searchApi   = "2025-05-01"
$storageApi  = "2023-05-01"
$fabricApi   = "2023-11-01"
$laApi       = "2023-09-01"
$appiApi     = "2020-02-02"
$roleApi     = "2022-04-01"
$tagsApi     = "2021-04-01"

$labTags = @{ SecurityControl = "Ignore"; microhack = "15_Microsoft_IQ" }

$chatModel      = "gpt-5.4-mini"
$graphModel     = "gpt-5.6-luna"
$embeddingModel = "text-embedding-3-small"
$modelPlan = @(
    [pscustomobject]@{ Name = $chatModel;      Capacity = $ChatModelCapacity }
    [pscustomobject]@{ Name = $graphModel;     Capacity = $GraphModelCapacity }
    [pscustomobject]@{ Name = $embeddingModel; Capacity = $EmbeddingModelCapacity }
)

$roles = @{
    AzureAIUser                = "53ca6127-db72-4b80-b1b0-d745d6d5456d"
    CognitiveServicesUser      = "a97b65f3-24c7-4388-baec-2e87135dc908"
    CognitiveServicesOpenAIUser = "5e0bd9bd-7b93-4f28-af87-19fc36ad61bd"
    SearchServiceContributor   = "7ca78c08-252a-4471-8644-bb5ff32d4ba0"
    SearchIndexDataContributor = "8ebe5a00-799e-43f5-93ac-243d3dce84a7"
    SearchIndexDataReader      = "1407120a-92aa-4202-b7e9-c0e197c71c8f"
    StorageBlobDataContributor = "ba92f5b4-2d11-453d-a403-e96b0029c9fe"
    StorageBlobDataReader      = "2a2b9908-6ea1-4ae2-8e65-a410df84e7d1"
}

# ---------------------------------------------------------------------------
# Validate inputs and derive names
# ---------------------------------------------------------------------------
if ($AllowedEntraUserIds.Count -eq 0) {
    throw "At least one attendee object ID must be supplied in AllowedEntraUserIds."
}
# The platform may pass PreferredLocation as one comma-separated string.
$candidateRegions = @($PreferredLocation | ForEach-Object { $_ -split ',' } |
    ForEach-Object { $_.Trim().ToLower() } | Where-Object { $_ })
if ($candidateRegions.Count -eq 0) { $candidateRegions = @("swedencentral", "francecentral", "switzerlandnorth") }

$stableHash = (Get-MhhStableHash -Value $AllowedEntraUserIds -Length 12).ToLower()

$effectiveRG = $ResourceGroupName
if ([string]::IsNullOrWhiteSpace($effectiveRG)) {
    # 'subscription' deployments get no resource group from the platform.
    $effectiveRG = "rg-iq-lab-$stableHash"
    if (-not (Get-AzResourceGroup -Name $effectiveRG -ErrorAction SilentlyContinue)) {
        New-AzResourceGroup -Name $effectiveRG -Location $candidateRegions[0] | Out-Null
        Write-Host "[OK]    Created resource group '$effectiveRG' (subscription deployment)."
    }
}

$foundryAccountName = "iq-$stableHash"
$foundryProjectName = "caldova-iq"
$searchName         = "iq-srch-$stableHash"
$storageName        = "iqst$stableHash"
$storageContainer   = "caldova-docs"
$laName             = "iq-log-$stableHash"
$appiName           = "iq-appi-$stableHash"
$fabricCapacityName = "iqcap$stableHash"
$emulatorName       = "iq-wiq-$stableHash"

$rgPath      = "/subscriptions/$SubscriptionId/resourceGroups/$effectiveRG"
$accountId   = "$rgPath/providers/Microsoft.CognitiveServices/accounts/$foundryAccountName"
$projectId   = "$accountId/projects/$foundryProjectName"
$searchId    = "$rgPath/providers/Microsoft.Search/searchServices/$searchName"
$storageId   = "$rgPath/providers/Microsoft.Storage/storageAccounts/$storageName"
$laId        = "$rgPath/providers/Microsoft.OperationalInsights/workspaces/$laName"
$appiId      = "$rgPath/providers/Microsoft.Insights/components/$appiName"
$fabricId    = "$rgPath/providers/Microsoft.Fabric/capacities/$fabricCapacityName"

# ---------------------------------------------------------------------------
# ARM REST helper. Uses the full management.azure.com -Uri form (the -Path form
# can drop the api-version on some PUT/PATCH calls) and checks the HTTP status,
# so a failed control-plane call throws instead of printing a false "[OK]".
# Pass -AllowNotFound for existence probes that may legitimately return 404.
# ---------------------------------------------------------------------------
function Invoke-MhhArm {
    param(
        [Parameter(Mandatory=$true)][ValidateSet('GET','PUT','PATCH','POST','DELETE')][string]$Method,
        [Parameter(Mandatory=$true)][string]$Path,
        [string]$Payload,
        [switch]$AllowNotFound,
        [int[]]$AllowStatus = @()
    )
    $uri = if ($Path -like 'https://*') { $Path } else { "https://management.azure.com$Path" }
    $params = @{ Method = $Method; Uri = $uri }
    if ($Payload) { $params.Payload = $Payload }
    $resp = $null
    for ($attempt = 1; $attempt -le 4; $attempt++) {
        $resp = Invoke-AzRestMethod @params
        # Throttling and transient gateway errors: back off and retry.
        if ($resp.StatusCode -in @(429, 502, 503, 504) -and $attempt -lt 4) {
            Start-Sleep -Seconds (10 * $attempt)
            continue
        }
        break
    }
    if (($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 300) -or
        ($AllowNotFound -and $resp.StatusCode -eq 404) -or
        ($resp.StatusCode -in $AllowStatus)) {
        return $resp
    }
    throw "ARM $Method $uri failed with HTTP $($resp.StatusCode): $($resp.Content)"
}

function Get-ArmJson {
    param([Parameter(Mandatory=$true)][string]$Path)
    $r = Invoke-MhhArm -Method GET -Path $Path -AllowNotFound
    if ($r.StatusCode -eq 404) { return $null }
    return ($r.Content | ConvertFrom-Json)
}

# Refresh platform credentials between long phases. The platform supplies
# Update-MhhToken; run-local.ps1 supplies a no-op stand-in.
function Update-LabToken {
    if (Get-Command Update-MhhToken -ErrorAction SilentlyContinue) { Update-MhhToken | Out-Null }
}

# Poll a resource until its provisioningState is terminal. Throws on failure or timeout.
function Wait-ArmProvisioned {
    param(
        [Parameter(Mandatory=$true)][string]$Path,
        [Parameter(Mandatory=$true)][string]$Label,
        [int]$TimeoutSeconds = 600,
        [int]$IntervalSeconds = 10,
        [scriptblock]$ExtraCheck
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $obj = $null; $state = "Unknown"
    while ((Get-Date) -lt $deadline) {
        $obj = Get-ArmJson -Path $Path
        if ($obj) {
            $state = [string]$obj.properties.provisioningState
            if ($state -in @('Failed', 'Canceled')) {
                throw "$Label provisioning ended as '$state': $($obj | ConvertTo-Json -Depth 8 -Compress)"
            }
            if ($state -eq 'Succeeded' -and (-not $ExtraCheck -or (& $ExtraCheck $obj))) {
                return $obj
            }
        }
        Start-Sleep -Seconds $IntervalSeconds
        Update-LabToken
    }
    throw "$Label did not reach Succeeded within ${TimeoutSeconds}s (last state: $state)."
}

# Deterministic role assignment name, so a re-run targets the same assignment.
function Get-DeterministicGuid {
    param([Parameter(Mandatory=$true)][string]$Seed)
    $md5 = [System.Security.Cryptography.MD5]::Create()
    try { return ([guid]::new($md5.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($Seed.ToLower())))).ToString() }
    finally { $md5.Dispose() }
}

# Idempotent RBAC through ARM REST (no Microsoft Graph lookup needed). Checks for an
# existing assignment first, tolerates RoleAssignmentExists, and retries while a new
# managed identity is still replicating (PrincipalNotFound).
function Grant-LabRole {
    param(
        [Parameter(Mandatory=$true)][string]$Scope,
        [Parameter(Mandatory=$true)][string]$PrincipalId,
        [Parameter(Mandatory=$true)][ValidateSet('User','ServicePrincipal','Group')][string]$PrincipalType,
        [Parameter(Mandatory=$true)][string]$RoleName,
        [Parameter(Mandatory=$true)][string]$Label
    )
    $roleId = $roles[$RoleName]
    $roleDefinitionId = "/subscriptions/$SubscriptionId/providers/Microsoft.Authorization/roleDefinitions/$roleId"

    $listPath = "$Scope/providers/Microsoft.Authorization/roleAssignments?api-version=$roleApi&`$filter=assignedTo('$PrincipalId')"
    $existing = Invoke-MhhArm -Method GET -Path $listPath -AllowNotFound
    if ($existing.StatusCode -eq 200) {
        $match = @(($existing.Content | ConvertFrom-Json).value | Where-Object {
            $_.properties.roleDefinitionId -like "*/$roleId" -and $Scope.ToLower().StartsWith(([string]$_.properties.scope).ToLower())
        })
        if ($match.Count -gt 0) {
            Write-Host "[OK]    '$RoleName' already assigned to $Label."
            return
        }
    }

    $assignmentName = Get-DeterministicGuid -Seed "$Scope|$PrincipalId|$roleId"
    $body = @{ properties = @{
        roleDefinitionId = $roleDefinitionId
        principalId      = $PrincipalId
        principalType    = $PrincipalType
    } } | ConvertTo-Json -Depth 4
    $putPath = "$Scope/providers/Microsoft.Authorization/roleAssignments/${assignmentName}?api-version=$roleApi"

    for ($attempt = 1; $attempt -le 12; $attempt++) {
        $resp = Invoke-AzRestMethod -Method PUT -Uri "https://management.azure.com$putPath" -Payload $body
        if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 300) {
            Write-Host "[OK]    Granted '$RoleName' to $Label."
            return
        }
        if ($resp.StatusCode -eq 409 -and $resp.Content -match 'RoleAssignmentExists') {
            Write-Host "[OK]    '$RoleName' already assigned to $Label."
            return
        }
        if ($resp.Content -match 'PrincipalNotFound|does not exist in the directory' -or
            $resp.StatusCode -in @(429, 500, 502, 503, 504)) {
            Start-Sleep -Seconds 15
            continue
        }
        throw "Could not grant '$RoleName' to ${Label} (HTTP $($resp.StatusCode)): $($resp.Content)"
    }
    throw "Could not grant '$RoleName' to $Label after 12 attempts (principal not replicated yet)."
}

# Error codes that mean "this region cannot host the lab right now, try the next one".
$regionRetryPattern = 'InsufficientQuota|QuotaExceeded|exceed\w*\W.{0,60}quota|SkuNotAvailable|SkuNotSupported|' +
    'NoRegisteredProviderFound|LocationNotAvailableForResourceType|ResourceNotAvailable|ResourcesUnavailable|' +
    'ModelNotSupported|DeploymentModelNotSupported|NotSupportedInRegion|InsufficientCapacity|' +
    'NotEnoughCapacity|NoCapacity|RegionCapacity|IQ_REGION_RETRY'

function Get-ModelInfo {
    param($Entry)
    if ($Entry.PSObject.Properties.Name -contains 'model' -and $Entry.model) { return $Entry.model }
    return $Entry
}

Write-Host "[INFO]  Deploying Microsoft IQ lab into '$effectiveRG' (hash $stableHash)."
Write-Host "[INFO]  Candidate regions: $($candidateRegions -join ', ')."

# ---------------------------------------------------------------------------
# Phase 1: resource providers and resource group tags
# ---------------------------------------------------------------------------
$requiredProviders = @(
    'Microsoft.CognitiveServices', 'Microsoft.Search', 'Microsoft.Storage',
    'Microsoft.OperationalInsights', 'Microsoft.Insights', 'Microsoft.Web', 'Microsoft.Fabric'
)
foreach ($ns in $requiredProviders) {
    $prov = Get-ArmJson -Path "/subscriptions/$SubscriptionId/providers/${ns}?api-version=2021-04-01"
    if (-not $prov -or $prov.registrationState -ne 'Registered') {
        Invoke-MhhArm -Method POST -Path "/subscriptions/$SubscriptionId/providers/$ns/register?api-version=2021-04-01" | Out-Null
        Write-Host "[INFO]  Registering resource provider '$ns'..."
    }
}
foreach ($ns in $requiredProviders) {
    $deadline = (Get-Date).AddMinutes(5)
    do {
        $prov = Get-ArmJson -Path "/subscriptions/$SubscriptionId/providers/${ns}?api-version=2021-04-01"
        if ($prov.registrationState -eq 'Registered') { break }
        Start-Sleep -Seconds 10
    } while ((Get-Date) -lt $deadline)
    if ($prov.registrationState -ne 'Registered') {
        if ($ns -eq 'Microsoft.Fabric') {
            Write-Host "[WARN]  Resource provider '$ns' is still '$($prov.registrationState)'. Fabric may fail."
        } else {
            throw "Resource provider '$ns' did not register within 5 minutes (state: $($prov.registrationState))."
        }
    }
}
Write-Host "[OK]    Resource providers registered."

# MCAPS subscriptions inherit management-group 'Modify' policies that force
# publicNetworkAccess=Disabled on Storage (and similar services). The attendee works
# from a Codespace and from Foundry, so the public endpoints must stay reachable.
# The standard MCAPS exemption is the RG tag SecurityControl=Ignore. Merge it so any
# existing tags (including the platform's) are preserved. Security is unchanged:
# every service here is keyless or Entra-first, so a token with a data role is required.
$rgTagBody = @{ operation = "Merge"; properties = @{ tags = $labTags } } | ConvertTo-Json -Depth 4
Invoke-MhhArm -Method PATCH -Path "$rgPath/providers/Microsoft.Resources/tags/default?api-version=$tagsApi" -Payload $rgTagBody | Out-Null
Write-Host "[OK]    Resource group tagged 'SecurityControl=Ignore' (merged)."

# ---------------------------------------------------------------------------
# Phase 2: choose the lab region
# On a re-run the region is locked to wherever the Foundry account or Search
# service already lives. On a fresh run, pick the first preferred region that
# offers Search Basic with the semantic ranker and has enough model quota.
# ---------------------------------------------------------------------------
$existingAccount = Get-ArmJson -Path "${accountId}?api-version=$cogApi"
$existingSearch  = Get-ArmJson -Path "${searchId}?api-version=$searchApi"
$lockedRegion = $null
if ($existingAccount) { $lockedRegion = ([string]$existingAccount.location).ToLower().Replace(' ', '') }
elseif ($existingSearch) { $lockedRegion = ([string]$existingSearch.location).ToLower().Replace(' ', '') }

$searchOfferings = $null
try {
    $searchOfferings = ((Invoke-MhhArm -Method POST -Path "/providers/Microsoft.Search/fetchOfferings?api-version=2026-09-01-preview").Content | ConvertFrom-Json).regions
} catch {
    Write-Host "[WARN]  Could not read Search regional offerings; skipping that pre-check. $_"
}

$locationModelVersions = @{}
function Test-LabRegion {
    param([Parameter(Mandatory=$true)][string]$Region)

    if ($searchOfferings) {
        $offer = $searchOfferings | Where-Object { ([string]$_.regionName).ToLower().Replace(' ', '') -eq $Region } | Select-Object -First 1
        if (-not $offer) { return "Azure AI Search is not offered there" }
        if (@($offer.skus | Where-Object { $_.sku.name -eq 'basic' }).Count -eq 0) {
            return "no new dedicated Search Basic services can be created there (high demand)"
        }
        if (@($offer.features | Where-Object { $_.name -eq 'SemanticSearch' }).Count -eq 0) {
            return "the Search semantic ranker (needed by agentic retrieval) is not available there"
        }
    }

    $searchUsage = Get-ArmJson -Path "/subscriptions/$SubscriptionId/providers/Microsoft.Search/locations/$Region/usages?api-version=$searchApi"
    $basic = $searchUsage.value | Where-Object { $_.name.value -eq 'basic' } | Select-Object -First 1
    if ($basic -and ([int]$basic.currentValue -ge [int]$basic.limit)) {
        return "the Search Basic service quota is used up ($($basic.currentValue)/$($basic.limit))"
    }

    $models = Get-ArmJson -Path "/subscriptions/$SubscriptionId/providers/Microsoft.CognitiveServices/locations/$Region/models?api-version=$cogApi"
    if (-not $models) { return "the Foundry model catalog could not be read" }
    $usages = Get-ArmJson -Path "/subscriptions/$SubscriptionId/providers/Microsoft.CognitiveServices/locations/$Region/usages?api-version=$cogApi"
    foreach ($m in $modelPlan) {
        $candidates = @($models.value | Where-Object { $_.kind -eq 'AIServices' } | ForEach-Object { Get-ModelInfo $_ } |
            Where-Object { $_.name -eq $m.Name -and @($_.skus | Where-Object { $_.name -eq 'GlobalStandard' }).Count -gt 0 })
        if ($candidates.Count -eq 0) { return "model '$($m.Name)' is not available as GlobalStandard" }
        $usage = $usages.value | Where-Object { $_.name.value -eq "OpenAI.GlobalStandard.$($m.Name)" } | Select-Object -First 1
        if ($usage) {
            $free = [int]$usage.limit - [int]$usage.currentValue
            if ($free -lt $m.Capacity) {
                return "model '$($m.Name)' has only $free K TPM of GlobalStandard quota left (needs $($m.Capacity))"
            }
        }
    }
    return $null
}

$regionsToTry = @()
if ($lockedRegion) {
    Write-Host "[OK]    Existing lab found in '$lockedRegion'; re-using that region."
    $regionsToTry = @($lockedRegion)
} else {
    foreach ($candidate in $candidateRegions) {
        $reason = Test-LabRegion -Region $candidate
        if ($reason) {
            Write-Warning "Skipping region '$candidate': $reason."
            continue
        }
        $regionsToTry += $candidate
    }
    if ($regionsToTry.Count -eq 0) {
        throw "None of the preferred regions can host this lab (Search Basic with semantic ranker plus model quota): $($candidateRegions -join ', ')"
    }
    Write-Host "[OK]    Regions that pass the pre-checks: $($regionsToTry -join ', ')."
}

# ---------------------------------------------------------------------------
# Phase 3: Search (submitted first because it takes longest) + Foundry account,
# project and model deployments, all in one region. On a fresh run, a quota or
# capacity error removes what this run created and moves on to the next region.
# ---------------------------------------------------------------------------
function Submit-SearchService {
    param([Parameter(Mandatory=$true)][string]$Region)
    $body = @{
        location   = $Region
        tags       = $labTags
        sku        = @{ name = "basic" }
        identity   = @{ type = "SystemAssigned" }
        properties = @{
            replicaCount        = 1
            partitionCount      = 1
            hostingMode         = "default"
            publicNetworkAccess = "enabled"
            disableLocalAuth    = $false
            authOptions         = @{ aadOrApiKey = @{ aadAuthFailureMode = "http401WithBearerChallenge" } }
            semanticSearch      = "free"
        }
    } | ConvertTo-Json -Depth 6
    Invoke-MhhArm -Method PUT -Path "${searchId}?api-version=$searchApi" -Payload $body | Out-Null
}

function Remove-FoundryAccountAndPurge {
    param([Parameter(Mandatory=$true)][string]$Region)
    Invoke-MhhArm -Method DELETE -Path "${accountId}?api-version=$cogApi" -AllowNotFound | Out-Null
    $deadline = (Get-Date).AddMinutes(5)
    while ((Get-Date) -lt $deadline -and (Get-ArmJson -Path "${accountId}?api-version=$cogApi")) { Start-Sleep -Seconds 10 }
    Invoke-MhhArm -Method DELETE -AllowNotFound `
        -Path "/subscriptions/$SubscriptionId/providers/Microsoft.CognitiveServices/locations/$Region/resourceGroups/$effectiveRG/deletedAccounts/${foundryAccountName}?api-version=$cogApi" | Out-Null
    Start-Sleep -Seconds 20
}

function New-FoundryAccount {
    param([Parameter(Mandatory=$true)][string]$Region)
    $body = @{
        kind     = "AIServices"
        sku      = @{ name = "S0" }
        location = $Region
        tags     = $labTags
        identity = @{ type = "SystemAssigned" }
        properties = @{
            customSubDomainName    = $foundryAccountName
            publicNetworkAccess    = "Enabled"
            allowProjectManagement = $true
            disableLocalAuth       = $true
        }
    } | ConvertTo-Json -Depth 5

    $resp = Invoke-AzRestMethod -Method PUT -Uri "https://management.azure.com${accountId}?api-version=$cogApi" -Payload $body
    # A soft-deleted account (48h retention) reserves the subdomain globally and blocks
    # re-creation with 409 CustomDomainInUse. Purge it and retry once.
    if ($resp.StatusCode -eq 409 -and $resp.Content -match 'CustomDomainInUse|FlagMustBeSetForRestore|soft') {
        Write-Host "[WARN]  Subdomain '$foundryAccountName' is held by a soft-deleted account; purging and retrying."
        $deleted = Get-ArmJson -Path "/subscriptions/$SubscriptionId/providers/Microsoft.CognitiveServices/deletedAccounts?api-version=$cogApi"
        foreach ($d in @($deleted.value | Where-Object { $_.name -eq $foundryAccountName })) {
            $delRg = if ($d.id -match '/resourceGroups/([^/]+)/deletedAccounts/') { $Matches[1] } else { $effectiveRG }
            Invoke-MhhArm -Method DELETE -AllowNotFound `
                -Path "/subscriptions/$SubscriptionId/providers/Microsoft.CognitiveServices/locations/$($d.location)/resourceGroups/$delRg/deletedAccounts/${foundryAccountName}?api-version=$cogApi" | Out-Null
        }
        Start-Sleep -Seconds 20
        $resp = Invoke-AzRestMethod -Method PUT -Uri "https://management.azure.com${accountId}?api-version=$cogApi" -Payload $body
    }
    if ($resp.StatusCode -ge 400) {
        throw "Foundry account create in '$Region' failed (HTTP $($resp.StatusCode)): $($resp.Content)"
    }
    Wait-ArmProvisioned -Path "${accountId}?api-version=$cogApi" -Label "Foundry account '$foundryAccountName'" -TimeoutSeconds 600 | Out-Null
}

function Resolve-ModelVersion {
    param([Parameter(Mandatory=$true)][string]$ModelName, [Parameter(Mandatory=$true)][string]$Region)
    $list = Get-ArmJson -Path "${accountId}/models?api-version=$cogApi"
    $entries = @($list.value | ForEach-Object { Get-ModelInfo $_ } |
        Where-Object { $_.name -eq $ModelName -and $_.format -eq 'OpenAI' -and @($_.skus | Where-Object { $_.name -eq 'GlobalStandard' }).Count -gt 0 })
    if ($entries.Count -eq 0) {
        # Fall back to the regional catalog if the account list is not populated yet.
        $loc = Get-ArmJson -Path "/subscriptions/$SubscriptionId/providers/Microsoft.CognitiveServices/locations/$Region/models?api-version=$cogApi"
        $entries = @($loc.value | Where-Object { $_.kind -eq 'AIServices' } | ForEach-Object { Get-ModelInfo $_ } |
            Where-Object { $_.name -eq $ModelName -and @($_.skus | Where-Object { $_.name -eq 'GlobalStandard' }).Count -gt 0 })
    }
    if ($entries.Count -eq 0) { throw "IQ_REGION_RETRY: model '$ModelName' is not available as GlobalStandard in '$Region'." }
    $default = $entries | Where-Object { $_.isDefaultVersion } | Select-Object -First 1
    if ($default) { return [string]$default.version }
    return [string](($entries | Sort-Object { [string]$_.version } -Descending | Select-Object -First 1).version)
}

function Initialize-FoundryStack {
    param([Parameter(Mandatory=$true)][string]$Region)

    if (-not (Get-ArmJson -Path "${accountId}?api-version=$cogApi")) {
        Write-Host "[INFO]  Creating Foundry account '$foundryAccountName' in '$Region'..."
        New-FoundryAccount -Region $Region
        Write-Host "[OK]    Foundry account '$foundryAccountName' created."
    } else {
        Wait-ArmProvisioned -Path "${accountId}?api-version=$cogApi" -Label "Foundry account '$foundryAccountName'" | Out-Null
        Write-Host "[OK]    Foundry account '$foundryAccountName' already exists."
    }

    # allowProjectManagement must be true before a project can be created, and the
    # create body does not always honour it. Keep disableLocalAuth=true as well.
    $acct = Get-ArmJson -Path "${accountId}?api-version=$cogApi"
    if (-not $acct.properties.allowProjectManagement -or -not $acct.properties.disableLocalAuth -or
        $acct.properties.publicNetworkAccess -ne 'Enabled') {
        $patch = @{ properties = @{ allowProjectManagement = $true; disableLocalAuth = $true; publicNetworkAccess = "Enabled" } } | ConvertTo-Json -Depth 3
        Invoke-MhhArm -Method PATCH -Path "${accountId}?api-version=$cogApi" -Payload $patch | Out-Null
        Wait-ArmProvisioned -Path "${accountId}?api-version=$cogApi" -Label "Foundry account update" -TimeoutSeconds 300 `
            -ExtraCheck { param($o) $o.properties.allowProjectManagement -and $o.properties.disableLocalAuth } | Out-Null
        Write-Host "[OK]    Foundry account settings enforced (project management on, local auth off)."
    }

    # Project (must carry a system identity or the API rejects it).
    if (-not (Get-ArmJson -Path "${projectId}?api-version=$cogApi")) {
        $projectBody = @{
            location   = $Region
            tags       = $labTags
            identity   = @{ type = "SystemAssigned" }
            properties = @{ description = "Microsoft IQ MicroHack (Caldova Components)"; displayName = "Caldova IQ" }
        } | ConvertTo-Json -Depth 4
        Invoke-MhhArm -Method PUT -Path "${projectId}?api-version=$cogApi" -Payload $projectBody | Out-Null
    }
    $project = Wait-ArmProvisioned -Path "${projectId}?api-version=$cogApi" -Label "Foundry project '$foundryProjectName'" -TimeoutSeconds 300 `
        -ExtraCheck { param($o) [bool]$o.identity.principalId }
    Write-Host "[OK]    Foundry project '$foundryProjectName' ready."

    # Model deployments, one at a time (the account serialises deployment operations).
    foreach ($m in $modelPlan) {
        $depPath = "${accountId}/deployments/$($m.Name)?api-version=$cogApi"
        $existing = Get-ArmJson -Path $depPath
        if ($existing -and $existing.properties.provisioningState -eq 'Succeeded') {
            Write-Host "[OK]    Model deployment '$($m.Name)' already exists (capacity $($existing.sku.capacity))."
            continue
        }
        $version = Resolve-ModelVersion -ModelName $m.Name -Region $Region
        $depBody = @{
            sku        = @{ name = "GlobalStandard"; capacity = $m.Capacity }
            properties = @{
                model                = @{ format = "OpenAI"; name = $m.Name; version = $version }
                versionUpgradeOption = "OnceNewDefaultVersionAvailable"
            }
        } | ConvertTo-Json -Depth 6
        Write-Host "[INFO]  Deploying model '$($m.Name)' version $version (GlobalStandard, $($m.Capacity)K TPM)..."
        $resp = $null
        for ($attempt = 1; $attempt -le 5; $attempt++) {
            $resp = Invoke-AzRestMethod -Method PUT -Uri "https://management.azure.com$depPath" -Payload $depBody
            # 409 means another operation on the account is still running.
            if ($resp.StatusCode -eq 409 -or $resp.StatusCode -in @(429, 500, 502, 503, 504)) { Start-Sleep -Seconds 20; continue }
            break
        }
        if ($resp.StatusCode -ge 400) {
            if ($resp.Content -match $regionRetryPattern) {
                throw "IQ_REGION_RETRY: model '$($m.Name)' could not be deployed in '$Region' (HTTP $($resp.StatusCode)): $($resp.Content)"
            }
            throw "Model deployment '$($m.Name)' failed (HTTP $($resp.StatusCode)): $($resp.Content)"
        }
        try {
            Wait-ArmProvisioned -Path $depPath -Label "Model deployment '$($m.Name)'" -TimeoutSeconds 600 | Out-Null
        } catch {
            if ("$_" -match $regionRetryPattern) { throw "IQ_REGION_RETRY: $_" }
            throw
        }
        Write-Host "[OK]    Model deployment '$($m.Name)' ready."
    }
    return $project
}

$labRegion = $null
$projectResource = $null
foreach ($region in $regionsToTry) {
    Update-LabToken
    $searchCreatedHere  = $false
    $accountCreatedHere = $false
    try {
        if (-not (Get-ArmJson -Path "${searchId}?api-version=$searchApi")) {
            Write-Host "[INFO]  Submitting Azure AI Search '$searchName' (Basic) in '$region'..."
            try { Submit-SearchService -Region $region }
            catch {
                if ("$_" -match $regionRetryPattern) { throw "IQ_REGION_RETRY: Search create rejected in '$region'. $_" }
                throw
            }
            $searchCreatedHere = $true
        }
        $accountCreatedHere = -not (Get-ArmJson -Path "${accountId}?api-version=$cogApi")
        $projectResource = Initialize-FoundryStack -Region $region
        $labRegion = $region
        break
    } catch {
        $msg = "$_"
        if ($msg -notmatch 'IQ_REGION_RETRY' -or $lockedRegion) { throw }
        Write-Warning "Region '$region' cannot host the lab: $msg"
        if ($accountCreatedHere) {
            Write-Host "[INFO]  Removing the Foundry account created in '$region' before trying the next region..."
            Remove-FoundryAccountAndPurge -Region $region
        }
        if ($searchCreatedHere) {
            Write-Host "[INFO]  Removing the Search service created in '$region' before trying the next region..."
            Invoke-MhhArm -Method DELETE -Path "${searchId}?api-version=$searchApi" -AllowNotFound | Out-Null
            $deadline = (Get-Date).AddMinutes(10)
            while ((Get-Date) -lt $deadline -and (Get-ArmJson -Path "${searchId}?api-version=$searchApi")) { Start-Sleep -Seconds 15 }
        }
    }
}
if (-not $labRegion) {
    throw "Could not deploy the Foundry models and Search service in any preferred region: $($regionsToTry -join ', ')"
}
Write-Host "[OK]    Lab region: '$labRegion'."

# ---------------------------------------------------------------------------
# Phase 4: Log Analytics + Application Insights, connected to the Foundry project
# so the Traces tab works with no manual setup.
# ---------------------------------------------------------------------------
Update-LabToken
if (-not (Get-ArmJson -Path "${laId}?api-version=$laApi")) {
    $laBody = @{ location = $labRegion; tags = $labTags; properties = @{ sku = @{ name = "PerGB2018" }; retentionInDays = 30 } } | ConvertTo-Json -Depth 5
    Invoke-MhhArm -Method PUT -Path "${laId}?api-version=$laApi" -Payload $laBody | Out-Null
}
Wait-ArmProvisioned -Path "${laId}?api-version=$laApi" -Label "Log Analytics workspace '$laName'" -TimeoutSeconds 300 | Out-Null
Write-Host "[OK]    Log Analytics workspace '$laName' ready."

if (-not (Get-ArmJson -Path "${appiId}?api-version=$appiApi")) {
    $aiBody = @{ location = $labRegion; kind = "web"; tags = $labTags; properties = @{ Application_Type = "web"; WorkspaceResourceId = $laId } } | ConvertTo-Json -Depth 5
    Invoke-MhhArm -Method PUT -Path "${appiId}?api-version=$appiApi" -Payload $aiBody | Out-Null
}
$appiConnString = $null
for ($i = 0; $i -lt 12 -and -not $appiConnString; $i++) {
    $appiConnString = (Get-ArmJson -Path "${appiId}?api-version=$appiApi").properties.ConnectionString
    if (-not $appiConnString) { Start-Sleep -Seconds 5 }
}
if (-not $appiConnString) { throw "Application Insights '$appiName' has no connection string yet." }
Write-Host "[OK]    Application Insights '$appiName' ready."

$appiConnPath = "${projectId}/connections/appinsights?api-version=$cogApi"
$appiConnBody = @{ properties = @{
    category      = "AppInsights"
    target        = $appiId
    authType      = "ApiKey"
    isSharedToAll = $true
    credentials   = @{ key = $appiConnString }
    metadata      = @{ ApiType = "Azure"; ResourceId = $appiId }
} } | ConvertTo-Json -Depth 6
Invoke-MhhArm -Method PUT -Path $appiConnPath -Payload $appiConnBody | Out-Null
Write-Host "[OK]    Application Insights connected to the Foundry project (agent tracing)."

# ---------------------------------------------------------------------------
# Phase 5: Storage account for the knowledge corpus
# Foundry IQ's entity graph needs blob soft delete ON and versioning OFF.
# Shared key access is disabled; Search and attendees use Entra RBAC.
# ---------------------------------------------------------------------------
Update-LabToken
$storageBody = @{
    location   = $labRegion
    kind       = "StorageV2"
    sku        = @{ name = "Standard_LRS" }
    tags       = $labTags
    properties = @{
        accessTier               = "Hot"
        publicNetworkAccess      = "Enabled"
        allowBlobPublicAccess    = $false
        allowSharedKeyAccess     = $false
        minimumTlsVersion        = "TLS1_2"
        supportsHttpsTrafficOnly = $true
        networkAcls              = @{ defaultAction = "Allow"; bypass = "AzureServices" }
    }
} | ConvertTo-Json -Depth 6

if (-not (Get-ArmJson -Path "${storageId}?api-version=$storageApi")) {
    $nameCheck = (Invoke-MhhArm -Method POST -Path "/subscriptions/$SubscriptionId/providers/Microsoft.Storage/checkNameAvailability?api-version=$storageApi" `
        -Payload (@{ name = $storageName; type = "Microsoft.Storage/storageAccounts" } | ConvertTo-Json)).Content | ConvertFrom-Json
    if (-not $nameCheck.nameAvailable) {
        throw "Storage account name '$storageName' is not available: $($nameCheck.message)"
    }
    Write-Host "[INFO]  Creating storage account '$storageName'..."
    Invoke-MhhArm -Method PUT -Path "${storageId}?api-version=$storageApi" -Payload $storageBody | Out-Null
}
Wait-ArmProvisioned -Path "${storageId}?api-version=$storageApi" -Label "Storage account '$storageName'" -TimeoutSeconds 300 | Out-Null

# The MCAPS policy can flip publicNetworkAccess asynchronously after create. Verify
# the effective setting for new and existing accounts, and repair it if needed.
$storageReachable = $false
for ($try = 1; $try -le 10 -and -not $storageReachable; $try++) {
    $st = Get-ArmJson -Path "${storageId}?api-version=$storageApi"
    $p = $st.properties
    if ($p.provisioningState -eq 'Succeeded' -and $p.publicNetworkAccess -eq 'Enabled' -and
        $p.networkAcls.defaultAction -eq 'Allow') {
        $storageReachable = $true
        break
    }
    if ($p.provisioningState -eq 'Succeeded') {
        $fix = @{ properties = @{ publicNetworkAccess = "Enabled"; networkAcls = @{ defaultAction = "Allow"; bypass = "AzureServices" } } } | ConvertTo-Json -Depth 4
        $rec = Invoke-AzRestMethod -Method PATCH -Uri "https://management.azure.com${storageId}?api-version=$storageApi" -Payload $fix
        if ($rec.StatusCode -ge 200 -and $rec.StatusCode -lt 300) {
            Write-Host "[INFO]  Re-enabled storage public network access; verifying..."
        } elseif ($rec.StatusCode -notin @(409, 412, 429, 500, 502, 503, 504)) {
            throw "Could not re-enable storage public access (HTTP $($rec.StatusCode)): $($rec.Content)"
        }
    }
    Start-Sleep -Seconds 15
}
if (-not $storageReachable) { throw "Storage account '$storageName' public endpoint could not be enabled (policy?)." }
Write-Host "[OK]    Storage account '$storageName' ready (public endpoint verified, shared key off)."

$blobSvcPath = "${storageId}/blobServices/default?api-version=$storageApi"
$blobSvcBody = @{ properties = @{
    deleteRetentionPolicy = @{ enabled = $true; days = 7 }
    isVersioningEnabled   = $false
} } | ConvertTo-Json -Depth 4
Invoke-MhhArm -Method PUT -Path $blobSvcPath -Payload $blobSvcBody | Out-Null
$blobSvc = Get-ArmJson -Path $blobSvcPath
if (-not $blobSvc.properties.deleteRetentionPolicy.enabled -or $blobSvc.properties.isVersioningEnabled) {
    throw "Blob service settings did not apply (soft delete must be on, versioning off)."
}
Write-Host "[OK]    Blob soft delete (7 days) on, versioning off."

$containerPath = "${storageId}/blobServices/default/containers/${storageContainer}?api-version=$storageApi"
if (-not (Get-ArmJson -Path $containerPath)) {
    Invoke-MhhArm -Method PUT -Path $containerPath -Payload (@{ properties = @{ publicAccess = "None" } } | ConvertTo-Json) | Out-Null
}
if (-not (Get-ArmJson -Path $containerPath)) { throw "Container '$storageContainer' was not created." }
Write-Host "[OK]    Container '$storageContainer' ready."

# ---------------------------------------------------------------------------
# Phase 6: wait for Search, then verify its settings (Entra auth, semantic ranker,
# public endpoint) and repair them if a policy changed something.
# ---------------------------------------------------------------------------
Update-LabToken
Write-Host "[INFO]  Waiting for Azure AI Search '$searchName' to be running (this can take several minutes)..."
$search = Wait-ArmProvisioned -Path "${searchId}?api-version=$searchApi" -Label "Search service '$searchName'" `
    -TimeoutSeconds 1500 -IntervalSeconds 20 `
    -ExtraCheck { param($o) $o.properties.status -eq 'running' -and [bool]$o.identity.principalId }
$sp = $search.properties
if ($sp.publicNetworkAccess -ne 'enabled' -or -not $sp.authOptions.aadOrApiKey -or $sp.semanticSearch -ne 'free') {
    Write-Host "[INFO]  Re-applying Search settings (public access, Entra auth, semantic ranker)..."
    Submit-SearchService -Region $labRegion
    $search = Wait-ArmProvisioned -Path "${searchId}?api-version=$searchApi" -Label "Search service update" `
        -TimeoutSeconds 900 -IntervalSeconds 20 `
        -ExtraCheck { param($o) $o.properties.status -eq 'running' -and $o.properties.publicNetworkAccess -eq 'enabled' }
}
$searchPrincipalId = [string]$search.identity.principalId
Write-Host "[OK]    Azure AI Search '$searchName' running (Basic, Entra + key auth, semantic ranker free)."

# ---------------------------------------------------------------------------
# Phase 7: RBAC
# The platform grants the attendee Owner on the resource group (control plane only).
# Data-plane roles are granted here.
# ---------------------------------------------------------------------------
Update-LabToken
foreach ($userId in $AllowedEntraUserIds) {
    $who = "attendee '$userId'"
    Grant-LabRole -Scope $accountId -PrincipalId $userId -PrincipalType User -RoleName AzureAIUser -Label $who
    Grant-LabRole -Scope $accountId -PrincipalId $userId -PrincipalType User -RoleName CognitiveServicesUser -Label $who
    Grant-LabRole -Scope $accountId -PrincipalId $userId -PrincipalType User -RoleName CognitiveServicesOpenAIUser -Label $who
    Grant-LabRole -Scope $searchId  -PrincipalId $userId -PrincipalType User -RoleName SearchServiceContributor -Label $who
    Grant-LabRole -Scope $searchId  -PrincipalId $userId -PrincipalType User -RoleName SearchIndexDataContributor -Label $who
    Grant-LabRole -Scope $storageId -PrincipalId $userId -PrincipalType User -RoleName StorageBlobDataContributor -Label $who
}

$searchWho = "Search identity '$searchPrincipalId'"
Grant-LabRole -Scope $accountId -PrincipalId $searchPrincipalId -PrincipalType ServicePrincipal -RoleName CognitiveServicesOpenAIUser -Label $searchWho
Grant-LabRole -Scope $storageId -PrincipalId $searchPrincipalId -PrincipalType ServicePrincipal -RoleName StorageBlobDataReader -Label $searchWho

$projectPrincipalId = [string]$projectResource.identity.principalId
$projectWho = "Foundry project identity '$projectPrincipalId'"
Grant-LabRole -Scope $searchId  -PrincipalId $projectPrincipalId -PrincipalType ServicePrincipal -RoleName SearchIndexDataReader -Label $projectWho
Grant-LabRole -Scope $accountId -PrincipalId $projectPrincipalId -PrincipalType ServicePrincipal -RoleName AzureAIUser -Label $projectWho

# ---------------------------------------------------------------------------
# Phase 8: Fabric capacity (per attendee, attendee is capacity admin)
# Capacity admin members must be UPNs, so resolve the object IDs with the platform
# helper Get-MhhLabUser (served from a platform-seeded cache, no Graph permission
# needed). A Fabric failure does not fail the lab: the Foundry, Search and Work IQ
# parts still work and a coach can create the capacity by hand.
# ---------------------------------------------------------------------------
Update-LabToken
$fabricReady = $false
$fabricRegion = $null
$adminUpns = @()
foreach ($uid in $AllowedEntraUserIds) {
    try {
        $u = Get-MhhLabUser -UserId $uid -ErrorAction Stop
        if ($u.UserPrincipalName) { $adminUpns += [string]$u.UserPrincipalName }
    } catch {
        Write-Host "[WARN]  Could not resolve attendee '$uid' to a UPN via Get-MhhLabUser: $_"
    }
}

if ($adminUpns.Count -eq 0) {
    Write-Host "[WARN]  No attendee UPNs resolved; skipping the Fabric capacity. Create it by hand and add the attendee as capacity admin."
} else {
    $cap = Get-ArmJson -Path "${fabricId}?api-version=$fabricApi"
    if ($cap) {
        $fabricRegion = ([string]$cap.location).ToLower().Replace(' ', '')
        Write-Host "[OK]    Fabric capacity '$fabricCapacityName' already exists in '$fabricRegion'."
        $members = @($cap.properties.administration.members)
        $missing = @($adminUpns | Where-Object { $members -notcontains $_ })
        if ($missing.Count -gt 0 -or $cap.sku.name -ne $FabricSkuName) {
            $patch = @{ sku = @{ name = $FabricSkuName; tier = "Fabric" }; properties = @{ administration = @{ members = @(@($members) + $missing | Select-Object -Unique) } } } | ConvertTo-Json -Depth 6
            Invoke-MhhArm -Method PATCH -Path "${fabricId}?api-version=$fabricApi" -Payload $patch | Out-Null
            Write-Host "[OK]    Fabric capacity admins/SKU updated."
        }
    } else {
        $fabricRegions = @($labRegion) + @($candidateRegions | Where-Object { $_ -ne $labRegion })
        foreach ($region in $fabricRegions) {
            Write-Host "[INFO]  Creating Fabric $FabricSkuName capacity '$fabricCapacityName' in '$region'..."
            $capBody = @{
                location   = $region
                tags       = $labTags
                sku        = @{ name = $FabricSkuName; tier = "Fabric" }
                properties = @{ administration = @{ members = @($adminUpns) } }
            } | ConvertTo-Json -Depth 6
            $capResp = Invoke-AzRestMethod -Method PUT -Uri "https://management.azure.com${fabricId}?api-version=$fabricApi" -Payload $capBody
            if ($capResp.StatusCode -ge 400) {
                Write-Warning "Fabric capacity create in '$region' failed (HTTP $($capResp.StatusCode)): $($capResp.Content). Trying the next region."
                continue
            }
            try {
                Wait-ArmProvisioned -Path "${fabricId}?api-version=$fabricApi" -Label "Fabric capacity '$fabricCapacityName'" -TimeoutSeconds 600 | Out-Null
                $fabricRegion = $region
                Write-Host "[OK]    Fabric $FabricSkuName capacity '$fabricCapacityName' created in '$region'."
                break
            } catch {
                Write-Warning "Fabric capacity did not provision in '$region': $_. Trying the next region."
                Invoke-AzRestMethod -Method DELETE -Uri "https://management.azure.com${fabricId}?api-version=$fabricApi" | Out-Null
                Start-Sleep -Seconds 30
            }
        }
    }

    if ($fabricRegion) {
        # A coach may have paused the capacity to save money; the lab needs it Active.
        $deadline = (Get-Date).AddMinutes(10)
        do {
            $cap = Get-ArmJson -Path "${fabricId}?api-version=$fabricApi"
            $capState = [string]$cap.properties.state
            if ($capState -eq 'Active') { $fabricReady = $true; break }
            if ($capState -in @('Paused', 'Suspended')) {
                Write-Host "[INFO]  Fabric capacity is '$capState'; resuming..."
                Invoke-MhhArm -Method POST -Path "${fabricId}/resume?api-version=$fabricApi" -AllowStatus @(409) | Out-Null
            }
            Start-Sleep -Seconds 15
        } while ((Get-Date) -lt $deadline)
        if ($fabricReady) {
            Write-Host "[OK]    Fabric capacity '$fabricCapacityName' is Active."
        } else {
            Write-Host "[WARN]  Fabric capacity '$fabricCapacityName' is '$capState', not Active. Resume it in the Azure portal."
        }
    } else {
        Write-Host "[WARN]  Could not create the Fabric capacity in any preferred region (check the Fabric CU quota). The rest of the lab works; create the capacity by hand."
    }
}

# ---------------------------------------------------------------------------
# Phase 9: Work IQ emulator (Azure Functions Flex Consumption MCP server)
# Keys are derived with New-MhhStablePassword ([A-Za-z0-9] only, safe in HTTP
# headers) so a re-run keeps the values already shown on the dashboard.
# ---------------------------------------------------------------------------
Update-LabToken
$emulatorScript = Join-Path $PSScriptRoot 'workiq-emulator\Deploy-WorkIQEmulator.ps1'
if (-not (Test-Path $emulatorScript)) {
    throw "Work IQ emulator deployment script not found: $emulatorScript"
}
. $emulatorScript
# The emulator script enables strict mode at file level; keep this script's own mode.
Set-StrictMode -Off

$personaKeys = [ordered]@{
    'sales-lead'     = New-MhhStablePassword -Purpose 'workiq-sales-lead' -Length 48
    'supply-planner' = New-MhhStablePassword -Purpose 'workiq-supply-planner' -Length 48
    'quality-head'   = New-MhhStablePassword -Purpose 'workiq-quality-head' -Length 48
    'plant-manager'  = New-MhhStablePassword -Purpose 'workiq-plant-manager' -Length 48
}
$adminKey = New-MhhStablePassword -Purpose 'workiq-admin' -Length 48
$foundryOpenAIEndpoint = "https://$foundryAccountName.openai.azure.com/"

# Build the call from what Deploy-WorkIQEmulator actually exposes, so optional
# parameters (for example the Foundry account id for its role assignment) are
# passed only when the function declares them.
$emuCmd = Get-Command Deploy-WorkIQEmulator -ErrorAction Stop
$emuParams = @{
    SubscriptionId              = $SubscriptionId
    ResourceGroupName           = $effectiveRG
    Location                    = $labRegion
    Name                        = $emulatorName
    AppInsightsConnectionString = $appiConnString
    FoundryOpenAIEndpoint       = $foundryOpenAIEndpoint
    FoundryChatDeployment       = $chatModel
    Keys                        = [hashtable]$personaKeys
    AdminKey                    = $adminKey
    Tags                        = $labTags
}
foreach ($optName in @('FoundryAccountResourceId', 'FoundryAccountId', 'FoundryResourceId')) {
    if ($emuCmd.Parameters.ContainsKey($optName)) { $emuParams[$optName] = $accountId; break }
}
foreach ($key in @($emuParams.PSBase.Keys)) {
    if (-not $emuCmd.Parameters.ContainsKey($key)) {
        Write-Host "[WARN]  Deploy-WorkIQEmulator has no -$key parameter; not passing it."
        $emuParams.Remove($key)
    }
}
Write-Host "[INFO]  Deploying the Work IQ emulator '$emulatorName'..."
# Keep only the result object; the function may also write other output.
$emulator = @(Deploy-WorkIQEmulator @emuParams) | Where-Object {
    ($_ -is [hashtable] -and $_.ContainsKey('McpEndpoint')) -or
    ($_ -isnot [hashtable] -and $_ -and $_.PSObject.Properties.Name -contains 'McpEndpoint')
} | Select-Object -Last 1
if (-not $emulator -or -not $emulator.McpEndpoint) {
    throw "Deploy-WorkIQEmulator did not return an McpEndpoint."
}
Write-Host "[OK]    Work IQ emulator ready at $($emulator.McpEndpoint)."

# ---------------------------------------------------------------------------
# Credentials for the attendee dashboard (emitted only after everything is ready)
# ---------------------------------------------------------------------------
$tenantId        = (Get-AzContext).Tenant.Id
$projectEndpoint = "https://$foundryAccountName.services.ai.azure.com/api/projects/$foundryProjectName"
$searchEndpoint  = "https://$searchName.search.windows.net"

# Foundry portal deep link: the subscription GUID as base64url (string byte order),
# then <rg>,,<account>,<project>.
$subHex   = $SubscriptionId -replace '-', ''
$subBytes = for ($i = 0; $i -lt $subHex.Length; $i += 2) { [Convert]::ToByte($subHex.Substring($i, 2), 16) }
$subToken = [Convert]::ToBase64String([byte[]]$subBytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
$projectPortalUrl = "https://ai.azure.com/nextgen/r/$subToken,$effectiveRG,,$foundryAccountName,$foundryProjectName/home?tid=$tenantId"

Write-Host "[OK]    Lab provisioning complete."

@{ HackboxCredential = @{ name = "FoundryProjectUrl"; value = $projectPortalUrl
    note = "Open your Foundry project in the portal (sign in with your lab user)." } }
@{ HackboxCredential = @{ name = "FoundryProjectEndpoint"; value = $projectEndpoint
    note = "Foundry project endpoint (FOUNDRY_PROJECT_ENDPOINT)." } }
@{ HackboxCredential = @{ name = "ModelDeploymentName"; value = $chatModel
    note = "Chat model for your agents (MODEL_DEPLOYMENT_NAME)." } }
@{ HackboxCredential = @{ name = "GraphModelDeploymentName"; value = $graphModel
    note = "Model for Foundry IQ knowledge graph extraction and knowledge base query planning." } }
@{ HackboxCredential = @{ name = "EmbeddingDeploymentName"; value = $embeddingModel
    note = "Embedding model for the Foundry IQ knowledge source." } }
@{ HackboxCredential = @{ name = "SearchEndpoint"; value = $searchEndpoint
    note = "Foundry IQ (Azure AI Search) endpoint. Use your Entra identity, no keys." } }
@{ HackboxCredential = @{ name = "StorageAccountName"; value = $storageName
    note = "Storage account for the Caldova documents (Entra auth only)." } }
@{ HackboxCredential = @{ name = "StorageContainer"; value = $storageContainer
    note = "Upload the Caldova documents here." } }
if ($fabricReady) {
    @{ HackboxCredential = @{ name = "FabricCapacityName"; value = $fabricCapacityName
        note = "Your own Fabric $FabricSkuName capacity. Assign your Fabric workspace to it." } }
    @{ HackboxCredential = @{ name = "FabricPortalUrl"; value = "https://app.fabric.microsoft.com/home?tid=$tenantId"
        note = "Fabric portal (sign in with your lab user)." } }
}
@{ HackboxCredential = @{ name = "WorkIQEmulatorEndpoint"; value = [string]$emulator.McpEndpoint
    note = "Work IQ (emulated) MCP endpoint. Authenticate with 'Authorization: Bearer <persona key>'." } }
if ($emulator.ViewerUrl) {
    @{ HackboxCredential = @{ name = "WorkIQViewerUrl"; value = [string]$emulator.ViewerUrl
        note = "Browse the emulated Microsoft 365 content per persona." } }
}
@{ HackboxCredential = @{ name = "WorkIQKeySalesLead"; value = $personaKeys['sales-lead']
    note = "Work IQ persona key: Sales Lead." } }
@{ HackboxCredential = @{ name = "WorkIQKeySupplyPlanner"; value = $personaKeys['supply-planner']
    note = "Work IQ persona key: Supply Planner." } }
@{ HackboxCredential = @{ name = "WorkIQKeyQualityHead"; value = $personaKeys['quality-head']
    note = "Work IQ persona key: Quality Head." } }
@{ HackboxCredential = @{ name = "WorkIQKeyPlantManager"; value = $personaKeys['plant-manager']
    note = "Work IQ persona key: Plant Manager." } }
@{ HackboxCredential = @{ name = "ApplicationInsightsConnectionString"; value = $appiConnString
    note = "Optional: send your own app telemetry to the lab Application Insights." } }
@{ HackboxCredential = @{ name = "LabRegion"; value = $labRegion
    note = "Azure region of your lab resources." } }
