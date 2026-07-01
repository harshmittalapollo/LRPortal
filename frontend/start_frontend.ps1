param(
    [string]$Port = $env:FRONTEND_PORT
)

Set-Location $PSScriptRoot
if (-not $Port) { $Port = "3001" }
$env:PORT = $Port
$env:FRONTEND_PORT = $Port
$env:REACT_APP_API_URL = "http://127.0.0.1:8002"
Write-Host "Starting frontend on port $Port..."
& "C:\Program Files\nodejs\npm.cmd" start
