# TLS Deployment for MRS Server

For production, run `mrs-server` behind a TLS reverse proxy.

Recommended architecture:
- `mrs-server` binds to `127.0.0.1:8000` (HTTP, local only)
- Reverse proxy handles HTTPS on `:443`
- Reverse proxy forwards to `http://127.0.0.1:8000`

## App configuration
Set these environment variables for production:

```bash
export MRS_HOST=127.0.0.1
export MRS_PORT=8000
export MRS_SERVER_URL="https://mrs.example.com"
export MRS_SERVER_DOMAIN="mrs.example.com"
```

`MRS_SERVER_URL` should be the public HTTPS URL.

---

## Apache (mod_ssl + mod_proxy)

Enable modules (Debian/Ubuntu):

```bash
sudo a2enmod ssl proxy proxy_http headers rewrite
sudo systemctl reload apache2
```

Example vhost:

```apache
<VirtualHost *:80>
    ServerName mrs.example.com
    RewriteEngine On
    RewriteRule ^ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]
</VirtualHost>

<VirtualHost *:443>
    ServerName mrs.example.com

    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/mrs.example.com/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/mrs.example.com/privkey.pem

    ProxyPreserveHost On
    RequestHeader set X-Forwarded-Proto "https"
    RequestHeader set X-Forwarded-Port "443"
    RequestHeader set X-Forwarded-For "%{REMOTE_ADDR}s"

    ProxyPass / http://127.0.0.1:8000/
    ProxyPassReverse / http://127.0.0.1:8000/

    ErrorLog ${APACHE_LOG_DIR}/mrs-error.log
    CustomLog ${APACHE_LOG_DIR}/mrs-access.log combined
</VirtualHost>
```

---

## Caddy

`Caddyfile`:

```caddy
mrs.example.com {
    reverse_proxy 127.0.0.1:8000
}
```

Caddy will automatically provision and renew Let's Encrypt certs.

---

## Nginx

```nginx
server {
    listen 80;
    server_name mrs.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name mrs.example.com;

    ssl_certificate /etc/letsencrypt/live/mrs.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/mrs.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Port 443;
    }
}
```

---

## Verification checklist

1. One-command TLS verification:

```bash
./scripts/verify-tls.sh mrs.example.com https://mrs.example.com
```

2. HTTPS endpoint works:

```bash
curl -fsS https://mrs.example.com/.well-known/mrs | jq .
```

3. Redirect from HTTP to HTTPS works:

```bash
curl -I http://mrs.example.com/
```

4. Well-known server URL is HTTPS:
- `/.well-known/mrs` → `server` should be `https://mrs.example.com`

5. Direct app port is not publicly exposed:
- `127.0.0.1:8000` only
