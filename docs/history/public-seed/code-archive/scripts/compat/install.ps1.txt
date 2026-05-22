$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
& (Join-Path $ScriptDir "..\..\install\windows\install.ps1") @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
