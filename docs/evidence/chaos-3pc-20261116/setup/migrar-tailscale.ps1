# Pasa el nodo de esta PC de Hamachi a Tailscale (dentro de Ubuntu/WSL). No toca Windows.
# Uso:  powershell -NoProfile -ExecutionPolicy Bypass -File migrar-tailscale.ps1 -NodeName pharmago-b
param([Parameter(Mandatory)][ValidateSet('pharmago-b', 'pharmago-c')][string]$NodeName)
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$distro = 'Ubuntu-24.04'
$serverIp = '100.114.33.19'

function Invoke-Wsl([string]$Command) {
    wsl.exe -d $distro -u root -- bash -c $Command
    if ($LASTEXITCODE -ne 0) { throw "Fallo un paso dentro de Ubuntu (codigo $LASTEXITCODE). Mandar foto de esta ventana." }
}

foreach ($f in 'migrate-node.sh', 'TOKEN-privado.txt', 'TAILSCALE-KEY.txt') {
    if (-not (Test-Path (Join-Path $here $f))) { throw "Falta $f en la carpeta" }
}
$installed = ((wsl.exe -l -q) -replace "`0", '') -contains $distro
if (-not $installed) { throw "No existe $distro en WSL: primero hay que haber corrido unirse-nodo.ps1" }

$dir = ((wsl.exe -d $distro -u root -- wslpath -a "$here") -replace "`0", '').Trim()
if ($LASTEXITCODE -ne 0 -or -not $dir) { throw 'No se pudo traducir la ruta de la carpeta a WSL' }

# Claves a archivos con permiso 600, sin pasarlas por la linea de comandos
Invoke-Wsl "tr -d '\r\n' < '$dir/TAILSCALE-KEY.txt' > /root/.ts-key && tr -d '\r\n' < '$dir/TOKEN-privado.txt' > /root/.k3s-token && chmod 600 /root/.ts-key /root/.k3s-token && tr -d '\r' < '$dir/migrate-node.sh' > /root/migrate-node.sh"
Invoke-Wsl "bash /root/migrate-node.sh $NodeName $serverIp"

Write-Host "`nListo: migracion completa. Dejá abierta la otra ventana (la de 'NODO ACTIVO')."
