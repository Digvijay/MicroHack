# Local-only wrapper to run deploy-lab.ps1 outside the MicroHack platform.
# It supplies stand-ins for the platform helpers (Get-MhhStableHash,
# New-MhhStablePassword, Get-MhhLabUser, Update-MhhToken), pre-creates the
# resource group, passes the signed-in user's Entra object ID, runs deploy-lab.ps1
# and prints the credentials it returns.
# Not part of the hack deliverable. For local end-to-end verification only.
#
# Prerequisites: Connect-AzAccount (Az PowerShell) and az login (Azure CLI) to the
# test subscription, Az.Accounts and Az.Resources installed.

param(
    # Defaults to the current Az context subscription.
    [string]$SubscriptionId = ((Get-AzContext -ErrorAction SilentlyContinue).Subscription.Id),
    [string]$ResourceGroupName = "rg-iq-lab-local",
    [string]$Location = "swedencentral",
    [string[]]$PreferredLocation = @("swedencentral", "francecentral", "switzerlandnorth"),
    # Defaults to the signed-in user's Entra object ID (resolved below).
    [string[]]$AllowedEntraUserIds = @(),
    [ValidateSet('F2','F4','F8','F16','F32','F64')]
    [string]$FabricSkuName = "F2",
    # Print secret values (keys, connection strings). Masked by default.
    [switch]$ShowSecrets
)

$ErrorActionPreference = "Stop"

if (-not $SubscriptionId) {
    throw "No subscription in context. Run Connect-AzAccount first, or pass -SubscriptionId."
}

# Decode the claims of the current ARM access token. Used as a fallback when
# Get-AzADUser cannot reach Microsoft Graph (for example with an access-token login).
function Get-LocalTokenClaims {
    $tok = Get-AzAccessToken -ResourceUrl "https://management.azure.com/" -ErrorAction Stop
    $raw = $tok.Token
    if ($raw -is [System.Security.SecureString]) {
        $raw = [System.Net.NetworkCredential]::new('', $raw).Password
    }
    $payload = $raw.Split('.')[1].Replace('-', '+').Replace('_', '/')
    switch ($payload.Length % 4) { 2 { $payload += '==' } 3 { $payload += '=' } }
    return ([System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($payload)) | ConvertFrom-Json)
}

$claims = $null
try { $claims = Get-LocalTokenClaims } catch { Write-Host "[WARN]  Could not decode the access token: $_" }

if ($AllowedEntraUserIds.Count -eq 0) {
    $signedInId = $null
    try { $signedInId = (Get-AzADUser -SignedIn -ErrorAction Stop).Id } catch { }
    if (-not $signedInId -and $claims) { $signedInId = $claims.oid }
    if (-not $signedInId) {
        throw "Could not resolve your Entra object ID. Pass -AllowedEntraUserIds <object-id> explicitly."
    }
    $AllowedEntraUserIds = @($signedInId)
}
Write-Host "[INFO]  Attendee object ID(s): $($AllowedEntraUserIds -join ', ')"

# ---------------------------------------------------------------------------
# Stand-ins for the platform helpers. Simplified, but with the same parameters.
# ---------------------------------------------------------------------------
function Get-MhhStableHash {
    param(
        [Parameter(Mandatory = $true, Position = 0, ValueFromPipeline = $true)][string[]]$Value,
        [ValidateRange(12, 64)][int]$Length = 24
    )
    begin { $all = @() }
    process { $all += $Value }
    end {
        # Order and casing do not matter, like the platform version.
        $joined = (($all | ForEach-Object { $_.ToLowerInvariant() }) | Sort-Object) -join '|'
        $sha = [System.Security.Cryptography.SHA256]::Create()
        try { $bytes = $sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($joined)) } finally { $sha.Dispose() }
        $hex = -join ($bytes | ForEach-Object { $_.ToString('x2') })
        return $hex.Substring(0, $Length)
    }
}

function New-MhhStablePassword {
    param(
        [Parameter(Position = 0)][string]$Purpose = 'default',
        [ValidateRange(16, 128)][int]$Length = 16,
        [string]$SubscriptionId = $script:SubscriptionId,
        [string]$ResourceGroupName = $script:ResourceGroupName,
        [string]$Secret = $(if ($env:MHH_LOCAL_SECRET) { $env:MHH_LOCAL_SECRET } else { 'microhack-local-dev' }),
        [switch]$AsSecureString
    )
    $alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
    $hmac = [System.Security.Cryptography.HMACSHA256]::new([System.Text.Encoding]::UTF8.GetBytes($Secret))
    try {
        $chars = New-Object System.Collections.Generic.List[char]
        $counter = 0
        while ($chars.Count -lt $Length) {
            $block = $hmac.ComputeHash([System.Text.Encoding]::UTF8.GetBytes("$SubscriptionId|$ResourceGroupName|$Purpose|$Length|$counter"))
            foreach ($b in $block) { if ($chars.Count -lt $Length) { $chars.Add($alphabet[$b % $alphabet.Length]) } }
            $counter++
        }
    } finally { $hmac.Dispose() }
    # Guarantee one lowercase, one uppercase and one digit, like the platform version.
    $chars[0] = $alphabet[26 + ([int]$chars[0] % 26)]
    $chars[1] = $alphabet[([int]$chars[1] % 26)]
    $chars[2] = $alphabet[52 + ([int]$chars[2] % 10)]
    $pw = -join $chars
    if ($AsSecureString) { return (ConvertTo-SecureString $pw -AsPlainText -Force) }
    return $pw
}

function Get-MhhLabUser {
    [CmdletBinding()]
    param([Parameter(Mandatory = $true, ValueFromPipeline = $true)][Alias('ObjectId', 'Id')][string[]]$UserId)
    process {
        foreach ($id in $UserId) {
            $upn = $null
            if ($claims -and $claims.oid -eq $id) {
                $upn = if ($claims.upn) { $claims.upn } elseif ($claims.unique_name) { $claims.unique_name } else { (Get-AzContext).Account.Id }
            }
            if (-not $upn) {
                try { $upn = (Get-AzADUser -ObjectId $id -ErrorAction Stop).UserPrincipalName } catch { }
            }
            if (-not $upn) { throw "Could not resolve user '$id' to a UPN." }
            [pscustomobject]@{ Id = $id; UserPrincipalName = $upn; ShortName = $upn.Split('@')[0].ToLower() }
        }
    }
}

function Update-MhhToken {
    # Locally the credential is whatever you logged in with; nothing to refresh.
    return @{ Mode = 'Local'; Rotated = $false; Refreshed = @(); Skipped = @('AzPowerShell', 'AzureCli') }
}

# ---------------------------------------------------------------------------
# Pre-create the resource group (the platform does this for 'resourcegroup').
# ---------------------------------------------------------------------------
if (-not (Get-AzResourceGroup -Name $ResourceGroupName -ErrorAction SilentlyContinue)) {
    Write-Host "[INFO]  Creating resource group '$ResourceGroupName' in '$Location'..."
    New-AzResourceGroup -Name $ResourceGroupName -Location $Location | Out-Null
    Write-Host "[OK]    Resource group created."
} else {
    Write-Host "[OK]    Resource group '$ResourceGroupName' already exists."
}

$started = Get-Date
$output = & "$PSScriptRoot\deploy-lab.ps1" `
    -DeploymentType 'resourcegroup' `
    -SubscriptionId $SubscriptionId `
    -ResourceGroupName $ResourceGroupName `
    -PreferredLocation $PreferredLocation `
    -AllowedEntraUserIds $AllowedEntraUserIds `
    -FabricSkuName $FabricSkuName

$creds = @($output | Where-Object { $_ -is [hashtable] -and $_.ContainsKey('HackboxCredential') } | ForEach-Object { $_.HackboxCredential })
Write-Host ""
Write-Host "==== Credentials returned to the dashboard ($($creds.Count)) ===="
foreach ($c in $creds) {
    $isSecret = $c.name -match 'Key|ConnectionString'
    $shown = if ($isSecret -and -not $ShowSecrets) { "<hidden, $($c.value.Length) chars>" } else { $c.value }
    Write-Host ("{0,-36} {1}" -f $c.name, $shown)
}
Write-Host ("Duration: {0:n1} minutes" -f ((Get-Date) - $started).TotalMinutes)
