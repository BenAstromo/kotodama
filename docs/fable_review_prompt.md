# Prompt: pre-launch review of Kotodama (for Fable 5.2)

Paste everything below the line into a new Claude Code session in this folder, with Fable 5.2 selected.

---

You're doing a **pre-launch review** of Kotodama 言霊, an Anki add-on in this folder. You only read and run existing tests. You don't change any code. What you produce is a written implementation guide that Claude Opus 5.5 will follow later, one item at a time, after the owner approves each one. Write it so that a capable engineer who has never seen this conversation can act on every item without having to rediscover your reasoning.

## What Kotodama is and who it's for

Kotodama reads a Japanese learner's own Anki deck. It shows their progress through the JLPT levels (N5–N1) in vocabulary, kanji and grammar. The grammar comes from a built-in parser that finds JLPT grammar points in the example sentences on their cards, and that's the add-on's strongest unique feature. Around that sit several gamified layers:
- a Japanese rank with belts, counting toward 20,000 words, whose top rank is a secret until it's reached
- a JLPT Goal card that works out a daily pace toward a test date
- Frequency Check and Text Check
- History
- Nakama, an optional friends-only comparison that goes through a small Cloudflare Worker in `server/`
- a mini widget on Anki's main screen, and a share image

The users are learners of every level, many of them not technical, who use Anki on desktop, in Anki 2.1.50 or newer. The owner is one person who designs by feel. They decide every change; Claude writes the code.

The learning philosophy matters for judging ideas. Anki trains **recognition**. "Known" means recognised, not produced. Immersion leads to acquisition, which leads to production. The gamification rewards real study and never punishes: no streaks, nothing lost for a missed day, and nothing earned can be bought. Accuracy beats inflated numbers, and it also beats strictness.

**State:** version 3.0.0, feature-complete. The plan is to launch on AnkiWeb, with the GitHub repo made public, before the JLPT on **6 December 2026**. The soft launch is around 18 November. So the most useful thing you can find is something that would hurt a real new user in the first weeks.

## Read first

1. `APP_VISION.md`. Start with §0 (current state), then §1–§9. Its lists **"Decided, keep as is"**, **"Backburner"** and **"Closed, don't propose again"** are binding. Don't propose anything on them, not even in a new form.
2. Your memory index (`MEMORY.md`, loaded automatically) and the memory files it links to. These are the owner's standing rules.
3. `README.md`, `docs/GUIDE.md`, and `release_drafts.md` §6 (the AnkiWeb page).
4. Then the code, guided by the code map in `APP_VISION.md` §4. `docs/HISTORY.md` is a long archive. Grep it for the background on a decision; don't read it start to finish.

## Rules while reviewing

- **Read only.** Don't edit, create or delete project files except the guide itself, and don't commit or push.
- **Don't open Anki and don't start servers.** Never use port 8765, which belongs to AnkiConnect. You may run the offline tests listed in `APP_VISION.md` §0 and `tools/dev/maint/README.md`. Python lives at `%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe`; the PyQt6 venv is at `%TEMP%\qtv`. Delete the `env/` folder that `t_scenarios.py` creates when you're done.
- **`user_files/` holds the owner's personal data.** Read it only if you need to; never change it.
- **Accuracy tuning of the parser is finished** (see the "stop when diminishing" memory). Don't propose more of it unless you find an outright bug, such as a crash or one sentence that breaks a whole count.
- **Fewer settings:** prefer a fixed, sensible behaviour over a new option.
- **Any English UI text change** needs a matching Japanese line in `divine_text.py`, and `tools/check_gold_text.py` must still print OK. Say so in every item that changes wording.
- **The code must stay Python 3.9 compatible** (`parse39.py`, `compat39.py`).
- **Verify before you report.** Every finding needs evidence: `file:line`, plus a concrete situation that goes wrong (the inputs or the user's setup, and what happens). If you can show it with an existing test or a small throwaway script in your scratchpad, do. Mark each item **Confirmed** (shown or traced end to end) or **Plausible** (likely, not shown). Leave out anything you couldn't support.

## What to look for, in priority order

1. **Breaks for someone who isn't the owner.**
   - Their setup: a fresh profile, unusual note types or field names, an empty deck or one with only new cards, no sentence field, several decks.
   - Their environment: Anki 2.1.50 versus the newest version, Anki's light theme, macOS and Linux (fonts, file paths, the share image), a non-English Anki interface, very large decks (30k+ notes).
   - Errors in hooks that run while the user reviews must never interrupt Anki.
   - Also: a failed migration or a corrupted file in `user_files/`, and no internet connection for Nakama.
2. **The first ten minutes for a new user.** Installing, Settings, empty and loading states, wording that only the owner would understand, and anything a confused user would report as a bug.
3. **Nakama and the server.** How the key is handled, input checks, rate limits, staying inside the free plan's limits, and what is sent and stored compared with what the privacy text promises.
4. **The AnkiWeb page and README.** Claims that don't match what the add-on actually does, and missing install or setup steps.
5. **Speed** only where a real user would feel it. Recent measurements are in §0 and HISTORY.
6. **After launch:** at most five ideas, and only ones that fit the philosophy and aren't on the closed lists. These are optional; skip this section if nothing is clearly worth it.

## The guide

Write it to `docs/IMPLEMENTATION_GUIDE.md` with these sections:

1. **Summary.** Five lines at most: how ready it is for launch, and the three most important items.
2. **Must fix before launch.** At most about 12 items, worst first.
3. **Fix in 3.0.x** (the first weeks after launch).
4. **Ideas for later** (optional, five at most).
5. **Checked and fine.** What you looked at and found no problem with, so nobody checks it again.

Give each item in sections 2–4:
- **Title** and **Confirmed / Plausible**
- **What a user sees**, in one or two plain sentences
- **Evidence:** `file:line` and the situation that goes wrong
- **Fix:** concrete steps for Opus 5.5: which functions to change, the approach, edge cases, what must not change
- **Tests:** which existing tests to run afterwards, and any new check worth adding
- **Size** (S / M / L) and **risk** (what the fix could break)
- **Owner decision needed?** If yes, the question in one line

Keep the guide plain and short. Owner-facing parts should use everyday words. If the code is in better shape than expected, say so, and keep the must-fix list short rather than filling it.
