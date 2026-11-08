<#
.SYNOPSIS
    Avvio del NEXUS Local Inference Gateway V1 su Windows.

.DESCRIPTION
    1. Carica LocalBridge\.env se presente (serve NEXUS_LOCAL_INFERENCE_GATEWAY_TOKEN).
    2. Verifica che Ollama locale sia raggiungibile (solo lettura).
    3. Avvia il gateway, bindato esclusivamente a 127.0.0.1 - va esposto
       all'esterno SOLO tramite un tunnel autenticato (Cloudflare Tunnel /
       Tailscale Funnel), mai direttamente.
    Ctrl+C ferma il processo.
#>

$ErrorActionPreference = "Stop"
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
}

if (-not $env:NEXUS_LOCAL_INFERENCE_GATEWAY_TOKEN -or $env:NEXUS_LOCAL_INFERENCE_GATEWAY_TOKEN.Length -lt 32) {
    Write-Host "NEXUS_LOCAL_INFERENCE_GATEWAY_TOKEN mancante o troppo corto (minimo 32 caratteri)." -ForegroundColor Red
    exit 1
}

$port = 8765
if ($env:NEXUS_LOCAL_INFERENCE_GATEWAY_PORT) {
    $port = [int]$env:NEXUS_LOCAL_INFERENCE_GATEWAY_PORT
}

python (Join-Path $PSScriptRoot "gateway_process.py") --port $port
if ($LASTEXITCODE -eq 0) {
    Write-Host "Gateway gia' in ascolto su 127.0.0.1:${port}. Nessun secondo processo."
    exit 0
}
if ($LASTEXITCODE -ne 4) {
    Write-Host "La porta $port non identifica questo gateway. Avvio non eseguito."
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "=== Avvio gateway (bind 127.0.0.1 - mai esporre direttamente) ==="
python (Join-Path $PSScriptRoot "nexus_local_inference_gateway.py")
