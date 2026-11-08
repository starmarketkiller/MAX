# T04 prepared rollback. Running this file without -Confirm changes nothing.
# It does not stop Ollama, metatester64, or a gateway, and it does not read tokens.
param([switch]$Confirm)

$ErrorActionPreference = "Stop"
$TaskName = "NEXUS Local Inference"

if (-not $Confirm) {
    Write-Host "Rollback non applicato: manca -Confirm. Nessun task, processo o variabile e' stato modificato."
    exit 2
}

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Rimosso lo scheduled task '$TaskName'."
} else {
    Write-Host "Nessuno scheduled task '$TaskName' da rimuovere."
}

Write-Host "Render e i processi locali non sono stati modificati da questo rollback."
exit 0
