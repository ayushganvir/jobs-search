#!/usr/bin/env python3
"""Rewrite the "Already applied or in progress" company list in every prompts/*_AGENT.md from applied_log.jsonl.
Run before pasting a prompt into Claude in Chrome: python3 prompts/refresh_skip_lists.py"""
import pathlib, re, sys
J = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(J))
import joblog
KEEP = {"submitted", "confirmed", "interview", "rejected", "offer", "needs_user", "blocked"}
names = sorted({re.sub(r"\s*\(.*?\)", "", r.get("company") or "").strip() for r in joblog.latest().values()
                if r.get("status") in KEEP}, key=str.lower)
names = [n for n in names if n and not n.startswith("r/")]
for p in sorted((J / "prompts").glob("*_AGENT.md")):
    s = p.read_text()
    m = re.search(r"(Already applied or in progress \(skip these companies\):\n)(.*?)(\n\n)", s, re.S)
    if m:
        p.write_text(s[:m.start(2)] + ", ".join(names) + s[m.end(2):])
        print(f"{p.name}: {len(names)} companies")
