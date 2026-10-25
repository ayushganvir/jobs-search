# Job tracker

- `python3 sync.py` merges `../applied_log.jsonl` + `gmail_status.json` into `data.json` (Gmail signal overrides log status). The server also re-runs it on every `/data.json` request.
- `gmail_status.json` is written via Gmail MCP (read-only): `[{company, role, classification, date, viewUrl}]`; classification: confirmed|interview|assessment|rejected|other.
- `python3 server.py` serves http://127.0.0.1:8787 with Basic auth: user `ayush`, password in `.password` (chmod 600).
- Public access: `ngrok http 8787` (needs your own authtoken: `ngrok config add-authtoken <TOKEN>`); keep Basic auth on.
