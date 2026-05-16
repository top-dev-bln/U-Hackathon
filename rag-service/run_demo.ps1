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
    throw "Python venv not found at $venvPython. Create .venv first."
}

function Read-JsonFile {
    param([string]$Path)
    return Get-Content -Raw -Path $Path | ConvertFrom-Json
}

function Wait-ForHealth {
    param(
        [string]$Url,
        [int]$TimeoutSec
    )
    $start = Get-Date
    while ((Get-Date) -lt $start.AddSeconds($TimeoutSec)) {
        try {
            $resp = Invoke-RestMethod -Method GET -Uri $Url -TimeoutSec 2
            if ($resp.status -eq "ok") {
                return $true
            }
        }
        catch {
            Start-Sleep -Milliseconds 700
        }
    }
    return $false
}

$baseUrl = "http://$HostName`:$Port"
$healthUrl = "$baseUrl/health"
$serverProcess = $null
$startedHere = $false

try {
    Write-Host "Checking existing API server at $healthUrl ..."
    $serverUp = $false
    try {
        $health = Invoke-RestMethod -Method GET -Uri $healthUrl -TimeoutSec 2
        if ($health.status -eq "ok") {
            $serverUp = $true
            Write-Host "Server already running."
        }
    }
    catch {
        $serverUp = $false
    }

    if (-not $serverUp) {
        Write-Host "Starting local API server..."
        $serverProcess = Start-Process `
            -FilePath $venvPython `
            -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", $HostName, "--port", "$Port") `
            -WorkingDirectory $projectRoot `
            -PassThru
        $startedHere = $true

        $ok = Wait-ForHealth -Url $healthUrl -TimeoutSec $HealthTimeoutSec
        if (-not $ok) {
            throw "Server did not become healthy in $HealthTimeoutSec seconds."
        }
    }

    Write-Host "Building request payload from local input files..."
    $tacticalBaseline = Read-JsonFile (Join-Path $projectRoot "input_tactical_intelligence.json")
    $payload = [ordered]@{
        matchId  = [int]$tacticalBaseline.matchId
        teamId   = [int]$tacticalBaseline.teamId
        teamName = [string]$tacticalBaseline.teamName
        source   = "generated_models"
        outputs  = [ordered]@{
            fusion          = Read-JsonFile (Join-Path $projectRoot "input_tactical_fusion.json")
            tacticalBaseline = $tacticalBaseline
            decisionQuality = Read-JsonFile (Join-Path $projectRoot "input_decision_quality.json")
            playerProfiles  = @(
                Read-JsonFile (Join-Path $projectRoot "input_player_profile.json")
            )
            pressing       = Read-JsonFile (Join-Path $projectRoot "input_pressing.json")
            passingNetwork = Read-JsonFile (Join-Path $projectRoot "input_passing_newtork.json")
        }
        options  = [ordered]@{
            vectorStore           = "faiss"
            rebuild               = $true
            topNPhases            = 10
            includeDebugDocuments = $false
        }
    }

    $payloadJson = $payload | ConvertTo-Json -Depth 100
    $payloadPath = Join-Path $projectRoot "demo_request_payload.json"
    Set-Content -Path $payloadPath -Value $payloadJson -Encoding UTF8

    Write-Host "Calling POST /index/match ..."
    $indexResponse = Invoke-RestMethod `
        -Method POST `
        -Uri "$baseUrl/index/match" `
        -ContentType "application/json" `
        -Body $payloadJson `
        -TimeoutSec 600

    Write-Host "Calling GET /index/matches ..."
    $matchesResponse = Invoke-RestMethod -Method GET -Uri "$baseUrl/index/matches" -TimeoutSec 30

    $matchId = [int]$payload.matchId
    Write-Host "Calling GET /index/matches/$matchId/documents ..."
    $docsResponse = Invoke-RestMethod -Method GET -Uri "$baseUrl/index/matches/$matchId/documents" -TimeoutSec 30

    Write-Host ""
    Write-Host "=== DEMO RESULT ==="
    Write-Host ("matchId:           {0}" -f $indexResponse.matchId)
    Write-Host ("status:            {0}" -f $indexResponse.status)
    Write-Host ("documentsCreated:  {0}" -f $indexResponse.documentsCreated)
    Write-Host ("embeddingsCreated: {0}" -f $indexResponse.embeddingsCreated)
    Write-Host ("vectorStore:       {0}" -f $indexResponse.vectorStore)
    Write-Host ("collectionName:    {0}" -f $indexResponse.collectionName)
    Write-Host ("warningsCount:     {0}" -f $indexResponse.warnings.Count)
    Write-Host ("indexedMatches:    {0}" -f $matchesResponse.Count)
    Write-Host ("loadedDocuments:   {0}" -f $docsResponse.Count)
    Write-Host ("payloadSavedAt:    {0}" -f $payloadPath)

    Write-Host ""
    Write-Host "Top document types:"
    $indexResponse.documentTypes.PSObject.Properties |
        Sort-Object -Property Value -Descending |
        Select-Object -First 8 |
        ForEach-Object { Write-Host ("  - {0}: {1}" -f $_.Name, $_.Value) }

    Write-Host ""
    Write-Host "Preview documents:"
    $docsResponse |
        Select-Object -First 3 |
        ForEach-Object {
            $preview = [string]$_.text
            if ($preview.Length -gt 160) {
                $preview = $preview.Substring(0, 160) + "..."
            }
            Write-Host ("  - {0} [{1}]" -f $_.docId, $_.documentType)
            Write-Host ("    {0}" -f $preview)
        }
}
finally {
    if ($startedHere -and $null -ne $serverProcess) {
        Write-Host ""
        Write-Host "Stopping local API server (PID $($serverProcess.Id))..."
        Stop-Process -Id $serverProcess.Id -Force -ErrorAction SilentlyContinue
    }
}
