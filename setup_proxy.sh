#!/bin/bash
# ============================================================
# 🌐 Proxy Server Setup Script
# For: simple_proxy.py (YouTube Bypass Proxy)
# Tested on: Debian/Ubuntu (IPv6 Server with Cloudflare Tunnel)
# ============================================================

set -e  # Exit on error

# --- Configuration ---
PROXY_PORT=2082       # External Port (Cloudflare supported)
INTERNAL_PORT=6178    # Internal Python Port
INSTALL_DIR="/opt/proxy_server"
SERVICE_NAME="proxy_server"
GITHUB_RAW_URL="https://raw.githubusercontent.com/pgwiz/ytstreamurl-serverless-api3-m-v2/main/simple_proxy.py"

echo "============================================="
echo "  🚀 Proxy Server Setup"
echo "============================================="

# --- 1. Check Python ---
echo "[1/5] Checking Python..."

# Check if Python 3.11+ is available
PYTHON_BIN=""
for py_cmd in python3.11 python3.12 python3.13 python3; do
    if command -v $py_cmd &> /dev/null; then
        PY_VERSION=$($py_cmd --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
        PY_MAJOR=$(echo $PY_VERSION | cut -d. -f1)
        PY_MINOR=$(echo $PY_VERSION | cut -d. -f2)
        
        if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 10 ]; then
            PYTHON_BIN=$(command -v $py_cmd)
            echo "   ✅ Found Python $PY_VERSION: $PYTHON_BIN"
            break
        fi
    fi
done

# Install Python 3.11 if needed
if [ -z "$PYTHON_BIN" ]; then
    echo "   ⚠️  Python 3.10+ not found. Installing Python 3.11..."
    
    # Clean up any stale Ubuntu PPAs (if this is Debian)
    if [ -f /etc/debian_version ] && [ ! -f /etc/lsb-release ]; then
        echo "   🧹 Removing stale Ubuntu PPAs..."
        rm -f /etc/apt/sources.list.d/*deadsnakes* 2>/dev/null
        rm -f /etc/apt/sources.list.d/*ppa* 2>/dev/null
    fi
    
    # Detect OS
    DISTRO_ID=$(grep "^ID=" /etc/os-release | cut -d= -f2 | tr -d '"')
    
    if [ "$DISTRO_ID" = "debian" ]; then
        # Debian-based system
        echo "   📦 Detected Debian system"
        
        # Try installing from Debian testing (simplest method)
        apt-get update
        apt-get install -y wget build-essential libssl-dev zlib1g-dev \
            libncurses5-dev libncursesw5-dev libreadline-dev libsqlite3-dev \
            libgdbm-dev libdb5.3-dev libbz2-dev libexpat1-dev liblzma-dev \
            libffi-dev uuid-dev
        
        # Download and compile Python 3.11
        cd /tmp
        wget https://www.python.org/ftp/python/3.11.7/Python-3.11.7.tgz
        tar -xzf Python-3.11.7.tgz
        cd Python-3.11.7
        ./configure --enable-optimizations --prefix=/usr/local
        make -j$(nproc)
        make altinstall  # altinstall to not override system python3
        cd /
        rm -rf /tmp/Python-3.11.7*
        
        PYTHON_BIN="/usr/local/bin/python3.11"
    elif [ "$DISTRO_ID" = "ubuntu" ]; then
        # Ubuntu-based system
        echo "   📦 Detected Ubuntu system"
        apt-get update
        apt-get install -y software-properties-common
        add-apt-repository -y ppa:deadsnakes/ppa
        apt-get update
        apt-get install -y python3.11
        PYTHON_BIN=$(command -v python3.11)
    else
        # Fallback or other Debian derivatives
        echo "   ⚠️ Unknown distro ID: $DISTRO_ID. Assuming apt-compatible."
        apt-get update
        apt-get install -y software-properties-common
        # Try adding PPA anyway as fallback, or instruct user
        add-apt-repository -y ppa:deadsnakes/ppa 2>/dev/null || true
        apt-get update
        apt-get install -y python3.11
        PYTHON_BIN=$(command -v python3.11)
    fi
    
    if [ -z "$PYTHON_BIN" ] || [ ! -f "$PYTHON_BIN" ]; then
        echo "   ❌ Failed to install Python 3.11"
        exit 1
    fi
    
    echo "   ✅ Installed Python 3.11: $PYTHON_BIN"
fi

# --- 1b. Install yt-dlp ---
echo "   📦 Checking yt-dlp..."
if command -v yt-dlp &> /dev/null; then
    echo "   ✅ yt-dlp already installed"
else
    echo "   📥 Installing yt-dlp..."
    curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp
    chmod a+rx /usr/local/bin/yt-dlp
    echo "   ✅ yt-dlp installed"
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
# Append random query param to bypass GitHub Raw caching
echo "   ⬇️  Downloading simple_proxy.py..."
# Force fresh download by appending timestamp
curl -fsSL -o "$TARGET_FILE.new" "https://raw.githubusercontent.com/pgwiz/ytstreamurl-serverless-api3-m-v2/main/simple_proxy.py?t=$(date +%s)"

# Check if file changed
if [ ! -f "$TARGET_FILE" ]; then
    mv "$TARGET_FILE.new" "$TARGET_FILE"
    echo "   ✅ Installed simple_proxy.py"
else
    # Simple check if content differs (ignoring timestamp comment if any)
    if ! cmp -s "$TARGET_FILE" "$TARGET_FILE.new"; then
        echo "   🔄 Updating simple_proxy.py (content changed)..."
        mv "$TARGET_FILE.new" "$TARGET_FILE"
        systemctl restart ${SERVICE_NAME}
    else
        rm -f "$TARGET_FILE.new"
        echo "   ✅ No changes: simple_proxy.py (already up-to-date)"
    fi
fi

# --- 3. Create Systemd Service ---
echo "[3/5] Creating systemd service..."
cat > /etc/systemd/system/${SERVICE_NAME}.service <<EOF
[Unit]
Description=YouTube Bypass Proxy Server
After=network.target

[Service]
Type=simple
User=root
Group=root
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

# --- 3b. Configure Firewall (UFW) ---
if command -v ufw &> /dev/null; then
    echo "[3b/5] Configuring Firewall..."
    if ufw status | grep -q "Active"; then
        echo "   🛡️  UFW is active. Allowing port $PROXY_PORT..."
        ufw allow $PROXY_PORT/tcp
        ufw allow 80/tcp
        ufw allow 443/tcp
        ufw reload
    else
        echo "   ℹ️  UFW is inactive. Skipping firewall rules."
    fi
fi

# --- 4. Configure Nginx ---
echo "[4/5] Configuring Nginx..."

# Check if Nginx is installed
if ! command -v nginx &> /dev/null; then
    echo "   📦 Nginx not found. Installing..."
    apt-get update && apt-get install -y nginx
fi

# Cleanup Recursive Configs
echo "   🧹 Cleaning up old proxy configs..."
rm -f /etc/nginx/sites-enabled/proxy-* 2>/dev/null
rm -f /etc/nginx/sites-available/proxy-* 2>/dev/null
# Restart to clear them from memory before re-adding
rm -f /etc/nginx/sites-enabled/default 2>/dev/null
systemctl reload nginx 2>/dev/null

    # Always create nginx config for the proxy
    # Use catch-all server_name to accept traffic on this port regardless of domain
    PROXY_DOMAIN="catchall"
    NGINX_PROXY_CONF="/etc/nginx/sites-available/proxy-default"
    
    echo "   🌐 Configuring Nginx on port $PROXY_PORT (Catch-all)..."
    
    cat > "$NGINX_PROXY_CONF" <<EOF
# Proxy server for ANY domain on port $PROXY_PORT
server {
    listen $PROXY_PORT default_server;
    # IPv6 removed to prevent 'duplicate listen options' or bind conflicts on some systems
    server_name _;
    
    # Log all requests reaching nginx on this port
    access_log /var/log/nginx/proxy_access.log;
    error_log /var/log/nginx/proxy_error.log;

    # Handle Long URLs (Essential for YouTube Streams)
    large_client_header_buffers 4 64k;
    client_header_buffer_size 64k;
    client_body_buffer_size 64k;
    client_max_body_size 10M;

    location /stream {
        proxy_pass http://127.0.0.1:$INTERNAL_PORT;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        
        proxy_connect_timeout 60s;
        proxy_read_timeout 60s;
    }

    location / {
        proxy_pass http://127.0.0.1:$INTERNAL_PORT;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Proxy-Trace-Id \$request_id;
        
        # Websocket support (if needed)
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        
        proxy_connect_timeout 60s;
        proxy_read_timeout 60s;
    }
}
EOF

    # Enable the site
    ln -sf "$NGINX_PROXY_CONF" "/etc/nginx/sites-enabled/proxy-default"
    
    # Test and reload nginx
    if nginx -t 2>/dev/null; then
        systemctl reload nginx
        echo "   ✅ Nginx configured: http://<your-ip>:$PROXY_PORT"
    else
        echo "   ❌ Nginx config test failed:"
        nginx -t
        rm -f "/etc/nginx/sites-enabled/proxy-default"
    fi

# --- 5. Verify ---
echo "[5/5] Verifying..."
sleep 2
if systemctl is-active --quiet ${SERVICE_NAME}; then
    echo "   ✅ Proxy service is RUNNING on port $INTERNAL_PORT (Backend) -> $PROXY_PORT (Nginx)"
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
