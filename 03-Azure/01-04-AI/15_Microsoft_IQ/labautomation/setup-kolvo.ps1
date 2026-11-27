<#
.SYNOPSIS
    Pre-builds Kolvo's side of the Microsoft IQ MicroHack in the 'kolvo' Foundry project.

.DESCRIPTION
    Called by deploy-lab.ps1 (and safe to run again on its own). It uses only the current
    Az context (Invoke-AzRestMethod, Get-AzAccessToken) and never logs in.

      1. Rival supplier agents 'nordic-drive-parts' and 'hallberg-repair' (prompt agents),
         with incoming A2A enabled (agent card + responses and a2a protocols).
      2. A2A connections in the kolvo project (category RemoteA2A, Entra agent identity):
           nordic-drive-parts-a2a, hallberg-repair-a2a and strandvik-a2a. The Strandvik target
           (strandvik-customer-service in the strandvik project) does not exist yet: the
           participants create it in challenge 2.
      3. 'maria-procurement': Maria's procurement agent with the three A2A tools.
      4. Foundry Agent Consumer for Maria's agent identity on the kolvo project, so it can
         call the rivals. NOT on the strandvik project: that is the participants' task.

    Idempotent: an agent whose definition is unchanged is left alone; a changed definition
    becomes a new version. Connections and role assignments are PUTs with stable names.

.OUTPUTS
    [pscustomobject] with MariaPrincipalId, KolvoProjectEndpoint and the agent names.
#>
param(
    [Parameter(Mandatory = $true)][string]$SubscriptionId,
    [Parameter(Mandatory = $true)][string]$ResourceGroupName,
    [Parameter(Mandatory = $true)][string]$AccountName,
    [string]$KolvoProject = "kolvo",
    [string]$StrandvikProject = "strandvik",
    [string]$Model = "gpt-5.4-mini",
    [string]$StrandvikAgentName = "strandvik-customer-service",
    # How long to wait for the rivals' public A2A agent cards (0 = do not wait).
    [int]$CardWaitSeconds = 900
)

$ErrorActionPreference = "Stop"

$connApi   = "2025-06-01"
$agentApi  = "v1"
$audience  = "https://ai.azure.com"
$consumerRoleId = "eed3b665-ab3a-47b6-8f48-c9382fb1dad6"   # Foundry Agent Consumer

$host_          = "https://$AccountName.services.ai.azure.com"
$kolvoEndpoint  = "$host_/api/projects/$KolvoProject"
$accountId      = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroupName/providers/Microsoft.CognitiveServices/accounts/$AccountName"
$kolvoProjectId = "$accountId/projects/$KolvoProject"

function Get-A2AUrl([string]$Project, [string]$Agent) {
    "$host_/api/projects/$Project/agents/$Agent/endpoint/protocols/a2a"
}

# ---------------------------------------------------------------------------
# Agent definitions (scenario facts v2)
# ---------------------------------------------------------------------------
$nordicInstructions = @'
You are the order desk agent of Nordic Drive Parts, a parts distributor in Sweden.
Other companies' purchasing agents send you requests for spare parts, usually at night.

How you work:
- You answer at once, from your stock list. You never check with a person.
- Stock list (updated every evening): SD-900 drive unit: IN STOCK, 1 unit, Malmo warehouse.
  SD-700 drive unit: IN STOCK, 2 units. Spare gearbox seals: IN STOCK.
- For anything on the stock list, answer: "In stock, ships today." Delivery: by road,
  usually the next working day in southern Sweden.
- Price: our standard list price, confirmed on the order confirmation.
- You cannot hold or reserve a unit. Stock goes to whoever orders first.
- You do not install. You have no service technicians; the customer arranges installation.
- Always answer in English, short and friendly. Sign as "Nordic Drive Parts order desk".
'@

$hallbergInstructions = @'
You are the automatic reply agent of Hallberg Repair Services, a repair shop for drive
units and gearboxes in western Sweden.

Office hours are 08:00 to 17:00 CET, Monday to Friday. Requests from other companies'
agents arrive outside office hours (tonight). Treat every request as received outside
office hours.

For every request:
- Thank the sender and confirm that the request is received.
- Say that the office is closed now and that a person will answer after 08:45.
- Do not give prices, delivery times, stock levels or repair times. A person will do that.
- Always answer in English, whatever language the request uses. Keep it short.
  Sign as "Hallberg Repair Services".
'@

$mariaInstructions = @'
You are Kolvo's procurement agent. You act for Maria Lind, production manager of the
press shop at Kolvo AB (cab plant, Hisingen, Gothenburg).

Maria's standing instruction: "When a critical part fails and there is no spare, ask our
approved suppliers for price and delivery; never order without me."

Tonight: the SD-900 drive unit on press line 2 (serial SD9-K-0412) started shaking at
02:10. The press runs at half speed, which buys time until Thursday 17 December 06:00.
Kolvo has no spare. A replacement SD-900 must be installed before then.

When you are asked to handle this (or any similar request):
1. Send a request to EACH of Kolvo's three approved suppliers, using your tools:
   Strandvik Drives (tool for strandvik), Nordic Drive Parts (tool for nordic-drive-parts)
   and Hallberg Repair Services (tool for hallberg-repair).
2. In every request: introduce yourself as "maria-procurement, Kolvo AB's procurement agent,
   acting for Maria, production manager, press shop"; name the unit SD9-K-0412 (SD-900) on
   press line 2;
   say it is needed before Thursday 17 December 06:00; and ask for (a) the price,
   (b) the delivery time to Kolvo, Hisingen, and (c) whether they can hold the unit for
   Kolvo until Maria decides.
3. If a supplier does not answer, or the call fails, write that down for that supplier
   ("no answer" and the reason) and carry on with the others.
4. Summarise per supplier: price, delivery time, can they hold the unit, installation,
   and anything that needs a person to confirm.

Rules:
- You only ask for price and delivery (a quote). Never place an order, accept an offer,
  or commit Kolvo to anything. Only Maria can decide. End with: "Maria decides."
- Do not invent answers for a supplier.
'@

$nordicCard = @{
    description = "Nordic Drive Parts order desk. Answers stock and delivery questions for drive units and spare parts at once, from the stock list."
    version     = "1.0"
    skills      = @(@{ id = "stock-and-delivery"; name = "Stock and delivery"
                      description = "Checks the stock list for a part and answers whether it is in stock and when it ships." })
}
$hallbergCard = @{
    description = "Hallberg Repair Services. Receives repair and replacement requests for drive units; a person answers in office hours (08:00 to 17:00 CET)."
    version     = "1.0"
    skills      = @(@{ id = "repair-request"; name = "Repair request"
                      description = "Receives a repair or replacement request and confirms when a person will answer." })
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
function Get-FoundryToken {
    $tok = Get-AzAccessToken -ResourceUrl $audience -WarningAction SilentlyContinue
    if ($tok.Token -is [System.Security.SecureString]) { return [System.Net.NetworkCredential]::new('', $tok.Token).Password }
    return [string]$tok.Token
}

# Foundry data-plane call. Retries 401/403 for a few minutes (a new data role takes a
# while to apply), plus throttling and gateway errors. Returns $null on an allowed 404.
function Invoke-Foundry {
    param([string]$Method, [string]$Path, $Body, [switch]$AllowNotFound, [int]$AuthWaitSeconds = 600)
    $uri = if ($Path -like 'https://*') { $Path } else { "$kolvoEndpoint$Path" }
    $uri += $(if ($uri.Contains('?')) { '&' } else { '?' }) + "api-version=$agentApi"
    $deadline = (Get-Date).AddSeconds($AuthWaitSeconds)
    $attempt = 0
    while ($true) {
        $attempt++
        $params = @{ Method = $Method; Uri = $uri; Headers = @{ Authorization = "Bearer $(Get-FoundryToken)" }
                     ContentType = 'application/json'; SkipHttpErrorCheck = $true; TimeoutSec = 300 }
        if ($null -ne $Body) { $params.Body = ($Body | ConvertTo-Json -Depth 20) }
        try { $r = Invoke-WebRequest @params }
        catch {
            # Client-side timeout or connection reset: retry a few times.
            if ($attempt -lt 4) { Write-Host "[WARN]  Foundry $Method call failed ($($_.Exception.Message)); retrying..."; Start-Sleep -Seconds 15; continue }
            throw
        }
        $code = [int]$r.StatusCode
        if ($code -ge 200 -and $code -lt 300) { if ($r.Content) { return ($r.Content | ConvertFrom-Json -Depth 50) } else { return $null } }
        if ($code -eq 404 -and $AllowNotFound) { return $null }
        if ($code -in @(401, 403) -and (Get-Date) -lt $deadline) {
            if ($attempt -eq 1) { Write-Host "[INFO]  Waiting for Foundry data-plane access to apply (HTTP $code)..." }
            Start-Sleep -Seconds 20; continue
        }
        if ($code -in @(408, 429, 500, 502, 503, 504) -and $attempt -lt 6) { Start-Sleep -Seconds (10 * $attempt); continue }
        throw "Foundry $Method $($uri -replace '\?.*$','') failed with HTTP ${code}: $($r.Content)"
    }
}

function Invoke-Arm {
    param([string]$Method, [string]$Path, $Body, [switch]$AllowNotFound)
    $params = @{ Method = $Method; Uri = "https://management.azure.com$Path" }
    if ($null -ne $Body) { $params.Payload = ($Body | ConvertTo-Json -Depth 10) }
    for ($attempt = 1; $attempt -le 5; $attempt++) {
        $r = Invoke-AzRestMethod @params
        if ($r.StatusCode -in @(429, 500, 502, 503, 504) -and $attempt -lt 5) { Start-Sleep -Seconds (10 * $attempt); continue }
        break
    }
    if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 300) { if ($r.Content) { return ($r.Content | ConvertFrom-Json -Depth 30) } else { return $null } }
    if ($r.StatusCode -eq 404 -and $AllowNotFound) { return $null }
    throw "ARM $Method $Path failed with HTTP $($r.StatusCode): $($r.Content)"
}

# Canonical JSON of the parts of a definition we control, to detect changes.
function Get-DefinitionKey($Definition) {
    $tools = @($Definition.tools | ForEach-Object { "$($_.type)|$($_.project_connection_id)" } | Sort-Object)
    return "$($Definition.model)|$(([string]$Definition.instructions).Replace("`r`n", "`n").Trim())|$($tools -join ',')"
}

function Set-PromptAgent {
    param([string]$Name, [string]$Instructions, [object[]]$Tools = @(), [string]$Description)
    $definition = @{ kind = "prompt"; model = $Model; instructions = $Instructions.Replace("`r`n", "`n").Trim() }
    if ($Tools.Count -gt 0) { $definition.tools = $Tools }
    $existing = Invoke-Foundry -Method GET -Path "/agents/$Name" -AllowNotFound
    if (-not $existing) {
        try {
            Invoke-Foundry -Method POST -Path "/agents" -Body @{ name = $Name; description = $Description; definition = $definition } | Out-Null
        } catch {
            # A retried create after a client timeout can find the agent already created.
            if ("$_" -notmatch 'HTTP 409|already exists') { throw }
        }
        Write-Host "[OK]    Agent '$Name' created."
    } else {
        $latest = $existing.versions.latest.definition
        if ((Get-DefinitionKey $latest) -ne (Get-DefinitionKey ([pscustomobject]$definition))) {
            Invoke-Foundry -Method POST -Path "/agents/$Name/versions" -Body @{ description = $Description; definition = $definition } | Out-Null
            Write-Host "[OK]    Agent '$Name' updated (new version)."
        } else {
            Write-Host "[OK]    Agent '$Name' already up to date."
        }
    }
    # Confirm it exists and return the current JSON.
    $agent = Invoke-Foundry -Method GET -Path "/agents/$Name"
    if (-not $agent) { throw "Agent '$Name' was not created." }
    return $agent
}

function Enable-IncomingA2A {
    param([string]$Name, [hashtable]$Card)
    $body = @{ agent_card = $Card; agent_endpoint = @{ protocol_configuration = @{ responses = @{}; a2a = @{} } } }
    Invoke-Foundry -Method PATCH -Path "/agents/$Name" -Body $body | Out-Null
    # Confirm the PATCH landed on the agent.
    $a = Invoke-Foundry -Method GET -Path "/agents/$Name"
    if (@($a.agent_endpoint.protocols) -notcontains 'a2a' -or -not $a.agent_card) {
        throw "Incoming A2A was not enabled on '$Name': $($a.agent_endpoint | ConvertTo-Json -Depth 6 -Compress)"
    }
    Write-Host "[OK]    Incoming A2A enabled on '$Name' (agent card + a2a protocol)."
}

# On a brand-new project the public A2A endpoint answers "Project not found" for a while
# after the agent is configured. Wait for the v1.0 agent card; warn (do not fail) on timeout.
function Wait-AgentCard {
    param([string]$Name, [int]$TimeoutSeconds = 1200)
    $cardUrl = "$(Get-A2AUrl $KolvoProject $Name)/agentCard/v1.0"
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $started = Get-Date
    while ((Get-Date) -lt $deadline) {
        $c = Invoke-Foundry -Method GET -Path $cardUrl -AllowNotFound
        if ($c -and $c.name) {
            Write-Host ("[OK]    A2A agent card for '$Name' is served (after {0:n0} s)." -f ((Get-Date) - $started).TotalSeconds)
            return $true
        }
        Start-Sleep -Seconds 30
    }
    Write-Host "[WARN]  The A2A agent card for '$Name' is not served yet (new project still propagating). It normally appears within minutes."
    return $false
}

function Set-A2AConnection {
    param([string]$Name, [string]$Target)
    $path = "$kolvoProjectId/connections/${Name}?api-version=$connApi"
    Invoke-Arm -Method PUT -Path $path -Body @{ properties = @{
        category      = "RemoteA2A"
        target        = $Target
        authType      = "AgenticIdentityToken"
        audience      = $audience
        isSharedToAll = $true
        metadata      = @{ audience = $audience }
    } } | Out-Null
    $conn = Invoke-Arm -Method GET -Path $path -AllowNotFound
    if (-not $conn) { throw "A2A connection '$Name' was not created." }
    Write-Host "[OK]    A2A connection '$Name' -> $Target"
    return $conn.id
}

function Grant-Role {
    param([string]$Scope, [string]$PrincipalId, [string]$RoleId, [string]$Label)
    $md5 = [System.Security.Cryptography.MD5]::Create()
    try { $name = ([guid]::new($md5.ComputeHash([System.Text.Encoding]::UTF8.GetBytes("$Scope|$PrincipalId|$RoleId".ToLower())))).ToString() }
    finally { $md5.Dispose() }
    $body = @{ properties = @{
        roleDefinitionId = "/subscriptions/$SubscriptionId/providers/Microsoft.Authorization/roleDefinitions/$RoleId"
        principalId      = $PrincipalId
        principalType    = "ServicePrincipal"
    } } | ConvertTo-Json -Depth 4
    for ($attempt = 1; $attempt -le 12; $attempt++) {
        $r = Invoke-AzRestMethod -Method PUT -Uri "https://management.azure.com$Scope/providers/Microsoft.Authorization/roleAssignments/${name}?api-version=2022-04-01" -Payload $body
        if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 300) { Write-Host "[OK]    Granted Foundry Agent Consumer to $Label."; return }
        if ($r.StatusCode -eq 409 -and $r.Content -match 'RoleAssignmentExists') { Write-Host "[OK]    Foundry Agent Consumer already assigned to $Label."; return }
        if ($r.Content -match 'PrincipalNotFound|does not exist in the directory' -or $r.StatusCode -in @(429, 500, 502, 503, 504)) {
            Start-Sleep -Seconds 15; continue
        }
        throw "Could not grant Foundry Agent Consumer to $Label (HTTP $($r.StatusCode)): $($r.Content)"
    }
    throw "Could not grant Foundry Agent Consumer to $Label (principal not replicated yet)."
}

# ---------------------------------------------------------------------------
# 1. Rival suppliers with incoming A2A
# ---------------------------------------------------------------------------
Set-PromptAgent -Name "nordic-drive-parts" -Instructions $nordicInstructions `
    -Description "Rival supplier: parts distributor. Answers at once from a stock list; cannot hold a unit." | Out-Null
Enable-IncomingA2A -Name "nordic-drive-parts" -Card $nordicCard
Set-PromptAgent -Name "hallberg-repair" -Instructions $hallbergInstructions `
    -Description "Rival supplier: repair shop. Answers in office hours (08:00 to 17:00 CET), after 08:45." | Out-Null
Enable-IncomingA2A -Name "hallberg-repair" -Card $hallbergCard

# ---------------------------------------------------------------------------
# 2. A2A connections (Strandvik's target is created by the participants later)
# ---------------------------------------------------------------------------
$connIds = [ordered]@{
    strandvik = Set-A2AConnection -Name "strandvik-a2a"          -Target (Get-A2AUrl $StrandvikProject $StrandvikAgentName)
    nordic    = Set-A2AConnection -Name "nordic-drive-parts-a2a" -Target (Get-A2AUrl $KolvoProject "nordic-drive-parts")
    hallberg  = Set-A2AConnection -Name "hallberg-repair-a2a"    -Target (Get-A2AUrl $KolvoProject "hallberg-repair")
}

# ---------------------------------------------------------------------------
# 3. Maria's procurement agent
# ---------------------------------------------------------------------------
$mariaTools = @($connIds.Values | ForEach-Object { @{ type = "a2a"; a2a_version = "1.0"; project_connection_id = $_ } })
$maria = Set-PromptAgent -Name "maria-procurement" -Instructions $mariaInstructions -Tools $mariaTools `
    -Description "Kolvo's procurement agent, acting for Maria Lind (production manager, press shop). Asks approved suppliers for price and delivery; never orders."

$mariaPrincipalId = [string]$maria.versions.latest.instance_identity.principal_id
if (-not $mariaPrincipalId) { $mariaPrincipalId = [string]$maria.instance_identity.principal_id }
if (-not $mariaPrincipalId) { throw "maria-procurement has no instance_identity.principal_id: $($maria | ConvertTo-Json -Depth 6 -Compress)" }

# ---------------------------------------------------------------------------
# 4. Maria may call the rivals (kolvo project only)
# ---------------------------------------------------------------------------
Grant-Role -Scope $kolvoProjectId -PrincipalId $mariaPrincipalId -RoleId $consumerRoleId -Label "maria-procurement identity '$mariaPrincipalId' (kolvo project)"

$cardsReady = $null
if ($CardWaitSeconds -gt 0) {
    $cardsReady = (Wait-AgentCard -Name "nordic-drive-parts" -TimeoutSeconds $CardWaitSeconds) -and
                  (Wait-AgentCard -Name "hallberg-repair" -TimeoutSeconds $CardWaitSeconds)
}

[pscustomobject]@{
    CardsReady           = $cardsReady
    KolvoProjectEndpoint = $kolvoEndpoint
    MariaAgentName       = "maria-procurement"
    MariaPrincipalId     = $mariaPrincipalId
    RivalAgents          = @("nordic-drive-parts", "hallberg-repair")
    StrandvikA2ATarget   = Get-A2AUrl $StrandvikProject $StrandvikAgentName
}
