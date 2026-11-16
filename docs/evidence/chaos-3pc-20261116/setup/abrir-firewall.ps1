# Abre SOLO para la red de Hamachi (25.0.0.0/8) los puertos que usa k3s.
# Correr en PowerShell COMO ADMINISTRADOR, una vez por PC (las 3).
#requires -RunAsAdministrator
$ErrorActionPreference = 'Stop'
$net = '25.0.0.0/8'
$rules = @(
    @{ Name = 'PharmaGo k3s API (Hamachi)';     Proto = 'TCP'; Port = 6444 },
    @{ Name = 'PharmaGo k3s kubelet (Hamachi)'; Proto = 'TCP'; Port = 10250 },
    @{ Name = 'PharmaGo k3s VXLAN (Hamachi)';   Proto = 'UDP'; Port = 8472 }
)
foreach ($r in $rules) {
    Get-NetFirewallRule -DisplayName $r.Name -ErrorAction SilentlyContinue | Remove-NetFirewallRule
    New-NetFirewallRule -DisplayName $r.Name -Direction Inbound -Protocol $r.Proto -LocalPort $r.Port -RemoteAddress $net -Action Allow | Out-Null
    Write-Host "OK $($r.Name)"
}
# Ping (ICMP) solo desde Hamachi: Windows lo bloquea por defecto en redes publicas
$ping = 'PharmaGo ping (Hamachi)'
Get-NetFirewallRule -DisplayName $ping -ErrorAction SilentlyContinue | Remove-NetFirewallRule
New-NetFirewallRule -DisplayName $ping -Direction Inbound -Protocol ICMPv4 -IcmpType 8 -RemoteAddress $net -Action Allow | Out-Null
Write-Host "OK $ping"
# WSL en modo mirrored pasa ademas por el firewall de Hyper-V
$wslVm = '{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}'
Get-NetFirewallHyperVRule -Name 'pharmago-k3s-hamachi' -ErrorAction SilentlyContinue | Remove-NetFirewallHyperVRule
New-NetFirewallHyperVRule -Name 'pharmago-k3s-hamachi' -DisplayName 'PharmaGo k3s Hamachi' -Direction Inbound -VMCreatorId $wslVm -RemoteAddresses $net -Action Allow | Out-Null
Write-Host 'OK regla Hyper-V para WSL'
Write-Host 'Si usan Avast u otro firewall propio, permitir tambien la red 25.0.0.0/8 ahi y desactivar el analisis HTTPS.'
