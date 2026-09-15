param([switch]$Apply)
$ErrorActionPreference = 'Stop'
$active = Get-NetIPConfiguration | Where-Object { $_.IPv4Address.IPAddress -eq 'MINISFORUM_IP' }
if (@($active).Count -ne 1) { throw 'Interface Minisforum LAN non identifiee de maniere unique.' }
if ($Apply) {
    $admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $admin) { throw 'Executer Ansible depuis une session Windows administrateur pour modifier les DNS.' }
    $dnsBefore = @((Get-DnsClientServerAddress -InterfaceIndex $active.InterfaceIndex).ServerAddresses)
    if (($dnsBefore -join ',') -ne 'NAS_IP') {
        Set-DnsClientServerAddress -InterfaceIndex $active.InterfaceIndex -ServerAddresses 'NAS_IP'
        Write-Output 'CHANGED'
    }
}
Get-DnsClientServerAddress -InterfaceIndex $active.InterfaceIndex | Select-Object InterfaceAlias,AddressFamily,ServerAddresses
Resolve-DnsName grafana.PUBLIC_DOMAIN -Server NAS_IP -DnsOnly | Select-Object Name,IPAddress
