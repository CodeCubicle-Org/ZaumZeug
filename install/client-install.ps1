# Thin PowerShell wrapper for install/client_install.py (E1-S02 / E1.2).
# All install logic lives in the Python script; this file only finds Python and forwards args.
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Script = Join-Path (Join-Path $Root "install") "client_install.py"

# Prefer the Windows py launcher when present (avoids Microsoft Store python stubs).
$Py = Get-Command py -ErrorAction SilentlyContinue
if ($Py) {
    & $Py.Source -3 $Script @args
    exit $LASTEXITCODE
}

$Python = Get-Command python -ErrorAction SilentlyContinue
if (-not $Python) {
    $Python = Get-Command python3 -ErrorAction Stop
}
& $Python.Source $Script @args
exit $LASTEXITCODE
