# Scan the extracted unsigned package with the runner's Windows Defender.
# A clean result here is not proof for a home PC.
param(
    [Parameter(Mandatory = $true)][string]$Package,
    [Parameter(Mandatory = $true)][string]$Report
)
$ErrorActionPreference = 'Stop'
$Mp = Join-Path $env:ProgramFiles 'Windows Defender\MpCmdRun.exe'
if (-not (Test-Path -LiteralPath $Mp)) { throw "Windows Defender command was not found at $Mp." }
$Extract = Join-Path ([IO.Path]::GetTempPath()) ('notryn-defender-' + [guid]::NewGuid().ToString('n'))
New-Item -ItemType Directory -Path $Extract | Out-Null
try {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::ExtractToDirectory((Resolve-Path -LiteralPath $Package).Path, $Extract)
    Write-Host "Scanning $Extract"
    & $Mp -Scan -ScanType 3 -File $Extract
    $Code = $LASTEXITCODE
    $Summary = @"
Windows Defender custom scan (MpCmdRun -Scan -ScanType 3)
Target: extracted $Package
Exit code: $Code
0 means Defender reported no threats on this runner.
2 means Defender reported a threat.
This is the GitHub-hosted runner's Defender. It is not proof for a home PC.
"@
    $directory = Split-Path -Parent $Report
    if ($directory) { New-Item -ItemType Directory -Force -Path $directory | Out-Null }
    Set-Content -LiteralPath $Report -Value $Summary -Encoding utf8
    Write-Host $Summary
    if ($Code -ne 0) { throw "Windows Defender scan exited $Code. See $Report." }
} finally {
    if (Test-Path -LiteralPath $Extract) { Remove-Item -LiteralPath $Extract -Recurse -Force -ErrorAction SilentlyContinue }
}
