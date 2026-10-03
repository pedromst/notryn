# Launch the packaged Electron window, capture the screen, and create a note through its server.
param(
    [Parameter(Mandatory = $true)][string]$Package,
    [Parameter(Mandatory = $true)][string]$Screenshot,
    [Parameter(Mandatory = $true)][string]$Smoke
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class NotrynWindow {
    [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
}
"@
[NotrynWindow]::SetProcessDPIAware() | Out-Null

function Save-Screen([string]$Path) {
    $bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    $bitmap = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
    $directory = Split-Path -Parent $Path
    if ($directory) { New-Item -ItemType Directory -Force -Path $directory | Out-Null }
    $bitmap.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
    $graphics.Dispose()
    $bitmap.Dispose()
}

$Work = Join-Path ([IO.Path]::GetTempPath()) ('notryn-gui-' + [guid]::NewGuid().ToString('n'))
$Local = Join-Path $Work 'Local'
$Roaming = Join-Path $Work 'Roaming'
$Brains = Join-Path $Work 'Brains'
New-Item -ItemType Directory -Force -Path $Local, $Roaming, $Brains | Out-Null
$Extract = Join-Path $Work 'package'
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::ExtractToDirectory((Resolve-Path -LiteralPath $Package).Path, $Extract)
$Gui = Get-ChildItem -LiteralPath $Extract -Recurse -Filter 'Notryn.exe' -File |
    Where-Object { $_.Directory.Name -ne 'notryn' } |
    Select-Object -First 1
if (-not $Gui) { throw 'Notryn.exe was not found in the package.' }

$PreviousLocal = $env:LOCALAPPDATA
$PreviousRoaming = $env:APPDATA
$env:LOCALAPPDATA = $Local
$env:APPDATA = $Roaming
$Process = $null
try {
    $Process = Start-Process -FilePath $Gui.FullName -WorkingDirectory $Gui.Directory.FullName -ArgumentList '--disable-gpu' -PassThru
    $Deadline = (Get-Date).AddSeconds(90)
    $Title = ''
    while ((Get-Date) -lt $Deadline) {
        $Process.Refresh()
        if ($Process.HasExited) { throw "Notryn.exe exited before showing a window (code $($Process.ExitCode))." }
        if ($Process.MainWindowHandle -ne 0) {
            $Title = $Process.MainWindowTitle
            if ($Title) { break }
        }
        Start-Sleep -Milliseconds 500
    }
    $Process.Refresh()
    if ($Process.MainWindowHandle -eq 0) { throw 'Notryn.exe did not open a window within 90 seconds.' }
    Start-Sleep -Seconds 2
    Save-Screen $Screenshot
    Write-Host "Window title: $Title"
    Write-Host "Screenshot: $Screenshot"
    & python $Smoke --port 4783 --brains $Brains
    if ($LASTEXITCODE -ne 0) { throw "The window's local server did not accept a note (exit $LASTEXITCODE)." }
    $Process.CloseMainWindow() | Out-Null
    if (-not $Process.WaitForExit(20000)) {
        Stop-Process -Id $Process.Id -Force
        throw 'Notryn.exe did not close within 20 seconds.'
    }
    Write-Host "Notryn.exe closed with code $($Process.ExitCode)."
} catch {
    if (-not (Test-Path -LiteralPath $Screenshot)) {
        try { Save-Screen $Screenshot } catch { Write-Host $_ }
    }
    throw
} finally {
    if ($Process -and -not $Process.HasExited) {
        try { Stop-Process -Id $Process.Id -Force } catch { }
    }
    $env:LOCALAPPDATA = $PreviousLocal
    $env:APPDATA = $PreviousRoaming
}
