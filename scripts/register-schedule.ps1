# Registers a Windows Scheduled Task that runs scripts\update.ps1.
# Default: daily at 09:00 (a new export is picked up within a day; the checksum
# guard makes extra runs harmless).
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\register-schedule.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\register-schedule.ps1 -Time "07:30"
#   powershell -ExecutionPolicy Bypass -File scripts\register-schedule.ps1 -Remove

param(
    [string]$TaskName = "KeralaRERA-Update",
    [string]$Time = "09:00",
    [switch]$Remove
)

$ErrorActionPreference = "Stop"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "Removed scheduled task '$TaskName' (if it existed)."
    exit 0
}

$repo = Split-Path -Parent $PSScriptRoot
$script = Join-Path $repo "scripts\update.ps1"

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$script`""
$trigger = New-ScheduledTaskTrigger -Daily -At $Time
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Ingest the newest K-RERA export placed in data/raw/manual (skips if unchanged)." `
    -Force | Out-Null

Write-Output "Registered scheduled task '$TaskName' -> daily at $Time -> $script"
