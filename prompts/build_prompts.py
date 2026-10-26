#!/usr/bin/env python3
"""Build the Claude-in-Chrome prompts (prompts/<BOARD>_AGENT.md) from AGENT_BRIEF.md so they always carry the latest facts,
standing answers and the already-applied company list. Run: python3 prompts/build_prompts.py  (then paste a file into
Claude in Chrome on a signed-in tab of that board)."""
import pathlib, re, sys
J = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(J))
import joblog

brief = (J / "AGENT_BRIEF.md").read_text()
facts = brief[brief.index("## Facts"):brief.index("## Report format")].strip()
KEEP = {"submitted", "confirmed", "interview", "rejected", "offer", "needs_user", "blocked"}
skip = sorted({re.sub(r"\s*\(.*?\)", "", r.get("company") or "").strip() for r in joblog.latest().values() if r.get("status") in KEEP}, key=str.lower)
skip = ", ".join(n for n in skip if n and not n.startswith("r/"))
m = re.search(r"^- ([^;\n]+);", facts, re.M)
name = m.group(1).strip() if m else "the candidate"  # first Facts bullet starts with the full name

COMMON_PICK = """Pick a job only if ALL hold:
- Backend / full-stack / AI-LLM / voice-AI / forward-deployed / founding-engineer work with Python, Go or TypeScript (React/Vue/Next fine); roughly 2-6 years asked (skip 7+ years minimum, interns, freshers, lead/architect/manager/staff, Java/.NET/C++/PHP/SAP/Salesforce/mobile-only/QA/support/sales roles).
- A real product company or startup. Skip staffing / recruitment / placement agencies, IT-services body shops, "hiring for our client" and confidential employers.
- Pay, if shown, is not clearly below the minimum CTC in the standing answers; remote USD roles are fine. Location: as in the Facts (city preference order), or India-eligible remote.
- The company is NOT in the "already applied" list below and you have not applied to it in this session."""

RULES = """Rules (hard):
- Never solve a captcha or "verify you are human" check; if one appears, wait 2-3 minutes and continue elsewhere.
- Never create an account, sign in, type a password, verify phone/email, or click "Sign in with Google/LinkedIn" or any SSO chooser.
- Never type government ID numbers (PAN, Aadhaar, passport). If a form demands one, skip and note it.
- Never buy paid add-ons or premium, never message recruiters/founders outside the apply note, never edit the profile, resume or settings.
- Never send an AI-written note where the posting forbids AI-generated cover letters: note the job for the candidate instead.
- Answer questions ONLY from the facts and standing answers below; if a required question is not covered, skip the job and note the exact question.
- One application per company. Work slowly: one page at a time, a few seconds between pages."""

NOTE = """If the flow has a note / cover-letter box, write 3-4 plain sentences specific to the role from the Facts only:
who the candidate is + years and stack, the one or two strongest current-role results, one line linking that work to this role,
and the notice period. No invented facts or numbers.""" 

BOARDS = {
 "LINKEDIN": ("LinkedIn Jobs (https://www.linkedin.com/jobs/)", 20,
  'Search Jobs with "Easy Apply" filter ON, Date posted "Past week", Experience level "Mid-Senior" and "Associate"; keywords one at a time: "Python developer", "Backend engineer", "Full stack engineer", "AI engineer", "LLM engineer", "Generative AI", "Voice AI", "Forward deployed engineer", "Founding engineer"; locations Hyderabad, Mumbai, Bengaluru, then India (remote).',
  'Use only LinkedIn "Easy Apply". If the button is "Apply" (external site), do not apply: note company, title and URL. Use the saved resume. Many reposted jobs say "No longer accepting applications": skip those. Confirm "Application sent" after each.'),
 "NAUKRI": ("Naukri (https://www.naukri.com)", 20,
  'Jobs search with Freshness "Last 7 days", Experience 4 years, sort by Date; keywords one at a time: "Python developer", "Django", "Backend developer", "Full stack developer", "AI engineer", "LLM", "Generative AI", "voice AI", "Golang"; locations Hyderabad, Mumbai, Bengaluru, Pune, then Remote.',
  'Use only Naukri\'s own "Apply" (not "Apply on company site": note those). Naukri may open a recruiter questionnaire drawer: answer only from the facts. Naukri is full of consultancies: apply the staffing filter strictly. Confirm "Applied" after each. Stop if Naukri shows a daily apply limit.'),
 "INDEED": ("Indeed India (https://in.indeed.com)", 15,
  'Search sorted by date with "Date posted: Last 7 days": "Python developer", "Backend engineer", "Full stack developer", "AI engineer", "LLM engineer", "Generative AI", "voice AI", "founding engineer"; locations Hyderabad, Mumbai, Bengaluru, then Remote. Load pages slowly (Indeed triggers a Cloudflare check if you go fast).',
  'Use only Indeed\'s own apply ("Easily apply" / "Apply now" staying on indeed.com); note "Apply on company site" jobs. Keep the saved Indeed resume selected. Do not take Indeed assessments. Confirm "Your application has been submitted" after each.'),
 "WELLFOUND": ("Wellfound (https://wellfound.com/jobs)", 15,
  'Jobs > Role: Backend Engineer, then Full-Stack Engineer, then Machine Learning / AI Engineer; Locations Hyderabad, Mumbai, Bengaluru and Remote (India-eligible); sort newest. Also keywords "LLM", "voice AI", "GenAI", "founding engineer". Gurugram roles are OK (Gurugram may be added to the profile locations if required).',
  'Use Wellfound\'s own Apply with the note below; note jobs that only link to an external site. Skip jobs Wellfound blocks for the candidate location. Do not join Wellfound programs ("Featured Global") and close any "AI interview" prompt without starting it (tell the candidate instead). Confirm the job shows "Applied" after each.'),
}

for key, (board, limit, search, flow) in BOARDS.items():
    body = f"""You are applying to jobs for {name} on {board}, in their Chrome, already signed in. Their profile and resume are up to date.

Goal: apply to up to {limit} good-fit jobs, ONE per company.

Search: {search}

{COMMON_PICK}

How to apply: {flow}
{NOTE}

{RULES}

{facts}

Already applied or in progress (skip these companies):
{skip}

At the end, give one line per job you looked at seriously: Applied (company, title, city, URL) / Skipped (reason) / External (URL) / Needs {name} (exact question).
"""
    (J / "prompts" / f"{key}_AGENT.md").write_text(body)
    print(f"prompts/{key}_AGENT.md  {len(body)//1000}k chars")
