# Home Assistant OS - Hyper-V VM Setup Script
# Run this script as Administrator in PowerShell

$ErrorActionPreference = "Stop"

$VMName = "HomeAssistant"
$VHDXPath = "$PSScriptRoot\haos_ova-17.0.vhdx"
$SwitchName = "HA-External"

Write-Host "=== Home Assistant Hyper-V Setup ===" -ForegroundColor Cyan

# Step 1: Check for existing VM
$existingVM = Get-VM -Name $VMName -ErrorAction SilentlyContinue
if ($existingVM) {
    Write-Host "VM '$VMName' already exists. Removing..." -ForegroundColor Yellow
    Stop-VM -Name $VMName -Force -ErrorAction SilentlyContinue
    Remove-VM -Name $VMName -Force
}

# Step 2: Create External Virtual Switch (bridged to LAN)
$existingSwitch = Get-VMSwitch -Name $SwitchName -ErrorAction SilentlyContinue
if (-not $existingSwitch) {
    Write-Host "Creating External Virtual Switch..." -ForegroundColor Green

    # Find the physical network adapter (prefer Ethernet, fall back to Wi-Fi)
    $adapter = Get-NetAdapter -Physical | Where-Object { $_.Status -eq "Up" } |
        Sort-Object @{Expression={if ($_.Name -match "Ethernet") {0} else {1}}} |
        Select-Object -First 1

    if (-not $adapter) {
        Write-Error "No active physical network adapter found!"
        exit 1
    }

    Write-Host "Using adapter: $($adapter.Name) ($($adapter.InterfaceDescription))" -ForegroundColor Yellow
    Write-Host "WARNING: This may briefly disconnect your network." -ForegroundColor Red

    New-VMSwitch -Name $SwitchName -NetAdapterName $adapter.Name -AllowManagementOS $true
    Write-Host "External switch created." -ForegroundColor Green
} else {
    Write-Host "External switch '$SwitchName' already exists." -ForegroundColor Green
}

# Step 3: Create the VM
Write-Host "Creating VM '$VMName'..." -ForegroundColor Green
New-VM -Name $VMName `
    -Generation 2 `
    -MemoryStartupBytes 2GB `
    -VHDPath $VHDXPath `
    -SwitchName $SwitchName

# Step 4: Configure VM settings
Write-Host "Configuring VM..." -ForegroundColor Green

# Assign 2 CPU cores
Set-VM -Name $VMName -ProcessorCount 2

# Enable dynamic memory (2GB-4GB)
Set-VM -Name $VMName -DynamicMemory -MemoryMinimumBytes 2GB -MemoryMaximumBytes 4GB

# Disable Secure Boot (required for HA OS)
Set-VMFirmware -VMName $VMName -EnableSecureBoot Off

# Enable automatic start
Set-VM -Name $VMName -AutomaticStartAction Start -AutomaticStartDelay 30
Set-VM -Name $VMName -AutomaticStopAction ShutDown

# Step 5: Start the VM
Write-Host "Starting VM..." -ForegroundColor Green
Start-VM -Name $VMName

Write-Host ""
Write-Host "=== Setup Complete ===" -ForegroundColor Cyan
Write-Host "Home Assistant OS is booting up. It will take a few minutes for initial setup." -ForegroundColor Yellow
Write-Host ""
Write-Host "The VM will get an IP from your router via DHCP." -ForegroundColor Yellow
Write-Host "To find its IP, check your router's DHCP leases or run:" -ForegroundColor Yellow
Write-Host "  Get-VM -Name $VMName | Get-VMNetworkAdapter | Select-Object IPAddresses" -ForegroundColor White
Write-Host ""
Write-Host "Once you have the IP, access Home Assistant at:" -ForegroundColor Yellow
Write-Host "  http://<IP>:8123" -ForegroundColor White
