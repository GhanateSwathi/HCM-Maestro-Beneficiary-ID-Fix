<#
.SYNOPSIS
    Runs one test-plan case on the phone with the plan's log check around it,
    then records its PASS / FAIL / BLOCKED and ID ledger rows in the report.

.DESCRIPTION
    The case's flow comes from scripts\cases.csv: one file, or a case folder
    whose files run as one Maestro run each, in name order. On the test
    phone every Maestro run ends after 5-7 minutes whatever it does (P1 at
    5m18s and 5m57s, a read-only loop at 6m58s, 2026-10-30), so a longer
    case runs in parts. The app stays where a part leaves it - only the
    first part launches it - and each part's "VAR|NAME|VALUE" lines are
    passed to the parts after it as -e NAME=VALUE.

    The phone's log is recorded
    for the whole run (the plan's "adb logcat -c" before, "logcat -d" after)
    into <run>\<case>.log; its UPDATE_IDENTIFIER_STATUS lines go to
    <run>\<case>-id-status.log and their "reallocated" count is checked
    against cases.csv by scripts\report.py, which then rebuilds
    artifacts\report\ (results.xlsx, report.html) and TEST-CASES.md.

.EXAMPLE
    .\scripts\run-case.ps1 -Case P1
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string] $Case,
    [string] $Device,
    # The second device, for the parts named "...@2.yaml" (X9, D5); defaults
    # to DEVICE_ID_2 in .env.
    [string] $Device2,
    # Carry on a run that stopped: its folder (artifacts\runs\<...>-<case>)
    # and the first part to run again (e.g. 3-checks). The VARs of the parts
    # before it are read from that folder, and the result is recorded for
    # the whole run.
    [string] $Resume,
    [string] $From
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

$row = Import-Csv (Join-Path $PSScriptRoot 'cases.csv') | Where-Object Case -eq $Case
if (-not $row) { throw "Unknown case $Case - see scripts\cases.csv." }
if (-not $row.Flow) { throw "Case $Case has no flow yet (scripts\cases.csv)." }

$envMap = @{}
foreach ($line in Get-Content (Join-Path $root '.env')) {
    if ($line -match '^\s*([^#=]+?)\s*=\s*(.*)$') { $envMap[$Matches[1]] = $Matches[2].Trim() }
}
if (-not $Device) { $Device = $envMap['DEVICE_ID'] }
if (-not $Device) { throw "No device: pass -Device or set DEVICE_ID in .env." }

if ($Resume) {
    $runDir = (Resolve-Path $Resume).Path
    if (-not $From) { throw "-Resume needs -From <part>, the first part to run again." }
    # Each stretch of the run keeps its own device log; the log check reads them all.
    $log = Join-Path $runDir ('{0}.resume-{1}.log' -f $Case, (Get-Date -Format 'HHmmss'))
} else {
    $runDir = Join-Path $root ('artifacts\runs\{0}-{1}' -f (Get-Date -Format 'yyyyMMdd-HHmmss'), $Case)
    New-Item -ItemType Directory -Force $runDir | Out-Null
    $log = Join-Path $runDir "$Case.log"
}

$target = Join-Path $root $row.Flow
$parts = if (Test-Path $target -PathType Container) {
    @(Get-ChildItem $target -Filter *.yaml | Sort-Object Name)
} else { @(Get-Item $target) }

# Two-device cases (X9, D5): a part named "...@2.yaml" runs on the second
# device. Every part is told which device it runs on (DEVICE_ID), so the IDs
# it records in the ledger name their device.
$devices = @($Device)
if ($parts | Where-Object BaseName -match '@2$') {
    if (-not $Device2) { $Device2 = $envMap['DEVICE_ID_2'] }
    if (-not $Device2) { throw "Case $Case has parts for a second device: pass -Device2 or set DEVICE_ID_2 in .env." }
    $devices += $Device2
}

# The test phone (vivo, Android 13) logs at Error level only (log.tag=E): the
# app's own lines, Info level under the "flutter" tag, are dropped unless the
# tag is raised. Lasts until the phone restarts.
#
# Log check, before the case: clear the log, then record it for the whole run
# - a dump at the end could miss early lines once the ring buffer wraps. The
# second device's log goes to <case>.device2.log beside it.
$logcats = @()
foreach ($d in $devices) {
    adb -s $d shell setprop log.tag.flutter V | Out-Null
    adb -s $d logcat -c | Out-Null
    $out = if ($d -eq $Device) { $log } else { $log -replace '\.log$', '.device2.log' }
    $logcats += Start-Process -FilePath 'adb' -ArgumentList '-s', $d, 'logcat', '-v', 'time' `
        -RedirectStandardOutput $out -NoNewWindow -PassThru
}
$vars = [ordered]@{}
$code = 0

# A part Maestro lost - it stopped with no failed check: no maestro.log at
# all (the driver never started), a connection error, or a log that just
# ends. On the emulator (2026-11-02) adb drops the device for a moment
# whenever a Maestro session starts (offline -> authorizing -> device in
# "adb track-devices"), which killed runs 3-6 s in. Such a part is run
# again, up to twice: every part starts by waiting for the screen the
# previous one left, so a retry after the app has moved on stops there
# instead of registering anyone twice.
function Test-PartLost([string] $dir) {
    $logs = @(Get-ChildItem $dir -Recurse -Filter maestro.log -ErrorAction SilentlyContinue)
    if (-not $logs) { return $true }
    $text = ($logs | Get-Content -Raw) -join "`n"
    if ($text -match 'Assertion is false|Element not found') { return $false }
    return ($text -match 'DeviceServerDiedException|device offline|did not start up in time|StatusRuntimeException: UNAVAILABLE') -or
           ($text -notmatch 'onCommandFinished: .* FAILED')
}

try {
    foreach ($part in $parts) {
        $set = @($vars.GetEnumerator() | ForEach-Object { '{0}={1}' -f $_.Key, $_.Value })
        $partDir = Join-Path $runDir $part.BaseName
        if ($Resume -and $part.BaseName -lt $From) {
            # Already run: only its VARs are needed.
            foreach ($hit in Get-ChildItem $partDir -Recurse -Filter maestro.log -ErrorAction SilentlyContinue | Select-String -Pattern 'JsConsole: VAR\|([^|]+)\|(.*)$') {
                $vars[$hit.Matches[0].Groups[1].Value] = $hit.Matches[0].Groups[2].Value.Trim()
            }
            continue
        }
        if ($Resume -and (Test-Path $partDir)) {
            # The stopped run's attempt at this part: kept like a lost attempt.
            Rename-Item $partDir ('{0}.lost-resume-{1}' -f $part.BaseName, (Get-Date -Format 'HHmmss'))
        }
        $partDevice = if ($part.BaseName -match '@2$') { $Device2 } else { $Device }
        for ($attempt = 1; ; $attempt++) {
            Write-Host "Part $($part.BaseName) on $partDevice$(if ($attempt -gt 1) { " (attempt $attempt)" })$(if ($set) { ' with ' + ($set -join ', ') })"
            & (Join-Path $PSScriptRoot 'run.ps1') -Flow $part.FullName -Device $partDevice -RunDir $partDir -Set ($set + "DEVICE_ID=$partDevice")
            $code = $LASTEXITCODE
            if ($code -eq 0 -or $attempt -ge 3 -or -not (Test-PartLost $partDir)) { break }
            Write-Host "Maestro lost the device during part $($part.BaseName) - running it again."
            Rename-Item $partDir ('{0}.lost-{1}' -f $part.BaseName, $attempt)
            adb -s $partDevice wait-for-device | Out-Null
            Start-Sleep -Seconds 5
        }
        foreach ($hit in Get-ChildItem $partDir -Recurse -Filter maestro.log | Select-String -Pattern 'JsConsole: VAR\|([^|]+)\|(.*)$') {
            $vars[$hit.Matches[0].Groups[1].Value] = $hit.Matches[0].Groups[2].Value.Trim()
        }
        if ($code -ne 0) { break }
    }
} finally {
    Start-Sleep -Seconds 2
    foreach ($l in $logcats) { if (-not $l.HasExited) { Stop-Process -Id $l.Id -Force } }
}

# Log check, after the case - over every stretch of a resumed run.
$logs = @(Get-ChildItem $runDir -Filter "$Case*.log" | Where-Object Name -notmatch '-id-status\.log$' | ForEach-Object FullName)
# Sign-in logs the app's form config, whose actions include
#   "actionType": "UPDATE_IDENTIFIER_STATUS",
# (6 such lines in D6's log, 2026-11-02 13:12) - the config naming the
# action, not the app running it. Those are left out.
$idLines = @(Select-String -Path $logs -SimpleMatch 'UPDATE_IDENTIFIER_STATUS' -ErrorAction SilentlyContinue |
    Where-Object { $_.Line -notmatch '"actionType"\s*:' })
$idLines | ForEach-Object Line | Set-Content -Path (Join-Path $runDir "$Case-id-status.log") -Encoding utf8
$reallocated = @($idLines | Where-Object { $_.Line -match 'reallocat' }).Count
Write-Host ("Log check: {0} UPDATE_IDENTIFIER_STATUS line(s), {1} reallocated" -f $idLines.Count, $reallocated)

# The ID each form carried at Submit. The app logs it as
#   CONDITION_EVAL: navigation={nameOfIndividual: QAID-P1-A, UNIQUE_BENEFICIARY_ID: 082318772072, ...}
# (read off the P1 run of 2026-10-30 18:56): the search text and the ID the
# search screen pre-loaded. A second person offered the first one's ID is the
# stale-screen bug; report.py compares it with the ID each was saved with.
$offered = [ordered]@{}
foreach ($hit in Select-String -Path $logs -Pattern 'CONDITION_EVAL: navigation=\{nameOfIndividual: ([^,]+), UNIQUE_BENEFICIARY_ID: (\w+)') {
    $name = $hit.Matches[0].Groups[1].Value.Trim()
    if (-not $offered.Contains($name)) { $offered[$name] = $hit.Matches[0].Groups[2].Value }
}
$offeredArg = ($offered.GetEnumerator() | ForEach-Object { '{0}={1}' -f $_.Key, $_.Value }) -join ';'
if ($offeredArg) { Write-Host "Offered at Submit: $offeredArg" }

python (Join-Path $PSScriptRoot 'report.py') record --case $Case --run-dir $runDir --exit-code $code `
    --reallocated $reallocated --id-lines $idLines.Count "--offered=$offeredArg" `
    --phone $Device --user $envMap['HCM_CDD_USER_ID']

# A second case run inside this one (X2 inside X1) logs its lines tagged
# "X2:CHECK|..."; it is recorded as its own case from the same run.
$tags = @(Get-ChildItem $runDir -Recurse -Filter maestro.log |
    Select-String -Pattern 'JsConsole: ([A-Za-z0-9]+):(CHECK|NOTE|BLOCKED)\|' |
    ForEach-Object { $_.Matches[0].Groups[1].Value } | Where-Object { $_ -ne $Case } | Sort-Object -Unique)
foreach ($tag in $tags) {
    python (Join-Path $PSScriptRoot 'report.py') record --case $tag --tag $tag --run-dir $runDir --exit-code $code `
        --reallocated 0 --id-lines 0 --phone $Device --user $envMap['HCM_CDD_USER_ID']
}
exit $code
