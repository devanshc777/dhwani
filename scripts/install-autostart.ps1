# Install (or -Uninstall) dhwani autostart: a Startup-folder shortcut that
# launches the venv's pythonw.exe (no console window) with -m dhwani.
# Combined with DHWANI_IDLE_UNLOAD_MIN (default 30), the app starts with
# Windows, frees the model's ~300 MB after 30 idle minutes, and reloads it
# transparently on the next hotkey press.

param([switch]$Uninstall)

$ErrorActionPreference = "Stop"
$repo = Split-Path $PSScriptRoot -Parent
$lnk = Join-Path ([Environment]::GetFolderPath("Startup")) "dhwani.lnk"

if ($Uninstall) {
    if (Test-Path $lnk) { Remove-Item $lnk; Write-Host "autostart removed" }
    else { Write-Host "autostart was not installed" }
    exit
}

$pythonw = Join-Path $repo ".venv\Scripts\pythonw.exe"
if (-not (Test-Path $pythonw)) {
    Write-Error "no venv at $repo\.venv - run .\run.ps1 once first"
}

$shell = New-Object -ComObject WScript.Shell
$s = $shell.CreateShortcut($lnk)
$s.TargetPath = $pythonw
$s.Arguments = "-m dhwani"
$s.WorkingDirectory = $repo
$s.Description = "dhwani - local dictation (Ctrl+F9)"
$s.Save()
Write-Host "autostart installed -> $lnk"
Write-Host "runs hidden (pythonw); check http://127.0.0.1:8770 or Task Manager"
