# Vercel + Apple Reminders Architecture

## The core problem

**Vercel cannot talk to Apple Reminders directly.**

Apple Reminders has no public cloud API. Reminders live on your devices (Mac/iPhone) and sync via **iCloud**. The `osascript` integration only works on a Mac that is running locally.

```
❌  Vercel  ──X──▶  Apple Reminders  (no API exists)
✅  Your Mac  ─────▶  Apple Reminders  (via osascript)
✅  iPhone  ◀──iCloud──▶  Mac Reminders  (automatic sync)
```

## Solution: hybrid architecture

Split the app into two parts:

```
┌─────────────────────────────────────────────────────────────┐
│  VERCEL (cloud)                                             │
│  • PDF upload / chat API                                    │
│  • Free LLM (Groq / Gemini / OpenRouter)                    │
│  • Jira sync, daily plan, scoring                           │
│  • Database (Neon PostgreSQL)                               │
│  • Stores tasks with reminder_id = null                     │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS poll every 60s
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  MAC BRIDGE (runs on your MacBook)                          │
│  guide-todoo bridge                                         │
│  • GET /bridge/pending  → tasks not yet in Reminders        │
│  • Creates reminders via osascript                          │
│  • POST /bridge/ack     → marks task synced                 │
└──────────────────────────┬──────────────────────────────────┘
                           │ osascript
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  APPLE REMINDERS — "Guide Todoo" list                       │
│  MacBook Reminders app                                      │
└──────────────────────────┬──────────────────────────────────┘
                           │ iCloud sync (automatic)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  iPHONE REMINDERS                                           │
│  Same list appears with notifications                       │
└─────────────────────────────────────────────────────────────┘
```

**Your iPhone gets todos automatically** because Apple syncs the Reminders list over iCloud. You don't need a separate iPhone integration.

## Free LLM providers (2026)

| Provider | Sign up | Free tier | Model to use |
|----------|---------|-----------|--------------|
| **Groq** (recommended) | [console.groq.com](https://console.groq.com) | ~30 req/min, no card | `llama-3.3-70b-versatile` |
| **Google Gemini** | [aistudio.google.com](https://aistudio.google.com/apikey) | ~1500 req/day | `gemini-2.0-flash` |
| **OpenRouter** | [openrouter.ai](https://openrouter.ai) | 20 req/min, 28+ free models | `meta-llama/llama-3.3-70b-instruct:free` |

All three use OpenAI-compatible APIs — just set `LLM_PROVIDER` and `LLM_API_KEY` in `.env`.

## Step-by-step setup

### 1. Deploy to Vercel

```bash
cd guide_todoo
npm i -g vercel   # or use vercel.com dashboard
vercel
```

Set these **Environment Variables** in Vercel dashboard:

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | Neon connection string (`postgresql://...?sslmode=require`) |
| `LLM_PROVIDER` | `groq` |
| `LLM_API_KEY` | your Groq key |
| `REMINDERS_MODE` | `bridge` |
| `BRIDGE_SECRET` | long random string (e.g. `openssl rand -hex 32`) |
| `JIRA_BASE_URL` | (optional) |
| `JIRA_EMAIL` | (optional) |
| `JIRA_API_TOKEN` | (optional) |

> **Database:** Use [Neon](https://neon.tech) (free PostgreSQL). Copy the connection string into `DATABASE_URL`. Tables are created automatically on first run.

### 2. Run Mac bridge on your MacBook

Create `.env` on your Mac (not on Vercel):

```bash
REMINDERS_MODE=local          # bridge agent writes locally
REMINDERS_LIST=Guide Todoo
BRIDGE_SECRET=same-secret-as-vercel
BRIDGE_API_URL=https://your-app.vercel.app
```

Start the bridge (keep it running):

```bash
guide-todoo bridge
# polls Vercel every 60s, creates Reminders on your Mac
```

**Auto-start on login** (optional):

```bash
# Save as ~/Library/LaunchAgents/com.guidetodoo.bridge.plist
# Then: launchctl load ~/Library/LaunchAgents/com.guidetodoo.bridge.plist
```

See `scripts/com.guidetodoo.bridge.plist` in this repo.

### 3. iPhone setup

1. On Mac: open **Reminders** → create/confirm list **Guide Todoo**
2. On iPhone: **Settings → Apple ID → iCloud → Reminders** = ON
3. Open Reminders app on iPhone — the list syncs within seconds

Notifications on iPhone use the due date/time set when the Mac bridge creates each reminder.

### 4. Scheduled jobs on Vercel

Local `APScheduler` doesn't run on Vercel. Use **Vercel Cron** instead (in `vercel.json`):

| Cron | Endpoint | What it does |
|------|----------|--------------|
| `0 3 * * *` (8am IST) | `/api/cron/morning` | Jira sync + daily plan |
| `0 14 * * *` (8pm IST) | `/api/cron/eod` | End-of-day summary |
| `0 15 L * *` | `/api/cron/monthly` | Monthly report |

## What runs where

| Feature | Vercel | Mac bridge | iPhone |
|---------|--------|------------|--------|
| PDF parsing | ✅ | | |
| LLM task breakdown | ✅ | | |
| Jira sync | ✅ | | |
| Daily plan | ✅ | | |
| Create Reminders | | ✅ | receives via iCloud |
| Push notifications | | Mac | ✅ iPhone |
| EOD score | ✅ | ✅ reminder | ✅ |

## Alternative: Mac-only (no Vercel)

If your Mac is always on, skip Vercel entirely:

```bash
REMINDERS_MODE=local
guide-todoo serve
```

Everything runs locally. iPhone still syncs via iCloud. Simpler, but Mac must stay awake.

## Security

- `BRIDGE_SECRET` protects `/bridge/*` endpoints — only your Mac should know it
- Never commit `.env` to git
- Free LLM providers may use your data for training — don't send confidential PDFs through free tiers
