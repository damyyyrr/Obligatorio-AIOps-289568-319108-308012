$ErrorActionPreference = 'Stop'
$codeDirectory = Split-Path -Parent $PSScriptRoot
& docker compose --project-name pharmago-baseline --project-directory $codeDirectory --env-file (Join-Path $codeDirectory '.env') -f (Join-Path $codeDirectory 'compose.baseline.yaml') stop
if ($LASTEXITCODE -ne 0) { throw 'Could not stop the baseline containers.' }
Write-Host 'Baseline stopped. Containers and named volumes were preserved.'
