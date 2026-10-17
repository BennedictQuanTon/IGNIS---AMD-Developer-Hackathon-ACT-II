param([int]$BackendPort = 8765, [int]$FrontendPort = 5173, [string]$ResumeDataDirectory)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$outputsRoot = Join-Path $projectRoot 'outputs'
$stateFile = Join-Path $outputsRoot 'local-session.json'
if (Test-Path -LiteralPath $stateFile) { throw 'A local session is already recorded. Run scripts/stop_local.ps1 first.' }
foreach ($localPort in @($BackendPort, $FrontendPort)) {
    if (Get-NetTCPConnection -State Listen -LocalPort $localPort -ErrorAction SilentlyContinue) { throw "Port $localPort is occupied; existing services were preserved." }
}
$uvCommand = (Get-Command uv.exe -ErrorAction SilentlyContinue).Source
if (-not $uvCommand) { $uvCommand = Join-Path $env:USERPROFILE '.local\bin\uv.exe' }
if (-not (Test-Path -LiteralPath $uvCommand)) { throw 'Install uv or place uv.exe on PATH first.' }
$nodeCommand = (Get-Command node.exe).Source
$viteScript = Join-Path $projectRoot 'frontend\node_modules\vite\bin\vite.js'
if (-not (Test-Path -LiteralPath $viteScript)) { throw 'Run npm ci in frontend first.' }
$sessionRoot = Join-Path $outputsRoot ('local-sessions\' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N').Substring(0, 6))
$dataDirectory = Join-Path $sessionRoot 'backend'
if ($ResumeDataDirectory) {
    $dataDirectory = (Resolve-Path -LiteralPath $ResumeDataDirectory).Path
    $allowedPrefix = [IO.Path]::GetFullPath($outputsRoot) + [IO.Path]::DirectorySeparatorChar
    if (-not $dataDirectory.StartsWith($allowedPrefix, [StringComparison]::OrdinalIgnoreCase) -or -not (Test-Path -LiteralPath (Join-Path $dataDirectory 'state.sqlite3'))) {
        throw 'ResumeDataDirectory must be under this checkout outputs folder and contain state.sqlite3.'
    }
}
New-Item -ItemType Directory -Path $sessionRoot -Force | Out-Null
function Quote-Arg([string]$value) { return '"' + $value.Replace('"', '\"') + '"' }
$backendArgs = @('run','--no-project','--with-requirements','requirements-dev.txt','python','-u','scripts/serve_hosted.py',
    '--replay-dir','docs/benchmarks/replay','--port',"$BackendPort",'--db',(Join-Path $dataDirectory 'state.sqlite3'),'--data',$dataDirectory)
$backend = Start-Process -FilePath $uvCommand -ArgumentList (($backendArgs | ForEach-Object { Quote-Arg $_ }) -join ' ') -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $sessionRoot 'backend.stdout.log') -RedirectStandardError (Join-Path $sessionRoot 'backend.stderr.log')
$previousProxy = $env:IGNIS_API_PROXY
$previousBase = $env:VITE_API_BASE
try {
    $env:IGNIS_API_PROXY = "http://127.0.0.1:$BackendPort"
    $env:VITE_API_BASE = '/api'
    $frontendArgs = @($viteScript, '--host','127.0.0.1','--port',"$FrontendPort",'--strictPort')
    $frontend = Start-Process -FilePath $nodeCommand -ArgumentList (($frontendArgs | ForEach-Object { Quote-Arg $_ }) -join ' ') -WorkingDirectory (Join-Path $projectRoot 'frontend') -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $sessionRoot 'frontend.stdout.log') -RedirectStandardError (Join-Path $sessionRoot 'frontend.stderr.log')
} finally { $env:IGNIS_API_PROXY = $previousProxy; $env:VITE_API_BASE = $previousBase }
$session = [ordered]@{ project=$projectRoot; sourceCommit=(& git -C $projectRoot rev-parse HEAD).Trim(); workingTreeModified=[bool](& git -C $projectRoot status --porcelain);
    directory=$sessionRoot; dataDirectory=$dataDirectory; backendPid=$backend.Id; frontendPid=$frontend.Id;
    backendUrl="http://127.0.0.1:$BackendPort"; frontendUrl="http://127.0.0.1:$FrontendPort"; mode='hosted_replay'; liveModelCalls=0 }
$session | ConvertTo-Json | Set-Content -LiteralPath $stateFile -Encoding utf8
$ready = $false
for ($attempt=0; $attempt -lt 30; $attempt++) {
    try {
        $health = Invoke-RestMethod -Uri ($session.frontendUrl + '/api/health') -TimeoutSec 2
        $front = Invoke-WebRequest -Uri $session.frontendUrl -TimeoutSec 2 -UseBasicParsing
        if ($health.status -eq 'ready' -and $front.StatusCode -eq 200) { $ready=$true; break }
    } catch { Start-Sleep -Seconds 1 }
}
if (-not $ready) { throw "Startup failed. Inspect $sessionRoot and use scripts/stop_local.ps1 to stop this session." }
$session | ConvertTo-Json
