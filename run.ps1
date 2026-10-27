# dhwani bring-up: venv + deps + launch. Safe to re-run.
# -Background: launch hidden via pythonw (survives closing this window).

param([switch]$Background)

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

# The pythonw uv stub is worse than blocked: it relaunches console python.exe
# underneath, so "hidden" runs own a visible terminal and die when it's closed.
# Always ensure Scripts\pythonw.exe is the real base binary (~90KB, not ~45KB).
function Repair-VenvPythonw {
    param([string]$Venv = ".venv")
    $cfg = Join-Path $Venv "pyvenv.cfg"
    if (-not (Test-Path $cfg)) { return }
    $pyw = Join-Path $Venv "Scripts\pythonw.exe"
    if ((Test-Path $pyw) -and (Get-Item $pyw).Length -gt 60KB) { return }
    $base = (Select-String -Path $cfg -Pattern '^home\s*=\s*(.+)').Matches[0].Groups[1].Value.Trim()
    Copy-Item "$base\pythonw.exe" $pyw -Force
    Write-Host "pythonw stub replaced with base binary (windowless runs now truly detach)"
}

# Non-developers won't have uv. Install it for them (user-level, no admin) so
# "right-click run.ps1 -> Run with PowerShell" is genuinely the whole install.
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "uv not found - installing it (one time, no admin needed)..."
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
}
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Error "uv did not land on PATH. Close this window, open a new one, and run .\run.ps1 again."
    exit 1
}

if (-not (Test-Path ".venv")) {
    uv venv
    Repair-VenvPython
    uv pip install -e .
} else {
    Repair-VenvPython
}
Repair-VenvPythonw

Write-Host ""
if ($Background) {
    Start-Process -FilePath (Resolve-Path ".venv\Scripts\pythonw.exe") -ArgumentList "-m","dhwani" -WorkingDirectory $PSScriptRoot
    Write-Host "dhwani running hidden - Alt+3 to dictate - http://127.0.0.1:8770 (survives closing this window)"
} else {
    Write-Host "dhwani starting - Alt+3 to dictate - transcripts at http://127.0.0.1:8770 (closes with this window; use -Background to detach)"
    & ".venv\Scripts\python.exe" -m dhwani
}
