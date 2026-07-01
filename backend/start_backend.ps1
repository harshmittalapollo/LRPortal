param(
    [string]$Port = $env:BACKEND_PORT
)

$env:LRPORTAL_DATABASE_URL = "mysql+pymysql://root:1234@127.0.0.1:3306/lrportal"
Set-Location $PSScriptRoot
if (-not $Port) { $Port = "8002" }
$env:BACKEND_PORT = $Port
Write-Host "Starting backend on port $Port..."
& "C:\Users\Harsh Mittal\.vscode\venv\Scripts\python.exe" -m uvicorn main:app --host 127.0.0.1 --port $Port --reload
