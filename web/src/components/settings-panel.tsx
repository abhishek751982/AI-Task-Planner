"use client";

import { useEffect, useState } from "react";
import { Button, GlassCard, GlassCardContent, GlassCardHeader, Input, Label } from "@glinui/ui";
import { api } from "@/lib/api";

export function SettingsPanel() {
  const [connected, setConnected] = useState(false);
  const [slots, setSlots] = useState<{ start: string; end: string }[]>([]);
  const [leetcode, setLeetcode] = useState({ problem_slug: "", title: "", difficulty: "Medium" });
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    api.calendarStatus()
      .then((r) => setConnected(r.connected))
      .catch(() => undefined);
    api.calendarSlots()
      .then((r) => setSlots(r.slots))
      .catch(() => undefined);
  }, []);

  async function connectGoogle() {
    const { url } = await api.googleAuthUrl();
    window.location.href = url;
  }

  async function logSolve(e: React.FormEvent) {
    e.preventDefault();
    const res = await api.logLeetcode(leetcode);
    setMessage(`Logged. Total solves: ${res.stats.total}`);
    setLeetcode({ ...leetcode, problem_slug: "", title: "" });
  }

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <GlassCard>
        <GlassCardHeader>
          <h2 className="text-lg font-medium text-white">Google Calendar</h2>
          <p className="text-sm text-white/60">OAuth for free-window scheduling</p>
        </GlassCardHeader>
        <GlassCardContent className="space-y-4">
          <p className="text-sm text-white/70">Status: {connected ? "Connected" : "Not connected"}</p>
          <Button onClick={connectGoogle}>Connect Google</Button>
          {slots.length > 0 ? (
            <ul className="space-y-1 text-sm text-cyan-100/80">
              {slots.map((slot) => (
                <li key={`${slot.start}-${slot.end}`}>
                  {slot.start} – {slot.end}
                </li>
              ))}
            </ul>
          ) : null}
        </GlassCardContent>
      </GlassCard>

      <GlassCard>
        <GlassCardHeader>
          <h2 className="text-lg font-medium text-white">LeetCode log</h2>
          <p className="text-sm text-white/60">Track solves toward interview goals</p>
        </GlassCardHeader>
        <GlassCardContent>
          <form className="space-y-3" onSubmit={logSolve}>
            <div className="space-y-2">
              <Label htmlFor="slug">Slug</Label>
              <Input
                id="slug"
                value={leetcode.problem_slug}
                onChange={(e) => setLeetcode({ ...leetcode, problem_slug: e.target.value })}
                placeholder="two-sum"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="title">Title</Label>
              <Input
                id="title"
                value={leetcode.title}
                onChange={(e) => setLeetcode({ ...leetcode, title: e.target.value })}
                placeholder="Two Sum"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="difficulty">Difficulty</Label>
              <Input
                id="difficulty"
                value={leetcode.difficulty}
                onChange={(e) => setLeetcode({ ...leetcode, difficulty: e.target.value })}
              />
            </div>
            <Button type="submit">Log solve</Button>
            {message ? <p className="text-sm text-emerald-300">{message}</p> : null}
          </form>
        </GlassCardContent>
      </GlassCard>
    </div>
  );
}
