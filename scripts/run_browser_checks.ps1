param([switch]$Headed, [switch]$InstallBrowser, [switch]$ListOnly)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$previousUv = $env:IGNIS_UV
$previousCommit = $env:IGNIS_TEST_COMMIT
$previousChannel = $env:IGNIS_BROWSER_CHANNEL
try {
    $env:IGNIS_UV = (Get-Command uv.exe -ErrorAction SilentlyContinue).Source
    if (-not $env:IGNIS_UV) { $env:IGNIS_UV = Join-Path $env:USERPROFILE '.local\bin\uv.exe' }
    $env:IGNIS_TEST_COMMIT = ((& git -C $projectRoot rev-parse HEAD).Trim() + '; local uncommitted changes apply')
    Push-Location (Join-Path $projectRoot 'frontend')
    if ($InstallBrowser) {
        & npx.cmd playwright install chromium
        if ($LASTEXITCODE -ne 0) { throw 'Browser installation failed.' }
        $env:IGNIS_BROWSER_CHANNEL = 'chromium'
    }
    $testArgs = @('run', 'test:e2e', '--')
    if ($Headed) { $testArgs += '--headed' }
    if ($ListOnly) { $testArgs += '--list' }
    & npm.cmd @testArgs
    if ($LASTEXITCODE -ne 0) { throw 'Browser checks failed or are blocked. Inspect frontend/playwright-report.' }
} finally { Pop-Location; $env:IGNIS_UV=$previousUv; $env:IGNIS_TEST_COMMIT=$previousCommit; $env:IGNIS_BROWSER_CHANNEL=$previousChannel }
