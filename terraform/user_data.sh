#!/bin/bash
set -e
exec > /var/log/pufpay-setup.log 2>&1

apt-get update -y
apt-get install -y python3-pip python3-venv git nginx

# Clone repo
git clone ${github_repo} /opt/pufpay
cd /opt/pufpay

# Python venv + dependencies
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Streamlit server config — IAM role handles AWS credentials
mkdir -p /opt/pufpay/.streamlit
cat > /opt/pufpay/.streamlit/config.toml << 'TOML'
[server]
headless = true
port = 8501
enableCORS = false
enableXsrfProtection = false
TOML

chown -R ubuntu:ubuntu /opt/pufpay

# Systemd service
cat > /etc/systemd/system/pufpay.service << 'SERVICE'
[Unit]
Description=PUF-Pay Streamlit
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/pufpay
ExecStart=/opt/pufpay/venv/bin/streamlit run app.py
Restart=always
RestartSec=5
Environment=HOME=/home/ubuntu

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable pufpay
systemctl start pufpay

# nginx reverse proxy
cat > /etc/nginx/sites-available/pufpay << 'NGINX'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass         http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade $http_upgrade;
        proxy_set_header   Connection "upgrade";
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_read_timeout 86400;
    }
}
NGINX

ln -sf /etc/nginx/sites-available/pufpay /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx
