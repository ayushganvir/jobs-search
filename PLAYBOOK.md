# Job-hunt playbook: every flow, end to end

What we built and how it runs, from 2 days (2026-10-19/20) and ~140 applications in Ayush's Chrome.
Status: applying RESUMED 2026-10-21 (Ayush asked for more in the queue; `jobs/PAUSED` removed; the `auto-apply-jobs` schedule stays off, batches are run by hand). Queue covers all of India (Hyderabad > Mumbai > Bengaluru > remote > Pune/Chennai/NCR > rest) and leaves out Telegram reposts of LinkedIn jobs (mostly closed).

Files: facts + standing answers -> `AGENT_BRIEF.md`; per-platform techniques -> `PORTAL_FILL_GUIDE.md`; Claude-in-Chrome prompts -> `prompts/`; map of the folder -> `README.md`.

## 1. The pipeline

```
 sources (daily 08:00)          queue                 apply (Chrome)                 record              verify
 freehire API ─┐                                       coordinator (Claude Code)
 ATS boards ───┼─> candidates ─> make_queue.py ──────> spawns fill agents ─────────> joblog.py ───────> reconcile.py
 Workday cxs ──┤   .json +       today_queue.json      (Control_Chrome, 1-2 tabs     applied_log.jsonl  (Gmail receipts,
 Himalayas ────┤   extra_cand.   one per company,      each) + Ayush for sign-ins,   (append-only)      every 10 min)
 Telegram/HN ──┘   .json         target cities only    Claude in Chrome for walled         │                 │
                                 (empty when PAUSED)   boards (LinkedIn, Indeed)           └──> tracker/sync.py <──┘
                                                                                               data.json -> jobs.ayush.cc
                                                       chrome_tabs.py cleanup closes finished tabs
```

## 2. Status model (single source of truth)
- `applied_log.jsonl` is the only record. One JSON row per event: `company, title, status, date, ts, note, url, where ("tab <id>"), channel`.
- Write rows ONLY with `joblog.py add` (validates the status, needs a note for needs_user, stamps date+ts, enforces one application per company, closes the tab on a final status, re-syncs). Never hand-edit old rows; append a newer row instead.
- Statuses:

| status | meaning | who sets it |
|---|---|---|
| `needs_user` | filled as far as possible; Ayush must do one named step (sign in, captcha, answer, attach, click) | coordinator |
| `blocked` | cannot proceed (site broken, signed out mid-way) | coordinator |
| `submitted` | confirmation seen on the page | coordinator after verifying the tab |
| `confirmed` | receipt email matched | reconcile.py |
| `interview` / `rejected` / `offer` | later emails | reconcile.py |
| `skipped` | not applying (fit, closed, senior, campus drive...) with the reason | coordinator |
| `withdrawn` / `superseded` | retired / duplicate row | coordinator |

- Newest row wins. `tracker/sync.py` orders rows by position in the file: the latest row per company+title is the current state, and an open row is hidden only if an applied row for the same company was written after it. A receipt email beats an earlier `skipped` only when its job number matches the row's URL.
- One application per company: `joblog.py add --status submitted` refuses a second role at a company that already has one (override with `--force` only when Ayush asks).
- `joblog.py check` lints the log; `joblog.py show <company>` gives a company's history; `joblog.py open` lists everything waiting on Ayush with Go-to-tab links.

## 3. Coordinator loop (the main Claude Code session)
1. **Sweep** (on every "continue"): `python3 chrome_tabs.py list` for tab state; read each open job tab (step N of M, confirmation, errors, signed out); search Gmail for receipts; pipe new receipts to `reconcile.py`.
2. **Pick work**: queue rows (Hyderabad > Mumbai > Bengaluru > remote), one per company, vetted for fit (read the posting: years asked, stack, not a campus drive). For Workday, vet via the cxs JSON API before opening (PORTAL_FILL_GUIDE §13).
3. **Sign-in batch**: open the account portals (Workday/SuccessFactors/iCIMS/Oracle) in Chrome, log each as `needs_user` "sign in, then Claude fills" with its tab id, and give Ayush the list of Go-to-tab links. He signs in to all, says continue; re-check each tab (reload stale ones: a tab opened before sign-in still shows "Sign In").
4. **Resume link**: `python3 resume_link.py on full` once; every agent gets the same URL (running `on` again reuses the live link). `off` only when no agent is uploading.
5. **Spawn fill agents** in the background, 1-2 tabs each (Workday forms take 5-8 min each). Use the brief template in §6.
6. **On each agent report**: verify on the tab yourself (confirmation URL/text) and/or Gmail before logging. The agent's word is not proof.
   - Submitted -> `joblog.py add --status submitted --tab <id>` (closes the tab).
   - Blocked on a question -> ask Ayush (one AskUserQuestion with all pending questions), save the answer as a standing answer in `AGENT_BRIEF.md` + memory, then SendMessage the same agent to finish (it keeps its context).
   - Signed out / needs a human step -> `joblog.py add --status needs_user --note "<exact step>" --tab <id>`.
7. **Clean up**: `python3 chrome_tabs.py cleanup` after each batch (and the reconcile task runs it too).
8. **Report**: what was submitted (verified), what needs Ayush with [Go to tab](http://127.0.0.1:8787/go?tab=ID&u=URL) links, status fence at the end.

## 4. Chrome tab lifecycle
```
 open (open_url, logged needs_user with tab id) -> Ayush signs in -> agent fills -> confirmation seen
   -> coordinator verifies -> joblog.py add submitted --tab ID (tab closed)      [or needs_user: tab stays, link given]
 chrome_tabs.py cleanup also closes: helper tabs, confirmation pages, tabs of companies already final, duplicates, extra dashboards
```
- Tab ids are Chrome's own ids (same in Control_Chrome, AppleScript, `tabjump.py`). They survive navigation in the tab, not a Chrome restart.
- Never closed by cleanup: Gmail, YouTube, ChatGPT/Claude, Cloudflare, LinkedIn feed/notifications/profile, Naukri profile, tabs of companies with an open `needs_user`, tabs not matched to the log (Ayush's own browsing), one dashboard tab.
- Keep ≤ ~12 job tabs open. Close a tab the moment it is final; never leave a tab "just in case".
- Go-to-tab links: `http://127.0.0.1:8787/go?tab=<id>&u=<url>` (local only). `tracker/server.py` -> `tabjump.py` focuses the tab by id, else by URL, else opens the URL. The dashboard shows the same buttons (sync.py looks tab ids up live).
- Control_Chrome realities: JS only (no keystrokes/screenshots), one action per call, `switch_to_tab` before React-heavy work, a hidden tab can make Save and Continue silently fail, AppleScript `execute javascript` is disabled (use Control_Chrome for JS, AppleScript only for listing/focusing/closing).

## 5. Human-only steps (batch them, give links)
Sign in / create account (per Workday tenant), phone or email verification, image captcha, consent/NDA screens not covered by standing answers, file pickers that refuse scripts (Ashby, Google Forms), buttons that need a real click (Recruitee Send, LinkedIn Easy Apply, Zoho "I'm interested"), and genuinely new personal questions. Ask all pending questions in one go; every answer becomes a standing answer.

## 6. Fill-agent brief template
```
You are filling job applications for Ayush Ganvir in his real Google Chrome, using ONLY the mcp__Control_Chrome__* tools
(ToolSearch "select:mcp__Control_Chrome__execute_javascript,mcp__Control_Chrome__switch_to_tab,mcp__Control_Chrome__get_page_content,mcp__Control_Chrome__list_tabs,mcp__Control_Chrome__reload_tab").
No other browser, no screenshots. First read jobs/AGENT_BRIEF.md and jobs/PORTAL_FILL_GUIDE.md fully and follow them.
If a previous agent may have started a tab, FIRST read its state and never start a second application.
Your tabs (ONLY these; pass tab_id; switch_to_tab first): <id>: <Company>, <Role>, <City> (<platform>, signed in, at <path>)
Resume URL (fetch in-page, DataTransfer): <URL>. Do NOT run resume_link.py.
Never sign in/type passwords/create accounts/solve captchas; if signed out, stop and report. Fix the Workday autofill errors.
Submit only when every answer is factual; leave anything not covered blank and report the exact question. No file edits.
Final report: one line per company: submitted (confirmation text seen) or stuck at step N with the exact blocker.
```

## 7. Verification: what counts as submitted
Per platform "Done =" lines in PORTAL_FILL_GUIDE. In short: Workday `/jobTasks/completed/application` or Candidate Home "Submitted/Under Review/In Process"; iCIMS `mode=submit_apply`; Google Forms `formResponse` "recorded"; Ashby "successfully submitted"; Talemetry reload "already been completed"; any receipt email. A page that only says "Applied" without an email (Recruitee) is not proof.

## 8. Walled boards (LinkedIn, Indeed, Wellfound, Naukri)
- Applied only through Claude in Chrome (the extension), which can make real clicks. Prompts: `prompts/LINKEDIN_AGENT.md` (+ A/B/C splits to run three tabs in parallel), `prompts/INDEED_AGENT.md`, `prompts/WELLFOUND_AGENT.md` and `prompts/NAUKRI_AGENT.md` (all include the already-applied company list; run `python3 prompts/refresh_skip_lists.py` before each reuse).
- Their receipt emails are logged by the reconcile task with `add_if_missing` (LinkedIn "your application was sent to X"; Indeed "Indeed Application: ..."; Wellfound).
- Profiles: Wellfound and Indeed profiles are completed by a Control_Chrome agent once Ayush is signed in (Indeed needs his phone verification first).
- Lesson: most LinkedIn posts surfaced via Telegram channels were already closed; treat them as low-yield.

## 9. Scheduled tasks (run only while the Claude app and Chrome are open)
| task | when | does |
|---|---|---|
| `daily-job-digest` | 08:00 | daily.py: freehire digest, build_candidates, extra_sources (ATS boards, 58 Workday tenants, Himalayas, Remotive, HN, Jooble), make_queue (empty while PAUSED), sync |
| `reconcile-job-emails` | every 10 min 08:00-23:50 | new Gmail receipts -> reconcile.py -> log + dashboard; then `chrome_tabs.py cleanup` |
| `auto-apply-jobs` | 10:30, 16:30 | DISABLED (paused) |

## 10. Resuming applying later
1. Delete `jobs/PAUSED`; run `python3 make_queue.py`.
2. Re-enable `auto-apply-jobs` (scheduled tasks) or run the coordinator loop (§3) by hand.
3. Refresh `prompts/INDEED_AGENT.md`'s already-applied list (`joblog.py open` / log) before reusing it.

## 11. Lessons (keep adding)
- Verify, don't ask: read the tab and Gmail before asking Ayush whether something was submitted.
- Agents die with the session: background agents do not survive a Claude Code restart. Re-spawn them with "read the tab state first".
- Rotating the resume link mid-batch broke running agents; now `on` reuses the live link.
- A tab opened before Ayush signed in looks signed out: reload before deciding.
- Workday date fields: see PORTAL_FILL_GUIDE §1 (delete/re-add, reload, fiber onBlur).
- Campus drives hide behind generic titles (Rubrik "Software Engineer"): read the form's options before filling.
- Recruitee/Himalayas "Applied" views can be false; trust email.
- Consent screens (GDPR, AI screening, data retention, NDA-by-typing-name) need Ayush once; then they are standing answers.
- Guest Workday sessions reset when idle; submit promptly.
- Keep summaries honest: "filled" is not "submitted".
- Log under the real employer name, never the Workday tenant slug: "db" and "Deutsche Bank" were treated as two companies, so one role was skipped under one name and applied under the other. Check `joblog.py show <name>` with both spellings before applying.
- Tab cleanup once closed an in-progress EXL form because EXL's ATS host (oraclecloud.com) contains "oracle" and Oracle was final in the log. Name matching now ignores shared ATS hostnames; run `chrome_tabs.py cleanup --dry` first when unsure.
- After an agent submits, the receipt email usually lands within 1-5 minutes; the 10-minute reconciler upgrades the row to `confirmed`.
