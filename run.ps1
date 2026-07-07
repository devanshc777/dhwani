# dhwani bring-up: venv + deps + launch. Safe to re-run.

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# Self-heal for this machine's Application Control blocking fresh uv python
# stubs (see C:\Dev\infra\setup\SYSTEM.md "Known Issues"). Pattern borrowed
# from Budgetnista's start-local.ps1. Harmless on machines without the issue.
function Repair-VenvPython {
    param([string]$Venv = ".venv")
    $cfg = Join-Path $Venv "pyvenv.cfg"
    if (-not (Test-Path $cfg)) { return }
    $py = Join-Path $Venv "Scripts\python.exe"
    & $py -c "1" 2>$null
    if ($LASTEXITCODE -eq 0) { return }
    Write-Host "python stub blocked by Application Control - swapping in base interpreter..."
    $base = (Select-String -Path $cfg -Pattern '^home\s*=\s*(.+)').Matches[0].Groups[1].Value.Trim()
    Copy-Item "$base\python.exe" $py -Force
    foreach ($dll in 'python3.dll','python312.dll','vcruntime140.dll','vcruntime140_1.dll') {
        if (Test-Path "$base\$dll") { Copy-Item "$base\$dll" (Join-Path $Venv "Scripts") -Force }
    }
}

if (-not (Test-Path ".venv")) {
    uv venv
    Repair-VenvPython
    uv pip install -e .
} else {
    Repair-VenvPython
}

Write-Host ""
Write-Host "dhwani starting - Tab+Q to dictate - transcripts at http://127.0.0.1:8770"
& ".venv\Scripts\python.exe" -m dhwani
