$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$web = Join-Path $root "web"
$url = "http://localhost:3000/zh/timeline/"
$pidFile = Join-Path $root ".tutorial-server.pid"
$stdout = Join-Path $web "dev-server.log"
$stderr = Join-Path $web "dev-server.err.log"

function Test-TutorialReady {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 2
        return $response.StatusCode -ge 200 -and $response.StatusCode -lt 500
    } catch {
        return $false
    }
}

Write-Host "Learn Claude Code - Beginner Edition" -ForegroundColor Cyan

if (Test-TutorialReady) {
    Write-Host "The tutorial is already running. Opening it now." -ForegroundColor Green
    Write-Host "This launcher did not start that server, so it will not try to stop it later."
    Start-Process $url
    exit 0
}

Write-Host "Starting the tutorial website. Please wait..." -ForegroundColor Yellow
$process = Start-Process -FilePath "npm.cmd" -ArgumentList @("run", "dev") -WorkingDirectory $web -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
Set-Content -LiteralPath $pidFile -Value $process.Id -Encoding ascii

$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    if (Test-TutorialReady) {
        $ready = $true
        break
    }
}

if (-not $ready) {
    Write-Host "The website did not start in 30 seconds. Check web\dev-server.err.log." -ForegroundColor Red
    exit 1
}

Write-Host "Started successfully: $url" -ForegroundColor Green
Write-Host "When finished, double-click the Stop Tutorial CMD file in the project folder."
Start-Process $url
