# Build an unsigned Windows x64 zip: Electron shell plus the PyInstaller server.
$ErrorActionPreference = 'Stop'

$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$Version = (& python -c "import sys; sys.path.insert(0, r'$Root'); from notryn_version import VERSION; print(VERSION)").Trim()
if (-not $Version) { throw 'Could not read the Notryn version.' }

$Build = Join-Path $Root '.build\windows'
$Output = Join-Path $Root 'dist'
$Venv = Join-Path $Root '.build\packaging-venv'
New-Item -ItemType Directory -Force -Path $Build, $Output | Out-Null

& python -m venv $Venv
if ($LASTEXITCODE -ne 0) { throw "python -m venv exited with $LASTEXITCODE." }
& (Join-Path $Venv 'Scripts\python.exe') -m pip install --disable-pip-version-check -r (Join-Path $Root 'packaging\build-requirements.txt')
if ($LASTEXITCODE -ne 0) { throw "pip install exited with $LASTEXITCODE." }
& (Join-Path $Venv 'Scripts\pyinstaller.exe') --noconfirm --clean `
    --distpath (Join-Path $Build 'sidecar') `
    --workpath (Join-Path $Build 'work') `
    (Join-Path $Root 'packaging\windows\Notryn.spec')
if ($LASTEXITCODE -ne 0) { throw "PyInstaller exited with $LASTEXITCODE." }

$Sidecar = Join-Path $Build 'sidecar\notryn'
$Reported = (& (Join-Path $Sidecar 'notryn.exe') version | Out-String).Trim()
if ($LASTEXITCODE -ne 0) { throw "Sidecar version command exited with $LASTEXITCODE. Output: $Reported" }
if ($Reported -ne $Version) { throw "Sidecar reported '$Reported', expected '$Version'." }

$ElectronOut = Join-Path $Build 'electron'
$env:NOTRYN_SIDECAR_DIR = $Sidecar
$env:NOTRYN_ELECTRON_OUTPUT = $ElectronOut
$env:CSC_IDENTITY_AUTO_DISCOVERY = 'false'
& (Join-Path $Root 'node_modules\.bin\electron-builder.cmd') --config (Join-Path $Root 'desktop\electron-builder.cjs') --win zip --x64 --publish never
if ($LASTEXITCODE -ne 0) { throw "electron-builder exited with $LASTEXITCODE." }

$Name = "Notryn-$Version-windows-x86_64.zip"
$Built = Get-ChildItem -Path $ElectronOut -Filter $Name -Recurse -File | Select-Object -First 1
if (-not $Built) {
    $found = @(Get-ChildItem -Path $ElectronOut -Recurse -File | ForEach-Object { $_.FullName })
    throw "Windows zip was not produced. Found: $($found -join ', ')"
}
$Archive = Join-Path $Output $Name
Copy-Item -LiteralPath $Built.FullName -Destination $Archive -Force
$Hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Archive).Hash.ToLower()
Set-Content -LiteralPath "$Archive.sha256" -Value "$Hash  $Name" -Encoding ascii
Write-Output $Archive
