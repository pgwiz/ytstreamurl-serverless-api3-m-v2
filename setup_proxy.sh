#!/bin/bash
# ============================================================
# 🌐 Proxy Server Setup Script
# For: simple_proxy.py (YouTube Bypass Proxy)
# Tested on: Debian/Ubuntu (IPv6 Server with Cloudflare Tunnel)
# ============================================================

set -e  # Exit on error

# --- Configuration ---
PROXY_PORT=2082
INSTALL_DIR="/opt/proxy_server"
SERVICE_NAME="proxy_server"
GITHUB_RAW_URL="https://raw.githubusercontent.com/pgwiz/ytstreamurl-serverless-api3-m-v2/main/simple_proxy.py"

echo "============================================="
echo "  🚀 Proxy Server Setup"
echo "============================================="

# --- 1. Check Python ---
echo "[1/5] Checking Python..."
if command -v python3 &> /dev/null; then
    PYTHON_BIN=$(command -v python3)
    echo "   ✅ Found Python: $PYTHON_BIN"
else
    echo "   ❌ Python3 not found. Installing..."
    apt-get update && apt-get install -y python3
    PYTHON_BIN=$(command -v python3)
fi

# --- 2. Create Install Directory & Download Script ---
echo "[2/5] Setting up installation directory..."
mkdir -p "$INSTALL_DIR"
echo "   📂 $INSTALL_DIR"

ALTERED_FILES=""
TARGET_FILE="$INSTALL_DIR/simple_proxy.py"

# Check if file exists and compare
if [ -f "$TARGET_FILE" ]; then
    OLD_HASH=$(md5sum "$TARGET_FILE" 2>/dev/null | awk '{print $1}')
    echo "   ℹ️  Existing file found. Checking for updates..."
else
    OLD_HASH=""
    echo "   📥 First installation..."
fi

# Force download (always replace)
curl -fsSL "$GITHUB_RAW_URL" -o "$TARGET_FILE.new"

NEW_HASH=$(md5sum "$TARGET_FILE.new" 2>/dev/null | awk '{print $1}')

if [ "$OLD_HASH" != "$NEW_HASH" ]; then
    mv "$TARGET_FILE.new" "$TARGET_FILE"
    chmod +x "$TARGET_FILE"
    if [ -n "$OLD_HASH" ]; then
        echo "   🔄 UPDATED: simple_proxy.py"
        ALTERED_FILES="$ALTERED_FILES simple_proxy.py"
    else
        echo "   ✅ Downloaded: simple_proxy.py"
    fi
else
    rm -f "$TARGET_FILE.new"
    echo "   ✅ No changes: simple_proxy.py (already up-to-date)"
fi

# --- 3. Create Systemd Service ---
echo "[3/5] Creating systemd service..."
cat > /etc/systemd/system/${SERVICE_NAME}.service <<EOF
[Unit]
Description=YouTube Bypass Proxy Server
After=network.target

[Service]
Type=simple
User=nobody
Group=nogroup
WorkingDirectory=$INSTALL_DIR
ExecStart=$PYTHON_BIN $INSTALL_DIR/simple_proxy.py
Restart=always
RestartSec=5
# Memory limit to prevent runaway usage
MemoryMax=128M
MemoryHigh=100M

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable ${SERVICE_NAME}
systemctl restart ${SERVICE_NAME}
echo "   ✅ Service '${SERVICE_NAME}' created and (re)started."

# --- 4. Configure Nginx ---
echo "[4/5] Configuring Nginx..."

# Check if Nginx is installed
if ! command -v nginx &> /dev/null; then
    echo "   📦 Nginx not found. Installing..."
    apt-get update && apt-get install -y nginx
fi

# Detect first available domain from sites-enabled (excluding default)
PROXY_DOMAIN=""
if [ -d /etc/nginx/sites-enabled ]; then
    PROXY_DOMAIN=$(ls /etc/nginx/sites-enabled/ 2>/dev/null | grep -v "default" | grep -v ".backup" | head -1)
fi

if [ -z "$PROXY_DOMAIN" ]; then
    echo "   ⚠️  No domain found. Skipping nginx proxy config."
    echo "   ℹ️  Python proxy is directly accessible on port $PROXY_PORT"
else
    echo "   🌐 Found domain: $PROXY_DOMAIN"
    
    # Create nginx config for the proxy
    NGINX_PROXY_CONF="/etc/nginx/sites-available/proxy-$PROXY_DOMAIN"
    
    cat > "$NGINX_PROXY_CONF" <<EOF
# Proxy server for $PROXY_DOMAIN on port $PROXY_PORT
server {
    listen $PROXY_PORT;
    listen [::]:$PROXY_PORT;
    server_name $PROXY_DOMAIN;

    location / {
        proxy_pass http://127.0.0.1:6178;
        proxy_http_version 1.1;
        proxy_set_header Host \$host:\$server_port;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_connect_timeout 60s;
        proxy_read_timeout 60s;
    }
}
EOF

    # Enable the site
    ln -sf "$NGINX_PROXY_CONF" "/etc/nginx/sites-enabled/proxy-$PROXY_DOMAIN"
    
    # Test and reload nginx
    if nginx -t 2>/dev/null; then
        systemctl reload nginx
        echo "   ✅ Nginx configured: http://$PROXY_DOMAIN:$PROXY_PORT"
    else
        echo "   ❌ Nginx config test failed. Check: nginx -t"
        rm -f "/etc/nginx/sites-enabled/proxy-$PROXY_DOMAIN"
    fi
fi

# --- 5. Verify ---
echo "[5/5] Verifying..."
sleep 2
if systemctl is-active --quiet ${SERVICE_NAME}; then
    echo "   ✅ Proxy service is RUNNING on port $PROXY_PORT"
else
    echo "   ❌ Service failed to start. Check logs: journalctl -u ${SERVICE_NAME}"
fi

echo ""
echo "============================================="
echo "  ✅ Setup Complete!"
echo "============================================="
echo ""

# --- Detect Server IP ---
SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
if [ -z "$SERVER_IP" ]; then
    SERVER_IP="<YOUR_SERVER_IP>"
fi

echo "  Proxy URL: http://${SERVER_IP}:$PROXY_PORT"
echo "  Or via Cloudflare Tunnel."
echo ""

# --- Detect Nginx Domains ---
echo "  📋 Detected Nginx Domains:"
if command -v nginx &> /dev/null; then
    # Get domains from server_name directives
    DOMAINS=$(grep -rh "server_name" /etc/nginx/sites-enabled/ /etc/nginx/conf.d/ 2>/dev/null | \
              grep -v "#" | \
              sed 's/server_name//g' | \
              sed 's/;//g' | \
              tr -s ' ' '\n' | \
              sort -u | \
              grep -v "^$" | \
              grep -v "_" | \
              head -20)
    
    # Also add site-enabled filenames (often the domain name)
    if [ -d /etc/nginx/sites-enabled ]; then
        SITE_FILES=$(ls /etc/nginx/sites-enabled/ 2>/dev/null | grep -v "default" | grep -v ".backup")
        DOMAINS="$DOMAINS $SITE_FILES"
    fi
    
    # Remove duplicates and display
    DOMAINS=$(echo "$DOMAINS" | tr ' ' '\n' | sort -u | grep -v "^$")
    
    if [ -n "$DOMAINS" ]; then
        for domain in $DOMAINS; do
            echo "     - $domain"
        done
    else
        echo "     (No domains found in Nginx config)"
    fi
else
    echo "     (Nginx not installed)"
fi
echo ""

# --- Display Altered Files ---
if [ -n "$ALTERED_FILES" ]; then
    echo "  🔄 Altered Files:"
    for f in $ALTERED_FILES; do
        echo "     - $f"
    done
    echo ""
fi

echo "  Commands:"
echo "    Status:  systemctl status ${SERVICE_NAME}"
echo "    Logs:    journalctl -u ${SERVICE_NAME} -f"
echo "    Restart: systemctl restart ${SERVICE_NAME}"
echo ""
