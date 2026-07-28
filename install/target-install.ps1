# Thin PowerShell wrapper for target_install.py (E5-S01 bundle / E5-S09b).
# Invokes the sibling target_install.py so this works both under install/
# and when copied into deploy/<name>/.
$ErrorActionPreference = "Stop"

$Script = Join-Path $PSScriptRoot "target_install.py"

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
