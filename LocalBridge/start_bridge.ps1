<#
.SYNOPSIS
    Avvio semplice del NEXUS Local Agent Bridge V1 client su Windows.

.DESCRIPTION
    1. Carica LocalBridge\.env se presente (copialo da .env.example).
    2. Esegue --diagnose (solo lettura: nessun job viene reclamato).
    3. Se la diagnosi passa, avvia il client in polling outbound-only.
    Ctrl+C ferma il client in modo controllato (invia un ultimo heartbeat
    DEGRADED, nessuna chiusura brusca).
#>

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$EnvFile = Join-Path $PSScriptRoot ".env"

if (Test-Path $EnvFile) {
    Write-Host "Carico configurazione da $EnvFile"
    Get-Content $EnvFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
            $key, $value = $line.Split("=", 2)
            [System.Environment]::SetEnvironmentVariable($key.Trim(), $value.Trim(), "Process")
        }
    }
} else {
    Write-Host "Nessun $EnvFile trovato - uso le variabili d'ambiente gia' impostate nella sessione."
    Write-Host "Per creare una configurazione persistente: copia .env.example in .env e compilalo."
}

if (-not $env:NEXUS_REPO_ROOT) {
    $env:NEXUS_REPO_ROOT = $RepoRoot
}

Write-Host ""
Write-Host "=== Diagnosi (nessun job verra' reclamato) ==="
python (Join-Path $PSScriptRoot "nexus_agent_bridge.py") --diagnose
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Diagnosi fallita - correggi i punti sopra segnati FAIL prima di avviare il bridge." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== Avvio bridge (Ctrl+C per fermarlo in modo controllato) ==="
python (Join-Path $PSScriptRoot "nexus_agent_bridge.py")
