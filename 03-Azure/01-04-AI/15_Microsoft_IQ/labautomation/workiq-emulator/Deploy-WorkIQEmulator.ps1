#Requires -Version 7.2
<#
.SYNOPSIS
    Deploys the Work IQ emulator to Azure Functions Flex Consumption (Python 3.12).

.DESCRIPTION
    Dot-source this file, then call Deploy-WorkIQEmulator. It uses only Az PowerShell
    (Invoke-AzRestMethod and Get-AzAccessToken) against the current Az context. It never
    calls Connect-AzAccount, Set-AzContext, az login or az account set.

    Steps (all idempotent):
      1. Tag the resource group with SecurityControl=Ignore (creates the group if missing).
      2. Storage account for deployment packages and AzureWebJobsStorage. Shared key access
         is disabled; the function app uses its system-assigned identity.
      3. Flex Consumption plan (FC1) and function app (python 3.12, 2048 MB, max 1 instance).
      4. Role assignments: Storage Blob Data Owner on the storage account, and optionally
         Cognitive Services OpenAI User on the Foundry account.
      5. Zip the emulator (without tests, .venv, caches) and publish it with remote build
         through the Flex "one deploy" endpoint. Poll until the deployment succeeds.
      6. Probe https://<host>/healthz until it returns 200.

.EXAMPLE
    . ./Deploy-WorkIQEmulator.ps1
    $result = Deploy-WorkIQEmulator -SubscriptionId $sub -ResourceGroupName rg-lab01 -Location swedencentral `
        -Name func-workiq-lab01 -Keys @{ 'sales-lead' = $k1; 'supply-planner' = $k2; 'quality-head' = $k3; 'plant-manager' = $k4 } `
        -AdminKey $adminKey -Tags @{ project = 'microhack' }
    $result.McpEndpoint
#>

Set-StrictMode -Version Latest

$script:WorkIQEmulatorRoot = $PSScriptRoot
$script:WorkIQRoleStorageBlobDataOwner = 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b'
$script:WorkIQRoleOpenAIUser = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
$script:WorkIQPackageExclude = @('.venv', '__pycache__', '.pytest_cache', 'tests', 'scripts', '.vscode', '.git')
$script:WorkIQFileExclude = @('*.pyc', '*.zip', 'local.settings.json', 'requirements-dev.txt', 'Deploy-WorkIQEmulator.ps1', 'README.md', '.gitignore')

function Invoke-WorkIQArm {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][ValidateSet('GET', 'PUT', 'PATCH', 'POST', 'DELETE')][string]$Method,
        [Parameter(Mandatory)][string]$Path,
        [object]$Body,
        [int[]]$AllowStatus = @()
    )
    $params = @{ Method = $Method; Path = $Path }
    if ($null -ne $Body) { $params.Payload = ($Body | ConvertTo-Json -Depth 30 -Compress) }
    $resp = Invoke-AzRestMethod @params
    $code = [int]$resp.StatusCode
    if (($code -lt 200 -or $code -ge 300) -and ($AllowStatus -notcontains $code)) {
        $detail = $resp.Content
        if ($detail -and $detail.Length -gt 1500) { $detail = $detail.Substring(0, 1500) }
        $cleanPath = $Path -replace '\?.*$', ''
        throw "ARM $Method $cleanPath failed with HTTP $code. $detail"
    }
    [pscustomobject]@{
        StatusCode = $code
        Json       = if ($resp.Content) { try { $resp.Content | ConvertFrom-Json -Depth 50 } catch { $null } } else { $null }
    }
}

function Wait-WorkIQProvisioned {
    param([Parameter(Mandatory)][string]$Path, [int]$TimeoutSeconds = 300)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ($true) {
        $r = Invoke-WorkIQArm -Method GET -Path $Path -AllowStatus 404
        $state = $null
        if ($r.StatusCode -eq 200 -and $r.Json -and $r.Json.PSObject.Properties['properties']) {
            # Some resource types (for example Microsoft.Web/sites) do not report provisioningState.
            if (-not $r.Json.properties.PSObject.Properties['provisioningState']) { return $r.Json }
            $state = $r.Json.properties.provisioningState
        }
        if ($state -eq 'Succeeded') { return $r.Json }
        if ($state -in @('Failed', 'Canceled')) { throw "Provisioning of $($Path -replace '\?.*$','') ended in state $state." }
        if ((Get-Date) -gt $deadline) { throw "Timed out waiting for $($Path -replace '\?.*$','') to provision (last state: $state)." }
        Start-Sleep -Seconds 5
    }
}

function Get-WorkIQBearerToken {
    $tok = Get-AzAccessToken -ResourceUrl 'https://management.azure.com/' -WarningAction SilentlyContinue
    if ($tok.Token -is [System.Security.SecureString]) {
        return [System.Net.NetworkCredential]::new('', $tok.Token).Password
    }
    return [string]$tok.Token
}

function Get-WorkIQStableGuid {
    param([Parameter(Mandatory)][string]$Seed)
    $bytes = [System.Security.Cryptography.SHA256]::HashData([System.Text.Encoding]::UTF8.GetBytes($Seed))
    return ([guid]::new([byte[]]$bytes[0..15])).ToString()
}

function New-WorkIQRoleAssignment {
    param(
        [Parameter(Mandatory)][string]$SubscriptionId,
        [Parameter(Mandatory)][string]$Scope,
        [Parameter(Mandatory)][string]$RoleDefinitionId,
        [Parameter(Mandatory)][string]$PrincipalId
    )
    $name = Get-WorkIQStableGuid "$Scope|$RoleDefinitionId|$PrincipalId"
    $body = @{
        properties = @{
            roleDefinitionId = "/subscriptions/$SubscriptionId/providers/Microsoft.Authorization/roleDefinitions/$RoleDefinitionId"
            principalId      = $PrincipalId
            principalType    = 'ServicePrincipal'
        }
    }
    $path = "$Scope/providers/Microsoft.Authorization/roleAssignments/$($name)?api-version=2022-04-01"
    # A new managed identity can take a short while to replicate; retry PrincipalNotFound.
    for ($i = 1; $i -le 10; $i++) {
        $resp = Invoke-AzRestMethod -Method PUT -Path $path -Payload ($body | ConvertTo-Json -Depth 5 -Compress)
        $code = [int]$resp.StatusCode
        if ($code -in 200, 201) { return }
        if ($code -eq 409 -and $resp.Content -match 'RoleAssignmentExists') { return }
        if ($code -eq 400 -and $resp.Content -match 'PrincipalNotFound' -and $i -lt 10) { Start-Sleep -Seconds 10; continue }
        throw "Role assignment $RoleDefinitionId on $Scope failed with HTTP $code. $($resp.Content)"
    }
}

function New-WorkIQPackage {
    param([Parameter(Mandatory)][string]$SourceDir, [Parameter(Mandatory)][string]$ZipPath)
    Add-Type -AssemblyName System.IO.Compression, System.IO.Compression.FileSystem
    if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
    $root = (Resolve-Path $SourceDir).Path.TrimEnd('\', '/')
    $zip = [System.IO.Compression.ZipFile]::Open($ZipPath, [System.IO.Compression.ZipArchiveMode]::Create)
    try {
        Get-ChildItem -Path $root -Recurse -File -Force | ForEach-Object {
            $rel = $_.FullName.Substring($root.Length + 1)
            $parts = $rel -split '[\\/]'
            if ($parts | Where-Object { $script:WorkIQPackageExclude -contains $_ }) { return }
            foreach ($pattern in $script:WorkIQFileExclude) { if ($_.Name -like $pattern) { return } }
            # Zip entries must use forward slashes for the Linux remote build.
            [void][System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $_.FullName, ($parts -join '/'), [System.IO.Compression.CompressionLevel]::Optimal)
        }
    }
    finally { $zip.Dispose() }
    return $ZipPath
}

function ConvertTo-WorkIQAppSettings {
    param([hashtable]$Settings)
    return @($Settings.GetEnumerator() | Sort-Object Name | ForEach-Object { @{ name = $_.Name; value = [string]$_.Value } })
}

function Deploy-WorkIQEmulator {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$SubscriptionId,
        [Parameter(Mandatory)][string]$ResourceGroupName,
        [Parameter(Mandatory)][string]$Location,
        [Parameter(Mandatory)][ValidatePattern('^[a-z0-9][a-z0-9-]{1,40}[a-z0-9]$')][string]$Name,
        [string]$AppInsightsConnectionString = '',
        [string]$FoundryOpenAIEndpoint = '',
        [string]$FoundryChatDeployment = '',
        [string]$FoundryAccountResourceId = '',
        [Parameter(Mandatory)][hashtable]$Keys,
        [Parameter(Mandatory)][string]$AdminKey,
        [hashtable]$Tags = @{},
        [int]$DeployTimeoutSeconds = 600
    )
    $ErrorActionPreference = 'Stop'
    $rgPath = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroupName"
    $allTags = @{}
    foreach ($k in $Tags.Keys) { $allTags[$k] = [string]$Tags[$k] }
    $allTags['SecurityControl'] = 'Ignore'

    # -- validate secrets (never printed) ---------------------------------------
    if ($AdminKey.Length -lt 16) { throw 'AdminKey must be at least 16 characters.' }
    $appSettings = @{}
    foreach ($persona in $Keys.Keys) {
        if ($persona -notmatch '^[a-z][a-z0-9-]{1,30}$') { throw "Invalid persona id '$persona'." }
        $value = [string]$Keys[$persona]
        if ($value.Length -lt 16) { throw "The key for persona '$persona' must be at least 16 characters." }
        $appSettings['WORKIQ_KEY_' + $persona.ToUpperInvariant().Replace('-', '_')] = $value
    }
    if ($appSettings.Count -eq 0) { throw 'Keys must contain at least one persona key.' }

    # -- 1. resource group --------------------------------------------------------
    Write-Verbose "Resource group $ResourceGroupName"
    $rg = Invoke-WorkIQArm -Method GET -Path "$($rgPath)?api-version=2021-04-01" -AllowStatus 404
    if ($rg.StatusCode -eq 404) {
        Invoke-WorkIQArm -Method PUT -Path "$($rgPath)?api-version=2021-04-01" -Body @{ location = $Location; tags = $allTags } | Out-Null
    }
    else {
        Invoke-WorkIQArm -Method PATCH -Path "$rgPath/providers/Microsoft.Resources/tags/default?api-version=2021-04-01" -Body @{ operation = 'Merge'; properties = @{ tags = @{ SecurityControl = 'Ignore' } } } | Out-Null
    }

    # -- 2. storage account -------------------------------------------------------
    $clean = ($Name -replace '[^a-z0-9]', '')
    $suffix = (Get-WorkIQStableGuid "$SubscriptionId|$ResourceGroupName|$Name").Replace('-', '').Substring(0, 6)
    $storageName = ('stwiq' + $clean)
    if ($storageName.Length -gt 18) { $storageName = $storageName.Substring(0, 18) }
    $storageName = $storageName + $suffix
    $storagePath = "$rgPath/providers/Microsoft.Storage/storageAccounts/$storageName"
    Write-Verbose "Storage account $storageName"
    Invoke-WorkIQArm -Method PUT -Path "$($storagePath)?api-version=2023-05-01" -Body @{
        location   = $Location
        kind       = 'StorageV2'
        sku        = @{ name = 'Standard_LRS' }
        tags       = $allTags
        properties = @{
            allowSharedKeyAccess     = $false
            allowBlobPublicAccess    = $false
            publicNetworkAccess      = 'Enabled'
            minimumTlsVersion        = 'TLS1_2'
            supportsHttpsTrafficOnly = $true
            networkAcls              = @{ defaultAction = 'Allow'; bypass = 'AzureServices' }
        }
    } | Out-Null
    Wait-WorkIQProvisioned -Path "$($storagePath)?api-version=2023-05-01" | Out-Null
    $container = 'app-package-' + $clean
    if ($container.Length -gt 63) { $container = $container.Substring(0, 63) }
    $container = $container.TrimEnd('-')
    Invoke-WorkIQArm -Method PUT -Path "$storagePath/blobServices/default/containers/$($container)?api-version=2023-05-01" -Body @{ properties = @{ publicAccess = 'None' } } | Out-Null

    # -- 3. plan and function app -------------------------------------------------
    $planName = "plan-$Name"
    $planPath = "$rgPath/providers/Microsoft.Web/serverfarms/$planName"
    Write-Verbose "Flex Consumption plan $planName"
    Invoke-WorkIQArm -Method PUT -Path "$($planPath)?api-version=2024-04-01" -Body @{
        location   = $Location
        kind       = 'functionapp'
        sku        = @{ name = 'FC1'; tier = 'FlexConsumption' }
        tags       = $allTags
        properties = @{ reserved = $true }
    } | Out-Null
    Wait-WorkIQProvisioned -Path "$($planPath)?api-version=2024-04-01" | Out-Null

    $sessionBytes = [byte[]]::new(32)
    [System.Security.Cryptography.RandomNumberGenerator]::Fill($sessionBytes)
    $appSettings['WORKIQ_ADMIN_KEY'] = $AdminKey
    $appSettings['WORKIQ_SESSION_SECRET'] = [Convert]::ToBase64String($sessionBytes)
    $appSettings['AzureWebJobsStorage__accountName'] = $storageName
    if ($AppInsightsConnectionString) { $appSettings['APPLICATIONINSIGHTS_CONNECTION_STRING'] = $AppInsightsConnectionString }
    if ($FoundryOpenAIEndpoint) { $appSettings['FOUNDRY_OPENAI_ENDPOINT'] = $FoundryOpenAIEndpoint }
    if ($FoundryChatDeployment) { $appSettings['FOUNDRY_CHAT_DEPLOYMENT'] = $FoundryChatDeployment }

    $sitePath = "$rgPath/providers/Microsoft.Web/sites/$Name"
    Write-Verbose "Function app $Name"
    $siteBody = @{
        location   = $Location
        kind       = 'functionapp,linux'
        tags       = $allTags
        identity   = @{ type = 'SystemAssigned' }
        properties = @{
            serverFarmId      = $planPath
            httpsOnly         = $true
            siteConfig        = @{
                appSettings     = ConvertTo-WorkIQAppSettings $appSettings
                minTlsVersion   = '1.2'
                ftpsState       = 'Disabled'
                http20Enabled   = $true
                cors            = @{ allowedOrigins = @() }
            }
            functionAppConfig = @{
                deployment          = @{
                    storage = @{
                        type           = 'blobContainer'
                        value          = "https://$storageName.blob.core.windows.net/$container"
                        authentication = @{ type = 'SystemAssignedIdentity' }
                    }
                }
                runtime             = @{ name = 'python'; version = '3.12' }
                # Python defaults to 1 concurrent request per instance. With a single instance that
                # makes requests queue behind each other; the ASGI app handles concurrency itself.
                scaleAndConcurrency = @{
                    maximumInstanceCount = 1
                    instanceMemoryMB     = 2048
                    triggers             = @{ http = @{ perInstanceConcurrency = 16 } }
                }
            }
        }
    }
    Invoke-WorkIQArm -Method PUT -Path "$($sitePath)?api-version=2024-04-01" -Body $siteBody | Out-Null
    $site = Wait-WorkIQProvisioned -Path "$($sitePath)?api-version=2024-04-01"
    $principalId = $site.identity.principalId
    if (-not $principalId) { throw "Function app $Name has no system-assigned identity." }

    # Basic auth publishing is not needed; deployments use Entra tokens.
    foreach ($kind in 'scm', 'ftp') {
        Invoke-WorkIQArm -Method PUT -Path "$sitePath/basicPublishingCredentialsPolicies/$($kind)?api-version=2024-04-01" -Body @{ properties = @{ allow = $false } } | Out-Null
    }

    # -- 4. role assignments ------------------------------------------------------
    Write-Verbose 'Role assignments'
    New-WorkIQRoleAssignment -SubscriptionId $SubscriptionId -Scope $storagePath -RoleDefinitionId $script:WorkIQRoleStorageBlobDataOwner -PrincipalId $principalId
    if ($FoundryAccountResourceId) {
        $foundrySub = ($FoundryAccountResourceId -split '/')[2]
        New-WorkIQRoleAssignment -SubscriptionId $foundrySub -Scope $FoundryAccountResourceId.TrimEnd('/') -RoleDefinitionId $script:WorkIQRoleOpenAIUser -PrincipalId $principalId
    }

    # -- 5. package and one deploy ------------------------------------------------
    $hostName = $site.properties.defaultHostName
    $scmHost = @($site.properties.hostNameSslStates | Where-Object { $_.hostType -eq 'Repository' } | Select-Object -ExpandProperty name -First 1)
    $scmHost = if ($scmHost) { $scmHost[0] } else { "$Name.scm.azurewebsites.net" }
    $zipPath = Join-Path $script:WorkIQEmulatorRoot ".deploy-$([guid]::NewGuid().ToString('N')).zip"
    try {
        New-WorkIQPackage -SourceDir $script:WorkIQEmulatorRoot -ZipPath $zipPath | Out-Null
        $bytes = [System.IO.File]::ReadAllBytes($zipPath)
        Write-Verbose "Publishing $($bytes.Length) bytes to $scmHost"
        $publishUri = "https://$scmHost/api/publish?RemoteBuild=true&Deployer=microhack"
        $deploymentId = $null
        $locationHeader = $null
        # The storage role assignment can take a few minutes to apply; retry the upload.
        for ($attempt = 1; $attempt -le 8; $attempt++) {
            $headers = @{ Authorization = "Bearer $(Get-WorkIQBearerToken)" }
            try {
                $resp = Invoke-WebRequest -Uri $publishUri -Method POST -Headers $headers -ContentType 'application/zip' -Body $bytes -SkipHttpErrorCheck -TimeoutSec 300
            }
            catch {
                $resp = $null
                $err = $_.Exception.Message
            }
            $code = if ($resp) { [int]$resp.StatusCode } else { 0 }
            if ($code -ge 200 -and $code -lt 300) {
                $content = if ($resp.Content -is [byte[]]) { [System.Text.Encoding]::UTF8.GetString($resp.Content) } else { [string]$resp.Content }
                if ($content -match '([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})') { $deploymentId = $Matches[1] }
                if ($resp.Headers['Location']) { $locationHeader = @($resp.Headers['Location'])[0] }
                break
            }
            if ($attempt -eq 8) {
                $detail = if ($resp) { [string]$resp.Content } else { $err }
                throw "Publish to $scmHost failed with HTTP $code after $attempt attempts. $detail"
            }
            Write-Verbose "Publish attempt $attempt returned HTTP $code; retrying in 30 seconds"
            Start-Sleep -Seconds 30
        }

        $statusUri = if ($deploymentId) { "https://$scmHost/api/deployments/$deploymentId" } elseif ($locationHeader) { $locationHeader } else { "https://$scmHost/api/deployments/latest" }
        $deadline = (Get-Date).AddSeconds($DeployTimeoutSeconds)
        while ($true) {
            Start-Sleep -Seconds 10
            $headers = @{ Authorization = "Bearer $(Get-WorkIQBearerToken)" }
            $s = Invoke-WebRequest -Uri $statusUri -Headers $headers -SkipHttpErrorCheck -TimeoutSec 60
            $code = [int]$s.StatusCode
            $info = $null
            if ($s.Content) { try { $info = $s.Content | ConvertFrom-Json -Depth 20 } catch { $info = $null } }
            $status = if ($info -and $info.PSObject.Properties['status']) { $info.status } else { $null }
            $statusText = if ($info -and $info.PSObject.Properties['status_text']) { $info.status_text } else { '' }
            $complete = if ($info -and $info.PSObject.Properties['complete']) { [bool]$info.complete } else { $false }
            Write-Verbose "Deployment status HTTP $code status=$status $statusText"
            if ($code -eq 200 -and ($status -eq 4 -or "$status" -eq 'Success' -or ($complete -and $status -ne 3))) { break }
            if ($status -eq 3 -or "$status" -eq 'Failed' -or ($code -ge 400 -and $code -ne 404)) {
                throw "Deployment to $Name failed (HTTP $code, status $status). $statusText Check https://$scmHost/api/deployments/$deploymentId/log"
            }
            if ((Get-Date) -gt $deadline) { throw "Timed out after $DeployTimeoutSeconds seconds waiting for the deployment to $Name." }
        }
    }
    finally {
        if (Test-Path $zipPath) { Remove-Item $zipPath -Force -ErrorAction SilentlyContinue }
    }

    # -- 6. health probe ----------------------------------------------------------
    $healthUri = "https://$hostName/healthz"
    $deadline = (Get-Date).AddSeconds(300)
    while ($true) {
        try {
            $h = Invoke-WebRequest -Uri $healthUri -SkipHttpErrorCheck -TimeoutSec 60
            if ([int]$h.StatusCode -eq 200) { break }
            $last = "HTTP $([int]$h.StatusCode)"
        }
        catch { $last = $_.Exception.Message }
        if ((Get-Date) -gt $deadline) { throw "Health probe $healthUri did not return 200 within 5 minutes (last: $last)." }
        Start-Sleep -Seconds 10
    }

    [pscustomobject]@{
        McpEndpoint     = "https://$hostName/mcp"
        ViewerUrl       = "https://$hostName/viewer"
        FunctionAppName = $Name
    }
}
