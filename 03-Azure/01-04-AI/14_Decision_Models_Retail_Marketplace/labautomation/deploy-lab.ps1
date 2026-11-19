<#
.SYNOPSIS
    Deploys the per-attendee lab for "Decision Models for a Retail Marketplace".

.DESCRIPTION
    Called by the EMEA MicroHack platform once per attendee, in parallel.

    Provisions, in one Foundry (AIServices) resource:
      - Microsoft-Decision-1.1  deployment "decision"        (the gate's decision model)
      - gpt-6-luna              deployment "gpt-6-luna"      (Decisions API + generative baseline)
      - Microsoft-Decision-1    deployment "decision-judge"  (Challenge 6: judge in Foundry evaluations;
                                                              Decision-1.1 is not supported as a judge)
      - a Foundry project, so attendees can open the models in the Foundry portal
      - RBAC for each attendee: Cognitive Services User (inference) + Foundry User (evaluations)

    The resource is keyless (disableLocalAuth = true): attendees sign in with Entra ID.

    The script fails loudly instead of publishing a half-working lab. It only returns dashboard
    credentials after every deployment reports Succeeded AND a live call to each API (including
    an image, as the challenges send photos) has returned a valid typed answer.

    The platform pre-sets the Az context to $SubscriptionId and pre-creates the resource group.
    Do NOT call Connect-AzAccount or New-AzResourceGroup.

.PARAMETER DeploymentType
    Deployment scope — passed in by the platform.
.PARAMETER SubscriptionId
    Azure subscription — passed in by the platform.
.PARAMETER ResourceGroupName
    Pre-created resource group — passed in by the platform.
.PARAMETER PreferredLocation
    Ordered list of preferred Azure regions — passed in by the platform.
.PARAMETER AllowedEntraUserIds
    Entra user object IDs for this lab — passed in by the platform.
#>
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('subscription','resourcegroup','resourcegroup-with-subscriptionowner')]
    [string]$DeploymentType,

    [Parameter(Mandatory=$true)]
    [string]$SubscriptionId,

    [string]$ResourceGroupName = "",

    [string[]]$PreferredLocation = @(),

    [string[]]$AllowedEntraUserIds = @()
)

$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Sizing. One capacity unit = 1 request/min + 1,000 tokens/min for every model here.
# Data Zone quota is shared by every lab in the subscription, so keep
# labsPerSubscription (lab-defaults.json) x capacity <= the subscription quota:
#   gpt-6-luna           DataZoneStandard quota 333  -> 8 labs x 40  = 320
#   Microsoft-Decision-1.1 DataZoneStandard quota 4500 -> 8 labs x 500 = 4000
#   Microsoft-Decision-1   DataZoneStandard quota 4500 -> 8 labs x 50  = 400
# Azure's rate limiter counts request SIZE (a base64 photo counts in full), so the gate's
# image requests cost ~4-5K tokens of rate limit each; 500 units ~= 100 listings/min.
# ---------------------------------------------------------------------------
$models = @(
    @{ deployment = "decision";       name = "Microsoft-Decision-1.1"; format = "Microsoft"; version = "1";          capacity = 500; quota = "AIServices.DataZoneStandard.Microsoft-Decision-1.1" },
    @{ deployment = "gpt-6-luna";     name = "gpt-6-luna";             format = "OpenAI";    version = "2026-09-22"; capacity = 40;  quota = "OpenAI.DataZoneStandard.gpt-6-luna" },
    @{ deployment = "decision-judge"; name = "Microsoft-Decision-1";   format = "Microsoft"; version = "1";          capacity = 50;  quota = "AIServices.DataZoneStandard.Microsoft-Decision-1" }
)
$skuName     = "DataZoneStandard"
$projectName = "marketplace-gate"
$apiVersion  = "2025-04-01-preview"

# ---------------------------------------------------------------------------
# ARM REST helper: full management.azure.com URI form, and THROWS on any non-2xx so a
# failed control-plane call never prints a false "[OK]". -AllowNotFound for existence probes.
# ---------------------------------------------------------------------------
function Invoke-MhhArm {
    param(
        [Parameter(Mandatory=$true)][ValidateSet('GET','PUT','PATCH','POST','DELETE')][string]$Method,
        [Parameter(Mandatory=$true)][string]$Path,
        [string]$Payload,
        [switch]$AllowNotFound
    )
    $uri = if ($Path -like 'https://*') { $Path } else { "https://management.azure.com$Path" }
    $params = @{ Method = $Method; Uri = $uri }
    if ($Payload) { $params.Payload = $Payload }
    $resp = Invoke-AzRestMethod @params
    if (($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 300) -or
        ($AllowNotFound -and $resp.StatusCode -eq 404)) {
        return $resp
    }
    throw "ARM $Method $uri failed with HTTP $($resp.StatusCode): $($resp.Content)"
}

function Get-PlainToken([string]$ResourceUrl) {
    $t = (Get-AzAccessToken -ResourceUrl $ResourceUrl).Token
    if ($t -is [System.Security.SecureString]) { $t = ConvertFrom-SecureString -SecureString $t -AsPlainText }
    return $t
}

function Get-TokenObjectId([string]$Token) {
    $payload = $Token.Split('.')[1].Replace('-', '+').Replace('_', '/')
    switch ($payload.Length % 4) { 2 { $payload += '==' } 3 { $payload += '=' } }
    return ([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($payload)) | ConvertFrom-Json).oid
}

$candidateRegions = if ($PreferredLocation.Count -gt 0) { $PreferredLocation } else { @("swedencentral", "westeurope", "germanywestcentral") }
$effectiveRG      = $ResourceGroupName
$stableHash       = (Get-MhhStableHash $AllowedEntraUserIds -Length 12).ToLower()
$accountName      = "dm-$stableHash"
$accountBase      = "/subscriptions/$SubscriptionId/resourceGroups/$effectiveRG/providers/Microsoft.CognitiveServices/accounts/$accountName"

# ---------------------------------------------------------------------------
# 1. Pick a region that offers all three models on DataZoneStandard AND has quota left.
#    An existing account keeps its region.
# ---------------------------------------------------------------------------
$existing = Invoke-MhhArm -Method GET -Path "${accountBase}?api-version=$apiVersion" -AllowNotFound
if ($existing.StatusCode -eq 200) {
    $effectiveLocation = ($existing.Content | ConvertFrom-Json).location
    Write-Host "[OK]    Foundry resource '$accountName' already exists in '$effectiveLocation'."
} else {
    $effectiveLocation = $null
    foreach ($region in $candidateRegions) {
        $catalog = (Invoke-MhhArm -Method GET -Path "/subscriptions/$SubscriptionId/providers/Microsoft.CognitiveServices/locations/$region/models?api-version=$apiVersion").Content | ConvertFrom-Json
        $usages  = (Invoke-MhhArm -Method GET -Path "/subscriptions/$SubscriptionId/providers/Microsoft.CognitiveServices/locations/$region/usages?api-version=$apiVersion").Content | ConvertFrom-Json
        $problems = @()
        foreach ($m in $models) {
            $offered = $catalog.value | Where-Object {
                $_.kind -eq "AIServices" -and $_.model.name -eq $m.name -and $_.model.version -eq $m.version -and
                ($_.model.skus.name -contains $skuName)
            }
            if (-not $offered) { $problems += "$($m.name) $skuName not offered"; continue }
            $u = $usages.value | Where-Object { $_.name.value -eq $m.quota }
            if ($u -and (($u.limit - $u.currentValue) -lt $m.capacity)) {
                $problems += "$($m.name): only $($u.limit - $u.currentValue) of $($m.capacity) quota left"
            }
        }
        if ($problems.Count -eq 0) { $effectiveLocation = $region; break }
        Write-Warning "Region '$region' skipped: $($problems -join '; ')"
    }
    if (-not $effectiveLocation) {
        throw "No preferred region ($($candidateRegions -join ', ')) offers all models with enough DataZoneStandard quota. Lower labsPerSubscription or request quota."
    }
    Write-Host "[INFO]  Using region '$effectiveLocation'."
}

# ---------------------------------------------------------------------------
# 2. Foundry (AIServices) resource: keyless, public endpoint, project management enabled.
#    Resource-group tag SecurityControl=Ignore is the standard exemption on Microsoft-internal
#    (MCAPS) subscriptions whose policies would otherwise disable public network access.
#    Security is unchanged: local auth is disabled, so callers need an Entra token + a data role.
# ---------------------------------------------------------------------------
$rgTagBody = @{ operation = "Merge"; properties = @{ tags = @{ SecurityControl = "Ignore" } } } | ConvertTo-Json -Depth 4
Invoke-MhhArm -Method PATCH -Path "/subscriptions/$SubscriptionId/resourceGroups/$effectiveRG/providers/Microsoft.Resources/tags/default?api-version=2021-04-01" -Payload $rgTagBody | Out-Null

$accountBody = @{
    kind     = "AIServices"
    sku      = @{ name = "S0" }
    location = $effectiveLocation
    identity = @{ type = "SystemAssigned" }
    tags     = @{ SecurityControl = "Ignore" }
    properties = @{
        customSubDomainName    = $accountName
        publicNetworkAccess    = "Enabled"
        disableLocalAuth       = $true
        allowProjectManagement = $true
    }
} | ConvertTo-Json -Depth 5
Invoke-MhhArm -Method PUT -Path "${accountBase}?api-version=$apiVersion" -Payload $accountBody | Out-Null

$elapsed = 0
do {
    Start-Sleep -Seconds 10; $elapsed += 10
    $acct = ((Invoke-MhhArm -Method GET -Path "${accountBase}?api-version=$apiVersion").Content | ConvertFrom-Json).properties
} while ($acct.provisioningState -notin @("Succeeded", "Failed") -and $elapsed -lt 300)
if ($acct.provisioningState -ne "Succeeded") { throw "Foundry resource '$accountName' is '$($acct.provisioningState)' after ${elapsed}s." }
if ($acct.publicNetworkAccess -ne "Enabled") { throw "Foundry resource '$accountName' has publicNetworkAccess '$($acct.publicNetworkAccess)' (a policy may have changed it)." }
Write-Host "[OK]    Foundry resource '$accountName' ready (keyless, public endpoint)."

# ---------------------------------------------------------------------------
# 3. Foundry project (portal access to the deployments; optional logging of evaluations).
# ---------------------------------------------------------------------------
$projectUri = "$accountBase/projects/${projectName}?api-version=$apiVersion"
if ((Invoke-MhhArm -Method GET -Path $projectUri -AllowNotFound).StatusCode -ne 200) {
    $projectBody = @{ location = $effectiveLocation; identity = @{ type = "SystemAssigned" };
                      properties = @{ description = "Decision Models for a Retail Marketplace MicroHack" } } | ConvertTo-Json -Depth 3
    Invoke-MhhArm -Method PUT -Path $projectUri -Payload $projectBody | Out-Null
    $elapsed = 0
    do { Start-Sleep -Seconds 8; $elapsed += 8
         $r = Invoke-MhhArm -Method GET -Path $projectUri -AllowNotFound
    } while ($r.StatusCode -ne 200 -and $elapsed -lt 120)
    if ($r.StatusCode -ne 200) { throw "Foundry project '$projectName' did not become ready." }
}
Write-Host "[OK]    Foundry project '$projectName' ready."

# ---------------------------------------------------------------------------
# 4. Model deployments, one at a time (an account accepts one deployment operation at once).
#    Re-runs repair a failed or wrongly sized deployment.
# ---------------------------------------------------------------------------
foreach ($m in $models) {
    $depUri = "$accountBase/deployments/$($m.deployment)?api-version=$apiVersion"
    $cur = Invoke-MhhArm -Method GET -Path $depUri -AllowNotFound
    $curObj = if ($cur.StatusCode -eq 200) { $cur.Content | ConvertFrom-Json } else { $null }
    if ($curObj -and $curObj.properties.provisioningState -eq "Succeeded" -and $curObj.sku.capacity -eq $m.capacity) {
        Write-Host "[OK]    Deployment '$($m.deployment)' already ready."
        continue
    }
    $depBody = @{
        sku        = @{ name = $skuName; capacity = $m.capacity }
        properties = @{ model = @{ format = $m.format; name = $m.name; version = $m.version } }
    } | ConvertTo-Json -Depth 5
    $attempt = 0
    while ($true) {
        $attempt++
        $put = Invoke-AzRestMethod -Method PUT -Uri "https://management.azure.com$depUri" -Payload $depBody
        if ($put.StatusCode -ge 200 -and $put.StatusCode -lt 300) { break }
        # 409 = another operation on the account is still running; retry briefly.
        if ($put.StatusCode -eq 409 -and $attempt -lt 12) { Start-Sleep -Seconds 15; continue }
        throw "Deployment '$($m.deployment)' ($($m.name) $skuName x$($m.capacity)) was rejected, HTTP $($put.StatusCode): $($put.Content)"
    }
    $elapsed = 0
    do {
        Start-Sleep -Seconds 10; $elapsed += 10
        $state = ((Invoke-MhhArm -Method GET -Path $depUri).Content | ConvertFrom-Json).properties.provisioningState
    } while ($state -notin @("Succeeded", "Failed", "Canceled") -and $elapsed -lt 600)
    if ($state -ne "Succeeded") { throw "Deployment '$($m.deployment)' is '$state' after ${elapsed}s." }
    Write-Host "[OK]    Deployment '$($m.deployment)' ($($m.name), $skuName x$($m.capacity)) ready."
}

# ---------------------------------------------------------------------------
# 5. RBAC. Attendees: Cognitive Services User (call the models) + Foundry User, formerly
#    "Azure AI User" (evaluations with a decision-model judge need it on the resource).
#    The deployer also gets Cognitive Services User, only so step 6 can prove the lab works.
# ---------------------------------------------------------------------------
$roles = @{
    "Cognitive Services User" = "a97b65f3-24c7-4388-baec-2e87135dc908"
    "Foundry User"            = "53ca6127-db72-4b80-b1b0-d745d6d5456d"
}
foreach ($userId in $AllowedEntraUserIds) {
    foreach ($roleName in $roles.Keys) {
        if (Get-AzRoleAssignment -ObjectId $userId -Scope $accountBase -RoleDefinitionId $roles[$roleName] -ErrorAction SilentlyContinue) {
            continue
        }
        New-AzRoleAssignment -ObjectId $userId -RoleDefinitionId $roles[$roleName] -Scope $accountBase -ErrorAction Stop | Out-Null
        Write-Host "[OK]    Granted '$roleName' to $userId."
    }
}
$deployerId = Get-TokenObjectId (Get-PlainToken "https://management.azure.com/")
if (-not (Get-AzRoleAssignment -ObjectId $deployerId -Scope $accountBase -RoleDefinitionId $roles["Cognitive Services User"] -ErrorAction SilentlyContinue)) {
    New-AzRoleAssignment -ObjectId $deployerId -RoleDefinitionId $roles["Cognitive Services User"] -Scope $accountBase -ErrorAction Stop | Out-Null
}

# ---------------------------------------------------------------------------
# 6. Readiness: call every API the challenges use, with the deployer's identity, and retry
#    while the new role assignment propagates (it can take several minutes).
# ---------------------------------------------------------------------------
$decisionEndpoint = "https://$accountName.services.ai.azure.com"
$openaiEndpoint   = "https://$accountName.openai.azure.com"
# A 300 x 300 JPEG (red disc on grey): Decision-1.1 rejects images under 280 px per side.
$probeImage = "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"

$probes = @(
    @{ name = "Microsoft-Decision-1.1 (text)"; url = "$decisionEndpoint/providers/microsoft/v1/systemone"
       body = @{ model = "decision"; state = "Garden hose 25 m with brass fittings"
                 questions = @{ ok = @{ type = "noul"; instructions = "Is this a garden product?" } } }
       check = { param($r) $null -ne $r.answers.ok.noul } },
    @{ name = "Microsoft-Decision-1.1 (image)"; url = "$decisionEndpoint/providers/microsoft/v1/systemone"
       body = @{ model = "decision"; state = "Product photo: image:probe.jpg"
                 assets = @{ "probe.jpg" = @{ type = "image"; format = "jpeg"; data_base64 = $probeImage } }
                 questions = @{ ok = @{ type = "noul"; instructions = "Is the main shape in the photo red?" } } }
       check = { param($r) $null -ne $r.answers.ok.noul } },
    @{ name = "gpt-6-luna Decisions API"; url = "$openaiEndpoint/openai/v1/decisions"
       body = @{ model = "gpt-6-luna"; input = "Garden hose 25 m with brass fittings"
                 questions = @(@{ type = "predicate"; name = "ok"; instructions = "Is this a garden product?" }) }
       check = { param($r) $r.answers.Count -ge 1 } },
    @{ name = "gpt-6-luna Responses API"; url = "$openaiEndpoint/openai/v1/responses"
       body = @{ model = "gpt-6-luna"; input = "Reply with the single word: ready" }
       check = { param($r) $r.status -eq "completed" } },
    @{ name = "Microsoft-Decision-1 (judge)"; url = "$decisionEndpoint/providers/microsoft/v1/systemone"
       body = @{ model = "decision-judge"; state = "Garden hose 25 m with brass fittings"
                 questions = @{ ok = @{ type = "noul"; instructions = "Is this a garden product?" } } }
       check = { param($r) $null -ne $r.answers.ok.noul } }
)

foreach ($p in $probes) {
    $json = $p.body | ConvertTo-Json -Depth 10 -Compress
    $deadline = (Get-Date).AddMinutes(12)
    $lastError = ""
    while ($true) {
        $token = Get-PlainToken "https://cognitiveservices.azure.com"
        $resp = Invoke-WebRequest -Method POST -Uri $p.url -Body $json -ContentType "application/json" `
            -Headers @{ Authorization = "Bearer $token" } -SkipHttpErrorCheck -TimeoutSec 60
        if ($resp.StatusCode -eq 200) {
            $parsed = $resp.Content | ConvertFrom-Json
            if (& $p.check $parsed) { Write-Host "[OK]    Probe: $($p.name) answered."; break }
            $lastError = "HTTP 200 but no typed answer: $($resp.Content)"
        } else {
            $lastError = "HTTP $($resp.StatusCode): $($resp.Content)"
        }
        # 401/403 while the role assignment propagates, 429/5xx while the deployment warms up.
        if ($resp.StatusCode -notin @(200, 401, 403, 404, 408, 429, 500, 502, 503, 504)) { break }
        if ((Get-Date) -gt $deadline) { break }
        Start-Sleep -Seconds 20
    }
    if (-not ($resp.StatusCode -eq 200 -and (& $p.check ($resp.Content | ConvertFrom-Json)))) {
        throw "Readiness probe '$($p.name)' failed in '$effectiveLocation': $lastError"
    }
}

Write-Host "[OK]    Lab ready."

# ---------------------------------------------------------------------------
# 7. Dashboard credentials — only reached when everything above succeeded.
# ---------------------------------------------------------------------------
@{ HackboxCredential = @{ name = "DecisionEndpoint";   value = $decisionEndpoint; note = "src/.env DECISION_ENDPOINT (Microsoft-Decision-1.1 and the judge)" } }
@{ HackboxCredential = @{ name = "OpenAIEndpoint";     value = $openaiEndpoint;   note = "src/.env OPENAI_ENDPOINT (gpt-6-luna)" } }
@{ HackboxCredential = @{ name = "DecisionDeployment"; value = "decision";        note = "src/.env DECISION_DEPLOYMENT" } }
@{ HackboxCredential = @{ name = "LunaDeployment";     value = "gpt-6-luna";      note = "src/.env LUNA_DEPLOYMENT" } }
@{ HackboxCredential = @{ name = "JudgeDeployment";    value = "decision-judge";  note = "src/.env JUDGE_DEPLOYMENT (Challenge 6)" } }
@{ HackboxCredential = @{ name = "DecisionCapacity";   value = "$($models[0].capacity)"; note = "src/.env DECISION_CAPACITY" } }
@{ HackboxCredential = @{ name = "LunaCapacity";       value = "$($models[1].capacity)"; note = "src/.env LUNA_CAPACITY" } }
@{ HackboxCredential = @{ name = "FoundryProjectEndpoint"; value = "https://$accountName.services.ai.azure.com/api/projects/$projectName"; note = "Optional: src/.env PROJECT_ENDPOINT" } }
@{ HackboxCredential = @{ name = "ResourceGroupName";  value = $effectiveRG;      note = "Where your Foundry resource lives" } }
