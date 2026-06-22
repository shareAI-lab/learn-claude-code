$ErrorActionPreference = "Continue"

$root = Split-Path -Parent $PSScriptRoot
$pidFile = Join-Path $root ".tutorial-server.pid"

$serverPid = $null
if (Test-Path -LiteralPath $pidFile) {
    $rawPid = (Get-Content -LiteralPath $pidFile -Raw).Trim()
    if ($rawPid -match '^\d+$') {
        $serverPid = [int]$rawPid
    }
}

if (-not $serverPid) {
    Write-Host "No server started by Start Tutorial was found. You can close the browser tab." -ForegroundColor Yellow
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
    exit 0
}

$serverProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $serverPid" -ErrorAction SilentlyContinue
if (-not $serverProcess -or $serverProcess.CommandLine -notmatch 'npm(?:\.cmd)?\s+run\s+dev') {
    Write-Host "The saved PID does not belong to this tutorial. Nothing was stopped." -ForegroundColor Yellow
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
    exit 0
}

& taskkill.exe /PID $serverPid /T /F | Out-Null
Start-Sleep -Milliseconds 500
Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
Write-Host "Tutorial server stopped. You can close the browser tab." -ForegroundColor Green
