[CmdletBinding()]
param([switch]$SkipBuild, [switch]$SeedDemoData)

$ErrorActionPreference = 'Stop'
$codeDirectory = Split-Path -Parent $PSScriptRoot
$composeArguments = @('compose', '--project-name', 'pharmago-baseline', '--project-directory', $codeDirectory, '--env-file', (Join-Path $codeDirectory '.env'), '-f', (Join-Path $codeDirectory 'compose.baseline.yaml'))

function Invoke-BaselineCompose {
    param([string[]]$ComposeCommand)
    & docker @composeArguments @ComposeCommand
    if ($LASTEXITCODE -ne 0) { throw "Docker Compose failed: $($ComposeCommand[0]) (exit $LASTEXITCODE). Existing volumes were preserved." }
}

function Wait-BaselineHttp {
    param([string]$Uri, [int]$TimeoutSeconds = 180)
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $Uri -TimeoutSec 5 -UseBasicParsing
            if ($response.StatusCode -eq 200) { return }
        } catch { Start-Sleep -Seconds 3 }
    }
    throw "HTTP readiness timed out: $Uri. Inspect Compose logs before retrying."
}

& docker info --format '{{.ServerVersion}}' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Docker Linux engine is unavailable. Start Docker Desktop and retry.' }
$dockerMemory = & docker info --format '{{.MemTotal}}'
if ($LASTEXITCODE -ne 0 -or [long]$dockerMemory -lt 3.5GB) {
    throw 'This baseline needs at least 3.5 GiB assigned to the Linux engine (3.25 GiB container limits plus overhead). Check available host capacity before changing Docker resources.'
}
if (-not $SkipBuild) {
    $runningBaseline = @(& docker ps --filter 'label=com.docker.compose.project=pharmago-baseline' --format '{{.Names}}')
    if ($LASTEXITCODE -ne 0) { throw 'Could not check running baseline containers.' }
    if ($runningBaseline.Count -gt 0) {
        throw 'Baseline is already running. Use -SkipBuild, or stop this baseline before building to avoid memory pressure.'
    }
}

$envPath = Join-Path $codeDirectory '.env'
if (-not (Test-Path -LiteralPath $envPath)) {
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $secretBytes = New-Object byte[] 24
        $rng.GetBytes($secretBytes)
        $dbPassword = 'Pg!' + ([BitConverter]::ToString($secretBytes) -replace '-', '') + 'a9'
        $rng.GetBytes($secretBytes)
        $grafanaPassword = 'Gf!' + ([BitConverter]::ToString($secretBytes) -replace '-', '') + 'a9'
        [System.IO.File]::WriteAllText($envPath, "PHARMAGO_DB_PASSWORD=$dbPassword`nPHARMAGO_GRAFANA_PASSWORD=$grafanaPassword`n", [System.Text.UTF8Encoding]::new($false))
    } finally { $rng.Dispose() }
    Write-Host 'Created ignored .env with random passwords. Existing .env files are never overwritten.'
}
Invoke-BaselineCompose -ComposeCommand @('config', '--quiet')

if (-not $SkipBuild) {
    # One image at a time; do not run four compilers concurrently on an 8 GB host.
    foreach ($service in @('pharmago-users-service', 'pharmago-pharmacy-service', 'pharmago-api-gateway', 'pharmago-ui')) {
        Invoke-BaselineCompose -ComposeCommand @('build', $service)
    }
}

Invoke-BaselineCompose -ComposeCommand @('up', '-d', '--no-build', '--wait', '--wait-timeout', '240', 'pharmago-db', 'otlp-collector')
Invoke-BaselineCompose -ComposeCommand @('up', '-d', '--no-build', 'pharmago-users-service')
Wait-BaselineHttp -Uri 'http://127.0.0.1:5001/api/roles'

if ($SeedDemoData) {
    # Explicit opt-in for this isolated baseline database. The supplied seed only inserts missing demo rows.
    $seed = Get-Content -LiteralPath (Join-Path $codeDirectory 'Backend/seed-data.sql') -Raw -Encoding UTF8
    $sqlCommand = 'export SQLCMDPASSWORD="$MSSQL_SA_PASSWORD"; if [ -x /opt/mssql-tools18/bin/sqlcmd ]; then exec /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -C -b -d PharmaDb; else exec /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -b -d PharmaDb; fi'
    $seed | & docker @composeArguments exec -T pharmago-db sh -c $sqlCommand
    if ($LASTEXITCODE -ne 0) { throw 'Demo seed failed. Inspect the output; data was not reset.' }
}

Invoke-BaselineCompose -ComposeCommand @('up', '-d', '--no-build', 'pharmago-pharmacy-service', 'pharmago-api-gateway', 'pharmago-ui', 'prometheus', 'grafana')
foreach ($uri in @('http://127.0.0.1:5002/health', 'http://127.0.0.1:5000/api/drug', 'http://127.0.0.1:4200/', 'http://127.0.0.1:9090/-/ready', 'http://127.0.0.1:3000/api/health')) {
    Wait-BaselineHttp -Uri $uri
}
Invoke-BaselineCompose -ComposeCommand @('ps')
Write-Host 'Baseline HTTP checks passed. Run scripts/smoke-baseline.ps1 to record functional and telemetry evidence.'
