param(
    [int]$TimeoutSeconds = 30
)

Set-StrictMode -Version Latest
try {
    # Kill existing python processes that may hold port 8000
    Get-Process -Name python -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }
} catch {}

Start-Sleep -Seconds 1

$pythonExe = 'C:\Users\JARVIS\AppData\Local\Programs\Python\Python312\python.exe'
$repoRoot = Resolve-Path -Path (Join-Path $PSScriptRoot '..')
$logDir = Join-Path $repoRoot 'logs'
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
$logFile = Join-Path $logDir 'uvicorn.log'

# Ensure PYTHONPATH is set for the child process
$env:PYTHONPATH = $repoRoot

Write-Host "Starting uvicorn (logs -> $logFile)"
Start-Process -FilePath $pythonExe -ArgumentList '-m','uvicorn','omni_gateway:app','--host','127.0.0.1','--port','8000' -WorkingDirectory $repoRoot -NoNewWindow

$endTime = (Get-Date).AddSeconds($TimeoutSeconds)
Write-Host "Waiting up to $TimeoutSeconds seconds for /health..."
while ((Get-Date) -lt $endTime) {
    Start-Sleep -Seconds 1
    try {
        $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/health' -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($r.StatusCode -eq 200) {
            Write-Host 'uvicorn is healthy'
            exit 0
        }
    } catch {
        # continue waiting
    }
}

Write-Host 'uvicorn failed to respond within timeout; printing tail of log'
if (Test-Path $logFile) { Get-Content $logFile -Tail 200 }
exit 1
