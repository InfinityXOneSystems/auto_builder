Set-Location -LiteralPath (Join-Path $PSScriptRoot '..')
Write-Host 'Running pytest via exec_pytest_subprocess.py'
& 'C:\Users\JARVIS\AppData\Local\Programs\Python\Python312\python.exe' ops\exec_pytest_subprocess.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
