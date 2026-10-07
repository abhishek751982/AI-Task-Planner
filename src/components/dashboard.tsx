"use client";

import { useEffect, useState } from "react";
import { ArrowUpRight, CalendarRange, Loader2, RefreshCw, Sparkles, SunMedium } from "lucide-react";
import { EmptyIllustration } from "@/components/ambient";
import { CountUp, Item, Stagger } from "@/components/motion";
import { Bar, Btn, Card, CardHead, Eyebrow, InlineLoader, Input, Pill, Ring, Skeleton } from "@/components/ui";
import { api, type Health, type Progress as GoalProgress } from "@/lib/api";

const actions = [
  { id: "brief" as const, num: "01", icon: SunMedium, title: "Morning brief", desc: "A short read on the day ahead" },
  { id: "plan" as const, num: "02", icon: CalendarRange, title: "Daily plan", desc: "Drop tasks into your free windows" },
  { id: "sync" as const, num: "03", icon: RefreshCw, title: "Sync tasks", desc: "Pull the latest from Todoist" },
  { id: "weekly" as const, num: "04", icon: Sparkles, title: "Weekly review", desc: "Patterns worth noticing" },
];

function greetingFor(hour: number): string {
  if (hour < 5) return "Still up";
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  if (hour < 22) return "Good evening";
  return "Winding down";
}

export function Dashboard() {
  const [health, setHealth] = useState<Health | null>(null);
  const [progress, setProgress] = useState<GoalProgress | null>(null);
  const [tasks, setTasks] = useState<Record<string, unknown>[]>([]);
  const [brief, setBrief] = useState("");
  const [slots, setSlots] = useState<string[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stamp, setStamp] = useState("");
  const [chatMsg, setChatMsg] = useState("");
  const [adding, setAdding] = useState(false);

  // Rendered client-side only — the server has no idea what time it is for you.
  useEffect(() => {
    const now = new Date();
    const day = now.toLocaleDateString(undefined, { weekday: "short", day: "2-digit", month: "short" });
    setStamp(`${greetingFor(now.getHours())} · ${day}`);
  }, []);

  useEffect(() => {
    Promise.all([api.health(), api.progress(), api.tasks("pending")])
      .then(([h, p, t]) => {
        setHealth(h);
        setProgress(p);
        setTasks(t.tasks.slice(0, 8));
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  async function refreshTasks() {
    const [p, t] = await Promise.all([api.progress(), api.tasks("pending")]);
    setProgress(p);
    setTasks(t.tasks.slice(0, 8));
  }

  async function addTasks(e: React.FormEvent) {
    e.preventDefault();
    if (!chatMsg.trim()) return;
    setAdding(true);
    setError(null);
    try {
      const res = await api.ingestChat(chatMsg.trim());
      setChatMsg("");
      setBrief(`Added ${res.tasks_created} task${res.tasks_created === 1 ? "" : "s"} from your message.`);
      await refreshTasks();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add tasks");
    } finally {
      setAdding(false);
    }
  }

  async function run(action: (typeof actions)[number]["id"]) {
    setBusy(action);
    setError(null);
    try {
      if (action === "brief") {
        const res = await api.morningBrief();
        setBrief(String(res.brief || ""));
        setSlots(res.free_slots || []);
      } else if (action === "plan") {
        const res = await api.dailyPlan();
        setBrief(String(res.plan || ""));
        setSlots(res.free_slots || []);
      } else if (action === "sync") {
        const res = (await api.syncTodoist()) as {
          import?: { imported?: number; active?: number; completed?: number; skipped_reason?: string; error?: string };
          pull?: { synced?: number; completed?: unknown[]; skipped_reason?: string };
        };
        const imported = res.import ?? {};
        const pull = res.pull ?? {};
        const marked = pull.completed?.length ?? 0;
        const synced = pull.synced ?? 0;

        if (imported.skipped_reason === "todoist_not_configured" || pull.skipped_reason === "todoist_not_configured") {
          setBrief("Todoist is not connected. Set TODOIST_API_TOKEN in your environment to sync tasks.");
        } else if (imported.error) {
          setBrief(`Todoist import failed: ${imported.error}`);
        } else {
          const parts: string[] = [];
          if ((imported.imported ?? 0) > 0) {
            parts.push(
              `imported ${imported.imported} (${imported.active ?? 0} open, ${imported.completed ?? 0} done)`,
            );
          }
          if (synced > 0) {
            parts.push(`marked ${marked} of ${synced} linked as complete`);
          }
          setBrief(
            parts.length > 0
              ? `Sync complete — ${parts.join("; ")}.`
              : "Sync complete — no new Todoist tasks found. Add tasks below or in your Guide Todoo Todoist project.",
          );
        }

        await refreshTasks();
      } else {
        const res = await api.weeklyReview();
        setBrief(String(res.report || ""));
      }
      setProgress(await api.progress());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setBusy(null);
    }
  }

  if (loading) {
    return (
      <div className="bento">
        <Skeleton className="col-full h-40" />
        <Skeleton className="col-7 row-2 h-80" />
        <Skeleton className="col-5 h-64" />
        <Skeleton className="col-5 h-40" />
        <Skeleton className="col-full h-56" />
      </div>
    );
  }

  const pct = progress?.progress_pct ?? 0;

  return (
    <Stagger className="bento">
      {/* Actions ─────────────────────────────────────── */}
      <Item className="col-full">
        <div className="tiles">
          {actions.map(({ id, num, icon: Icon, title, desc }) => (
            <button key={id} type="button" className="tile" disabled={!!busy} onClick={() => run(id)}>
              <span className="tile-num">{num}</span>
              <span className="tile-icon">
                {busy === id ? <Loader2 className="h-4 w-4 spin" /> : <Icon className="h-4 w-4" strokeWidth={1.6} />}
              </span>
              <span className="tile-title">{title}</span>
              <span className="tile-desc">{desc}</span>
            </button>
          ))}
        </div>
      </Item>

      {/* Brief ───────────────────────────────────────── */}
      <Item className="col-7 row-2">
        <Card hero className="flex h-full flex-col p-6 md:p-8">
          <CardHead
            label={stamp || "Assistant"}
            title={
              <>
                Your <em>brief</em>
              </>
            }
            aside={
              <Pill tone={health?.ok ? "ok" : "warn"} pulse={health?.ok}>
                {health?.ok ? "Live" : "Offline"}
              </Pill>
            }
          />

          <div className="sunk flex-1 p-5">
            {busy ? (
              <InlineLoader label="Composing" />
            ) : brief ? (
              <div className="prose-out">{brief}</div>
            ) : (
              <div className="empty">
                <EmptyIllustration />
                <p className="body max-w-[26ch]">Pick an action above and your plan appears right here.</p>
              </div>
            )}
          </div>

          {error ? <p className="msg-err mt-4">{error}</p> : null}

          {slots.length > 0 ? (
            <div className="mt-5">
              <Eyebrow>Free windows</Eyebrow>
              <div className="mt-3 flex flex-wrap gap-2">
                {slots.map((s) => (
                  <span key={s} className="chip">
                    {s}
                  </span>
                ))}
              </div>
            </div>
          ) : null}
        </Card>
      </Item>

      {/* Goal ring ───────────────────────────────────── */}
      <Item className="col-5">
        <Card lift className="flex h-full flex-col items-center justify-center p-6 md:p-8">
          <Ring value={pct}>
            <div>
              <p className="stat">
                <CountUp value={pct} />
              </p>
              <p className="stat-label mt-3">percent</p>
            </div>
          </Ring>
          <p className="stat-label mt-6 accent">Goal progress</p>
          <p className="body mt-2 max-w-[30ch] text-center">{progress?.main_goal || "Set your mission in Setup"}</p>
        </Card>
      </Item>

      {/* Counts ──────────────────────────────────────── */}
      <Item className="col-5">
        <Card lift className="h-full p-6 md:p-8">
          <Eyebrow>Tally</Eyebrow>
          <div className="mt-5 grid grid-cols-3 gap-4">
            {[
              { label: "Done", value: progress?.completed ?? 0 },
              { label: "Pending", value: progress?.pending ?? 0 },
              { label: "LeetCode", value: progress?.leetcode.total ?? 0 },
            ].map(({ label, value }) => (
              <div key={label}>
                <p className="stat-sm">
                  <CountUp value={value} />
                </p>
                <p className="stat-label mt-2">{label}</p>
              </div>
            ))}
          </div>
          <div className="mt-6">
            <Bar value={pct} />
          </div>
          <p className="mono ink-3 mt-4">{health?.onboarded ? "Profile active" : "Setup incomplete"}</p>
        </Card>
      </Item>

      {/* Tasks ───────────────────────────────────────── */}
      <Item className="col-full">
        <Card className="p-6 md:p-8">
          <CardHead
            label="Queue"
            title={
              <>
                Waiting on <em>you</em>
              </>
            }
            aside={<Pill>{tasks.length} open</Pill>}
          />

          {tasks.length === 0 ? (
            <div className="empty">
              <EmptyIllustration />
              <p className="body max-w-[34ch]">Nothing queued yet. Sync from Todoist or describe tasks below.</p>
            </div>
          ) : (
            <ul>
              {tasks.map((task, i) => (
                <li key={String(task.id)} className="task">
                  <span className="task-num">{String(i + 1).padStart(2, "0")}</span>
                  <span className="task-title">{String(task.title)}</span>
                  {task.due_date ? <span className="task-meta">{String(task.due_date)}</span> : null}
                  <ArrowUpRight className="task-arrow h-4 w-4" strokeWidth={1.6} />
                </li>
              ))}
            </ul>
          )}

          <form className="mt-8 flex flex-col gap-3 border-t border-[var(--line)] pt-6 sm:flex-row" onSubmit={addTasks}>
            <Input
              value={chatMsg}
              onChange={(e) => setChatMsg(e.target.value)}
              placeholder="e.g. Study graphs tomorrow, finish resume by Friday"
              className="flex-1"
            />
            <Btn type="submit" loading={adding} disabled={!chatMsg.trim()}>
              Add tasks
            </Btn>
          </form>
        </Card>
      </Item>
    </Stagger>
  );
}
