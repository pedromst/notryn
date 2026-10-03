# Prove the PowerShell bootstrap against a zip built in this job.
param(
    [Parameter(Mandatory = $true)][string]$Package,
    [Parameter(Mandatory = $true)][string]$ChecksumFile,
    [Parameter(Mandatory = $true)][string]$Smoke
)
$ErrorActionPreference = 'Stop'
$Installer = Join-Path $PSScriptRoot 'install.ps1'
$env:NOTRYN_BOOTSTRAP = $Installer

function Invoke-Bootstrap {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Invoke-Expression -Command (Get-Content -LiteralPath `$env:NOTRYN_BOOTSTRAP -Raw)" | Out-Host
    return $LASTEXITCODE
}

$Names = @(
    'NOTRYN_INSTALL_PACKAGE', 'NOTRYN_INSTALL_CHECKSUM', 'NOTRYN_INSTALL_CHECKSUM_FILE',
    'NOTRYN_INSTALL_ROOT', 'NOTRYN_INSTALL_START_MENU', 'NOTRYN_INSTALL_NO_OPEN', 'NOTRYN_INSTALL_UNINSTALL'
)
$Saved = @{}
foreach ($Name in $Names) { $Saved[$Name] = [Environment]::GetEnvironmentVariable($Name) }
try {
    $BadRoot = Join-Path $env:TEMP ('notryn-bad-' + [guid]::NewGuid().ToString('n'))
    $env:NOTRYN_INSTALL_PACKAGE = (Resolve-Path -LiteralPath $Package).Path
    $env:NOTRYN_INSTALL_CHECKSUM = '0' * 64
    $env:NOTRYN_INSTALL_CHECKSUM_FILE = ''
    $env:NOTRYN_INSTALL_ROOT = $BadRoot
    $env:NOTRYN_INSTALL_START_MENU = Join-Path $BadRoot 'menu'
    $env:NOTRYN_INSTALL_NO_OPEN = '1'
    $env:NOTRYN_INSTALL_UNINSTALL = ''
    $BadCode = Invoke-Bootstrap
    if ($BadCode -eq 0) { throw 'A checksum mismatch was accepted.' }
    if (Test-Path -LiteralPath (Join-Path $BadRoot 'app')) { throw 'The app was installed despite a checksum mismatch.' }
    Write-Host 'Checksum mismatch was refused.'

    $Root = Join-Path $env:TEMP ('notryn-ok-' + [guid]::NewGuid().ToString('n'))
    $Menu = Join-Path $Root 'Start Menu'
    $env:NOTRYN_INSTALL_CHECKSUM = ''
    $env:NOTRYN_INSTALL_CHECKSUM_FILE = (Resolve-Path -LiteralPath $ChecksumFile).Path
    $env:NOTRYN_INSTALL_ROOT = $Root
    $env:NOTRYN_INSTALL_START_MENU = $Menu
    $GoodCode = Invoke-Bootstrap
    if ($GoodCode -ne 0) { throw "Installer failed with exit $GoodCode." }

    $App = Join-Path $Root 'app'
    $Gui = Join-Path $App 'Notryn.exe'
    $Sidecar = Join-Path $App 'resources\notryn\notryn.exe'
    $Shortcut = Join-Path $Menu 'Notryn.lnk'
    foreach ($Path in @($Gui, $Sidecar, $Shortcut, (Join-Path $Root 'uninstall.ps1'), (Join-Path $Root 'install.json'))) {
        if (-not (Test-Path -LiteralPath $Path)) { throw "Missing after install: $Path" }
    }
    $Shell = New-Object -ComObject WScript.Shell
    $Target = $Shell.CreateShortcut($Shortcut).TargetPath
    if ($Target -ne $Gui) { throw "Start Menu shortcut points at '$Target', not '$Gui'." }

    $Kept = Join-Path $Root 'brains.json'
    Set-Content -LiteralPath $Kept -Value '{"kept":true}' -Encoding ascii
    & python $Smoke --exe $Sidecar
    if ($LASTEXITCODE -ne 0) { throw "Installed server smoke test failed with exit $LASTEXITCODE." }

    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root 'uninstall.ps1')
    if ($LASTEXITCODE -ne 0) { throw "Uninstall failed with exit $LASTEXITCODE." }
    if (Test-Path -LiteralPath $App) { throw 'Uninstall left the application directory.' }
    if (Test-Path -LiteralPath $Shortcut) { throw 'Uninstall left the Start Menu shortcut.' }
    if ((Get-Content -LiteralPath $Kept -Raw) -ne '{"kept":true}') { throw 'Uninstall changed the notes file.' }
    Write-Host 'Installer, shortcut, smoke test and uninstall passed.'
} finally {
    foreach ($Name in $Names) { [Environment]::SetEnvironmentVariable($Name, $Saved[$Name]) }
    Remove-Item Env:NOTRYN_BOOTSTRAP -ErrorAction SilentlyContinue
}
