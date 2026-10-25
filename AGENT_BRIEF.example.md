# Application agent brief (the candidate Ganvir)

Every agent that fills a job application reads this file, then `PORTAL_FILL_GUIDE.md` (per-platform techniques).
The coordinator's side (spawning, verifying, logging, tab cleanup) is in `PLAYBOOK.md`.

## Rules
- Browser: ONLY the candidate's real Chrome ("the candidate Ganvir" profile) through the Control_Chrome tools. Never the built-in browser pane. No screenshots.
- Work only the tab ids you were given; pass `tab_id` on every call. Never touch Gmail, the dashboard, or any non-job tab.
- Never create accounts, sign in, type passwords, verify phone/email, or solve/bypass captchas or Cloudflare checks. If a tab is signed out, stop on it and report. If typing an email sends the page to a Google/LinkedIn/SSO sign-in or account-chooser screen, STOP immediately and report (join.com once turned an email step into a Google sign-in).
- open_url always with a NEW tab; never load a URL into the active tab (it may be the candidate's own tab, e.g. Chrome Remote Desktop).
- Do not accept terms, NDAs, GDPR or other consent screens beyond what the standing answers below cover; routine "I certify my information is accurate" / required privacy acknowledgements at submit are fine.
- Use only the facts and standing answers below. If a REQUIRED question is not covered, leave it blank, do not submit, and report the exact question text and options.
- Submit only on the Review page when every answer is factual. A job is submitted only when a confirmation shows (see PORTAL_FILL_GUIDE "Done =" per platform).
- One application per company. If the tab shows the company already has an application, report it; never start a second one.
- Agents do not edit files. The coordinator verifies and logs with `joblog.py` (see PLAYBOOK §3).
- Gmail is read-only and only for a security code from the exact company being applied to.

## Fit (when an agent picks jobs itself)
Apply only to genuine fits: AI/LLM/voice/agents engineering, forward-deployed or solutions engineering, founding engineer, or full-stack/backend with Python/Go/TypeScript/Vue/React; roughly 2-6 years asked; product companies. Skip: 7+ years, interns/freshers/campus drives, lead/architect/manager, BI/data engineering/support/testing, Java/.NET/C++/SAP/Salesforce stacks, staffing/IT-services firms, expired postings.

## Facts (never invent anything else)
- <Full Name>; <email>; phone <+91 XXXXXXXXXX>; address <line, city, state, PIN, country>.
- Locations: lives in <city>; relocation <yes/no + where>; preference <city order>.
- Website/portfolio <https://...>; LinkedIn <url>; GitHub <url>.
- Current CTC <X LPA, fixed/variable split>. Expected <range; free-text value>. Minimum acceptable <X LPA>. Notice <N days>.
- Experience <N years>; per-skill years <skill: years, ...>.
- Current role: <title, company, MM/YYYY - present: 2-4 factual bullets>.
- Previous role: <title, company, city, MM/YYYY - MM/YYYY: bullets>.
- Skills: <list>.
- Education: <degree, institute, years, CGPA>.
- Languages, gender, pronouns, EEO preference.
- A short backend/scaling story in the candidate's own words (used verbatim for "what have you built" questions).

## Standing answers (fill once, agents reuse them; never ask twice)
- Citizenship / work authorization / sponsorship.
- Non-compete, NDA, restrictive covenants.
- Relatives or government officials at the hiring company, its auditors, customers or vendors.
- Terminations, legal proceedings, convictions, regulatory investigations.
- Board seats / outside business / IP owned.
- Office days, relocation, night/US shifts, travel %, background check.
- AI-screening consent, data retention / talent-pool choice.
- ID-document name, date of birth, place of birth (only when required). Never store ID numbers (PAN, passport).
- Marital status, passport held, health-leave, career gaps.
- Other offers in hand, bond with current employer, contract work OK?
- Self-ratings that forms ask (DSA, GenAI, Docker...), AI tools used.
- References policy, open-source links, certifications.

## Report format (final reply)
One line per tab: company, role, outcome (submitted with the confirmation text seen / stuck at step N with the exact blocker / signed out), plus any answer you chose that is not literally in this file.
