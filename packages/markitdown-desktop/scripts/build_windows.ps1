param(
    [string]$Python = ".\.venv312\Scripts\python.exe",
    [string]$Version = "0.1.1",
    [string]$RepositoryUrl = "",
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
$distDir = Join-Path $repoRoot "dist"
$releaseDir = Join-Path $repoRoot "release"
$appDir = Join-Path $distDir "MarkItDownDesktop"
$portableZip = Join-Path $releaseDir "MarkItDownDesktop-$Version-portable.zip"
$installerScript = Join-Path $PSScriptRoot "..\installer\markitdown-desktop.iss"
$installerExe = Join-Path $releaseDir "MarkItDownDesktop-$Version-setup.exe"

Set-Location $repoRoot

if (-not (Test-Path $Python)) {
    throw "Python executable not found at '$Python'. Create the virtual environment and install the desktop package first."
}

if (-not (Test-Path $releaseDir)) {
    New-Item -ItemType Directory -Path $releaseDir | Out-Null
}

$existingProcesses = Get-Process MarkItDownDesktop -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -and $_.Path.StartsWith($appDir, [System.StringComparison]::OrdinalIgnoreCase) }
foreach ($process in $existingProcesses) {
    Write-Warning "Stopping existing packaged app process $($process.Id) before rebuild."
    Stop-Process -Id $process.Id -Force
}

& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name MarkItDownDesktop `
    --hidden-import PySide6.QtCore `
    --hidden-import PySide6.QtGui `
    --hidden-import PySide6.QtWidgets `
    --hidden-import pandas `
    --hidden-import openpyxl `
    --hidden-import xlrd `
    --collect-binaries PySide6 `
    --collect-data PySide6 `
    --collect-data magika `
    packages\markitdown-desktop\src\markitdown_desktop\bootstrap.py

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE."
}

$packagedIcuDlls = Get-ChildItem -Path $appDir -Recurse -Filter "icu*.dll" -File -ErrorAction SilentlyContinue
foreach ($icuDll in $packagedIcuDlls) {
    Remove-Item -LiteralPath $icuDll.FullName -Force
}
if ($packagedIcuDlls.Count -gt 0) {
    Write-Host "Removed bundled ICU DLLs to let Qt use the Windows system ICU runtime."
}

$exePath = Join-Path $appDir "MarkItDownDesktop.exe"
foreach ($smokeTest in @("--smoke-test", "--smoke-test-xlsx")) {
    $launchProcess = Start-Process -FilePath $exePath -ArgumentList $smokeTest -WindowStyle Hidden -PassThru
    $exited = $launchProcess.WaitForExit(30000)
    if (-not $exited) {
        Stop-Process -Id $launchProcess.Id -Force
        throw "Packaged application did not exit during $smokeTest."
    }
    if ($launchProcess.ExitCode -ne 0) {
        throw "Packaged application exited during $smokeTest with exit code $($launchProcess.ExitCode)."
    }
}

if (Test-Path $portableZip) {
    Remove-Item -LiteralPath $portableZip -Force
}
Compress-Archive -Path (Join-Path $appDir "*") -DestinationPath $portableZip -CompressionLevel Optimal
Write-Host "Portable package: $portableZip"

if ($SkipInstaller) {
    Write-Host "Installer build skipped."
    exit 0
}

$isccCommand = Get-Command ISCC.exe -ErrorAction SilentlyContinue
$isccPath = if ($null -ne $isccCommand) { $isccCommand.Source } else { $null }
if ($null -eq $isccPath) {
    $knownPaths = @(
        (Join-Path $repoRoot ".tools\Inno Setup\ISCC.exe"),
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    )
    foreach ($candidate in $knownPaths) {
        if ($candidate -and (Test-Path $candidate)) {
            $isccPath = (Resolve-Path $candidate).Path
            break
        }
    }
}

if ($null -eq $isccPath) {
    Write-Warning "Inno Setup Compiler (ISCC.exe) was not found. Install Inno Setup 6 and rerun this script to produce $installerExe."
    exit 0
}

$isccArgs = @(
    "/DAppVersion=$Version",
    "/DOutputDir=$releaseDir",
    "/DOutputBaseFilename=MarkItDownDesktop-$Version-setup"
)
if ($RepositoryUrl) {
    $isccArgs += "/DRepositoryUrl=$RepositoryUrl"
}
$isccArgs += $installerScript

& $isccPath @isccArgs

if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup failed with exit code $LASTEXITCODE."
}

Write-Host "Installer package: $installerExe"
