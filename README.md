# Guide Todoo

AI task assistant for macOS: send PDFs or chat messages, break work into small tasks, sync to **Apple Reminders** (Mac + iPhone via iCloud), pull **Jira**, auto-plan your day, and get daily scores + monthly analysis.

## Features

| Phase | What it does |
|-------|----------------|
| **A** | PDF upload → LLM breaks into sub-tasks → Apple Reminders |
| **B** | Chat input + Jira sync → prioritized daily plan → Reminders |
| **C** | Scheduled morning plan, EOD summary + score, month-end report |

## Free LLM (no paid OpenAI needed)

Set in `.env`:

```bash
LLM_PROVIDER=groq          # or gemini | openrouter
LLM_API_KEY=your-key-here
```

| Provider | Free tier | Get key |
|----------|-----------|---------|
| **Groq** (recommended) | ~30 req/min | [console.groq.com](https://console.groq.com) |
| **Gemini** | ~1500 req/day | [aistudio.google.com](https://aistudio.google.com/apikey) |
| **OpenRouter** | 20 req/min, 28+ free models | [openrouter.ai](https://openrouter.ai) |

## Vercel + Mac + iPhone

**Vercel cannot access Apple Reminders directly.** Use the hybrid setup:

1. Deploy API to **Vercel** (`REMINDERS_MODE=bridge`)
2. Run **Mac bridge** on your MacBook: `guide-todoo bridge`
3. **iPhone** gets todos via iCloud sync automatically

Full architecture guide: [docs/VERCEL_AND_REMINDERS.md](docs/VERCEL_AND_REMINDERS.md)

## Database (Neon PostgreSQL)

1. Create a free project at [neon.tech](https://neon.tech)
2. Copy the connection string (must include `?sslmode=require`)
3. Set in `.env` and Vercel environment variables:

```bash
DATABASE_URL=postgresql://user:pass@ep-xxx.region.aws.neon.tech/neondb?sslmode=require
```

Tables (`tasks`, `daily_plans`, `monthly_reports`) are created automatically on first API call.

## Requirements

- macOS for Apple Reminders (Mac bridge or local mode)
- Python 3.11+
- Neon PostgreSQL database
- Free LLM API key (Groq recommended)
- Jira API token (optional)

## Quick start

```bash
cd guide_todoo
python -m venv .venv
source .venv/bin/activate
pip install -e .

cp .env.example .env
# Edit .env — set DATABASE_URL (Neon) and LLM_API_KEY

# Start API + background scheduler
guide-todoo serve
```

API docs: http://127.0.0.1:8787/docs

## CLI

```bash
# Phase A — PDF → tasks → Reminders
guide-todoo pdf ~/Downloads/weekly-plan.pdf

# Phase B — chat + Jira + daily plan
guide-todoo chat "Finish API docs by Friday, review PR #42 tomorrow morning"
guide-todoo jira
guide-todoo plan

# Phase C — reviews
guide-todoo summary
guide-todoo monthly

# Vercel mode — run on Mac to sync cloud tasks → Reminders → iPhone
guide-todoo bridge
```

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/ingest/pdf` | Upload PDF, create tasks + reminders |
| POST | `/ingest/chat` | `{"message": "..."}` |
| POST | `/jira/sync` | Pull assigned Jira issues |
| POST | `/plan/daily` | Generate today's plan |
| GET | `/tasks` | List tasks |
| POST | `/tasks/complete` | Mark task done |
| GET | `/review/daily` | EOD summary + score |
| POST | `/review/monthly` | Monthly analysis report |

## Todoist (Mac + iPhone, different Apple IDs OK)

1. Sign up at [todoist.com](https://todoist.com) — same account on Mac + iPhone apps
2. **Settings → Integrations → Developer** → copy API token
3. Set in `.env`:

```bash
TASKS_BACKEND=todoist
TODOIST_API_TOKEN=your-token
TODOIST_PROJECT_NAME=Guide Todoo
REMINDERS_MODE=off
```

Tasks sync to Todoist automatically. Notifications go to Todoist app on both devices.

## Apple Reminders (optional legacy)

Tasks are created in the **Guide Todoo** list via AppleScript. If that list is synced with iCloud Reminders, they appear on your iPhone automatically.

Grant **Reminders** access when macOS prompts you on first run.

## Autonomous schedule

When the server runs (`guide-todoo serve`):

- **08:00** — Sync Jira + generate daily plan
- **20:00** — End-of-day summary + score reminder
- **Last day of month 21:00** — Monthly report

Configure times in `.env` (`MORNING_PLAN_HOUR`, `EOD_SUMMARY_HOUR`, `TIMEZONE`).

## Project structure

```
guide_todoo/
├── docs/PROJECT_PLAN.md
├── src/guide_todoo/
│   ├── api.py           # FastAPI server
│   ├── cli.py           # CLI commands
│   ├── planner.py       # Ingest + daily plan
│   ├── review.py        # EOD + monthly
│   ├── scheduler.py     # Background jobs
│   └── integrations/
│       ├── reminders.py # Apple Reminders
│       └── jira.py      # Jira REST
└── data/reports/          # Monthly reports (local files)
```

## Neon setup

1. Sign up at [neon.tech](https://neon.tech) → create project
2. Dashboard → **Connection string** → copy `DATABASE_URL`
3. Paste into `.env` locally and Vercel env vars

Neon integrates with Vercel: Vercel dashboard → Storage → Neon → auto-sets `DATABASE_URL`.

## Jira setup

1. Create an API token: https://id.atlassian.com/manage-profile/security/api-tokens
2. Set `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN` in `.env`

## License

MIT
