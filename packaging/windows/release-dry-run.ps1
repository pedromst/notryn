# Show which Windows files a future release would attach. Does not create a tag or release.
param(
    [Parameter(Mandatory = $true)][string]$Dist,
    [Parameter(Mandatory = $true)][string]$Report
)
$ErrorActionPreference = 'Stop'
$Installer = Join-Path $PSScriptRoot 'install.ps1'
$Fixture = Join-Path ([IO.Path]::GetTempPath()) ('notryn-releases-' + [guid]::NewGuid().ToString('n') + '.json')
@'
[
  {"tag_name":"v0.2.0-beta.12","draft":false,"prerelease":true,"assets":[{"name":"Notryn-0.2.0-beta.12-windows-x86_64.zip","state":"uploaded","digest":"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}]},
  {"tag_name":"v0.2.0-beta.13","draft":false,"prerelease":true,"assets":[{"name":"Notryn-0.2.0-beta.13-windows-x86_64.zip","state":"uploaded","digest":"sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"},{"name":"Notryn-0.2.0-beta.13-linux-x86_64.tar.gz","state":"uploaded","digest":"sha256:dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"}]},
  {"tag_name":"v9.9.9","draft":true,"prerelease":false,"assets":[{"name":"Notryn-9.9.9-windows-x86_64.zip","state":"uploaded","digest":"sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"}]}
]
'@ | Set-Content -LiteralPath $Fixture -Encoding ascii
try {
    $env:NOTRYN_INSTALL_SELECT_FIXTURE = $Fixture
    $env:NOTRYN_INSTALL_VERSION = ''
    $Selected = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Installer
    if ($LASTEXITCODE -ne 0) { throw "Release picker failed with exit $LASTEXITCODE. $Selected" }
    $Choice = $Selected | ConvertFrom-Json
    if ($Choice.version -ne '0.2.0-beta.13') { throw "Picker chose $($Choice.version), expected 0.2.0-beta.13." }
    if ($Choice.asset -ne 'Notryn-0.2.0-beta.13-windows-x86_64.zip') { throw "Picker chose asset $($Choice.asset)." }
    if ($Choice.sha256 -ne ('b' * 64)) { throw 'Picker did not keep the Windows asset digest.' }
    if ($Choice.url -ne 'https://github.com/pedromst/notryn/releases/download/v0.2.0-beta.13/Notryn-0.2.0-beta.13-windows-x86_64.zip') {
        throw "Picker built an unexpected URL: $($Choice.url)"
    }
    Write-Host 'Release picker chose the newest non-draft Windows asset.'
} finally {
    Remove-Item Env:NOTRYN_INSTALL_SELECT_FIXTURE -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $Fixture -Force -ErrorAction SilentlyContinue
}

$Zip = Get-ChildItem -LiteralPath $Dist -Filter 'Notryn-*-windows-x86_64.zip' -File | Select-Object -First 1
if (-not $Zip) { throw "No Windows zip in $Dist." }
$ChecksumFile = "$($Zip.FullName).sha256"
if (-not (Test-Path -LiteralPath $ChecksumFile)) { throw "Missing checksum file $ChecksumFile." }
$Expected = ((Get-Content -LiteralPath $ChecksumFile -TotalCount 1) -split '\s+')[0].ToLower()
$Actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $Zip.FullName).Hash.ToLower()
if ($Expected -ne $Actual) { throw 'The Windows zip does not match its SHA256 file.' }

$Lines = @(
    'DRY-RUN: no tag was created and no release was published.',
    'A future release workflow would attach these Windows files next to the Linux and macOS assets:',
    $Zip.Name,
    (Split-Path -Leaf $ChecksumFile),
    "sha256 $Actual"
)
$directory = Split-Path -Parent $Report
if ($directory) { New-Item -ItemType Directory -Force -Path $directory | Out-Null }
Set-Content -LiteralPath $Report -Value ($Lines -join "`r`n") -Encoding ascii
$Lines | ForEach-Object { Write-Host $_ }
