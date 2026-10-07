"use client";

import { useEffect, useState } from "react";
import { Item, Stagger } from "@/components/motion";
import { Btn, Card, CardHead, Eyebrow, Field, Input, Pill, Select, Skeleton } from "@/components/ui";
import { api } from "@/lib/api";

export function SettingsPanel() {
  const [connected, setConnected] = useState(false);
  const [slots, setSlots] = useState<{ start: string; end: string }[]>([]);
  const [leetcode, setLeetcode] = useState({ problem_slug: "", title: "", difficulty: "Medium" });
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState(false);
  const [logging, setLogging] = useState(false);

  useEffect(() => {
    Promise.all([api.calendarStatus(), api.calendarSlots()])
      .then(([status, cal]) => {
        setConnected(status.connected);
        setSlots(cal.slots);
      })
      .catch(() => undefined)
      .finally(() => setLoading(false));
  }, []);

  async function connectGoogle() {
    setConnecting(true);
    try {
      const { url } = await api.googleAuthUrl();
      window.location.href = url;
    } catch {
      setConnecting(false);
    }
  }

  async function logSolve(e: React.FormEvent) {
    e.preventDefault();
    setLogging(true);
    setMessage(null);
    setError(null);
    try {
      const res = await api.logLeetcode(leetcode);
      setMessage(`Logged — ${res.stats.total} total solves`);
      setLeetcode({ ...leetcode, problem_slug: "", title: "" });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not log that solve");
    } finally {
      setLogging(false);
    }
  }

  if (loading) {
    return (
      <div className="bento">
        <Skeleton className="col-5 h-96" />
        <Skeleton className="col-7 h-96" />
      </div>
    );
  }

  return (
    <Stagger className="bento">
      {/* Calendar ────────────────────────────────────── */}
      <Item className="col-5">
        <Card hero className="flex h-full flex-col p-6 md:p-8">
          <CardHead
            label="Integration"
            title={
              <>
                Google <em>Calendar</em>
              </>
            }
            aside={
              <Pill tone={connected ? "ok" : "warn"} pulse={connected}>
                {connected ? "Connected" : "Not linked"}
              </Pill>
            }
          />

          <p className="body">
            Reads your busy blocks so the planner only ever schedules into genuinely free windows.
          </p>

          <div className="note mt-5">
            Publish your OAuth app in Google Cloud Console first — the Calendar scope needs Google verification, which
            takes roughly one to four weeks.{" "}
            <a href="https://support.google.com/cloud/answer/10311615" target="_blank" rel="noreferrer">
              Verification guide ↗
            </a>
          </div>

          <div className="mt-6">
            <Btn loading={connecting} onClick={connectGoogle}>
              {connected ? "Reconnect Google" : "Connect Google"}
            </Btn>
          </div>

          {slots.length > 0 ? (
            <div className="mt-auto pt-7">
              <Eyebrow>Free today</Eyebrow>
              <div className="mt-3 flex flex-wrap gap-2">
                {slots.map((slot) => (
                  <span key={`${slot.start}-${slot.end}`} className="chip">
                    {slot.start} – {slot.end}
                  </span>
                ))}
              </div>
            </div>
          ) : null}
        </Card>
      </Item>

      {/* LeetCode ────────────────────────────────────── */}
      <Item className="col-7">
        <Card className="h-full p-6 md:p-8">
          <CardHead
            label="Tracker"
            title={
              <>
                Log a <em>solve</em>
              </>
            }
          />

          <form className="grid gap-5 sm:grid-cols-2" onSubmit={logSolve}>
            <Field label="Slug">
              <Input
                value={leetcode.problem_slug}
                onChange={(e) => setLeetcode({ ...leetcode, problem_slug: e.target.value })}
                placeholder="two-sum"
                required
              />
            </Field>
            <Field label="Title">
              <Input
                value={leetcode.title}
                onChange={(e) => setLeetcode({ ...leetcode, title: e.target.value })}
                placeholder="Two Sum"
                required
              />
            </Field>
            <Field label="Difficulty">
              <Select
                value={leetcode.difficulty}
                onChange={(e) => setLeetcode({ ...leetcode, difficulty: e.target.value })}
              >
                <option value="Easy">Easy</option>
                <option value="Medium">Medium</option>
                <option value="Hard">Hard</option>
              </Select>
            </Field>

            <div className="sm:col-span-2">
              <Btn type="submit" loading={logging}>
                Log solve
              </Btn>
              {message ? <p className="msg-ok mt-4">{message}</p> : null}
              {error ? <p className="msg-err mt-4">{error}</p> : null}
            </div>
          </form>
        </Card>
      </Item>
    </Stagger>
  );
}
