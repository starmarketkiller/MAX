<#
.SYNOPSIS
    LOCAL_INFERENCE_CONNECTIVITY_V1 - avvio in un solo comando dell'intera
    catena locale: Ollama (verifica, non lo avvia - gia' autostart via
    Startup\Ollama.lnk) -> Local Inference Gateway -> Cloudflare quick
    tunnel -> health check end-to-end attraverso il tunnel stesso.

.DESCRIPTION
    Pensato per essere lanciato una volta per sessione (manualmente, o
    registrato come Scheduled Task a logon - vedi register_startup_task.ps1)
    - non richiede piu' di aprire 3 PowerShell separate.

    Idempotente: se gateway/tunnel sono gia' in esecuzione su questa macchina
    non li duplica, verifica solo che siano sani.

    Non stampa mai il token reale - solo dove trovarlo (LocalBridge\.env).
    Scrive l'URL pubblico corrente in current_gateway_url.txt (gitignored,
    MAI il token) perche' un Cloudflare quick tunnel genera un hostname
    nuovo ad ogni riavvio del processo - limite noto, documentato, non
    nascosto (vedi docs/LOCAL_INFERENCE_CONNECTIVITY_V1.md).
#>
$ErrorActionPreference = "Stop"
$Here = $PSScriptRoot
$GatewayPort = 8765
$GatewayHealthUrl = "http://127.0.0.1:$GatewayPort/v1/jarvis/health"
$TunnelLog = Join-Path $Here "tunnel.log"
$GatewayLog = Join-Path $Here "gateway.log"
$UrlFile = Join-Path $Here "current_gateway_url.txt"
$CloudflaredExe = Join-Path $Here "cloudflared.exe"

function Test-OllamaReachable {
    try { Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/version" -TimeoutSec 5 | Out-Null; return $true }
    catch { return $false }
}

function Test-GatewayHealth($Url) {
    try {
        $r = Invoke-RestMethod -Uri $Url -TimeoutSec 10
        return ($r.ok -eq $true)
    } catch { return $false }
}

function Test-PortListening($Port) {
    return [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

Write-Host "=== LOCAL_INFERENCE_CONNECTIVITY_V1 ==="

# 1. Ollama - verifica, con retry (potrebbe stare ancora avviandosi subito dopo il logon).
Write-Host "[1/4] Verifica Ollama..."
$ollamaOk = $false
for ($i = 0; $i -lt 10; $i++) {
    if (Test-OllamaReachable) { $ollamaOk = $true; break }
    Start-Sleep -Seconds 3
}
if (-not $ollamaOk) {
    Write-Host "  Ollama non raggiungibile su 127.0.0.1:11434 dopo 30s. Verifica che sia installato e in esecuzione." -ForegroundColor Red
    exit 1
}
Write-Host "  Ollama OK."

# 2. Gateway - avvia solo se non gia' in esecuzione.
Write-Host "[2/4] Gateway locale..."
if (Test-PortListening $GatewayPort) {
    Write-Host "  Gia' in esecuzione su 127.0.0.1:$GatewayPort - non duplicato."
} else {
    Write-Host "  Avvio gateway (log: $GatewayLog)..."
    Start-Process -FilePath "powershell" -ArgumentList @(
        "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $Here "start_gateway.ps1")
    ) -RedirectStandardOutput $GatewayLog -RedirectStandardError "$GatewayLog.err" -WindowStyle Hidden
}
$gatewayReady = $false
for ($i = 0; $i -lt 15; $i++) {
    if (Test-GatewayHealth $GatewayHealthUrl) { $gatewayReady = $true; break }
    Start-Sleep -Seconds 2
}
if (-not $gatewayReady) {
    Write-Host "  Gateway non risponde su $GatewayHealthUrl dopo 30s - controlla $GatewayLog." -ForegroundColor Red
    exit 1
}
Write-Host "  Gateway OK (sano in locale)."

# 3. Tunnel - avvia solo se non gia' in esecuzione.
Write-Host "[3/4] Tunnel Cloudflare..."
if (-not (Test-Path $CloudflaredExe)) {
    Write-Host "  $CloudflaredExe non trovato. Scaricalo con:" -ForegroundColor Red
    Write-Host "  Invoke-WebRequest -Uri https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe -OutFile `"$CloudflaredExe`""
    exit 1
}
$cloudflaredRunning = Get-Process cloudflared -ErrorAction SilentlyContinue
if ($cloudflaredRunning) {
    Write-Host "  cloudflared gia' in esecuzione (PID $($cloudflaredRunning[0].Id)) - non duplicato."
} else {
    Remove-Item $TunnelLog -ErrorAction SilentlyContinue
    Write-Host "  Avvio tunnel (log: $TunnelLog)..."
    Start-Process -FilePath $CloudflaredExe -ArgumentList @(
        "tunnel", "--url", "http://127.0.0.1:$GatewayPort", "--logfile", $TunnelLog
    ) -WindowStyle Hidden
}
$publicUrl = $null
for ($i = 0; $i -lt 20; $i++) {
    if (Test-Path $TunnelLog) {
        $match = Select-String -Path $TunnelLog -Pattern "https://[a-z0-9-]+\.trycloudflare\.com" -ErrorAction SilentlyContinue |
                 Select-Object -Last 1
        if ($match) { $publicUrl = $match.Matches[0].Value; break }
    }
    Start-Sleep -Seconds 2
}
if (-not $publicUrl) {
    Write-Host "  URL pubblico non trovato in $TunnelLog dopo 40s." -ForegroundColor Red
    exit 1
}
Write-Host "  Tunnel OK - URL pubblico: $publicUrl"

# 4. Health check end-to-end ATTRAVERSO il tunnel (non solo in locale).
# Nota: un hostname trycloudflare.com MAI visto prima richiede qualche
# decina di secondi per diventare risolvibile via DNS (osservato ~20s su
# questa macchina per un hostname nuovo, istantaneo per uno gia' noto) -
# finestra di retry ampia apposta, non un bug se i primi tentativi falliscono.
Write-Host "[4/4] Health check end-to-end attraverso il tunnel..."
$tunnelHealthy = $false
for ($i = 0; $i -lt 20; $i++) {
    if (Test-GatewayHealth "$publicUrl/v1/jarvis/health") { $tunnelHealthy = $true; break }
    Start-Sleep -Seconds 4
}
if (-not $tunnelHealthy) {
    Write-Host "  Il gateway e' sano in locale ma non raggiungibile tramite $publicUrl dopo 80s - verifica il tunnel." -ForegroundColor Red
    exit 1
}
Write-Host "  OK - raggiungibile pubblicamente tramite il tunnel."

$publicUrl | Out-File -FilePath $UrlFile -Encoding utf8 -NoNewline
Write-Host ""
Write-Host "=== Pronto ===" -ForegroundColor Green
Write-Host "URL pubblico attuale (anche in $UrlFile): $publicUrl"
Write-Host "Su Render, imposta:"
Write-Host "  JARVIS_MINISTRAL_GATEWAY_URL = $publicUrl"
Write-Host "  JARVIS_MINISTRAL_GATEWAY_TOKEN = (il valore di NEXUS_LOCAL_INFERENCE_GATEWAY_TOKEN in LocalBridge\.env - non stampato qui)"
Write-Host ""
Write-Host "NOTA: un Cloudflare quick tunnel genera un URL nuovo ad ogni riavvio di questo" -ForegroundColor Yellow
Write-Host "script/processo - dopo un riavvio del PC rilancia questo script e aggiorna" -ForegroundColor Yellow
Write-Host "JARVIS_MINISTRAL_GATEWAY_URL su Render se e' cambiato (confronta con $UrlFile)." -ForegroundColor Yellow
