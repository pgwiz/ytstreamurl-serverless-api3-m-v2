# Proxy Setup Guide 🌐

This guide explains how to set up a bypass proxy server to resolve "Sign in to confirm you're not a bot" errors on Vercel.

---

## 1. Why is this needed?
YouTube blocks requests from Cloud Data Centers (like Vercel/AWS). To fix this, you need to route traffic through a server with a "clean" IP address (e.g., a standard VPS or Residential IP).

---

## 2. Server Setup (The "Clean" Server)

**Requirements:**
- A VPS or server with a non-blocked IP.
- Python 3 installed.
- Port `6178` open.

### Step A: Upload Script
Upload the `simple_proxy.py` file from this project to your server.

### Step B: Run the Proxy
Run the script. For long-term use, use `nohup` or `screen`.

```bash
# Basic Run
python3 simple_proxy.py

# Run in Background (Recommended)
nohup python3 simple_proxy.py > proxy.log 2>&1 &
```

### Step C: Firewall (Important!)
Ensure port `6178` allows incoming TCP traffic.
```bash
# UFW (Ubuntu)
sudo ufw allow 6178/tcp
```

---

## 3. Vercel Configuration

Configure your Vercel project to use this proxy.

1.  Go to **Settings** > **Environment Variables**.
2.  Add a new variable:
    - **Key:** `PROXY`
    - **Value:** `http://<YOUR_SERVER_IP>:6178`
      *(Example: `http://192.168.1.50:6178`)*

---

## 4. Troubleshooting

- **Connection Refused:** Check if `simple_proxy.py` is running and port 6178 is open.
- **Still 403/Sign-in:** Your VPS IP might also be blocked. Try generating fresh cookies ON THE VPS machine if possible, or use a Residential Proxy provider string instead (e.g., `http://user:pass@residential-proxy.com:port`).
