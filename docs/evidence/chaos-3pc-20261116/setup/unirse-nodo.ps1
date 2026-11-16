# Une esta PC al cluster PharmaGo (k3s) por Hamachi como nodo agent.
# Uso (PowerShell normal, NO hace falta admin):
#   .\unirse-nodo.ps1 -NodeName pharmago-b -MemoryGB 6     # compa con 16 GB
#   .\unirse-nodo.ps1 -NodeName pharmago-c -MemoryGB 3     # compa con 8 GB
# Antes: Hamachi encendido, en la misma red, con IPv4 (25.x.x.x), y haber corrido abrir-firewall.ps1 como admin.
param(
    [Parameter(Mandatory)][ValidateSet('pharmago-b', 'pharmago-c')][string]$NodeName,
    [Parameter(Mandatory)][ValidateRange(2, 12)][int]$MemoryGB,
    [string]$ServerIp = '25.21.165.40',
    [int]$ServerPort = 6444
)
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$distro = 'Ubuntu-24.04'
$tar = Join-Path $here 'pharmago-images-k8s-20261116-01.tar'
$tokenFile = Join-Path $here 'TOKEN-privado.txt'

foreach ($f in $tar, $tokenFile) { if (-not (Test-Path $f)) { throw "Falta $f en la carpeta del script" } }

# 1. IP de Hamachi
$myIp = (Get-NetIPAddress -InterfaceAlias Hamachi -AddressFamily IPv4 -ErrorAction SilentlyContinue).IPAddress
if (-not $myIp) { throw 'Hamachi sin IPv4: encenderlo y activar IPv4 en Preferencias > Configuracion > Modo de protocolo IP' }
Write-Host "IP Hamachi: $myIp"
if (-not (Test-NetConnection $ServerIp -Port $ServerPort -InformationLevel Quiet -WarningAction SilentlyContinue)) { throw "No se llega a ${ServerIp}:$ServerPort (server). Misma red de Hamachi? El de la PC A corrio abrir-firewall.ps1?" }

# 2. .wslconfig con red espejada (se guarda copia del anterior)
$cfg = Join-Path $HOME '.wslconfig'
if (Test-Path $cfg) { Copy-Item $cfg "$cfg.bak-pharmago" -Force; Write-Host "Copia del .wslconfig anterior en $cfg.bak-pharmago" }
@"
[wsl2]
memory=${MemoryGB}GB
swap=8GB
networkingMode=mirrored

[experimental]
autoMemoryReclaim=dropCache
hostAddressLoopback=true
"@ | Set-Content -Encoding ascii $cfg

# 3. WSL actualizado + Ubuntu como root con systemd
wsl.exe --update
wsl.exe --shutdown
$installed = ((wsl.exe -l -q) -replace "`0", '') -contains $distro
if (-not $installed) { wsl.exe --install -d $distro --no-launch }
wsl.exe -d $distro -u root -- bash -c "printf '[boot]\nsystemd=true\n[user]\ndefault=root\n' > /etc/wsl.conf"
wsl.exe --terminate $distro

# 4. Interfaz de Hamachi dentro de Ubuntu
$iface = (wsl.exe -d $distro -u root -- bash -c "ip -o -4 addr | awk '/ $myIp\//{print `$2}'") -replace "`0", ''
$iface = "$iface".Trim()
if (-not $iface) { throw 'Ubuntu no ve la IP de Hamachi: revisar networkingMode=mirrored y reiniciar la PC' }
Write-Host "Interfaz Hamachi en WSL: $iface"

# 5. k3s agent
$token = (Get-Content $tokenFile -Raw).Trim()
$cmd = "curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION='v1.34.1+k3s1' K3S_URL='https://${ServerIp}:${ServerPort}' K3S_TOKEN='$token' sh -s - agent --node-name $NodeName --node-ip $myIp --flannel-iface $iface"
wsl.exe -d $distro -u root -- bash -c $cmd

# 6. Imagenes de PharmaGo
$wslTar = (wsl.exe -d $distro -u root -- wslpath -a "$tar") -replace "`0", ''
wsl.exe -d $distro -u root -- bash -c "sha256sum '$($wslTar.Trim())'; k3s ctr -n k8s.io images import '$($wslTar.Trim())' && k3s crictl images | grep pharmago"

# 7. WSL apaga Ubuntu (y k3s) cuando no hay sesiones: dejar un proceso que lo mantenga vivo
Start-Process wsl.exe -ArgumentList '-d', $distro, '-u', 'root', '--', 'sleep', 'infinity' -WindowStyle Hidden
Write-Host 'Si reinicias la PC, volver a correr: Start-Process wsl.exe -ArgumentList ''-d'',''Ubuntu-24.04'',''-u'',''root'',''--'',''sleep'',''infinity'' -WindowStyle Hidden'

Write-Host "`nListo. Avisale al de la PC A que corra: kubectl --context pharmago-hamachi get nodes"
Write-Host 'Dejá la PC prendida, sin suspender y con Hamachi conectado mientras corran las pruebas.'
