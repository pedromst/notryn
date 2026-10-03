# Notryn Windows bootstrap.
# Public use: irm https://notryn.com/install.ps1 | iex
# The published release asset does not exist until a Windows package is released.
# CI points this script at a local zip with NOTRYN_INSTALL_PACKAGE.
& {
    $ErrorActionPreference = 'Stop'
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

    $Version = '0.2.0-beta.13'
    if ($env:NOTRYN_INSTALL_VERSION) { $Version = $env:NOTRYN_INSTALL_VERSION.Trim().TrimStart('v') }
    if ($Version -notmatch '^[0-9]+\.[0-9]+\.[0-9]+(-(alpha|beta|rc)\.[0-9]+)?$') {
        throw 'Invalid version.'
    }
    $Arch = $env:PROCESSOR_ARCHITECTURE
    if ($Arch -notin @('AMD64', 'x64')) {
        throw "This package is for 64-bit Windows. This computer is $Arch."
    }

    $Root = if ($env:NOTRYN_INSTALL_ROOT) { $env:NOTRYN_INSTALL_ROOT } else { Join-Path $env:LOCALAPPDATA 'Notryn' }
    $Menu = if ($env:NOTRYN_INSTALL_START_MENU) { $env:NOTRYN_INSTALL_START_MENU } else { Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs' }
    $App = Join-Path $Root 'app'
    $Shortcut = Join-Path $Menu 'Notryn.lnk'
    $Manifest = Join-Path $Root 'install.json'
    $Uninstall = Join-Path $Root 'uninstall.ps1'

    function Remove-ReparsePoint([string]$Path) {
        if (-not (Test-Path -LiteralPath $Path)) { return }
        $item = Get-Item -LiteralPath $Path -Force
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw "Refusing a symbolic link or junction at $Path."
        }
    }

    if ($env:NOTRYN_INSTALL_UNINSTALL -eq '1') {
        if (-not (Test-Path -LiteralPath $Uninstall)) { throw "No Notryn installation was found at $Root." }
        & powershell -NoProfile -ExecutionPolicy Bypass -File $Uninstall
        if ($LASTEXITCODE -ne 0) { throw "Uninstall failed with exit $LASTEXITCODE." }
        return
    }

    Remove-ReparsePoint $Root
    $AssetName = "Notryn-$Version-windows-x86_64.zip"
    $Work = Join-Path ([IO.Path]::GetTempPath()) ('notryn-setup-' + [guid]::NewGuid().ToString('n'))
    New-Item -ItemType Directory -Path $Work | Out-Null
    try {
        $Package = $env:NOTRYN_INSTALL_PACKAGE
        if ($Package) {
            if (-not (Test-Path -LiteralPath $Package)) { throw "Package not found: $Package" }
            $Package = (Resolve-Path -LiteralPath $Package).Path
            Write-Host "Preparing Notryn $Version for Windows x64 from a local package."
        } else {
            $Base = "https://github.com/pedromst/notryn/releases/download/v$Version"
            $Package = Join-Path $Work $AssetName
            $ChecksumFile = Join-Path $Work "$AssetName.sha256"
            Write-Host "Preparing Notryn $Version for Windows x64."
            Write-Host 'Downloading Notryn...'
            Invoke-WebRequest -Uri "$Base/$AssetName" -OutFile $Package -UseBasicParsing
            Invoke-WebRequest -Uri "$Base/$AssetName.sha256" -OutFile $ChecksumFile -UseBasicParsing
            $env:NOTRYN_INSTALL_CHECKSUM_FILE = $ChecksumFile
        }

        $Length = (Get-Item -LiteralPath $Package).Length
        if ($Length -le 0 -or $Length -gt (700MB)) { throw 'Download size is not acceptable. Nothing was installed.' }

        Write-Host 'Checking download...'
        $Actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $Package).Hash.ToLower()
        if ($env:NOTRYN_INSTALL_CHECKSUM) {
            $Expected = $env:NOTRYN_INSTALL_CHECKSUM.Trim().ToLower()
        } elseif ($env:NOTRYN_INSTALL_CHECKSUM_FILE) {
            $Line = (Get-Content -LiteralPath $env:NOTRYN_INSTALL_CHECKSUM_FILE -TotalCount 1)
            $Expected = ($Line -split '\s+')[0].Trim().ToLower()
        } else {
            throw 'Missing installer checksum. Nothing was installed.'
        }
        if ($Expected -notmatch '^[0-9a-f]{64}$') { throw 'Invalid installer checksum. Nothing was installed.' }
        if ($Expected -ne $Actual) { throw 'Installer checksum mismatch. Nothing was installed.' }

        Add-Type -AssemblyName System.IO.Compression.FileSystem
        $Archive = [System.IO.Compression.ZipFile]::OpenRead($Package)
        try {
            foreach ($Entry in $Archive.Entries) {
                $Name = ($Entry.FullName -replace '\\', '/')
                if ($Name -match '(^/|^[A-Za-z]:|(^|/)\.\.(/|$))') {
                    throw "Archive path refused: $Name"
                }
            }
        } finally {
            $Archive.Dispose()
        }

        Write-Host 'Installing...'
        $Stage = Join-Path $Work 'unpacked'
        [System.IO.Compression.ZipFile]::ExtractToDirectory($Package, $Stage)
        $Sidecar = Get-ChildItem -LiteralPath $Stage -Recurse -Filter 'notryn.exe' -File |
            Where-Object { $_.Directory.Name -eq 'notryn' -and $_.Directory.Parent.Name -eq 'resources' } |
            Select-Object -First 1
        if (-not $Sidecar) { throw 'The local server is missing from the package. Nothing was installed.' }
        $Bundle = $Sidecar.Directory.Parent.Parent
        $Gui = Join-Path $Bundle.FullName 'Notryn.exe'
        if (-not (Test-Path -LiteralPath $Gui)) { throw 'The desktop application is missing from the package. Nothing was installed.' }

        New-Item -ItemType Directory -Force -Path $Root, $Menu | Out-Null
        Remove-ReparsePoint $Root
        Remove-ReparsePoint $Menu
        if (Test-Path -LiteralPath $App) {
            Remove-ReparsePoint $App
            Remove-Item -LiteralPath $App -Recurse -Force
        }
        Copy-Item -LiteralPath $Bundle.FullName -Destination $App -Recurse

        $Shell = New-Object -ComObject WScript.Shell
        $Link = $Shell.CreateShortcut($Shortcut)
        $Link.TargetPath = Join-Path $App 'Notryn.exe'
        $Link.WorkingDirectory = $App
        $Link.Description = 'Notryn'
        $Link.Save()

        @{ version = $Version; sha256 = $Actual } | ConvertTo-Json | Set-Content -LiteralPath $Manifest -Encoding utf8
        @"
`$ErrorActionPreference = 'Stop'
`$shortcut = @'
$Shortcut
'@
`$app = @'
$App
'@
`$manifest = @'
$Manifest
'@
if (Test-Path -LiteralPath `$shortcut) { Remove-Item -LiteralPath `$shortcut -Force }
if (Test-Path -LiteralPath `$app) { Remove-Item -LiteralPath `$app -Recurse -Force }
if (Test-Path -LiteralPath `$manifest) { Remove-Item -LiteralPath `$manifest -Force }
Write-Output 'Notryn was uninstalled. Notes and settings were kept in:'
Write-Output @'
$Root
'@
"@ | Set-Content -LiteralPath $Uninstall -Encoding utf8

        Write-Host "Installed Notryn $Version."
        Write-Host "App: $App"
        Write-Host "Start Menu: $Shortcut"
        Write-Host "Uninstall: powershell -NoProfile -ExecutionPolicy Bypass -File `"$Uninstall`""
        if ($env:NOTRYN_INSTALL_NO_OPEN -ne '1') {
            Start-Process -FilePath (Join-Path $App 'Notryn.exe')
        }
    } finally {
        if (Test-Path -LiteralPath $Work) { Remove-Item -LiteralPath $Work -Recurse -Force -ErrorAction SilentlyContinue }
    }
}
