# Ingests the newest official K-RERA export placed in data/raw/manual/.
# Safe to run repeatedly: `rera update` skips when the source is unchanged.
#
# Usage:  powershell -ExecutionPolicy Bypass -File scripts\update.ps1

$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot   # scripts\ -> repository root
Set-Location -LiteralPath $repo

$logDir = Join-Path $repo "data\logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir "update.log"

function Write-Log([string]$message) {
    $stamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssK"
    Add-Content -Path $log -Value ("[{0}] {1}" -f $stamp, $message)
}

$rera = Join-Path $repo ".venv\Scripts\rera.exe"
if (-not (Test-Path $rera)) {
    Write-Log "ERROR: rera.exe not found at $rera. Create the venv and install deps: pip install -e .[postgres,api]"
    exit 1
}

Write-Log "update started"
try {
    $output = & $rera update 2>&1 | Out-String
    Add-Content -Path $log -Value $output.TrimEnd()
    $code = $LASTEXITCODE
    Write-Log "update finished (exit $code)"
    exit $code
}
catch {
    Write-Log ("ERROR: {0}" -f $_)
    exit 1
}
