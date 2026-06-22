$ErrorActionPreference = "Stop"

$projectRoot = (Get-Location).Path
Write-Host "=== AVS Gateway v0.3.5 HARD GATE ===" -ForegroundColor Cyan
Write-Host "Project: $projectRoot"

# Clean venv
if (Test-Path ".venv") {
    Remove-Item ".venv" -Recurse -Force
}

py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip | Out-Null
python -m pip install --no-cache-dir -e . | Out-Null
python -m pip install --force-reinstall "pytest<9" | Out-Null

# Path checks
$py = (Get-Command python).Source
$avs = (Get-Command avs).Source

Write-Host "`n[1] Paths"
Write-Host "python: $py"
Write-Host "avs:    $avs"

if ($py -notlike "*$projectRoot*") { throw "Python is not from this project venv." }
if ($avs -notlike "*$projectRoot*") { throw "AVS executable is not from this project venv." }

# Version checks
Write-Host "`n[2] Version checks"

$importOutput = python -c "import avs_gateway; print(avs_gateway.__version__); print(avs_gateway.__file__)" 2>&1
$moduleOutput = python -m avs_gateway.cli version 2>&1
$consoleOutput = avs version 2>&1

Write-Host "Import output:"
$importOutput | ForEach-Object { Write-Host "  $_" }

Write-Host "Module CLI output:"
$moduleOutput | ForEach-Object { Write-Host "  $_" }

Write-Host "Console CLI output:"
$consoleOutput | ForEach-Object { Write-Host "  $_" }

$allVersionText = (($importOutput + $moduleOutput + $consoleOutput) -join "`n")

if ($allVersionText -notmatch "0\.3\.5") { throw "0.3.5 not found in version outputs." }
if ($allVersionText -match "0\.3\.4") { throw "Old version 0.3.4 still appears." }
if ($allVersionText -match "cryptography library not available") { throw "Cryptography mock warning still appears." }
if (($moduleOutput -join "`n") -notmatch [regex]::Escape($projectRoot)) { throw "Module CLI output does not point to projectRoot." }
if (($consoleOutput -join "`n") -notmatch [regex]::Escape($projectRoot)) { throw "Console output does not point to projectRoot." }

# v0.3.6 contamination
Write-Host "`n[3] v0.3.6 contamination check"

$badPaths = @(
    "docs\ASR_1_RECEIPT_STANDARD.md",
    "schemas\asr_1_receipt.schema.json",
    "avs_gateway\receipts\asr1.py",
    "avs_gateway\identity\agent_identity.py",
    "avs_gateway\tools\tool_manifest.py",
    "examples\receipts"
)

foreach ($p in $badPaths) {
    if (Test-Path $p) {
        throw "v0.3.6 contamination found: $p"
    }
}

Write-Host "No v0.3.6 files found." -ForegroundColor Green

# Launch assets
Write-Host "`n[4] Launch assets check"

$laDir = "docs\LAUNCH_ASSETS"
if (-not (Test-Path $laDir)) {
    Write-Host "Could not find docs\LAUNCH_ASSETS. Searching similar folders/files..."
    Get-ChildItem -Recurse -Directory | Where-Object { $_.Name -match "LAUNCH|ASSET" } | Select-Object FullName
    Get-ChildItem -Recurse -File | Where-Object {
        $_.Name -match "GITHUB_RELEASE_NOTES|DEMO_VIDEO_SCRIPT|SHOW_HN|DESIGN_PARTNER|FAQ|COMPETITIVE|README_v0.3.5|STANDING|LINKEDIN"
    } | Select-Object FullName
    throw "docs\LAUNCH_ASSETS is missing."
}

$requiredAssets = @(
    "COMPETITIVE_POSITIONING.md",
    "DEMO_VIDEO_SCRIPT.md",
    "DESIGN_PARTNER_EMAIL.md",
    "FAQ_AND_OBJECTIONS.md",
    "GITHUB_RELEASE_NOTES.md",
    "README_v0.3.5_FINAL.md",
    "SHOW_HN_POST.md",
    "STANDING_WATCH_TEMPLATE.md",
    "X_LINKEDIN_LAUNCH_THREAD.md"
)

foreach ($asset in $requiredAssets) {
    $assetPath = Join-Path $laDir $asset
    if (-not (Test-Path $assetPath)) {
        throw "Missing launch asset: $asset"
    }
}

if (-not (Test-Path "plan-v0.3.5.md")) {
    throw "plan-v0.3.5.md is missing."
}

Write-Host "Launch assets present." -ForegroundColor Green

# Overclaim check
Write-Host "`n[5] Overclaim check"

$overclaims = Select-String -Path ".\README.md", ".\docs\LAUNCH_ASSETS\*.md" -Pattern "world first|official standard|sovereign|insurance-ready|SOC 2 compliant|SOC 2|HIPAA compliant|HIPAA|guaranteed|unhackable" -ErrorAction SilentlyContinue

if ($overclaims) {
    $overclaims | ForEach-Object { Write-Host $_ }
    throw "Overclaim language found."
}

Write-Host "No overclaim language found." -ForegroundColor Green

# Tests
Write-Host "`n[6] Full test suite"

$testOutput = python -m pytest .\avs_gateway\tests -q 2>&1
$pytestExit = $LASTEXITCODE

$testOutput | Select-Object -Last 30 | ForEach-Object { Write-Host "  $_" }

$joined = $testOutput -join "`n"

if ($pytestExit -ne 0) {
    throw "Pytest failed with exit code $pytestExit."
}

if ($joined -notmatch "496 passed") {
    throw "Expected exactly 496 passed, but did not see that pass line."
}

if ($joined -match "\bfailed\b|\berror\b") {
    throw "Pytest output contains failed/error."
}

# Demos
Write-Host "`n[7] CLI demos"

avs demo | Out-Null
avs quickstart | Out-Null

Write-Host "`n=============================================" -ForegroundColor Cyan
Write-Host "  HARD GATE PASSED - v0.3.5 IS LOCKABLE" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Cyan

