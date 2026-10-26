# Portal fill guide (per platform)

How to fill each application platform in Ayush's Chrome with the Control_Chrome tools. Learned 2026-10-19/20 across ~130 applications.
Facts and standing answers live in `AGENT_BRIEF.md` (read it first). The overall flow (status, tabs, agents, verification) is in `PLAYBOOK.md`.

## 0. Control_Chrome basics (every platform)
- Tools: `list_tabs`, `open_url`, `switch_to_tab`, `execute_javascript(code, tab_id)`, `get_page_content`, `reload_tab`, `close_tab`. Always pass `tab_id`; never work a tab you were not given.
- Wrap every snippet in an IIFE `(()=>{ ... })()`. Never top-level `const`/`let` (they persist per tab and break the next run).
- `missing value` / `JavaScript executed` with no value = the code threw, returned a Promise that never resolved, or the page navigated. Re-read state in a NEW call.
- One action per call. `setTimeout` chains stall when another agent moves Chrome focus. To wait: `(()=>new Promise(r=>setTimeout(()=>r(1),8000)))()`, then read state in a separate call.
- Hidden/background tabs get no focus/blur events: `switch_to_tab` first for React-heavy forms.
- Text inputs (React, Workday, Workable): `x.focus(); x.select(); document.execCommand('insertText', false, v); x.dispatchEvent(new FocusEvent('focusout',{bubbles:true})); x.blur()`. Plain forms: native value setter (`Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(x,v)`) + `input`/`change`/`blur` events.
- Buttons that ignore `.click()`: dispatch `pointerdown, mousedown, pointerup, mouseup` then `.click()`.
- Isolated world: the extension's JS cannot call page functions (e.g. `CareerSite.Apply...`) or reach React state on some sites. Then inject a `<script>` element so the code runs in the page world.
- Clicks that need a real user gesture are ignored entirely (LinkedIn Easy Apply, Recruitee "Send", Zoho "I'm interested", SmartRecruiters behind DataDome, Google Forms/Ashby file pickers). Leave those for Ayush or for Claude in Chrome.
- `window.open` from a script is popup-blocked; read the target URL from the DOM / iframe `src` and `open_url` it instead.
- Cross-origin iframes (Talemetry inside Jobvite pages, iCIMS on some hosts): read `iframe.src` and open it in its own tab.
- Resume upload: coordinator runs `python3 resume_link.py on full` (one live link shared by all agents; running `on` again reuses it). In the page: `fetch(URL).then(r=>r.blob())` -> `new File([b],'Ayush_Ganvir_Resume.pdf',{type:'application/pdf'})` -> `DataTransfer` -> `input.files = dt.files` -> dispatch `change` -> wait ~10 s -> confirm "uploaded". Agents never run resume_link.py.
- Cookie banners: decline non-essential.

## 1. Workday (`*.myworkdayjobs.com`, `wd*.myworkdaysite.com`) — the most common platform
- Accounts are per company (per tenant). Ayush signs in; a tab opened before he signed in still shows `Sign In`: `reload_tab` and re-check. Signed in = no `Sign In` button in the header AND, after Apply, the flow does not start at a "Create Account/Sign In" step. Check after the page has fully loaded (an unloaded job page shows no header buttons and looks signed in).
- Some tenants allow a guest application without sign-in (Equinix, Deutsche Bank). Guest sessions reset if idle: finish promptly.
- Entry: job page -> `Apply` -> choose `Autofill with Resume` (preferred), `Apply Manually`, or `Use My Last Application`.
- Steps (names vary, 5-7 steps): My Information -> My Experience -> Application Questions (1-2 pages) -> Voluntary Disclosures -> Self Identify -> Review -> Submit.
- After Save and Continue / Next wait 10-15 s and re-read `current step N of M` before deciding it failed. Click `[data-automation-id=pageFooterNextButton]` with pointer events + click.
- Dropdowns (`button[aria-haspopup=listbox]`): call 1 clicks the button; call 2 picks the visible `[role=option]` (height > 0; if two lists are open use the last visible `[role=listbox]`) with pointer events + click. Normalize diacritics (Mahārāshtra).
- Multiselect/prompt fields (How did you hear, school, field of study, skills): click the input, type with execCommand, send Enter (keydown/keypress/keyup), wait ~2.5 s, click the `[role=option]`. "How did you hear" is often 2 levels (category, then leaf).
- Autofill mistakes to fix every time: name parsed as "Healthcare Act"; a skills table pasted into the Edlion role description (replace with a factual summary); a "Punjabi" language row (resume lists English, Hindi only); education end year 2008; junk suggested skills ("English to Hindi Translation", "Marketing", "Social Media"); "Computer Science and Mathematics" as field of study.
- Dates: month/year inputs reject scripted typing (value shows, then "Must end after start date", or Save and Continue greys out). Fixes in order: (1) for education, delete the entry and re-add it without years; (2) reload the tab (earlier steps mostly stay saved); (3) inject a `<script>` into the page, walk the React fiber from the date input up to the `DateInput` component and call `memoizedProps.onBlur({yyyy:'2024', mm:'08'})` (year-only `{yyyy:'2017'}`). A plain DOB field (MM/DD/YYYY) usually accepts typing.
- Degree lists without B.Tech: pick "Bachelors" / "B.Eng." / "Bachelor's Degree"; field "Computer Science" or "Computer and Information Science".
- Back opens a hidden "Discard Application?" dialog: click `continueButton`, never Discard.
- Application Questions are where personal questions appear (non-compete/NDA, relatives, government officials, previous employment, disability, data retention, AI consent, Aadhaar name). Answer from AGENT_BRIEF standing answers; anything else stays blank and is reported.
- Done = `/jobTasks/completed/application` URL, "Application Submitted" dialog, or Candidate Home listing the requisition as Submitted / Under Review / In Process. Receipt email from `<tenant>@myworkday.com` follows within minutes.
- Candidate Home "create a password" prompts after a guest submit are optional: leave them.

## 2. SAP SuccessFactors (`career*.successfactors.com/.eu`)
- Per-company account. Pickers `input[id$=_input]`: focus, set 3 letters, dispatch `input` + `keyup`, wait, click the visible `a`/`li` match. Fixed lists: ArrowDown, then pick from `[class*=pickList] a`.
- AMETEK's tab stopped responding to scripts; a reload or Ayush is needed.

## 3. iCIMS (`*.icims.com`)
- Content is in `#icims_content_iframe`; same-origin on most hosts, otherwise open the iframe `src` directly.
- Sign-in can be "Sign in with Google" (Ayush does it). Done = URL `mode=submit_apply` and "Your application was submitted successfully". Some companies (DocuSign) need an iCIMS account: sign-in item.

## 4. Oracle HCM (`*.oraclecloud.com`) and Phenom (careers.lilly.com, careers.nttdata.com)
- Oracle JET forms accept `execCommand('insertText')`; email-code sign-in screens are Ayush's.
- Phenom: values set from the extension world show but never reach React state. Inject a `<script>` and set values from the page world (native setter + input/change). NTT wants phone "+91XXXXXXXXXX"; Lilly's Vue selects reset, Ayush finished it.

## 5. Greenhouse (`job-boards.greenhouse.io`, embeds on company sites)
- No account. Fields `#first_name`, `#last_name`, `#email`, `#phone`, `#resume`, `question_<id>`. Old embeds use native `<select>` without ids: list `form select` with their labels first.
- Read the selects before applying: campus forms (graduation year 2024-2026 only, CGPA, IIT/NIT tier) are fresher drives: skip. NDA-by-typing-your-name fields are agreements: Ayush only.
- Security-code step: read only that company's newest code email in Gmail.
- CSP blocks fetching the resume link on Greenhouse pages: add a hidden iframe pointing to the same site's /robots.txt (no CSP), fetch the PDF inside it, and hand the Blob back to the form. Greenhouse react-select dropdowns (and the phone country picker) only take values through the component's own select/onChange handler, called from an injected page-world <script>; phone as "+91XXXXXXXXXX".
- Boards API for vetting: `https://boards-api.greenhouse.io/v1/boards/<slug>/jobs/<id>?questions=true`.

## 6. Ashby, Lever, Workable, Freshteam, Keka, SmartRecruiters
- No account. Ashby's file picker and some required fields refuse scripts: fill the rest, Ayush attaches the resume and clicks Submit. Done = "Your application was successfully submitted".
- SmartRecruiters fields are in shadow DOM and DataDome blocks scripted submit: fill, leave Submit to Ayush.

## 7. Recruitee (`*.recruitee.com`, also reached from Himalayas)
- Simple form (`candidate.name`, `candidate.email`, `candidate.phone`, `candidate.cv`). The `Send` button ignores scripted clicks: fill everything, Ayush clicks Send. An "Applied / All done" view can show for an unrelated earlier visit: trust only a receipt email.

## 8. Jobvite + Talemetry (Ness)
- The careers page's Apply opens a cross-origin Talemetry iframe (`apply.talemetry.com/application/<uuid>`): open that URL in its own tab. 9 steps; step 1 is a GDPR consent (Ayush). Resume upload parses well but mislabels employers ("Flowie" for Navtech): fix work history. No thank-you page: a reload saying "The requested application has already been completed" means submitted.

## 9. Zoho Recruit (`*.zohorecruit.*`)
- "I'm interested" needs a real click; image captcha at submit: fill everything, leave the captcha for Ayush. Done = "Thank you for submitting" modal (the form stays behind it) or a "join our candidate portal" email.

- Zoho forms clear themselves after sitting idle (seen on nCircle, Alternative Path, Nirmitee): prefill only when Ayush is about to type the captcha, and tell him to do it soon. A form that reset needs a full refill.

## 10. Google Forms
- Fill text fields; file upload needs Ayush (Google picker). Done = `formResponse` URL with "Your response has been recorded".

## 11. LinkedIn, Indeed, Wellfound, Naukri (walled boards)
- Only inside Ayush's own signed-in Chrome, at small volume, through Claude in Chrome (the browser extension) with the prompts in `prompts/`. Control_Chrome clicks on Easy Apply / Indeed Apply are ignored.
- LinkedIn receipts: "Ayush, your application was sent to <Company>" from jobs-noreply@linkedin.com. Indeed receipts come from indeed.com ("Indeed Application: <title>").
- Many LinkedIn posts reached via Telegram channels are already closed ("No longer accepting applications").

## 12. Himalayas (`himalayas.app`)
- Needs a finished Himalayas profile. `Apply now` (scripted) opens an upsell modal; its "I'm ready to apply" link (`himalayas.app/apply/<code>`) redirects to the employer's own ATS (Recruitee for AMS). Open that link with `open_url` and fill the ATS form there.

## 13. Vetting a Workday job without opening it
- List: `POST https://<tenant>.<wd>.myworkdayjobs.com/wday/cxs/<tenant>/<site>/jobs` with `{"appliedFacets":{},"limit":20,"offset":0,"searchText":"python"}`.
- Detail: `GET https://<tenant>.<wd>.myworkdayjobs.com/wday/cxs/<tenant>/<site><externalPath>` -> `jobPostingInfo.jobDescription`; grep "N+ years". Tenants in `extra_sources.py` `WD`.
