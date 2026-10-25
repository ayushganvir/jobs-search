#!/usr/bin/env python3
"""resume_link.py on [plain|full] | off | status
Temporarily serves a resume PDF at https://jobs.ayush.cc/tmp-resume-<random>.pdf (CORS *) so a page in
Chrome can fetch() it and attach it to a file input. Prints the URL. The link expires 60 min after the last `on`.
`on` while a link for the same file is live REUSES it (and restarts the 60-min clock), so agents already holding the
URL keep working; run `off` only when no agent is still uploading.
plain = jobs/Ayush_Ganvir_Resume_plain.pdf (7 KB), full = ~/claude_base/resume/Ayush_Ganvir_Resume.pdf.
tracker/server.py reads tracker/.resume_link.json on every request, so no server restart is needed."""
import json, os, pathlib, secrets, sys, time
J = pathlib.Path(__file__).resolve().parent
STATE = J / "tracker" / ".resume_link.json"
TTL = 3600
PDF = {"plain": J / "Ayush_Ganvir_Resume_plain.pdf",
       "full": pathlib.Path.home() / "claude_base/resume/Ayush_Ganvir_Resume.pdf"}

def live():
    try:
        if time.time() - STATE.stat().st_mtime < TTL:
            return json.loads(STATE.read_text())
    except (OSError, ValueError):
        pass
    return None

cmd = sys.argv[1] if len(sys.argv) > 1 else ""
if cmd == "on":
    which = sys.argv[2] if len(sys.argv) > 2 else "plain"
    cur = live()
    if cur and cur.get("file") == str(PDF[which]):
        os.utime(STATE)  # reuse the live link, restart its clock
        path = cur["path"]
    else:
        path = f"/tmp-resume-{secrets.token_hex(8)}.pdf"
        STATE.write_text(json.dumps({"path": path, "file": str(PDF[which])}))
    print("https://jobs.ayush.cc" + path)
elif cmd == "off":
    STATE.unlink(missing_ok=True)
    print("off")
elif cmd == "status":
    cur = live()
    print(f"on: https://jobs.ayush.cc{cur['path']} ({int(TTL - (time.time() - STATE.stat().st_mtime)) // 60} min left)" if cur else "off")
else:
    sys.exit(__doc__)
