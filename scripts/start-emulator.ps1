<#
.SYNOPSIS
    Starts one of the project's emulators the way the cases need it and
    waits until it can reach UAT.

.DESCRIPTION
    Two emulators, identical but for their name, for the cases that need two
    devices (X9, D5):
      HCM_Beneficiary_ID    -Port 5554  -> emulator-5554  (DEVICE_ID)
      HCM_Beneficiary_ID_2  -Port 5556  -> emulator-5556  (DEVICE_ID_2)
    Both get the same flags, the same device settings and the same app build.

    Each setting answers something that broke a run on 2026-11-02:
      -no-snapshot           A quick-boot snapshot restored a dead network
                             (no route, no DNS) after a restart. Cold boot
                             every time, and never save one.
      -gpu swiftshader_indirect
                             The emulator crashed (exit 139) in its host GPU
                             layer mid-run.
      -dns-server            The PC's disconnected Ethernet adapter still lists
                             DNS servers; pinned to the Wi-Fi router's, with a
                             public one behind it.
    Then, on the device: the app installed from HCM_APK (.env) if missing, a
    GPS fix (Household Location waits for one), heads-up notifications off
    (the Auto Sync banner covered the Back link) and Play Store off (its
    update of Play Services killed the app).

.EXAMPLE
    .\scripts\start-emulator.ps1
    .\scripts\start-emulator.ps1 -Avd HCM_Beneficiary_ID_2 -Port 5556
#>
[CmdletBinding()]
param(
    [string] $Avd = 'HCM_Beneficiary_ID',
    [int]    $Port = 5554,
    [string] $DnsServers = '192.168.5.1,8.8.8.8',
    [string] $UatHost = 'kaduna-central-hcm.digit.org'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$serial = "emulator-$Port"
$log = Join-Path $root ('artifacts\emulator-{0}-{1}.log' -f $Avd, (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Force (Split-Path $log) | Out-Null

$envMap = @{}
foreach ($line in Get-Content (Join-Path $root '.env')) {
    if ($line -match '^\s*([^#=]+?)\s*=\s*(.*)$') { $envMap[$Matches[1]] = $Matches[2].Trim() }
}

if (adb devices | Select-String -Pattern "^$serial\s+device") {
    Write-Host "$serial is already running - not starting it again."
} else {
    Start-Process -FilePath 'emulator' -ArgumentList '-avd', $Avd, '-port', $Port, '-no-snapshot', '-no-boot-anim',
        '-gpu', 'swiftshader_indirect', '-dns-server', $DnsServers, '-netdelay', 'none', '-netspeed', 'full' `
        -RedirectStandardOutput $log -RedirectStandardError ($log -replace '\.log$', '-err.log') -WindowStyle Minimized
    Write-Host "Starting $Avd as $serial (log: $log)..."
}

adb -s $serial wait-for-device | Out-Null
while ("$(adb -s $serial shell getprop sys.boot_completed)".Trim() -ne '1') { Start-Sleep -Seconds 3 }
Write-Host "$serial booted."

$app = $envMap['HCM_APP_ID']
if ($app -and -not (adb -s $serial shell pm list packages $app | Select-String -SimpleMatch "package:$app")) {
    $apk = $envMap['HCM_APK']
    if (-not $apk -or -not (Test-Path $apk)) { throw "$app is not installed on $serial and HCM_APK in .env does not point to the APK." }
    Write-Host "Installing $apk on $serial..."
    adb -s $serial install $apk | Out-Null
}

adb -s $serial emu geo fix 7.4388 10.5222 | Out-Null
adb -s $serial shell settings put global heads_up_notifications_enabled 0 | Out-Null
adb -s $serial shell pm disable-user --user 0 com.android.vending | Out-Null

# DNS comes up 20-40 s after boot.
for ($i = 0; $i -lt 30; $i++) {
    # The redirect runs on the device: in Windows PowerShell a 2>&1 here
    # would turn ping's "unknown host" into a terminating error.
    if ("$(adb -s $serial shell "ping -c 1 -W 2 $UatHost 2>&1")" -match '^PING') {
        Write-Host "$serial reaches $UatHost - ready."
        exit 0
    }
    Start-Sleep -Seconds 5
}
throw "$serial cannot resolve $UatHost after 2.5 minutes. Restart it with this script (it cold-boots)."
