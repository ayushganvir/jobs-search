# Job hunt folder: read README.md first

This folder is Ayush's job-application system. Before doing anything here, read `README.md` (map, workflow, hard rules) and, before spawning application agents, `AGENT_BRIEF.md` (facts and procedure). Never re-ask facts that are in those files (CTC, notice period, links, backend story) and never ask which Cloudflare account to use (`cf whereis <domain>`).

Non-negotiables: no captcha solving, no account creation, no passwords/tokens; leave anything needing Ayush open and filled with a clear `where` note; keep Gmail read-only; write every status change with `python3 joblog.py add` (it validates, closes finished tabs and re-syncs); run `python3 chrome_tabs.py cleanup` after a batch; flows are in `PLAYBOOK.md`; end replies with the status diff fence.
