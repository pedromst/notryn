# Notryn Windows (beta) bootstrap.
# Public use: irm https://notryn.com/install.ps1 | iex
# Unsigned beta. SmartScreen may say Windows protected your PC: choose More info, then Run anyway.
# CI can point this script at a local zip with NOTRYN_INSTALL_PACKAGE.
# NOTRYN_INSTALL_SELECT_FIXTURE runs the release picker only and installs nothing.
& {
    $ErrorActionPreference = 'Stop'
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

    function Get-NotrynVersionKey([string]$Value) {
        if ($Value -match '^v?(\d+)\.(\d+)\.(\d+)(?:-(alpha|beta|rc)\.(\d+))?$') {
            $stage = 3
            $number = 0
            if ($Matches[4]) {
                $stage = @{ alpha = 0; beta = 1; rc = 2 }[$Matches[4]]
                $number = [int]$Matches[5]
            }
            return '{0:D5}.{1:D5}.{2:D5}.{3:D5}.{4:D5}' -f [int]$Matches[1], [int]$Matches[2], [int]$Matches[3], $stage, $number
        }
        return $null
    }

    function Select-NotrynWindowsRelease {
        param($Releases, [string]$Version)
        $Best = $null
        $BestKey = ''
        foreach ($Release in @($Releases)) {
            if ($Release.draft) { continue }
            $Tag = [string]$Release.tag_name
            $Key = Get-NotrynVersionKey $Tag
            if (-not $Key) { continue }
            $Ver = $Tag.TrimStart('v')
            if ($Version -and $Ver -ne $Version.Trim().TrimStart('v')) { continue }
            $AssetName = "Notryn-$Ver-windows-x86_64.zip"
            $Asset = @($Release.assets) | Where-Object { $_ -and $_.name -eq $AssetName -and $_.state -eq 'uploaded' } | Select-Object -First 1
            if (-not $Asset) { continue }
            if ($Key -le $BestKey) { continue }
            $Sha = ''
            if ([string]$Asset.digest -match '^sha256:([0-9a-f]{64})$') { $Sha = $Matches[1] }
            $BestKey = $Key
            $Best = [pscustomobject]@{
                tag = $Tag
                version = $Ver
                asset = $AssetName
                sha256 = $Sha
                url = "https://github.com/pedromst/notryn/releases/download/$Tag/$AssetName"
                sha256Url = "https://github.com/pedromst/notryn/releases/download/$Tag/$AssetName.sha256"
            }
        }
        if (-not $Best) { throw 'No published Windows release asset was found.' }
        return $Best
    }

    if ($env:NOTRYN_INSTALL_SELECT_FIXTURE) {
        $Fixture = Get-Content -LiteralPath $env:NOTRYN_INSTALL_SELECT_FIXTURE -Raw -Encoding utf8 | ConvertFrom-Json
        $Chosen = Select-NotrynWindowsRelease -Releases $Fixture -Version $env:NOTRYN_INSTALL_VERSION
        Write-Output ($Chosen | ConvertTo-Json -Compress)
        return
    }

    $Arch = $env:PROCESSOR_ARCHITECTURE
    if ($Arch -notin @('AMD64', 'x64')) {
        throw "This package is for 64-bit Windows. This computer is $Arch."
    }

    $Root = if ($env:NOTRYN_INSTALL_ROOT) { $env:NOTRYN_INSTALL_ROOT } else { Join-Path $env:LOCALAPPDATA 'Notryn' }
    $Menu = if ($env:NOTRYN_INSTALL_START_MENU) { $env:NOTRYN_INSTALL_START_MENU } else { Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs' }
    $App = Join-Path $Root 'app'
    $Shortcut = Join-Path $Menu 'Notryn.lnk'
    $Manifest = Join-Path $Root 'installation.json'
    $Uninstall = Join-Path $Root 'uninstall.ps1'
    $Launcher = Join-Path $Root 'notryn.cmd'
    $Backups = Join-Path $Root '.notryn-backups'

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
    $Work = Join-Path ([IO.Path]::GetTempPath()) ('notryn-setup-' + [guid]::NewGuid().ToString('n'))
    New-Item -ItemType Directory -Path $Work | Out-Null
    try {
        $Package = $env:NOTRYN_INSTALL_PACKAGE
        $Version = if ($env:NOTRYN_INSTALL_VERSION) { $env:NOTRYN_INSTALL_VERSION.Trim().TrimStart('v') } else { '' }
        if ($Package) {
            if (-not (Test-Path -LiteralPath $Package)) { throw "Package not found: $Package" }
            $Package = (Resolve-Path -LiteralPath $Package).Path
            if (-not $Version -and [IO.Path]::GetFileName($Package) -match '^Notryn-(.+)-windows-x86_64\.zip$') {
                $Version = $Matches[1]
            }
            if (-not $Version) { throw 'Set NOTRYN_INSTALL_VERSION for this local package.' }
            Write-Host "Preparing Notryn $Version for Windows x64 (beta) from a local package."
        } else {
            Write-Host 'Looking up the latest Windows release...'
            $Headers = @{ 'User-Agent' = 'Notryn installer'; 'Accept' = 'application/vnd.github+json' }
            $Index = Invoke-RestMethod -Uri 'https://api.github.com/repos/pedromst/notryn/releases?per_page=100' -Headers $Headers
            $Chosen = Select-NotrynWindowsRelease -Releases $Index -Version $Version
            $Version = $Chosen.version
            $Package = Join-Path $Work $Chosen.asset
            Write-Host "Preparing Notryn $Version for Windows x64 (beta)."
            Write-Host 'Downloading Notryn...'
            Invoke-WebRequest -Uri $Chosen.url -OutFile $Package -UseBasicParsing
            if ($Chosen.sha256) {
                $env:NOTRYN_INSTALL_CHECKSUM = $Chosen.sha256
            } else {
                $ChecksumFile = Join-Path $Work "$($Chosen.asset).sha256"
                Invoke-WebRequest -Uri $Chosen.sha256Url -OutFile $ChecksumFile -UseBasicParsing
                $env:NOTRYN_INSTALL_CHECKSUM_FILE = $ChecksumFile
            }
        }
        if ($Version -notmatch '^[0-9]+\.[0-9]+\.[0-9]+(-(alpha|beta|rc)\.[0-9]+)?$') {
            throw 'Invalid version.'
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
        $PreviousName = $null
        if (Test-Path -LiteralPath $App) {
            Remove-ReparsePoint $App
            New-Item -ItemType Directory -Force -Path $Backups | Out-Null
            Remove-ReparsePoint $Backups
            $OldVersion = 'legacy'
            if (Test-Path -LiteralPath $Manifest) {
                try { $OldVersion = (Get-Content -LiteralPath $Manifest -Raw -Encoding utf8 | ConvertFrom-Json).version } catch { $OldVersion = 'legacy' }
            }
            $PreviousName = 'notryn-' + $OldVersion + '-' + [guid]::NewGuid().ToString('n').Substring(0, 12)
            $Backup = Join-Path $Backups $PreviousName
            Move-Item -LiteralPath $App -Destination $Backup
            if (Test-Path -LiteralPath $Manifest) {
                Copy-Item -LiteralPath $Manifest -Destination ($Backup + '.json')
            }
        }
        Copy-Item -LiteralPath $Bundle.FullName -Destination $App -Recurse
        $SidecarPath = Join-Path $App 'resources\notryn\notryn.exe'
        Set-Content -LiteralPath $Launcher -Value "@echo off`r`n`"$SidecarPath`" %*`r`n" -Encoding ascii

        $Shell = New-Object -ComObject WScript.Shell
        $Link = $Shell.CreateShortcut($Shortcut)
        $Link.TargetPath = Join-Path $App 'Notryn.exe'
        $Link.WorkingDirectory = $App
        $Link.Description = 'Notryn'
        $Link.Save()

        $Record = [ordered]@{
            version = $Version
            platform = 'windows'
            arch = 'x86_64'
            private = $false
            previous = $PreviousName
            sha256 = $Actual
        }
        $Record | ConvertTo-Json | Set-Content -LiteralPath $Manifest -Encoding utf8
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
`$launcher = @'
$Launcher
'@
if (Test-Path -LiteralPath `$shortcut) { Remove-Item -LiteralPath `$shortcut -Force }
if (Test-Path -LiteralPath `$app) { Remove-Item -LiteralPath `$app -Recurse -Force }
if (Test-Path -LiteralPath `$manifest) { Remove-Item -LiteralPath `$manifest -Force }
if (Test-Path -LiteralPath `$launcher) { Remove-Item -LiteralPath `$launcher -Force }
Write-Output 'Notryn was uninstalled. Notes and settings were kept in:'
Write-Output @'
$Root
'@
"@ | Set-Content -LiteralPath $Uninstall -Encoding utf8

        Write-Host "Installed Notryn $Version."
        Write-Host "App: $App"
        Write-Host "Start Menu: $Shortcut"
        Write-Host "Command: $Launcher"
        Write-Host "Uninstall: powershell -NoProfile -ExecutionPolicy Bypass -File `"$Uninstall`""
        if ($env:NOTRYN_INSTALL_NO_OPEN -ne '1') {
            Start-Process -FilePath (Join-Path $App 'Notryn.exe')
        }
    } finally {
        if (Test-Path -LiteralPath $Work) { Remove-Item -LiteralPath $Work -Recurse -Force -ErrorAction SilentlyContinue }
    }
}
