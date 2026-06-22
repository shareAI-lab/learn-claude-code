$ErrorActionPreference = "Continue"

$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
$web = Join-Path $root "web"
$failed = $false

function Test-Step([string]$name, [scriptblock]$action) {
    Write-Host -NoNewline "[TEST] $name ... "
    try {
        & $action
        if ($LASTEXITCODE -ne $null -and $LASTEXITCODE -ne 0) {
            throw "Exit code $LASTEXITCODE"
        }
        Write-Host "PASS" -ForegroundColor Green
    } catch {
        $script:failed = $true
        Write-Host "FAIL" -ForegroundColor Red
        Write-Host "       $($_.Exception.Message)" -ForegroundColor DarkRed
    }
}

Write-Host "Learn Claude Code - Installation Test" -ForegroundColor Cyan
Test-Step "Node.js" { & node.exe --version | Out-Null }
Test-Step "npm" { & npm.cmd --version | Out-Null }
Test-Step "Python virtual environment" { & $python --version | Out-Null }
Test-Step "Python course packages" { & $python -c "import anthropic, dotenv, yaml" }
Test-Step "Web packages" {
    if (-not (Test-Path -LiteralPath (Join-Path $web "node_modules\next"))) {
        throw "Missing web\node_modules. Run npm.cmd install inside the web folder."
    }
}

$envPath = Join-Path $root ".env"
if (-not (Test-Path -LiteralPath $envPath)) {
    Write-Host "[NOTE] No .env yet. The simulator works; configure an API key before a real AI run." -ForegroundColor Yellow
}

if ($failed) {
    Write-Host "`nSome tests failed. Send a screenshot of this window to Codex." -ForegroundColor Red
    exit 1
}

Write-Host "`nALL TESTS PASSED. Double-click the Start Tutorial CMD file." -ForegroundColor Green
