param(
    [int]$TimeoutSeconds = 20
)
Set-Location -LiteralPath (Join-Path $PSScriptRoot '..')
Write-Host 'Starting gateway via start_uvicorn_and_wait.ps1'
& powershell -NoProfile -ExecutionPolicy Bypass -File .\ops\start_uvicorn_and_wait.ps1 -TimeoutSeconds $TimeoutSeconds
exit $LASTEXITCODE
