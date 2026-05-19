$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
python "$ScriptDir/workroot_cli.py" bootstrap-dev @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
