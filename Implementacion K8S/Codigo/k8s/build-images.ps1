# Python 3.10+; install requirements.txt first. Context is always explicit.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Context,
    [Parameter(Mandatory=$true)][string]$ImageTag,
    [Parameter(Mandatory=$true)][string]$Profile,
    [int]$Timeout = 600,
    [string]$OutputPath,
    [string]$Python = 'python'
)
$ErrorActionPreference = 'Stop'
$arguments = @((Join-Path $PSScriptRoot 'manage.py'), 'build', '--context', $Context, '--timeout', "$Timeout")
$arguments += @('--image-tag', $ImageTag)
$arguments += @('--profile', $Profile)
if ($OutputPath) { $arguments += @('--output', $OutputPath) }
& $Python @arguments
exit $LASTEXITCODE
