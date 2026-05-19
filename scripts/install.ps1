param(
    [switch]$DryRun,
    [switch]$Help
)

$InstallDir = if ($env:AI_WORKROOT_INSTALL_DIR) {
    $env:AI_WORKROOT_INSTALL_DIR
} else {
    Join-Path $env:LOCALAPPDATA "AIWorkroot\bin"
}
$SourceDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$CommandPath = Join-Path $InstallDir "workroot.ps1"

function Show-Usage {
    Write-Host "AI Workroot CLI wrapper installer"
    Write-Host ""
    Write-Host "Usage:"
    Write-Host "  scripts/install.ps1 [-DryRun]"
    Write-Host "  scripts/install.ps1 -Help"
    Write-Host ""
    Write-Host "Installs a user-level workroot.ps1 wrapper for scripts/workroot_cli.py."
    Write-Host "This installer does not run first-use setup and does not initialize a Workroot."
}

if ($Help) {
    Show-Usage
    exit 0
}

if ($DryRun) {
    Write-Host "AI Workroot CLI wrapper installer"
    Write-Host "would install workroot CLI wrapper to $CommandPath"
    Write-Host "would run: workroot.ps1 init --name <name> --directory <directory> --no-native-agent-entry"
    exit 0
}

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Set-Content -Encoding UTF8 -Path $CommandPath -Value @"
python "$SourceDir\scripts\workroot_cli.py" @args
if (`$LASTEXITCODE -ne 0) { exit `$LASTEXITCODE }
"@

Write-Host "Installed workroot CLI to $CommandPath"
Write-Host "Run: workroot.ps1 init --name <name> --directory <directory> --no-native-agent-entry"
