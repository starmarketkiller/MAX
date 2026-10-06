<#
.SYNOPSIS
    LOCAL_INFERENCE_CONNECTIVITY_V1 - registra start_local_inference.ps1 come
    Scheduled Task eseguito al logon dell'utente corrente, finestra nascosta.

.DESCRIPTION
    Esegui questo script UNA VOLTA (richiede una PowerShell con permessi
    utente normali, nessun amministratore necessario per un task scope
    utente). Da quel momento, ad ogni logon Windows avvia automaticamente
    Gateway + tunnel (Ollama e' gia' autostart via Startup\Ollama.lnk) senza
    aprire alcuna finestra visibile.

    Per rimuovere: Unregister-ScheduledTask -TaskName "NEXUS Local Inference" -Confirm:$false
#>
$ErrorActionPreference = "Stop"
$TaskName = "NEXUS Local Inference"
$ScriptPath = Join-Path $PSScriptRoot "start_local_inference.ps1"

$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument `
    "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$ScriptPath`""
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Settings = New-ScheduledTaskSettingsSet -Hidden -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Write-Host "Task '$TaskName' gia' registrato - lo aggiorno."
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings `
    -Description "Avvia Local Inference Gateway + tunnel Cloudflare per Mistral via Telegram (LOCAL_INFERENCE_CONNECTIVITY_V1)." | Out-Null

Write-Host "Registrato: '$TaskName' - si avviera' automaticamente al prossimo logon."
Write-Host "Per testarlo subito senza rifare il logon: Start-ScheduledTask -TaskName `"$TaskName`""
