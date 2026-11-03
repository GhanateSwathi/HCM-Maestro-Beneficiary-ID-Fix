<#
.SYNOPSIS
    Runs Maestro flows in this project on the test phone.

.EXAMPLE
    .\scripts\run.ps1 -Flow flows\setup\cdd-sign-in.yaml
    .\scripts\run.ps1 -Flow flows\retest
    .\scripts\run.ps1 -Tags phase-a
#>
[CmdletBinding()]
param(
    [string[]] $Flow,
    [string]   $Tags,
    [string]   $ExcludeTags,
    # adb serial; defaults to DEVICE_ID in .env.
    [string]   $Device,
    # KEY=VALUE pairs that replace .env's for this run only.
    [string[]] $Set,
    # Where the run's report, screenshots and logs go; defaults to
    # artifacts\runs\<yyyyMMdd-HHmmss>. run-case.ps1 picks its own.
    [string]   $RunDir
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

# The Maestro CLI hard-fails on Java 11, which is this machine's default.
# Pin 17 for this process only so Maven/Playwright keep running on 11.
$jdk17 = 'C:\Program Files\Amazon Corretto\jdk17.0.20_10'
if (Test-Path $jdk17) {
    $env:JAVA_HOME = $jdk17
} else {
    Write-Warning "Corretto 17 not found at $jdk17 - Maestro needs Java 17 or higher."
}

# Both banners print to stdout and are noise in CI logs.
$env:MAESTRO_CLI_NO_ANALYTICS = '1'
$env:MAESTRO_CLI_ANALYSIS_NOTIFICATION_DISABLED = 'true'

# A fresh emulator installs Maestro's driver on the first run, which took
# longer than Maestro's default wait on 2026-11-02 ("Android driver did not
# start up in time").
if (-not $env:MAESTRO_DRIVER_STARTUP_TIMEOUT) { $env:MAESTRO_DRIVER_STARTUP_TIMEOUT = '180000' }

$maestro = Join-Path $env:USERPROFILE '.maestro\bin\maestro.bat'
if (-not (Test-Path $maestro)) {
    throw "Maestro CLI not found at $maestro. Install it from https://docs.maestro.dev."
}

$envFile = Join-Path $root '.env'
if (-not (Test-Path $envFile)) {
    throw "Missing $envFile. Copy .env.example to .env and fill in the values."
}

$cliArgs = @('test')

# -Set replaces any .env entry with the same key.
$overrides = @()
if ($Set) { $overrides += $Set }
$overrideKeys = @($overrides | ForEach-Object { ($_ -split '=', 2)[0].Trim() })
foreach ($line in Get-Content $envFile) {
    $entry = $line.Trim()
    if ($entry -eq '' -or $entry.StartsWith('#')) { continue }
    $key = ($entry -split '=', 2)[0].Trim()
    if ($key -eq 'DEVICE_ID' -and -not $Device) { $Device = ($entry -split '=', 2)[1].Trim() }
    if ($overrideKeys -contains $key) { continue }
    $cliArgs += '-e'
    $cliArgs += $entry
}
foreach ($entry in $overrides) {
    $cliArgs += '-e'
    $cliArgs += $entry
}

if ($Device)      { $cliArgs += '--device';        $cliArgs += $Device }
if ($Tags)        { $cliArgs += '--include-tags';  $cliArgs += $Tags }
if ($ExcludeTags) { $cliArgs += '--exclude-tags';  $cliArgs += $ExcludeTags }

# Each run gets its own folder: an HTML report of every flow's result, plus
# each flow's screenshots, logs and view hierarchies. Without
# --test-output-dir Maestro 2.10 writes screenshots under ~/.maestro/tests/,
# not the working directory.
# Not HTML-DETAILED: it lists every step as executed, and the password step
# then shows the password in clear text.
if (-not $RunDir) { $RunDir = Join-Path $root ('artifacts\runs\' + (Get-Date -Format 'yyyyMMdd-HHmmss')) }
$cliArgs += '--test-output-dir'; $cliArgs += $RunDir
$cliArgs += '--format';          $cliArgs += 'HTML'
$cliArgs += '--output';          $cliArgs += (Join-Path $RunDir 'report.html')

# Target the workspace root rather than flows/ so config.yaml governs discovery.
# Maestro does not recurse into subdirectories on its own, and the flows are
# grouped into section subfolders - passing 'flows' here would find none.
if ($Flow) { $cliArgs += $Flow } else { $cliArgs += '.' }

# The test phone turns its screen off after 30 s, and Maestro then sees only
# the lock screen: on 2026-10-30 18:20 the first sign-in waited 60 s on a
# black "35% Charging" screen. Keep the screen on while it is plugged in
# (7 = AC, USB and wireless) for this run only - the phone's own setting is
# put back at the end - and wake it. The test phone has a PIN/pattern lock
# (secure keyguard, 2026-10-30), which adb cannot lift: a phone still locked
# after waking waits up to 10 minutes for someone to unlock it, then stops
# the run. With Developer options > Stay awake on, it stays unlocked between
# runs.
$adbArgs = if ($Device) { @('-s', $Device) } else { @() }
$stayOnBefore = "$(adb @adbArgs shell settings get global stay_on_while_plugged_in)".Trim()
if ($stayOnBefore -notmatch '^\d+$') { $stayOnBefore = '0' }
adb @adbArgs shell settings put global stay_on_while_plugged_in 7 | Out-Null
adb @adbArgs shell input keyevent KEYCODE_WAKEUP | Out-Null
adb @adbArgs shell wm dismiss-keyguard | Out-Null
Start-Sleep -Seconds 1
$lockedSince = Get-Date
while (adb @adbArgs shell dumpsys window | Select-String -SimpleMatch 'isKeyguardShowing=true') {
    if (((Get-Date) - $lockedSince).TotalMinutes -ge 10) {
        adb @adbArgs shell settings put global stay_on_while_plugged_in $stayOnBefore | Out-Null
        throw "The phone stayed locked for 10 minutes. Unlock it and run again."
    }
    Write-Host "Waiting for the phone to be unlocked..."
    adb @adbArgs shell input keyevent KEYCODE_WAKEUP | Out-Null
    Start-Sleep -Seconds 5
}

# Keep the PC awake and its display on while Maestro runs: on 2026-10-27 the
# PC went to sleep at 19:51 (5 minutes idle on the charger, 3 on battery) and
# froze a chained flow for 15 hours. Released when the run ends.
if (-not ('HcmRun.Power' -as [type])) {
    Add-Type -Namespace HcmRun -Name Power -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint flags);'
}
# 0x80000003 = ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED; the
# call answers the state before, restored at the end.
$awakeBefore = [HcmRun.Power]::SetThreadExecutionState([uint32]2147483651)

Push-Location $root
try {
    & $maestro @cliArgs
    $code = $LASTEXITCODE
    Write-Host "Report, screenshots and logs: $RunDir"
    exit $code
} finally {
    adb @adbArgs shell settings put global stay_on_while_plugged_in $stayOnBefore | Out-Null
    if ($awakeBefore) { [HcmRun.Power]::SetThreadExecutionState($awakeBefore) | Out-Null }
    Pop-Location
}
