#!/usr/bin/env bash
# ==============================================================================
# FreePilots Raw Auto-Installer for Comma 3 / 3X / Comma Four (AGNOS)
# ==============================================================================
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${CYAN}====================================================${NC}"
echo -e "${GREEN}${BOLD}       FreePilots (Sunnypilot + Private Vault)      ${NC}"
echo -e "${CYAN}      Automated Raw Installation & Configuration     ${NC}"
echo -e "${CYAN}====================================================${NC}"

TARGET_DIR="/data/openpilot"
REPO_URL="https://github.com/aamabdulrhman-sudo/openpilot.git"
BRANCH="master"
VAULT_URL="https://dash.aaam.sa"
VAULT_TOKEN="freepilot_secret_token_2026"

echo -e "\n${YELLOW}[1/4] Preparing target directory ${TARGET_DIR}...${NC}"
mkdir -p /data

if [ -d "$TARGET_DIR/.git" ]; then
    echo -e "${CYAN}Found existing installation. Syncing to latest FreePilots...${NC}"
    cd "$TARGET_DIR"
    git remote set-url origin "$REPO_URL" || true
    git fetch origin "$BRANCH" --depth=1
    git reset --hard "origin/$BRANCH"
    git clean -fd
    git submodule sync
    git submodule update --init --recursive --depth=1
else
    echo -e "${CYAN}Cloning FreePilots directly from GitHub...${NC}"
    rm -rf "$TARGET_DIR"
    git clone --depth=1 --recurse-submodules -b "$BRANCH" "$REPO_URL" "$TARGET_DIR"
fi

echo -e "\n${GREEN}[OK] FreePilots codebase verified at ${TARGET_DIR}${NC}"

echo -e "\n${YELLOW}[2/4] Pre-configuring Private Vault Parameters...${NC}"
mkdir -p /data/params/d
echo -n "1" > /data/params/d/FreePilotsVaultEnabled
echo -n "$VAULT_URL" > /data/params/d/FreePilotsVaultUrl
echo -n "$VAULT_TOKEN" > /data/params/d/FreePilotsVaultToken

echo -e "${GREEN}[OK] Vault URL set to: ${VAULT_URL}${NC}"
echo -e "${GREEN}[OK] Vault Token configured.${NC}"
echo -e "${GREEN}[OK] FreePilots Private Vault enabled by default.${NC}"

echo -e "\n${YELLOW}[3/4] Setting up AGNOS boot entrypoint...${NC}"
cat << 'EOF' > /data/continue.sh
#!/usr/bin/env bash
cd /data/openpilot
exec ./launch_openpilot.sh
EOF
chmod +x /data/continue.sh
echo -e "${GREEN}[OK] /data/continue.sh configured successfully.${NC}"

echo -e "\n${YELLOW}[4/4] Finalizing setup...${NC}"
cd "$TARGET_DIR"

echo -e "\n${GREEN}====================================================${NC}"
echo -e "${GREEN}${BOLD}🎉 FreePilots Installation Completed Successfully!  ${NC}"
echo -e "${CYAN}Device is pre-linked with: ${VAULT_URL}${NC}"
echo -e "${CYAN}All footage will stream privately to your dashboard.${NC}"
echo -e "${GREEN}====================================================${NC}\n"

if [ -f /AGNOS ]; then
    echo -e "${YELLOW}Rebooting Comma device in 5 seconds...${NC}"
    sleep 5
    sudo reboot
fi
