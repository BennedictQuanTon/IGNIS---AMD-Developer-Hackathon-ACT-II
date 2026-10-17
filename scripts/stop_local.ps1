$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$stateFile = Join-Path $projectRoot 'outputs\local-session.json'
if (-not (Test-Path -LiteralPath $stateFile)) { Write-Output 'No local session is recorded.'; exit 0 }
$session = Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json
$allProcesses = @(Get-CimInstance Win32_Process)
function Stop-SessionTree([int]$rootProcessId, [string]$identity) {
    $rootProcess = $allProcesses | Where-Object { $_.ProcessId -eq $rootProcessId } | Select-Object -First 1
    if (-not $rootProcess) { return }
    if (-not $rootProcess.CommandLine -or -not $rootProcess.CommandLine.Contains($identity)) { throw "Process $rootProcessId no longer matches this session; preserved." }
    $processIds = [System.Collections.Generic.List[int]]::new()
    $processIds.Add($rootProcessId)
    for ($index=0; $index -lt $processIds.Count; $index++) {
        foreach ($child in $allProcesses | Where-Object { $_.ParentProcessId -eq $processIds[$index] }) { $processIds.Add([int]$child.ProcessId) }
    }
    for ($index=$processIds.Count-1; $index -ge 0; $index--) { Stop-Process -Id $processIds[$index] -Force -ErrorAction SilentlyContinue }
}
Stop-SessionTree ([int]$session.backendPid) ([string]$session.dataDirectory)
Stop-SessionTree ([int]$session.frontendPid) ([string]$session.project)
Move-Item -LiteralPath $stateFile -Destination (Join-Path $session.directory 'stopped-session.json')
Write-Output "Stopped local services. Database, reports and logs remain in $($session.dataDirectory)."
