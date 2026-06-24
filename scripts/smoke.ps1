$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
if (!(Test-Path ".venv")) {
  py -3 -m venv .venv
}
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
$env:PYTHONPATH = $Root
& ".\.venv\Scripts\python.exe" tests\smoke_lite.py
