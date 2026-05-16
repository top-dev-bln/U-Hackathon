param(
    [string]$HostName = "127.0.0.1",
    [int]$Port = 8000,
    [int]$HealthTimeoutSec = 60
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    throw "Python venv not found at $venvPython."
}

function Read-JsonFile {
    param([string]$Path)
    return Get-Content -Raw -Path $Path | ConvertFrom-Json
}

function Wait-ForHealth {
    param([string]$Url, [int]$TimeoutSec)
    $start = Get-Date
    while ((Get-Date) -lt $start.AddSeconds($TimeoutSec)) {
        try {
            $resp = Invoke-RestMethod -Method GET -Uri $Url -TimeoutSec 2
            if ($resp.status -eq "ok") { return $true }
        } catch {
            Start-Sleep -Milliseconds 600
        }
    }
    return $false
}

$baseUrl = "http://$HostName`:$Port"
$healthUrl = "$baseUrl/health"
$serverProcess = $null
$startedHere = $false

try {
    $serverUp = $false
    try {
        $health = Invoke-RestMethod -Method GET -Uri $healthUrl -TimeoutSec 2
        if ($health.status -eq "ok") { $serverUp = $true }
    } catch {
        $serverUp = $false
    }

    if (-not $serverUp) {
        Write-Host "Starting API server..."
        $serverProcess = Start-Process `
            -FilePath $venvPython `
            -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", $HostName, "--port", "$Port") `
            -WorkingDirectory $projectRoot `
            -PassThru
        $startedHere = $true
        if (-not (Wait-ForHealth -Url $healthUrl -TimeoutSec $HealthTimeoutSec)) {
            throw "Server did not become healthy in $HealthTimeoutSec seconds."
        }
    }

    Write-Host "Preparing index payload..."
    $baseline = Read-JsonFile (Join-Path $projectRoot "input_tactical_intelligence.json")
    $payload = [ordered]@{
        matchId  = [int]$baseline.matchId
        teamId   = [int]$baseline.teamId
        teamName = [string]$baseline.teamName
        source   = "generated_models"
        outputs  = [ordered]@{
            fusion           = Read-JsonFile (Join-Path $projectRoot "input_tactical_fusion.json")
            tacticalBaseline = $baseline
            decisionQuality  = Read-JsonFile (Join-Path $projectRoot "input_decision_quality.json")
            playerProfiles   = @(
                Read-JsonFile (Join-Path $projectRoot "input_player_profile.json")
            )
            pressing         = Read-JsonFile (Join-Path $projectRoot "input_pressing.json")
            passingNetwork   = Read-JsonFile (Join-Path $projectRoot "input_passing_newtork.json")
        }
        options  = [ordered]@{
            vectorStore           = "faiss"
            rebuild               = $true
            topNPhases            = 10
            includeDebugDocuments = $false
        }
    }
    $payloadJson = $payload | ConvertTo-Json -Depth 100

    Write-Host "Indexing match..."
    $indexResp = Invoke-RestMethod -Method POST -Uri "$baseUrl/index/match" -ContentType "application/json" -Body $payloadJson -TimeoutSec 600
    $matchId = [int]$indexResp.matchId

    $questions = @(
        "Care au fost principalele riscuri tactice?",
        "Ce jucatori trebuie prioritizati si de ce?",
        "Ce focus de antrenament recomanzi pentru build-up?"
    )
    $sessionId = [guid]::NewGuid().ToString()
    Write-Host ("SessionId: {0}" -f $sessionId)

    Write-Host ""
    Write-Host "=== RAG QUERY RESULTS ==="
    foreach ($q in $questions) {
        $qBody = @{
            sessionId = $sessionId
            question = $q
            matchId  = $matchId
            topK     = 6
        } | ConvertTo-Json

        $resp = Invoke-RestMethod -Method POST -Uri "$baseUrl/rag/query" -ContentType "application/json" -Body $qBody -TimeoutSec 120
        Write-Host ""
        Write-Host ("Q: {0}" -f $q)
        Write-Host ("Model: {0}" -f $resp.model)
        Write-Host ("Retrieved: {0}" -f $resp.retrievedCount)
        Write-Host "Answer:"
        Write-Host $resp.answer
    }

    Write-Host ""
    Write-Host "Running debug query..."
    $debugBody = @{
        sessionId = $sessionId
        question = $questions[0]
        matchId  = $matchId
        topK     = 6
    } | ConvertTo-Json
    $debugResp = Invoke-RestMethod -Method POST -Uri "$baseUrl/rag/query/debug" -ContentType "application/json" -Body $debugBody -TimeoutSec 120
    Write-Host ("Debug retrieved docs: {0}" -f $debugResp.retrievedCount)
    Write-Host ("Debug context length: {0}" -f $debugResp.context.Length)

    $historyResp = Invoke-RestMethod -Method GET -Uri "$baseUrl/rag/sessions/$sessionId/history" -TimeoutSec 30
    Write-Host ("Session history messages: {0}" -f $historyResp.Count)
}
finally {
    if ($startedHere -and $null -ne $serverProcess) {
        Write-Host ""
        Write-Host "Stopping API server (PID $($serverProcess.Id))..."
        Stop-Process -Id $serverProcess.Id -Force -ErrorAction SilentlyContinue
    }
}
