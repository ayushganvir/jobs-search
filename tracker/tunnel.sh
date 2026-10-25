#!/bin/bash
# (Re)start the jobs.ayush.cc Cloudflare tunnel (personal "ayush" account). Uses HTTP/2 over TCP, because QUIC/UDP
# drops on some networks (error 530 on jobs.ayush.cc). The API token comes from the Keychain and is never printed.
set -euo pipefail
TID=$(cat ~/.cloudflared/jobs-dashboard-ayush.id)
CF=$(security find-generic-password -a "$USER" -s cloudflare-ayush -w)
H=(-H "Authorization: Bearer $CF")
ACC=$(curl -s "https://api.cloudflare.com/client/v4/accounts" "${H[@]}" | python3 -c "import sys,json;print(json.load(sys.stdin)['result'][0]['id'])")
TOK=$(curl -s "https://api.cloudflare.com/client/v4/accounts/$ACC/cfd_tunnel/$TID/token" "${H[@]}" | python3 -c "import sys,json;print(json.load(sys.stdin)['result'])")
for p in $(pgrep -f "cloudflared tunnel --no-autoupdate" || true); do
  if ps eww -p "$p" | grep -q "TUNNEL_TOKEN=$TOK"; then kill "$p"; fi
done
TUNNEL_TOKEN="$TOK" nohup cloudflared tunnel --no-autoupdate --protocol http2 run > /tmp/jobs-tunnel2.log 2>&1 &
sleep 6
curl -s -o /dev/null -w "jobs.ayush.cc %{http_code}\n" --max-time 10 https://jobs.ayush.cc/
