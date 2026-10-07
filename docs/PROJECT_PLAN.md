# Guide Todoo — Project Plan

AI task assistant: ingest PDFs and chat, break work into small tasks, sync to Apple Reminders (Mac + iPhone via iCloud), plan your day, pull Jira, and report daily/monthly.

## Phases (A → B → C)

### Phase A — PDF → Tasks → Reminders
- Upload or drop a PDF (weekly plan, spec, notes)
- Extract text, use LLM to break into actionable sub-tasks
- Create reminders in Apple Reminders list `Guide Todoo` (syncs to iPhone)

### Phase B — Chat + Jira → Daily Plan
- Natural-language task input via API/chat
- Jira API: pull assigned issues, merge with local tasks
- Generate prioritized daily plan, push to Reminders with due times

### Phase C — Autonomous loop + Reviews
- Background scheduler: morning plan, due reminders, nudges
- End-of-day: summary + productivity score
- Month-end: analysis report (completion rate, Jira vs local, trends)

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│ PDF / Chat  │────▶│ Task Engine  │────▶│ Neon PostgreSQL │
│ API upload  │     │ (LLM parse)  │     └────────┬────────┘
└─────────────┘     └──────────────┘              │
       │                    │                     ▼
       │              ┌──────▼──────┐     ┌─────────────────┐
       └─────────────▶│ Daily Plan  │────▶│ Apple Reminders │
                      └─────────────┘     │ (osascript)     │
                             ▲            └─────────────────┘
                      ┌──────┴──────┐
                      │ Jira API    │
                      └─────────────┘
                             │
                      ┌──────▼──────┐
                      │ Scheduler   │──▶ EOD summary, monthly report
                      └─────────────┘
```

## Stack
- **Python 3.11+**, FastAPI, Neon PostgreSQL, APScheduler
- **OpenAI** (or compatible API) for PDF/chat parsing and planning
- **Apple Reminders** via `osascript` (macOS only for write; iPhone via iCloud sync)
- **Jira REST API** (API token)

## Setup
See [README.md](../README.md).

## Milestones
| Milestone | Deliverable |
|-----------|-------------|
| A1 | PDF upload API + task extraction |
| A2 | Reminder creation on Mac |
| B1 | Chat/task endpoint |
| B2 | Jira sync + daily plan |
| C1 | Scheduler + EOD score |
| C2 | Monthly report endpoint |
