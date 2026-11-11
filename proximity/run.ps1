<#
.SYNOPSIS
    Runs one Search by proximity flow (proximity\cases\) on the emulator.

.DESCRIPTION
    Wraps scripts\run.ps1 with the Kaduna build and boundary every proximity
    case runs against, so .env can stay set up for the beneficiary ID fix
    suite. Sign-in still comes from .env: HCM_CDD_USER_ID and
    HCM_CDD_PASSWORD must be the Kaduna CDD (dis-qa-oct29).

    Each part's report, screenshots and logs go to
    artifacts\proximity\runs\<yyyyMMdd>-<case>\<part>, e.g.
    artifacts\proximity\runs\20261106-NB6\4-register-and-nearby; a part run
    again the same day gets a -HHmmss suffix.

.EXAMPLE
    .\proximity\run.ps1 -Flow proximity\cases\NB5\1-register-and-nearby.yaml -Set 'NAME=Swathi','LAST_NAME=Ghanate'
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string] $Flow,
    # adb serial; defaults to DEVICE_ID in .env.
    [string]   $Device,
    # KEY=VALUE pairs for this run only; they win over the Kaduna values below.
    [string[]] $Set,
    [string]   $RunDir
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

# Kaduna UAT 2.2.122 (kaduna-azm-signed-db-2.2.122.apk), CDD dis-qa-oct29.
$kaduna = [ordered]@{
    HCM_APP_ID           = 'org.egov.azm.gombe'
    HEALTH_FACILITY      = 'Fangwani Health Clinic'
    REGISTRATION_VILLAGE = 'Rigan Ori'
}
$given = @($Set | Where-Object { $_ } | ForEach-Object { ($_ -split '=', 2)[0].Trim() })
$overrides = @($kaduna.Keys | Where-Object { $given -notcontains $_ } | ForEach-Object { "$_=$($kaduna[$_])" })
$overrides += @($Set | Where-Object { $_ })

# scripts\run.ps1 runs Maestro from the repo root, so hand it a full path.
$flowPath = (Resolve-Path $Flow).Path
if (-not $RunDir) {
    $case = Split-Path -Leaf (Split-Path -Parent $flowPath)
    $part = [IO.Path]::GetFileNameWithoutExtension($flowPath)
    $RunDir = Join-Path $root ('artifacts\proximity\runs\{0}-{1}\{2}' -f (Get-Date -Format 'yyyyMMdd'), $case, $part)
    if (Test-Path $RunDir) { $RunDir += '-' + (Get-Date -Format 'HHmmss') }
}

$runArgs = @{ Flow = @($flowPath); Set = $overrides; RunDir = $RunDir }
if ($Device) { $runArgs.Device = $Device }
& (Join-Path $root 'scripts\run.ps1') @runArgs
exit $LASTEXITCODE
