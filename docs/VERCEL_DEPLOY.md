# Vercel Deployment Guide

## 1. Prerequisites

- Code on GitHub: `Kartik989-max/AI-Based-Task-Planner`
- [Neon](https://neon.tech) database created
- [Groq](https://console.groq.com) API key (free)
- Vercel account (log in with **Kartik989-max** GitHub)

## 2. Import project in Vercel

1. Go to [vercel.com/new](https://vercel.com/new)
2. **Import Git Repository** → select `AI-Based-Task-Planner`
3. Framework Preset: **Other**
4. Root Directory: `./` (leave default)
5. **Do not deploy yet** — add env vars first (step 3)

## 3. Environment variables

In Vercel → Project → **Settings → Environment Variables**, add:

| Variable | Value | Environments |
|----------|-------|--------------|
| `DATABASE_URL` | Neon connection string (`postgresql://...?sslmode=require`) | Production, Preview, Development |
| `LLM_PROVIDER` | `groq` | All |
| `LLM_API_KEY` | your Groq key | All |
| `LLM_MODEL` | `llama-3.3-70b-versatile` | All |
| `REMINDERS_MODE` | `bridge` | Production |
| `BRIDGE_SECRET` | random string (`openssl rand -hex 32`) | All |
| `CRON_SECRET` | same or another random string | Production |
| `TIMEZONE` | `Asia/Kolkata` | All |

Optional (Jira):

| Variable | Value |
|----------|-------|
| `JIRA_BASE_URL` | `https://your-domain.atlassian.net` |
| `JIRA_EMAIL` | your email |
| `JIRA_API_TOKEN` | Jira API token |

### Connect Neon to Vercel (easier)

1. Vercel project → **Storage** tab → **Create Database** → **Neon**
2. This auto-adds `DATABASE_URL` to your project

## 4. Deploy

Click **Deploy** (or push to `main` — Vercel auto-deploys).

Your API will be at:

```
https://ai-based-task-planner.vercel.app
```

(or similar — check Vercel dashboard)

## 5. Verify deployment

```bash
curl https://YOUR-APP.vercel.app/health
```

Expected:

```json
{
  "ok": true,
  "database": "neon",
  "llm_configured": true,
  "reminders_mode": "bridge"
}
```

API docs: `https://YOUR-APP.vercel.app/docs`

## 6. Mac bridge (for Apple Reminders → iPhone)

On your Mac, update `.env`:

```bash
REMINDERS_MODE=local
BRIDGE_API_URL=https://YOUR-APP.vercel.app
BRIDGE_SECRET=same-as-vercel-BRIDGE_SECRET
```

Run:

```bash
guide-todoo bridge
```

This polls Vercel every 60s and creates Reminders on your Mac → syncs to iPhone via iCloud.

## 7. Cron jobs (automatic)

Defined in `vercel.json` (requires Vercel Pro for cron on hobby may be limited):

| Schedule (UTC) | Endpoint | Local time (IST) |
|----------------|----------|------------------|
| `0 3 * * *` | `/api/cron/morning` | 8:30 AM |
| `0 14 * * *` | `/api/cron/eod` | 7:30 PM |
| `0 15 28-31 * *` | `/api/cron/monthly` | month-end |

Vercel sends `Authorization: Bearer <CRON_SECRET>` — set `CRON_SECRET` in env vars.

> **Note:** Cron jobs require Vercel **Pro** plan on team accounts; Hobby has limits. You can also trigger manually:
> `curl -H "Authorization: Bearer YOUR_CRON_SECRET" https://YOUR-APP.vercel.app/api/cron/morning`

## 8. CLI deploy (alternative)

```bash
npm i -g vercel
cd guide_todoo
vercel login
vercel
vercel --prod
```

## Troubleshooting

| Error | Fix |
|-------|-----|
| `ModuleNotFoundError: guide_todoo` | Ensure latest code is pushed (`api/index.py` has src path fix) |
| `database: unavailable` | Check `DATABASE_URL` in Vercel env vars; Neon must allow Vercel IPs |
| `llm_configured: false` | Add `LLM_API_KEY` in Vercel settings |
| 401 on cron | Set `CRON_SECRET` in Vercel env |
| Reminders not appearing | Run `guide-todoo bridge` on Mac with matching `BRIDGE_SECRET` |
