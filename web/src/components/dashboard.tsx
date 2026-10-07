"use client";

import { GlassCard, GlassCardContent, GlassCardHeader, Progress, Button } from "@glinui/ui";
import { useEffect, useState } from "react";
import { api, type Health, type Progress as GoalProgress } from "@/lib/api";

export function Dashboard() {
  const [health, setHealth] = useState<Health | null>(null);
  const [progress, setProgress] = useState<GoalProgress | null>(null);
  const [tasks, setTasks] = useState<Record<string, unknown>[]>([]);
  const [brief, setBrief] = useState<string>("");
  const [slots, setSlots] = useState<string[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.health(), api.progress(), api.tasks("pending")])
      .then(([h, p, t]) => {
        setHealth(h);
        setProgress(p);
        setTasks(t.tasks.slice(0, 8));
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  async function run(action: "brief" | "plan" | "sync" | "weekly") {
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
        await api.syncTodoist();
        const t = await api.tasks("pending");
        setTasks(t.tasks.slice(0, 8));
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

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <GlassCard className="lg:col-span-2">
        <GlassCardHeader>
          <h2 className="text-xl font-medium text-white">Today</h2>
          <p className="text-sm text-white/60">Morning brief, calendar slots, and quick actions</p>
        </GlassCardHeader>
        <GlassCardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Button disabled={!!busy} onClick={() => run("brief")}>
              {busy === "brief" ? "Generating…" : "Morning brief"}
            </Button>
            <Button disabled={!!busy} onClick={() => run("plan")}>
              {busy === "plan" ? "Planning…" : "Daily plan"}
            </Button>
            <Button disabled={!!busy} onClick={() => run("sync")}>
              {busy === "sync" ? "Syncing…" : "Sync Todoist"}
            </Button>
            <Button disabled={!!busy} onClick={() => run("weekly")}>
              {busy === "weekly" ? "Reviewing…" : "Weekly review"}
            </Button>
          </div>
          {error ? <p className="text-sm text-red-300">{error}</p> : null}
          {brief ? (
            <pre className="max-h-80 overflow-auto whitespace-pre-wrap rounded-xl bg-black/20 p-4 text-sm text-white/80">
              {brief}
            </pre>
          ) : (
            <p className="text-sm text-white/50">Run morning brief or daily plan to see output here.</p>
          )}
          {slots.length > 0 ? (
            <p className="text-sm text-cyan-200/80">Free slots: {slots.join(" · ")}</p>
          ) : null}
        </GlassCardContent>
      </GlassCard>

      <div className="space-y-6">
        <GlassCard>
          <GlassCardHeader>
            <h2 className="text-lg font-medium text-white">Goal progress</h2>
          </GlassCardHeader>
          <GlassCardContent className="space-y-3">
            <p className="text-sm text-white/70">{progress?.main_goal || "Set your goal in onboarding"}</p>
            <Progress value={progress?.progress_pct || 0} />
            <p className="text-sm text-white/60">
              {progress?.completed ?? 0}/{progress?.total_tasks ?? 0} tasks · LeetCode {progress?.leetcode.total ?? 0}
            </p>
          </GlassCardContent>
        </GlassCard>

        <GlassCard>
          <GlassCardHeader>
            <h2 className="text-lg font-medium text-white">System</h2>
          </GlassCardHeader>
          <GlassCardContent className="space-y-2 text-sm text-white/70">
            <p>API: {health?.ok ? "online" : "offline"}</p>
            <p>Onboarded: {health?.onboarded ? "yes" : "no"}</p>
            <p>Google Calendar: {health?.google_calendar ? "connected" : "not connected"}</p>
            <p>Todoist: {health?.todoist_configured ? "configured" : "missing token"}</p>
          </GlassCardContent>
        </GlassCard>
      </div>

      <GlassCard className="lg:col-span-3">
        <GlassCardHeader>
          <h2 className="text-lg font-medium text-white">Pending tasks</h2>
        </GlassCardHeader>
        <GlassCardContent>
          {tasks.length === 0 ? (
            <p className="text-sm text-white/50">No pending tasks. Upload a PDF or chat ingest from API.</p>
          ) : (
            <ul className="space-y-2">
              {tasks.map((task) => (
                <li key={String(task.id)} className="rounded-xl bg-white/5 px-4 py-3 text-sm text-white/80">
                  <span className="font-medium text-white">{String(task.title)}</span>
                  {task.due_date ? <span className="ml-2 text-white/50">due {String(task.due_date)}</span> : null}
                </li>
              ))}
            </ul>
          )}
        </GlassCardContent>
      </GlassCard>
    </div>
  );
}
