# Claude in Chrome prompts

Walled job boards (LinkedIn, Indeed, Wellfound, Naukri) only accept real clicks, so they are worked by the Claude in Chrome
extension with a pasted prompt instead of the scripted Control_Chrome agents.

The filled prompts (`*_AGENT.md`, `FINISH_DRAFTS.md`) contain the candidate's personal facts and are gitignored.

**Generate them:** `python3 prompts/build_prompts.py` writes LINKEDIN / NAUKRI / INDEED / WELLFOUND prompts from your private
`AGENT_BRIEF.md` (Facts + Standing answers) plus the already-applied list from `applied_log.jsonl`. Re-run it whenever you add
standing answers or before each paste. Manual alternative, from `EXAMPLE_AGENT.md`:

1. Copy `EXAMPLE_AGENT.md` to `<BOARD>_AGENT.md` and set the board, search terms and limits.
2. Paste the Facts block from your private `AGENT_BRIEF.md`.
3. Run `python3 prompts/refresh_skip_lists.py` to fill the "Already applied or in progress" list from `applied_log.jsonl`.
4. Paste the file into Claude in Chrome on a signed-in tab of that board.
