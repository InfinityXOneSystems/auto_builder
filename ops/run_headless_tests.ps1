Set-Location -LiteralPath (Join-Path $PSScriptRoot '..')
Write-Host 'Running headless team tests'
& 'C:\Users\JARVIS\AppData\Local\Programs\Python\Python312\python.exe' ops\run_headless_test_now.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
