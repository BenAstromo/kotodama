# One fresh process per grid (memory is only meaningful on a fresh heap),
# merged into one report:  .\t_perf_all.ps1 <out.json> [rounds]
# Uses the PyQt6 venv %TEMP%\qtv. Deletes env\ afterwards.
param([string]$Out = "perf.json", [int]$Rounds = 3)
$py = "$env:TEMP\qtv\Scripts\python.exe"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$grids = @("base", "word:All", "word:freq:6000", "word:freq:20000", "kanji:All", "grammar:All",
           "word:All gold", "word:N5")
$merged = @{ grids = @{} }
foreach ($g in $grids) {
    $tmp = Join-Path $env:TEMP ("kt_perf_" + ($g -replace '[^A-Za-z0-9]', '_') + ".json")
    Push-Location $here
    & $py -X utf8 t_perf.py $tmp $Rounds $g *> $null
    Pop-Location
    if (-not (Test-Path $tmp)) { Write-Output "FAILED: $g"; continue }
    $r = Get-Content $tmp -Raw -Encoding utf8 | ConvertFrom-Json
    if ($g -eq "base") {
        foreach ($p in $r.PSObject.Properties) { if ($p.Name -ne "grids") { $merged[$p.Name] = $p.Value } }
    } else {
        foreach ($p in $r.grids.PSObject.Properties) { $merged.grids[$p.Name] = $p.Value }
    }
    Remove-Item $tmp
    Write-Output "done: $g"
}
$merged | ConvertTo-Json -Depth 5 | Out-File -Encoding utf8 $Out
$envdir = Join-Path $here "env"
if (Test-Path $envdir) { Remove-Item -Recurse -Force $envdir }
