# Guide Todoo — Intelligent Personal Flow

## The problem with generic task apps

Users ignore notifications when:
- Tasks don't fit their real schedule (9–6 job + DSA prep)
- Too many pings (notification fatigue)
- No connection to *their* goals (feels like a habit tracker, not a coach)
- Plans ignore what already worked or failed for them

**Guide Todoo should feel like a coach that knows you**, not a dumb reminder bot.

---

## Recommended flow

```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 0 — ONBOARDING (once, updatable)                         │
│  "Before I plan anything, let me understand your life"          │
│                                                                 │
│  • Role: student / working professional / both                  │
│  • Working hours: 9am–6pm Mon–Fri                               │
│  • Deep work window: 7–9am (best focus)                         │
│  • Side goals: DSA prep 2h/day, gym 1h                          │
│  • Activity split: 60% work, 30% study, 10% personal            │
│  • Notification style: gentle (max 2/day)                     │
│  • Quiet hours: 10pm–7am                                        │
│  • Main goal: "Crack FAANG interviews by Dec 2026"              │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 1 — INGEST (PDF / chat / Jira)                           │
│  LLM reads WITH user profile + memory                           │
│                                                                 │
│  "You work 9–6. DSA only fits 7–9am or after 7pm.               │
│   Spread 8-week plan across evenings + weekends, max 2/day."    │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 2 — SMART SCHEDULE (not blast everything at once)        │
│                                                                 │
│  • Only schedule in FREE windows                               │
│  • Hard tasks → deep work hours                                 │
│  • Light tasks → lunch / commute slots                          │
│  • Never exceed user's max_tasks_per_day                        │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 3 — INTELLIGENT NOTIFICATIONS (anti-ignore)              │
│                                                                 │
│  Morning (1 ping):  "Today: 2 DSA problems, 1 PR review"         │
│  Mid-day (optional): "90 min free before meeting — do Trees"    │
│  Evening (1 ping):  "Score 72/100. Tomorrow: start Graphs"       │
│                                                                 │
│  NOT: 15 separate Todoist tasks all due at 9am                  │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 4 — MEMORY (learn over time)                             │
│                                                                 │
│  Auto-saved facts:                                              │
│  • "Completes DSA tasks mostly 7–8am"                           │
│  • "Skips tasks scheduled on Friday evenings"                   │
│  • "Priority: Arrays > DP this month"                           │
│  • "Works at Fermi, Jira tasks due by EOD"                      │
│                                                                 │
│  Injected into every LLM call for planning                      │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 5 — EOD REFLECT + ROLLOVER                               │
│                                                                 │
│  • Sync Todoist completions → DB                                │
│  • Roll incomplete → next free slot (not just tomorrow)         │
│  • Extract 1–2 new memories from the day                        │
│  • Score + personalized summary notification                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Onboarding questions (API: `POST /onboard`)

| # | Question | Why |
|---|----------|-----|
| 1 | **Role** — student / professional / both | Schedules around job vs full-time study |
| 2 | **Work hours** — start/end, days | Blocks job time from task scheduling |
| 3 | **Deep work window** — when you focus best | Hard tasks (DSA, coding) go here |
| 4 | **Side goal hours/day** — e.g. 2h DSA | Caps study tasks per day |
| 5 | **Activity split** — work % / study % / personal % | Balances workload types |
| 6 | **Main goal** — free text | Every plan ties back to this |
| 7 | **Notification style** — gentle / normal / focused | Controls ping frequency |
| 8 | **Quiet hours** — no notifications | Respects sleep/family time |
| 9 | **Max tasks per day** — realistic number | Prevents overload (default 4) |

---

## Memory system

### What we store (`user_memories` table)

| Type | Example |
|------|---------|
| `preference` | "Prefers studying 7–9am" |
| `behavior` | "Often completes tasks on Tuesday, skips Friday" |
| `goal` | "Targeting FAANG by Dec 2026" |
| `context` | "Works at Fermi, uses Jira daily" |
| `insight` | "DP tasks take 2x longer than Arrays" |

### When memories are created

- **Onboarding** — profile → initial memories
- **After EOD** — LLM extracts 1–2 learnings from the day
- **After PDF ingest** — "User is on 8-week DSA plan"

### How memories are used

Every LLM call gets:
```
USER PROFILE: professional, 9-6, deep work 7-9am, goal: FAANG...
MEMORIES: [top 10 relevant facts]
TODAY: 2026-07-31, workload: 3 tasks Thursday...
```

---

## Notification strategy (why users won't ignore)

| Bad (ignore) | Good (follow) |
|--------------|---------------|
| 12 tasks all due 9am | 2–3 tasks in realistic slots |
| Generic "Do task X" | "Before your 2pm meeting: 45min for Trees" |
| Daily spam | Morning brief + EOD score only |
| Same message every day | Adapts to what you completed yesterday |
| No connection to goals | "This gets you closer to FAANG prep week 3" |

### Notification budget

| Style | Max pushes/day |
|-------|----------------|
| gentle | 2 (morning + evening) |
| normal | 3 (+ 1 mid-day nudge) |
| focused | 4 (urgent only) |

---

## What makes this NOT a habit tracker

| Habit tracker | Guide Todoo |
|---------------|-------------|
| "Drink water daily" | Reads your actual DSA PDF plan |
| Fixed reminders | Schedules around your job hours |
| No memory | Learns you skip Friday evenings |
| One-size-fits-all | Molds to professional + student life |
| Streak guilt | Coach tone: "2 tasks rolled, that's OK" |

---

## Implementation phases

| Phase | Status | What |
|-------|--------|------|
| A | ✅ Done | PDF/chat → Todoist, Neon DB, rollover |
| B | ✅ Done | Todoist ↔ DB sync, EOD score |
| C | **Now** | Onboarding + user profile + memory |
| D | Next | Schedule only in free windows |
| E | Next | Smart notification budget |
| F | Later | Multi-user auth |

---

## API endpoints (new)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/onboard` | Save user profile (run once) |
| GET | `/profile` | Get current profile + memories |
| PATCH | `/profile` | Update preferences |
| GET | `/onboard/status` | Check if onboarding complete |

**Rule:** If onboarding not complete, `/ingest/*` returns 400 with link to onboard first.
