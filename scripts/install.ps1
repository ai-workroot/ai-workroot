$InstallDir = if ($env:AI_WORKROOT_INSTALL_DIR) {
    $env:AI_WORKROOT_INSTALL_DIR
} else {
    Join-Path $env:LOCALAPPDATA "AIWorkroot\bin"
}
$SourceDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$CommandPath = Join-Path $InstallDir "workroot.ps1"

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Set-Content -Encoding UTF8 -Path $CommandPath -Value @"
python "$SourceDir\scripts\workroot_cli.py" @args
if (`$LASTEXITCODE -ne 0) { exit `$LASTEXITCODE }
"@

Write-Host "Installed workroot CLI to $CommandPath"
Write-Host "Run: workroot.ps1 init --name <name> --directory <directory> --no-native-agent-entry"
