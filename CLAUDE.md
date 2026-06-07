# CineForge Workflow Constitution

## Plan first
For any task touching ≥3 files or ≥1 new module, write the plan in `plans/YYYY-MM-DD-<slug>.md`, get it self-reviewed (read it back, look for sideways drift), then execute. If the work goes sideways mid-execution, stop and re-plan — don't push through.

## Subagents
Decompose generously. One subagent per concern: ingest, director, promptforge, generator, stitcher, ledger, UI. Each subagent owns its module and its tests.

## Verification gates
Before marking any task done:
- Run the relevant tests; if you didn't write any, that's your bug.
- Diff the behavior change against the plan. If they don't match, the code is wrong, not the plan.
- Ask: "would a staff engineer approve this PR?" If no, fix it before claiming done.

## Self-improvement
After any correction the user gives you, append a one-line lesson to `lessons.md` of the form:
`YYYY-MM-DD | rule | because <one-sentence rationale>`
Re-read `lessons.md` at the start of every session.

## Principles
- **Simplicity first.** Smallest diff that solves the root cause.
- **No laziness.** Fix root causes, never paper over with try/except. No temp files left in the repo.
- **Minimal impact.** Only touch what's necessary. New code must not introduce side effects in untouched modules.
- **Elegance bar.** Non-trivial changes meet a senior-engineer-review bar. Trivial fixes can be quick.

## Autonomous bug fixing
You don't need to ask before fixing bugs you find while doing other work. Fix, note, move on.

## Communication
Each step: a high-level one-paragraph summary of what changed and why. No play-by-play.

## What is out of scope right now
See the build prompt §1 "Non-goals." Do not invent features outside that boundary. If you think a non-goal item is necessary, write the case in `plans/scope-change-<slug>.md` and stop.
