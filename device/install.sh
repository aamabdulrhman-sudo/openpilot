#!/usr/bin/env bash
# ==============================================================================
# FreePilots Comma Auto-Installer & Activator
# For Comma 3 / 3X / Comma Four running Sunnypilot / AGNOS
# ==============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${CYAN}====================================================${NC}"
echo -e "${GREEN}     FreePilots Private Vault Client Installer      ${NC}"
echo -e "${CYAN}   Private Dashcam & Drive Archive for Sunnypilot  ${NC}"
echo -e "${CYAN}====================================================${NC}"

SERVER_URL="https://dash.aaam.sa"
VAULT_TOKEN="freepilot_secret_token_2026"
BLOCK_COMMA="y"
DELETE_LOCAL="n"

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --url) SERVER_URL="$2"; shift ;;
        --token) VAULT_TOKEN="$2"; shift ;;
        --block-comma) BLOCK_COMMA="$2"; shift ;;
        --delete-after-upload) DELETE_LOCAL="$2"; shift ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

echo -e "\n${YELLOW}[1/2] Server URL:${NC} $SERVER_URL"
echo -e "${YELLOW}[2/2] Security Token:${NC} [CONFIGURED]"

# Clean trailing slash
SERVER_URL="${SERVER_URL%/}"

echo -e "\n${CYAN}Configuring Comma parameters...${NC}"

# Configure Native Sunnypilot Parameters
mkdir -p /data/params/d
echo -n "1" > /data/params/d/FreePilotsVaultEnabled
echo -n "$SERVER_URL" > /data/params/d/FreePilotsVaultUrl
echo -n "$VAULT_TOKEN" > /data/params/d/FreePilotsVaultToken

# Create FreePilots directory
mkdir -p /data/freepilots

# Write config file
cat <<EOF > /data/freepilots.json
{
  "server": "$SERVER_URL",
  "token": "$VAULT_TOKEN",
  "delete_after_upload": $([ "$DELETE_LOCAL" == "y" ] && echo "true" || echo "false")
}
EOF

echo -e "${GREEN}[OK] Native parameters saved in /data/params/d/${NC}"
echo -e "${GREEN}[OK] Configuration saved to /data/freepilots.json${NC}"

# Download sync daemon
curl -sSL "https://raw.githubusercontent.com/aamabdulrhman-sudo/openpilot/master/device/freepilot_sync.py" -o /data/freepilots/freepilot_sync.py
chmod +x /data/freepilots/freepilot_sync.py

# Optional 100% Privacy Protection
if [ "$BLOCK_COMMA" == "y" ]; then
    echo -e "\n${YELLOW}Enforcing 100% Privacy: Blocking api.commadotai.com in /etc/hosts...${NC}"
    if ! grep -q "api.commadotai.com" /etc/hosts; then
        echo "127.0.0.1 api.commadotai.com" >> /etc/hosts || sudo sh -c 'echo "127.0.0.1 api.commadotai.com" >> /etc/hosts'
        echo -e "${GREEN}[OK] Comma Cloud upload blocked! Footage will only go to your private vault.${NC}"
    else
        echo -e "${GREEN}[OK] Comma Cloud was already blocked.${NC}"
    fi
fi

# Create background service in AGNOS/Sunnypilot
SERVICE_FILE="/etc/systemd/system/freepilot.service"

if [ -d "/etc/systemd/system" ]; then
    sudo bash -c "cat <<EOF > $SERVICE_FILE
[Unit]
Description=FreePilots Private Vault Uploader
After=network.target

[Service]
Type=simple
User=comma
WorkingDirectory=/data/freepilots
ExecStart=/usr/bin/python3 /data/freepilots/freepilot_sync.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF"

    sudo systemctl daemon-reload
    sudo systemctl enable freepilot.service
    sudo systemctl restart freepilot.service
    echo -e "${GREEN}[OK] Systemd background service enabled and started!${NC}"
else
    echo -e "${YELLOW}Starting FreePilots in background...${NC}"
    nohup python3 /data/freepilots/freepilot_sync.py > /data/freepilots/sync.log 2>&1 &
fi

echo -e "\n${GREEN}====================================================${NC}"
echo -e "${GREEN}🎉 FreePilots Installation Complete!${NC}"
echo -e "${CYAN}Your Comma device is now paired with: ${SERVER_URL}${NC}"
echo -e "${CYAN}Drive recordings will stream to your private vault.${NC}"
echo -e "${GREEN}====================================================${NC}\n"
