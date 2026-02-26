<# :
@echo off
title Pico HID Setup
powershell -ExecutionPolicy Bypass -NoProfile -Command "& ([scriptblock]::Create((Get-Content -LiteralPath '%~f0' -Raw)))"
pause
goto :EOF
#>

# ── Pico HID Setup Script ──────────────────────────────────────────────────────
# Batch/PowerShell polyglot: double-click the .bat to run.
# Communicates with a Pico HID device over USB CDC serial.

$ErrorActionPreference = 'Stop'
$script:port = $null

function Read-Input($prompt) {
    Write-Host "${prompt}: " -NoNewline
    return [Console]::ReadLine()
}

# ── Serial helpers ──────────────────────────────────────────────────────────────

function Find-PicoPort {
    $devices = Get-CimInstance Win32_PnPEntity |
        Where-Object { $_.Name -match 'COM\d+' -and $_.DeviceID -match 'VID_2E8A' }
    if (-not $devices) { return $null }

    $devList = @($devices)
    if ($devList.Count -eq 1) {
        if ($devList[0].Name -match '\((COM\d+)\)') { return $Matches[1] }
    }

    Write-Host 'Multiple Pico devices found:' -ForegroundColor Yellow
    for ($i = 0; $i -lt $devList.Count; $i++) {
        Write-Host ('  [' + ($i + 1) + '] ' + $devList[$i].Name)
    }
    do {
        $sel = Read-Host 'Select device'
        $idx = [int]$sel - 1
    } while ($idx -lt 0 -or $idx -ge $devList.Count)

    if ($devList[$idx].Name -match '\((COM\d+)\)') { return $Matches[1] }
    return $null
}

function Open-PicoPort($comName) {
    $p = New-Object System.IO.Ports.SerialPort $comName, 115200
    $p.ReadTimeout  = 5000
    $p.WriteTimeout = 5000
    $p.NewLine      = "`n"
    $p.DtrEnable    = $true
    $p.Open()
    Start-Sleep -Milliseconds 500
    # Drain any boot messages
    while ($p.BytesToRead -gt 0) { $p.ReadExisting() | Out-Null }
    return $p
}

function Send-Command {
    param(
        [string]$cmd,
        [int]$timeoutMs = 5000
    )
    $oldTimeout = $script:port.ReadTimeout
    $script:port.ReadTimeout = $timeoutMs
    try {
        # Drain stale data
        while ($script:port.BytesToRead -gt 0) { $script:port.ReadExisting() | Out-Null }

        $script:port.WriteLine($cmd)
        Start-Sleep -Milliseconds 100

        $lines = @()
        $deadline = [DateTime]::Now.AddMilliseconds($timeoutMs)

        while ([DateTime]::Now -lt $deadline) {
            try {
                $line = $script:port.ReadLine().Trim()
                if ($line) { $lines += $line }

                if ($script:port.BytesToRead -eq 0) {
                    Start-Sleep -Milliseconds 50
                    if ($script:port.BytesToRead -eq 0) { break }
                }
            }
            catch [System.TimeoutException] { break }
        }

        return ($lines -join "`n")
    }
    finally {
        $script:port.ReadTimeout = $oldTimeout
    }
}

function Get-DeviceStatus {
    return Send-Command 'status'
}

# ── Main menu ───────────────────────────────────────────────────────────────────

function Show-MainMenu {
    while ($true) {
        Clear-Host
        Write-Host '========================================' -ForegroundColor Cyan
        Write-Host '          Pico HID Setup'               -ForegroundColor Cyan
        Write-Host '========================================' -ForegroundColor Cyan
        Write-Host ''

        $status = Get-DeviceStatus
        if ($status) {
            foreach ($l in $status.Split("`n")) {
                $l = $l.Trim()
                if ($l -match '^wifi:') {
                    $color = if ($l -match 'connected ip=') { 'Green' } else { 'Yellow' }
                    Write-Host "  $l" -ForegroundColor $color
                }
                elseif ($l -match '^api:') {
                    $color = if ($l -match 'enabled') { 'Green' } else { 'Yellow' }
                    Write-Host "  $l" -ForegroundColor $color
                }
                elseif ($l -match '^webui:') {
                    $color = if ($l -match 'enabled') { 'Green' } else { 'Yellow' }
                    Write-Host "  $l" -ForegroundColor $color
                }
                else {
                    Write-Host "  $l"
                }
            }
        }
        else {
            Write-Host '  (could not read status)' -ForegroundColor Red
        }

        Write-Host ''
        Write-Host '----------------------------------------' -ForegroundColor DarkGray
        Write-Host '  [1] Setup Wizard  (first-time setup)'
        Write-Host '  [2] WiFi'
        Write-Host '  [3] API & Web UI'
        Write-Host '  [4] Exit'
        Write-Host '========================================' -ForegroundColor Cyan
        Write-Host ''

        $choice = Read-Host 'Select option'
        switch ($choice) {
            '1' { Start-SetupWizard }
            '2' { Show-WifiMenu }
            '3' { Show-ApiMenu }
            '4' { return }
        }
    }
}

# ── Setup wizard ────────────────────────────────────────────────────────────────

function Start-SetupWizard {
    Clear-Host
    Write-Host '========================================' -ForegroundColor Cyan
    Write-Host '          Setup Wizard'                  -ForegroundColor Cyan
    Write-Host '========================================' -ForegroundColor Cyan
    Write-Host ''
    Write-Host 'This wizard will help you configure your Pico HID device.' -ForegroundColor White
    Write-Host ''

    # Step 1 — WiFi
    Write-Host '--- Step 1: WiFi ---' -ForegroundColor Yellow
    $wifiConnected = $false
    while (-not $wifiConnected) {
        $ssid = Read-Input 'Enter WiFi SSID'
        $pass = Read-Input 'Enter WiFi password'
        if (-not $ssid -or -not $pass) {
            Write-Host 'SSID and password are required.' -ForegroundColor Red
            continue
        }

        Write-Host 'Saving credentials...' -NoNewline
        $r = Send-Command "wifi set $ssid $pass"
        Write-Host " $r"

        Write-Host 'Connecting to WiFi (this may take up to 15 seconds)...' -ForegroundColor White
        $r = Send-Command 'wifi connect' 20000
        if ($r -match '(?m)^OK') {
            Write-Host $r -ForegroundColor Green
            $wifiConnected = $true
        }
        else {
            Write-Host $r -ForegroundColor Red
            Write-Host ''
            Write-Host 'Connection failed. Please check your credentials and try again.' -ForegroundColor Yellow
            $retry = Read-Host 'Retry? (y/n)'
            if ($retry -ne 'y' -and $retry -ne 'Y') {
                Write-Host 'Skipping WiFi setup.' -ForegroundColor Yellow
                break
            }
        }
    }

    Write-Host ''

    # Step 2 — Enable API?
    Write-Host '--- Step 2: Enable API? ---' -ForegroundColor Yellow
    $enableApi = Read-Host 'Enable API? (y/n)'
    Write-Host ''

    # Step 3 — Enable Web UI?
    Write-Host '--- Step 3: Enable Web UI? ---' -ForegroundColor Yellow
    $enableWebui = Read-Host 'Enable Web UI? (y/n)'

    $wantApi   = ($enableApi   -eq 'y' -or $enableApi   -eq 'Y')
    $wantWebui = ($enableWebui -eq 'y' -or $enableWebui -eq 'Y')

    # Step 4 — API token (only if needed)
    if ($wantApi -or $wantWebui) {
        Write-Host ''
        Write-Host '--- Step 4: API Token ---' -ForegroundColor Yellow
        Write-Host 'An API token is required to authenticate requests.' -ForegroundColor White
        $token = Read-Input 'Enter API token'
        if ($token) {
            $r = Send-Command "api token $token"
            Write-Host $r -ForegroundColor Green

            if ($wantWebui) {
                $r = Send-Command 'webui enable'
                Write-Host $r -ForegroundColor Green
            }
            elseif ($wantApi) {
                $r = Send-Command 'api enable'
                Write-Host $r -ForegroundColor Green
            }
        }
        else {
            Write-Host 'No token provided. Skipping API/WebUI enable.' -ForegroundColor Yellow
        }
    }

    Write-Host ''

    # Final status
    Write-Host '--- Final Status ---' -ForegroundColor Yellow
    $status = Get-DeviceStatus
    if ($status) {
        foreach ($l in $status.Split("`n")) {
            Write-Host "  $($l.Trim())"
        }
    }
    Write-Host ''
    Write-Host 'Setup complete!' -ForegroundColor Green
    Read-Host 'Press Enter to return to main menu'
}

# ── WiFi menu ───────────────────────────────────────────────────────────────────

function Show-WifiMenu {
    while ($true) {
        Clear-Host
        Write-Host '--- WiFi ---' -ForegroundColor Cyan
        Write-Host ''

        $wifiStatus = Send-Command 'wifi status'
        if ($wifiStatus) {
            $color = if ($wifiStatus -match 'connected ip=') { 'Green' } else { 'Yellow' }
            Write-Host "  Status: $wifiStatus" -ForegroundColor $color
        }
        else {
            Write-Host '  Status: unknown' -ForegroundColor Yellow
        }

        Write-Host ''
        Write-Host '  [1] Connect to WiFi'
        Write-Host '  [2] Disconnect'
        Write-Host '  [3] Clear Saved Credentials'
        Write-Host '  [4] Back'
        Write-Host ''

        $choice = Read-Host 'Select option'
        switch ($choice) {
            '1' {
                Write-Host ''
                $connected = $false
                while (-not $connected) {
                    $ssid = Read-Input 'Enter WiFi SSID'
                    $pass = Read-Input 'Enter WiFi password'
                    if (-not $ssid -or -not $pass) {
                        Write-Host 'SSID and password are required.' -ForegroundColor Red
                        continue
                    }

                    $r = Send-Command "wifi set $ssid $pass"
                    Write-Host $r

                    Write-Host 'Connecting (up to 15 seconds)...' -ForegroundColor White
                    $r = Send-Command 'wifi connect' 20000
                    if ($r -match '(?m)^OK') {
                        Write-Host $r -ForegroundColor Green
                        $connected = $true
                    }
                    else {
                        Write-Host $r -ForegroundColor Red
                        $retry = Read-Host 'Retry? (y/n)'
                        if ($retry -ne 'y' -and $retry -ne 'Y') { break }
                    }
                }
                Read-Host 'Press Enter to continue'
            }
            '2' {
                $r = Send-Command 'wifi disconnect'
                Write-Host $r -ForegroundColor Green
                Read-Host 'Press Enter to continue'
            }
            '3' {
                $r = Send-Command 'wifi clear'
                Write-Host $r -ForegroundColor Green
                Read-Host 'Press Enter to continue'
            }
            '4' { return }
        }
    }
}

# ── API & Web UI menu ──────────────────────────────────────────────────────────

function Show-ApiMenu {
    while ($true) {
        Clear-Host
        Write-Host '--- API & Web UI ---' -ForegroundColor Cyan
        Write-Host ''

        $apiStatus   = Send-Command 'api status'
        $webuiStatus = Send-Command 'webui status'
        $apiEnabled   = $apiStatus   -match 'enabled'
        $webuiEnabled = $webuiStatus -match 'enabled'

        $apiColor   = if ($apiEnabled)   { 'Green' } else { 'Yellow' }
        $webuiColor = if ($webuiEnabled) { 'Green' } else { 'Yellow' }

        Write-Host "  API:    $apiStatus"   -ForegroundColor $apiColor
        Write-Host "  WebUI:  $webuiStatus" -ForegroundColor $webuiColor
        Write-Host ''

        $apiToggleLabel   = if ($apiEnabled)   { 'Disable API' }    else { 'Enable API' }
        $webuiToggleLabel = if ($webuiEnabled) { 'Disable Web UI' } else { 'Enable Web UI' }

        Write-Host '  [1] Set API Token'
        Write-Host "  [2] $apiToggleLabel"
        Write-Host "  [3] $webuiToggleLabel"
        Write-Host '  [4] Back'
        Write-Host ''

        $choice = Read-Host 'Select option'
        switch ($choice) {
            '1' {
                Write-Host ''
                $token = Read-Input 'Enter API token'
                if ($token) {
                    $r = Send-Command "api token $token"
                    Write-Host $r -ForegroundColor Green
                }
                else {
                    Write-Host 'No token entered.' -ForegroundColor Yellow
                }
                Read-Host 'Press Enter to continue'
            }
            '2' {
                if ($apiEnabled) { $r = Send-Command 'api disable' }
                else             { $r = Send-Command 'api enable' }
                if ($r -match '(?m)^OK') { Write-Host $r -ForegroundColor Green }
                else                 { Write-Host $r -ForegroundColor Red }
                Read-Host 'Press Enter to continue'
            }
            '3' {
                if ($webuiEnabled) { $r = Send-Command 'webui disable' }
                else               { $r = Send-Command 'webui enable' }
                if ($r -match '(?m)^OK') { Write-Host $r -ForegroundColor Green }
                else                 { Write-Host $r -ForegroundColor Red }
                Read-Host 'Press Enter to continue'
            }
            '4' { return }
        }
    }
}

# ── Entry point ─────────────────────────────────────────────────────────────────

$comPort = Find-PicoPort
if (-not $comPort) {
    Write-Host ''
    Write-Host 'ERROR: No Pico device found!' -ForegroundColor Red
    Write-Host ''
    Write-Host 'Troubleshooting:' -ForegroundColor Yellow
    Write-Host '  - Make sure the Pico is plugged in via USB'
    Write-Host '  - Check that the firmware has been flashed'
    Write-Host '  - Try a different USB cable (some are charge-only)'
    Write-Host '  - Check Device Manager for the COM port'
    Write-Host ''
    Read-Host 'Press Enter to exit'
    exit 1
}

Write-Host "Connecting to Pico on $comPort..." -ForegroundColor White
try {
    $script:port = Open-PicoPort $comPort
}
catch {
    Write-Host ''
    Write-Host "ERROR: Could not open ${comPort}: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ''
    Write-Host 'Make sure no other program (e.g. host.py, PuTTY) is using the port.' -ForegroundColor Yellow
    Write-Host ''
    Read-Host 'Press Enter to exit'
    exit 1
}

# Verify the device responds
$r = Send-Command 'ping'
if ($r -notmatch 'PONG') {
    Write-Host 'WARNING: Device did not respond to ping. It may still be booting.' -ForegroundColor Yellow
    Start-Sleep -Seconds 2
    $r = Send-Command 'ping'
    if ($r -notmatch 'PONG') {
        Write-Host 'ERROR: Device is not responding.' -ForegroundColor Red
        $script:port.Close()
        Read-Host 'Press Enter to exit'
        exit 1
    }
}

try {
    Show-MainMenu
}
finally {
    if ($script:port -and $script:port.IsOpen) { $script:port.Close() }
}

Write-Host ''
Write-Host 'Disconnected. Goodbye!' -ForegroundColor Green
