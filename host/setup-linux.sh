#!/usr/bin/env bash
# ── Pico HID Proxy Setup Script (Linux/macOS) ───────────────────────────────
# Communicates with a Pico HID Proxy device over USB CDC serial.
# Zero dependencies — uses raw /dev/ttyACM* access via stty.

set -euo pipefail

# ── Colors ───────────────────────────────────────────────────────────────────

C_CYAN='\033[36m'
C_GREEN='\033[32m'
C_YELLOW='\033[33m'
C_RED='\033[31m'
C_GRAY='\033[90m'
C_RESET='\033[0m'

# ── Serial helpers ───────────────────────────────────────────────────────────

PORT=""
FD=3

find_pico_port() {
    local devices=()
    for tty in /sys/class/tty/ttyACM*; do
        [ -e "$tty" ] || continue
        local vidfile="$tty/device/../../idVendor"
        [ -f "$vidfile" ] || continue
        local vid
        vid=$(cat "$vidfile" 2>/dev/null) || continue
        if [ "$vid" = "2e8a" ]; then
            devices+=("/dev/$(basename "$tty")")
        fi
    done

    if [ ${#devices[@]} -eq 0 ]; then
        return 1
    fi

    if [ ${#devices[@]} -eq 1 ]; then
        echo "${devices[0]}"
        return 0
    fi

    echo -e "${C_YELLOW}Multiple Pico devices found:${C_RESET}" >&2
    for i in "${!devices[@]}"; do
        echo "  [$((i + 1))] ${devices[$i]}" >&2
    done
    local sel
    while true; do
        read -rp "Select device: " sel
        if [[ "$sel" =~ ^[0-9]+$ ]] && [ "$sel" -ge 1 ] && [ "$sel" -le ${#devices[@]} ]; then
            echo "${devices[$((sel - 1))]}"
            return 0
        fi
    done
}

open_port() {
    stty -F "$PORT" 115200 raw -echo -echoe -echok -echoctl -echoke -icanon -isig min 0 time 1 2>/dev/null
    eval "exec $FD<>\"$PORT\""
    sleep 0.5
    # Drain boot messages
    while IFS= read -r -t 0.1 _ <&$FD 2>/dev/null; do :; done
}

close_port() {
    eval "exec $FD>&-" 2>/dev/null || true
}

send_command() {
    local cmd="$1"
    local timeout_sec="${2:-5}"

    # Drain stale data
    while IFS= read -r -t 0.1 _ <&$FD 2>/dev/null; do :; done

    echo "$cmd" >&$FD

    sleep 0.1

    local lines=()
    local deadline=$((SECONDS + timeout_sec))

    while [ $SECONDS -lt $deadline ]; do
        local line
        if IFS= read -r -t 1 line <&$FD 2>/dev/null; then
            line="${line%$'\r'}"
            line="${line#"${line%%[![:space:]]*}"}"
            line="${line%"${line##*[![:space:]]}"}"
            if [ -n "$line" ]; then
                lines+=("$line")
            fi
        else
            if [ ${#lines[@]} -gt 0 ]; then
                break
            fi
        fi
    done

    local IFS=$'\n'
    echo "${lines[*]}"
}

get_device_status() {
    send_command "status"
}

# ── Display helpers ──────────────────────────────────────────────────────────

print_status_line() {
    local line="$1"
    case "$line" in
        wifi:*connected\ ip=*)  echo -e "  ${C_GREEN}${line}${C_RESET}" ;;
        wifi:*)                 echo -e "  ${C_YELLOW}${line}${C_RESET}" ;;
        api:*enabled*)          echo -e "  ${C_GREEN}${line}${C_RESET}" ;;
        api:*)                  echo -e "  ${C_YELLOW}${line}${C_RESET}" ;;
        webui:*enabled*)        echo -e "  ${C_GREEN}${line}${C_RESET}" ;;
        webui:*)                echo -e "  ${C_YELLOW}${line}${C_RESET}" ;;
        *)                      echo "  $line" ;;
    esac
}

response_has_ok() {
    echo "$1" | grep -q '^OK'
}

press_enter() {
    read -rp "Press Enter to continue"
}

# ── Main menu ────────────────────────────────────────────────────────────────

show_main_menu() {
    while true; do
        clear
        echo -e "${C_CYAN}========================================${C_RESET}"
        echo -e "${C_CYAN}          Pico HID Proxy Setup${C_RESET}"
        echo -e "${C_CYAN}========================================${C_RESET}"
        echo

        local status
        status=$(get_device_status)
        if [ -n "$status" ]; then
            while IFS= read -r l; do
                print_status_line "$l"
            done <<< "$status"
        else
            echo -e "  ${C_RED}(could not read status)${C_RESET}"
        fi

        echo
        echo -e "${C_GRAY}----------------------------------------${C_RESET}"
        echo "  [1] Setup Wizard  (first-time setup)"
        echo "  [2] WiFi"
        echo "  [3] API & Web UI"
        echo "  [4] Exit"
        echo -e "${C_CYAN}========================================${C_RESET}"
        echo

        read -rp "Select option: " choice
        case "$choice" in
            1) setup_wizard ;;
            2) wifi_menu ;;
            3) api_menu ;;
            4) return ;;
        esac
    done
}

# ── Setup wizard ─────────────────────────────────────────────────────────────

setup_wizard() {
    clear
    echo -e "${C_CYAN}========================================${C_RESET}"
    echo -e "${C_CYAN}          Setup Wizard${C_RESET}"
    echo -e "${C_CYAN}========================================${C_RESET}"
    echo
    echo "This wizard will help you configure your Pico HID Proxy device."
    echo

    # Step 1 — WiFi
    echo -e "${C_YELLOW}--- Step 1: WiFi ---${C_RESET}"
    local wifi_connected=false
    while [ "$wifi_connected" = false ]; do
        read -rp "Enter WiFi SSID: " ssid
        read -rp "Enter WiFi password: " pass
        if [ -z "$ssid" ] || [ -z "$pass" ]; then
            echo -e "${C_RED}SSID and password are required.${C_RESET}"
            continue
        fi

        echo -n "Saving credentials..."
        local r
        r=$(send_command "wifi set $ssid $pass")
        echo " $r"

        echo "Connecting to WiFi (this may take up to 15 seconds)..."
        r=$(send_command "wifi connect" 20)
        if response_has_ok "$r"; then
            echo -e "${C_GREEN}${r}${C_RESET}"
            wifi_connected=true
        else
            echo -e "${C_RED}${r}${C_RESET}"
            echo
            echo -e "${C_YELLOW}Connection failed. Please check your credentials and try again.${C_RESET}"
            read -rp "Retry? (y/n): " retry
            if [ "$retry" != "y" ] && [ "$retry" != "Y" ]; then
                echo -e "${C_YELLOW}Skipping WiFi setup.${C_RESET}"
                break
            fi
        fi
    done

    echo

    # Step 2 — Enable API?
    echo -e "${C_YELLOW}--- Step 2: Enable API? ---${C_RESET}"
    read -rp "Enable API? (y/n): " enable_api
    echo

    # Step 3 — Enable Web UI?
    echo -e "${C_YELLOW}--- Step 3: Enable Web UI? ---${C_RESET}"
    read -rp "Enable Web UI? (y/n): " enable_webui

    local want_api=false want_webui=false
    [[ "$enable_api" == [yY] ]] && want_api=true
    [[ "$enable_webui" == [yY] ]] && want_webui=true

    # Step 4 — API token (only if needed)
    if [ "$want_api" = true ] || [ "$want_webui" = true ]; then
        echo
        echo -e "${C_YELLOW}--- Step 4: API Token ---${C_RESET}"
        echo "An API token is required to authenticate requests."
        read -rp "Enter API token: " token
        if [ -n "$token" ]; then
            local r
            r=$(send_command "api token $token")
            echo -e "${C_GREEN}${r}${C_RESET}"

            if [ "$want_webui" = true ]; then
                r=$(send_command "webui enable")
                echo -e "${C_GREEN}${r}${C_RESET}"
            elif [ "$want_api" = true ]; then
                r=$(send_command "api enable")
                echo -e "${C_GREEN}${r}${C_RESET}"
            fi
        else
            echo -e "${C_YELLOW}No token provided. Skipping API/WebUI enable.${C_RESET}"
        fi
    fi

    echo

    # Final status
    echo -e "${C_YELLOW}--- Final Status ---${C_RESET}"
    local status
    status=$(get_device_status)
    if [ -n "$status" ]; then
        while IFS= read -r l; do
            echo "  $l"
        done <<< "$status"
    fi
    echo
    echo -e "${C_GREEN}Setup complete!${C_RESET}"
    read -rp "Press Enter to return to main menu"
}

# ── WiFi menu ────────────────────────────────────────────────────────────────

wifi_menu() {
    while true; do
        clear
        echo -e "${C_CYAN}--- WiFi ---${C_RESET}"
        echo

        local wifi_status
        wifi_status=$(send_command "wifi status")
        if [ -n "$wifi_status" ]; then
            if echo "$wifi_status" | grep -q 'connected ip='; then
                echo -e "  Status: ${C_GREEN}${wifi_status}${C_RESET}"
            else
                echo -e "  Status: ${C_YELLOW}${wifi_status}${C_RESET}"
            fi
        else
            echo -e "  Status: ${C_YELLOW}unknown${C_RESET}"
        fi

        echo
        echo "  [1] Connect to WiFi"
        echo "  [2] Disconnect"
        echo "  [3] Clear Saved Credentials"
        echo "  [4] Back"
        echo

        read -rp "Select option: " choice
        case "$choice" in
            1)
                echo
                local connected=false
                while [ "$connected" = false ]; do
                    read -rp "Enter WiFi SSID: " ssid
                    read -rp "Enter WiFi password: " pass
                    if [ -z "$ssid" ] || [ -z "$pass" ]; then
                        echo -e "${C_RED}SSID and password are required.${C_RESET}"
                        continue
                    fi

                    local r
                    r=$(send_command "wifi set $ssid $pass")
                    echo "$r"

                    echo "Connecting (up to 15 seconds)..."
                    r=$(send_command "wifi connect" 20)
                    if response_has_ok "$r"; then
                        echo -e "${C_GREEN}${r}${C_RESET}"
                        connected=true
                    else
                        echo -e "${C_RED}${r}${C_RESET}"
                        read -rp "Retry? (y/n): " retry
                        if [ "$retry" != "y" ] && [ "$retry" != "Y" ]; then
                            break
                        fi
                    fi
                done
                press_enter
                ;;
            2)
                local r
                r=$(send_command "wifi disconnect")
                echo -e "${C_GREEN}${r}${C_RESET}"
                press_enter
                ;;
            3)
                local r
                r=$(send_command "wifi clear")
                echo -e "${C_GREEN}${r}${C_RESET}"
                press_enter
                ;;
            4) return ;;
        esac
    done
}

# ── API & Web UI menu ───────────────────────────────────────────────────────

api_menu() {
    while true; do
        clear
        echo -e "${C_CYAN}--- API & Web UI ---${C_RESET}"
        echo

        local api_status webui_status
        api_status=$(send_command "api status")
        webui_status=$(send_command "webui status")

        local api_enabled=false webui_enabled=false
        echo "$api_status" | grep -q 'enabled' && api_enabled=true
        echo "$webui_status" | grep -q 'enabled' && webui_enabled=true

        local api_color="$C_YELLOW" webui_color="$C_YELLOW"
        [ "$api_enabled" = true ] && api_color="$C_GREEN"
        [ "$webui_enabled" = true ] && webui_color="$C_GREEN"

        echo -e "  API:    ${api_color}${api_status}${C_RESET}"
        echo -e "  WebUI:  ${webui_color}${webui_status}${C_RESET}"
        echo

        local api_toggle_label webui_toggle_label
        if [ "$api_enabled" = true ]; then
            api_toggle_label="Disable API"
        else
            api_toggle_label="Enable API"
        fi
        if [ "$webui_enabled" = true ]; then
            webui_toggle_label="Disable Web UI"
        else
            webui_toggle_label="Enable Web UI"
        fi

        echo "  [1] Set API Token"
        echo "  [2] $api_toggle_label"
        echo "  [3] $webui_toggle_label"
        echo "  [4] Back"
        echo

        read -rp "Select option: " choice
        case "$choice" in
            1)
                echo
                read -rp "Enter API token: " token
                if [ -n "$token" ]; then
                    local r
                    r=$(send_command "api token $token")
                    echo -e "${C_GREEN}${r}${C_RESET}"
                else
                    echo -e "${C_YELLOW}No token entered.${C_RESET}"
                fi
                press_enter
                ;;
            2)
                local r
                if [ "$api_enabled" = true ]; then
                    r=$(send_command "api disable")
                else
                    r=$(send_command "api enable")
                fi
                if response_has_ok "$r"; then
                    echo -e "${C_GREEN}${r}${C_RESET}"
                else
                    echo -e "${C_RED}${r}${C_RESET}"
                fi
                press_enter
                ;;
            3)
                local r
                if [ "$webui_enabled" = true ]; then
                    r=$(send_command "webui disable")
                else
                    r=$(send_command "webui enable")
                fi
                if response_has_ok "$r"; then
                    echo -e "${C_GREEN}${r}${C_RESET}"
                else
                    echo -e "${C_RED}${r}${C_RESET}"
                fi
                press_enter
                ;;
            4) return ;;
        esac
    done
}

# ── Entry point ──────────────────────────────────────────────────────────────

PORT=$(find_pico_port 2>&1) || true
if [ -z "$PORT" ]; then
    echo
    echo -e "${C_RED}ERROR: No Pico device found!${C_RESET}"
    echo
    echo -e "${C_YELLOW}Troubleshooting:${C_RESET}"
    echo "  - Make sure the Pico is plugged in via USB"
    echo "  - Check that the firmware has been flashed"
    echo "  - Try a different USB cable (some are charge-only)"
    echo "  - Check: ls /dev/ttyACM*"
    echo
    exit 1
fi

# Check permissions
if [ ! -r "$PORT" ] || [ ! -w "$PORT" ]; then
    echo
    echo -e "${C_RED}ERROR: No permission to access $PORT${C_RESET}"
    echo
    echo -e "${C_YELLOW}Fix options:${C_RESET}"
    echo "  1) Add yourself to the dialout group (recommended, requires re-login):"
    echo "       sudo usermod -aG dialout \$USER"
    echo "  2) Run this script with sudo:"
    echo "       sudo $0"
    echo
    read -rp "Try running with sudo now? (y/n): " use_sudo
    if [ "$use_sudo" = "y" ] || [ "$use_sudo" = "Y" ]; then
        exec sudo "$0" "$@"
    fi
    exit 1
fi

echo -e "Connecting to Pico on ${PORT}..."

open_port

trap close_port EXIT

# Verify device responds
r=$(send_command "ping")
if ! echo "$r" | grep -q 'PONG'; then
    echo -e "${C_YELLOW}WARNING: Device did not respond to ping. It may still be booting.${C_RESET}"
    sleep 2
    r=$(send_command "ping")
    if ! echo "$r" | grep -q 'PONG'; then
        echo -e "${C_RED}ERROR: Device is not responding.${C_RESET}"
        exit 1
    fi
fi

show_main_menu

echo
echo -e "${C_GREEN}Disconnected. Goodbye!${C_RESET}"
