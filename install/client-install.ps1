# Thin PowerShell wrapper for install/client_install.py (E1-S02 / E1.2).
# All install logic lives in the Python script; this file only finds Python and forwards args.
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Script = Join-Path (Join-Path $Root "install") "client_install.py"

# Prefer a real `python` on PATH (CI setup-python / activated venv) so console
# scripts like zaumzeug.exe land on PATH. Skip Microsoft Store stubs.
# Fall back to the py launcher for developer machines with store aliases only.
$Python = Get-Command python -ErrorAction SilentlyContinue
if ($Python -and ($Python.Source -notmatch '[\\/]WindowsApps[\\/]')) {
    & $Python.Source $Script @args
    exit $LASTEXITCODE
}

$Python3 = Get-Command python3 -ErrorAction SilentlyContinue
if ($Python3 -and ($Python3.Source -notmatch '[\\/]WindowsApps[\\/]')) {
    & $Python3.Source $Script @args
    exit $LASTEXITCODE
}

$Py = Get-Command py -ErrorAction SilentlyContinue
if ($Py) {
    & $Py.Source -3 $Script @args
    exit $LASTEXITCODE
}

Write-Error "error: Python 3.11+ is required but no working python/python3/py was found on PATH."
exit 1
