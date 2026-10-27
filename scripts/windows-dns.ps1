param(
    [switch]$Apply,
    [Parameter(Mandatory = $true)][string]$LocalAddress,
    [Parameter(Mandatory = $true)][string]$DnsServer,
    [Parameter(Mandatory = $true)][string]$PublicDomain
)
$ErrorActionPreference = 'Stop'
$active = Get-NetIPConfiguration | Where-Object { $_.IPv4Address.IPAddress -eq $LocalAddress }
if (@($active).Count -ne 1) { throw 'Interface Minisforum LAN non identifiee de maniere unique.' }
if ($Apply) {
    $admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $admin) { throw 'Executer Ansible depuis une session Windows administrateur pour modifier les DNS.' }
    $dnsBefore = @((Get-DnsClientServerAddress -InterfaceIndex $active.InterfaceIndex).ServerAddresses)
    if (($dnsBefore -join ',') -ne $DnsServer) {
        Set-DnsClientServerAddress -InterfaceIndex $active.InterfaceIndex -ServerAddresses $DnsServer
        Write-Output 'CHANGED'
    }
}
Get-DnsClientServerAddress -InterfaceIndex $active.InterfaceIndex | Select-Object InterfaceAlias,AddressFamily,ServerAddresses
Resolve-DnsName "grafana.$PublicDomain" -Server $DnsServer -DnsOnly | Select-Object Name,IPAddress
