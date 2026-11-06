[CmdletBinding()]
param([PSCredential]$DemoCredential, [string]$EvidenceDirectory)

$ErrorActionPreference = 'Stop'
$codeDirectory = Split-Path -Parent $PSScriptRoot
$repositoryDirectory = Split-Path -Parent (Split-Path -Parent $codeDirectory)
if (-not $EvidenceDirectory) {
    $EvidenceDirectory = Join-Path $repositoryDirectory ('docs/evidence/baseline-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
}
New-Item -ItemType Directory -Path $EvidenceDirectory -Force | Out-Null
$checks = [System.Collections.Generic.List[object]]::new()
$runId = 'baseline-' + [Guid]::NewGuid().ToString('N')
$startedAt = [DateTimeOffset]::Now.ToString('o')
$failure = $null
$composeArguments = @('compose', '--project-name', 'pharmago-baseline', '--project-directory', $codeDirectory, '--env-file', (Join-Path $codeDirectory '.env'), '-f', (Join-Path $codeDirectory 'compose.baseline.yaml'))

function Assert-Baseline {
    param([string]$Name, [bool]$Condition, [string]$Detail)
    $checks.Add([pscustomobject]@{name=$Name; passed=$Condition; detail=$Detail})
    if (-not $Condition) { throw "${Name}: $Detail" }
}

function Read-BaselineHttp {
    param([string]$Uri)
    $timer = [Diagnostics.Stopwatch]::StartNew()
    try {
        $response = Invoke-WebRequest -Uri $Uri -Headers @{'X-Correlation-ID'=$runId} -TimeoutSec 15 -UseBasicParsing
        Assert-Baseline -Name $Uri -Condition ($response.StatusCode -eq 200) -Detail "HTTP $($response.StatusCode); $($timer.ElapsedMilliseconds) ms"
        return $response
    } finally { $timer.Stop() }
}

try {
    $frontend = Read-BaselineHttp -Uri 'http://127.0.0.1:4200/'
    Assert-Baseline -Name 'Angular document' -Condition ($frontend.Content -match '<app-root') -Detail 'Frontend serves the Angular entry document; browser interaction is not covered by this HTTP check.'
    $rolesResponse = Read-BaselineHttp -Uri 'http://127.0.0.1:5000/api/roles'
    $roles = @($rolesResponse.Content | ConvertFrom-Json)
    Assert-Baseline -Name 'Gateway -> Users -> SQL' -Condition ($roles.Count -gt 0) -Detail "$($roles.Count) persisted roles returned."
    $drugsResponse = Read-BaselineHttp -Uri 'http://127.0.0.1:5000/api/drug'
    $drugs = @($drugsResponse.Content | ConvertFrom-Json)
    Assert-Baseline -Name 'Gateway -> Pharmacy -> SQL' -Condition ($drugs.Count -gt 0) -Detail "$($drugs.Count) persisted drugs returned."
    Assert-Baseline -Name 'Gateway correlation header' -Condition (($drugsResponse.Headers['X-Correlation-ID'] -join ',') -eq $runId) -Detail 'The gateway preserves the supplied correlation ID.'
    Read-BaselineHttp -Uri 'http://127.0.0.1:9090/-/ready' | Out-Null
    Read-BaselineHttp -Uri 'http://127.0.0.1:3000/api/health' | Out-Null

    if ($DemoCredential) {
        $body = @{userName=$DemoCredential.UserName; password=$DemoCredential.GetNetworkCredential().Password} | ConvertTo-Json
        $login = Invoke-WebRequest -Uri 'http://127.0.0.1:5000/api/login' -Method Post -ContentType 'application/json' -Headers @{'X-Correlation-ID'=$runId} -Body $body -TimeoutSec 15 -UseBasicParsing
        $loginResult = $login.Content | ConvertFrom-Json
        Assert-Baseline -Name 'Persisted demo login through gateway' -Condition ($login.StatusCode -eq 200 -and -not [string]::IsNullOrWhiteSpace($loginResult.token)) -Detail 'Login returned HTTP 200 and a nonempty token. Token and password are not saved.'
        $body = $null
        $loginResult = $null
        $login = $null
        $businessLogs = & docker @composeArguments logs --no-color --no-log-prefix --since 5m pharmago-users-service 2>&1
        if ($LASTEXITCODE -ne 0) { throw 'Could not read Users logs.' }
        $businessEvent = @($businessLogs | Where-Object { "$_".Contains($runId) -and "$_".Contains('Login succeeded') })
        Assert-Baseline -Name 'Correlated business log' -Condition ($businessEvent.Count -gt 0) -Detail 'Users business event contains the gateway correlation ID.'
        $parsedEvent = $businessEvent[-1].ToString() | ConvertFrom-Json
        Assert-Baseline -Name 'JSON log' -Condition ($null -ne $parsedEvent.Message -and $null -ne $parsedEvent.Scopes) -Detail 'Business event parses as JSON and includes structured scopes.'
        $businessEvent[-1].ToString() | Set-Content -LiteralPath (Join-Path $EvidenceDirectory 'login-event.json') -Encoding UTF8
    }

    # Allow at most 45 seconds for the configured 5s scrape interval and exporter collection.
    $deadline = [DateTime]::UtcNow.AddSeconds(45)
    do {
        $targets = Invoke-RestMethod -Uri 'http://127.0.0.1:9090/api/v1/targets' -TimeoutSec 10
        $active = @($targets.data.activeTargets)
        $healthyJobs = @($active | Where-Object health -eq 'up' | ForEach-Object { $_.labels.job })
        $missingJobs = @(@('users-service','pharmacy-service','api-gateway','otlp-collector') | Where-Object { $_ -notin $healthyJobs })
        if ($missingJobs.Count -eq 0) { break }
        Start-Sleep -Seconds 3
    } while ([DateTime]::UtcNow -lt $deadline)
    Assert-Baseline -Name 'Prometheus scrape targets' -Condition ($missingJobs.Count -eq 0) -Detail "Healthy jobs: $($healthyJobs -join ', '); missing: $($missingJobs -join ', ')."
    $active | ForEach-Object { [pscustomobject]@{job=$_.labels.job; health=$_.health; scrapeUrl=$_.scrapeUrl; lastError=$_.lastError} } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $EvidenceDirectory 'prometheus-targets.json') -Encoding UTF8

    $query = 'sum(pharmago_http_requests_total_1{job="api-gateway",endpoint="/api/drug",status_code="200"})'
    $deadline = [DateTime]::UtcNow.AddSeconds(45)
    do {
        $metric = Invoke-RestMethod -Uri ('http://127.0.0.1:9090/api/v1/query?query=' + [Uri]::EscapeDataString($query)) -TimeoutSec 10
        $samples = @($metric.data.result)
        if ($samples.Count -gt 0) { break }
        Start-Sleep -Seconds 3
    } while ([DateTime]::UtcNow -lt $deadline)
    Assert-Baseline -Name 'Successful business request metric' -Condition ($samples.Count -gt 0 -and [double]$samples[0].value[1] -ge 1) -Detail 'Prometheus contains successful /api/drug requests from the gateway; the direct scrape job is selected to avoid double counting.'
    [pscustomobject]@{query=$query; result=$metric.data.result} | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $EvidenceDirectory 'request-metric.json') -Encoding UTF8
} catch {
    $failure = $_.Exception.Message
} finally {
    $commit = & git -C $repositoryDirectory rev-parse HEAD
    $summary = [pscustomobject]@{startedAt=$startedAt; completedAt=[DateTimeOffset]::Now.ToString('o'); sourceCommit=$commit; workingTree='Local baseline changes are uncommitted; see implementation notes.'; runId=$runId; passed=($null -eq $failure); checks=@($checks.ToArray()); failure=$failure; limitations=@('Compose only; Kubernetes and physical-node compliance are not evaluated.', 'HTTP frontend check does not execute Angular in a browser.', 'ELK, complete tracing, alerts, chaos and model evaluation are outside this baseline.')}
    $summary | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $EvidenceDirectory 'summary.json') -Encoding UTF8
    $checks | Format-Table -AutoSize
    Write-Host "Evidence: $EvidenceDirectory"
}
if ($failure) { throw $failure }
