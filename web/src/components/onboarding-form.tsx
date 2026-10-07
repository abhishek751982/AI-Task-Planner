"use client";

import { useEffect, useState } from "react";
import { Button, GlassCard, GlassCardContent, GlassCardHeader, Input, Label, Select } from "@glinui/ui";
import { api } from "@/lib/api";

const defaultForm = {
  role: "student",
  work_start: "09:00",
  work_end: "18:00",
  deep_work_start: "07:00",
  deep_work_end: "09:00",
  main_goal: "",
  notification_style: "normal",
  quiet_hours_start: "22:00",
  quiet_hours_end: "07:00",
  max_tasks_per_day: 4,
  timezone: "Asia/Kolkata",
  focus_day: "",
  morning_plan_hour: 8,
  side_goal_hours_per_day: 2,
  activity_split: { work: 30, study: 50, personal: 20 },
  work_days: ["mon", "tue", "wed", "thu", "fri"],
};

export function OnboardingForm() {
  const [form, setForm] = useState(defaultForm);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.profile()
      .then((res) => setForm({ ...defaultForm, ...(res.profile as typeof defaultForm) }))
      .catch(() => undefined);
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setStatus("Saving…");
    setError(null);
    try {
      const payload = {
        ...form,
        focus_day: form.focus_day || null,
        max_tasks_per_day: Number(form.max_tasks_per_day),
        morning_plan_hour: Number(form.morning_plan_hour),
        side_goal_hours_per_day: Number(form.side_goal_hours_per_day),
      };
      await api.onboard(payload);
      setStatus("Profile saved. LLM planning will use your preferences.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
      setStatus(null);
    }
  }

  return (
    <GlassCard>
      <GlassCardHeader>
        <h2 className="text-xl font-medium text-white">Onboarding</h2>
        <p className="text-sm text-white/60">Work hours, goals, quiet hours, and focus days</p>
      </GlassCardHeader>
      <GlassCardContent>
        <form className="grid gap-4 md:grid-cols-2" onSubmit={submit}>
          <div className="space-y-2">
            <Label htmlFor="role">Role</Label>
            <Select
              id="role"
              value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value })}
              options={[
                { label: "Student", value: "student" },
                { label: "Professional", value: "professional" },
                { label: "Both", value: "both" },
              ]}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="main_goal">Main goal</Label>
            <Input
              id="main_goal"
              value={form.main_goal}
              onChange={(e) => setForm({ ...form, main_goal: e.target.value })}
              placeholder="Crack FAANG interviews by Dec 2026"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="work_start">Work start</Label>
            <Input id="work_start" value={form.work_start} onChange={(e) => setForm({ ...form, work_start: e.target.value })} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="work_end">Work end</Label>
            <Input id="work_end" value={form.work_end} onChange={(e) => setForm({ ...form, work_end: e.target.value })} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="deep_work_start">Deep work start</Label>
            <Input
              id="deep_work_start"
              value={form.deep_work_start}
              onChange={(e) => setForm({ ...form, deep_work_start: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="deep_work_end">Deep work end</Label>
            <Input
              id="deep_work_end"
              value={form.deep_work_end}
              onChange={(e) => setForm({ ...form, deep_work_end: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="max_tasks">Max tasks / day</Label>
            <Input
              id="max_tasks"
              type="number"
              min={1}
              max={10}
              value={form.max_tasks_per_day}
              onChange={(e) => setForm({ ...form, max_tasks_per_day: Number(e.target.value) })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="focus_day">Focus / quiet day (YYYY-MM-DD)</Label>
            <Input
              id="focus_day"
              value={form.focus_day}
              onChange={(e) => setForm({ ...form, focus_day: e.target.value })}
              placeholder="2026-08-15"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="notification_style">Notification style</Label>
            <Select
              id="notification_style"
              value={form.notification_style}
              onChange={(e) => setForm({ ...form, notification_style: e.target.value })}
              options={[
                { label: "Gentle", value: "gentle" },
                { label: "Normal", value: "normal" },
                { label: "Focused", value: "focused" },
              ]}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="timezone">Timezone</Label>
            <Input id="timezone" value={form.timezone} onChange={(e) => setForm({ ...form, timezone: e.target.value })} />
          </div>
          <div className="md:col-span-2">
            <Button type="submit">Save profile</Button>
            {status ? <p className="mt-3 text-sm text-emerald-300">{status}</p> : null}
            {error ? <p className="mt-3 text-sm text-red-300">{error}</p> : null}
          </div>
        </form>
      </GlassCardContent>
    </GlassCard>
  );
}
