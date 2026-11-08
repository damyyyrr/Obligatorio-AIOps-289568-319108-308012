# Python 3.10+; install requirements.txt first. Context is always explicit.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Context,
    [int]$Timeout = 600,
    [string]$OutputPath,
    [string]$Python = 'python'
)
$ErrorActionPreference = 'Stop'
$arguments = @((Join-Path $PSScriptRoot 'manage.py'), 'stop', '--context', $Context, '--timeout', "$Timeout")
if ($OutputPath) { $arguments += @('--output', $OutputPath) }
& $Python @arguments
exit $LASTEXITCODE
