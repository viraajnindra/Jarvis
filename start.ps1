# J.A.R.V.I.S. launcher — starts backend (new window) then the desktop app.
# Usage:  ./start.ps1
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

# Backend in its own window so you can watch logs / Ctrl+C it.
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "Set-Location '$root\backend'; uv run main.py"
)

# Wait for the backend health endpoint before launching the UI.
Write-Host "Waiting for backend on 127.0.0.1:8735..."
for ($i = 0; $i -lt 30; $i++) {
    try {
        Invoke-WebRequest http://127.0.0.1:8735/health -TimeoutSec 2 -UseBasicParsing | Out-Null
        Write-Host "Backend up."
        break
    } catch { Start-Sleep -Seconds 1 }
}

# Desktop app (Tauri dev). Rust must be on PATH.
$env:Path += ";$env:USERPROFILE\.cargo\bin"
Set-Location "$root\frontend"
npm run tauri dev
