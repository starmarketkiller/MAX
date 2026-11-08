# LOCAL_OPERABILITY_FIX_01 rollback.
# Without -Confirm this file changes nothing.
# With -Confirm it stops only a pid file that still points at the probe gateway.
# It does not stop metatester64, Ollama, a scheduled task, a tunnel, or Render.
param(
    [switch]$Confirm,
    [string]$PidFile
)

$ErrorActionPreference = "Stop"

if (-not $Confirm) {
    Write-Host "Rollback non applicato: manca -Confirm. Nessun processo o servizio e' stato modificato."
    exit 2
}

if (-not $PidFile -or -not (Test-Path $PidFile)) {
    Write-Host "Nessun pid file della prova. Nessun processo e' stato arrestato."
    exit 0
}

$probePid = [int](Get-Content $PidFile -Raw).Trim()
$proc = Get-CimInstance Win32_Process -Filter "ProcessId=$probePid" -ErrorAction SilentlyContinue
if (-not $proc) {
    Write-Host "Il pid $probePid non e' piu' attivo."
    exit 0
}
$command = [string]$proc.CommandLine
if ($command -notlike "*nexus_local_inference_gateway.py*") {
    Write-Host "Il pid $probePid non e' il gateway della prova. Non viene arrestato."
    exit 3
}
Stop-Process -Id $probePid -Force
Write-Host "Arrestato solo il gateway della prova, pid $probePid."
exit 0
