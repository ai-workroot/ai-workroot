$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)
$existingPythonPath = [Environment]::GetEnvironmentVariable("PYTHONPATH")
if ([string]::IsNullOrEmpty($existingPythonPath)) {
    $env:PYTHONPATH = Join-Path $ProjectRoot "src"
} else {
    $env:PYTHONPATH = (Join-Path $ProjectRoot "src") + [IO.Path]::PathSeparator + $existingPythonPath
}
python -m ai_workroot bootstrap-dev @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
