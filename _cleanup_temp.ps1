$ErrorActionPreference = 'Continue'
$cut = (Get-Date).AddDays(-7)
$temp = $env:TEMP

$targets = @(Get-ChildItem -LiteralPath $temp -Force -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -lt $cut })

"temp dir      : $temp"
"cutoff        : $($cut.ToString('yyyy-MM-dd HH:mm'))  (older than 7 days)"
"candidates    : $($targets.Count)"

$deleted = 0
$failed = 0
$freed = 0
$failList = @()

foreach ($t in $targets) {
    $size = 0
    try {
        if ($t.PSIsContainer) {
            $s = (Get-ChildItem -LiteralPath $t.FullName -Recurse -Force -File -ErrorAction SilentlyContinue |
                  Measure-Object -Property Length -Sum).Sum
            if ($s) { $size = $s }
        } else {
            $size = $t.Length
        }
    } catch { }

    try {
        Remove-Item -LiteralPath $t.FullName -Recurse -Force -ErrorAction Stop
        $deleted++
        $freed += $size
    } catch {
        $failed++
        $failList += $t.Name
    }
}

"deleted       : $deleted"
"skipped/locked: $failed"
"freed MB      : $([math]::Round($freed / 1MB, 1))"

if ($failList.Count -gt 0) {
    ""
    "first locked/skipped items:"
    $failList | Select-Object -First 10 | ForEach-Object { "  $_" }
}
