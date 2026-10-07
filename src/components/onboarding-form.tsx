"use client";

import { useEffect, useRef, useState } from "react";
import { FileUp, X } from "lucide-react";
import { Item, Stagger } from "@/components/motion";
import { Btn, Card, CardHead, Field, Input, Select } from "@/components/ui";
import { api } from "@/lib/api";

const TIMEZONES = [
  "Asia/Kolkata",
  "Asia/Dubai",
  "Asia/Singapore",
  "Asia/Tokyo",
  "Europe/London",
  "Europe/Berlin",
  "America/New_York",
  "America/Chicago",
  "America/Los_Angeles",
  "UTC",
];

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
  const [saving, setSaving] = useState(false);
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api
      .onboardStatus()
      .then((s) => {
        if (!s.onboarded) return;
        return api.profile().then((res) => setForm({ ...defaultForm, ...(res.profile as typeof defaultForm) }));
      })
      .catch(() => undefined);
  }, []);

  function set<K extends keyof typeof defaultForm>(key: K, value: (typeof defaultForm)[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function pickPdf(file: File | null) {
    if (!file) {
      setPdfFile(null);
      return;
    }
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setError("Please choose a PDF file.");
      return;
    }
    setError(null);
    setPdfFile(file);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setStatus(null);
    setError(null);
    try {
      await api.onboard({
        ...form,
        focus_day: form.focus_day || null,
        max_tasks_per_day: Number(form.max_tasks_per_day),
        morning_plan_hour: Number(form.morning_plan_hour),
        side_goal_hours_per_day: Number(form.side_goal_hours_per_day),
      });

      let msg = "Saved. Your planner now works the way you do.";
      if (pdfFile) {
        const res = await api.uploadPdf(pdfFile);
        msg += ` Parsed ${res.tasks_created} task${res.tasks_created === 1 ? "" : "s"} from ${res.filename}.`;
        setPdfFile(null);
        if (fileRef.current) fileRef.current.value = "";
      }
      setStatus(msg);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit}>
      <Stagger className="bento">
        {/* Who you are ───────────────────────────────── */}
        <Item className="col-full">
          <Card hero className="p-6 md:p-8">
            <CardHead
              label="01 — Identity"
              title={
                <>
                  Who&rsquo;s <em>planning</em>
                </>
              }
            />
            <div className="grid gap-5 md:grid-cols-3">
              <Field label="Role">
                <Select value={form.role} onChange={(e) => set("role", e.target.value)}>
                  <option value="student">Student</option>
                  <option value="professional">Professional</option>
                  <option value="both">Both</option>
                </Select>
              </Field>
              <Field label="Timezone">
                <Select value={form.timezone} onChange={(e) => set("timezone", e.target.value)}>
                  {[...new Set([form.timezone, ...TIMEZONES])].map((tz) => (
                    <option key={tz} value={tz}>
                      {tz.replace(/_/g, " ")}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Main goal">
                <Input
                  value={form.main_goal}
                  onChange={(e) => set("main_goal", e.target.value)}
                  placeholder="Crack FAANG interviews by Dec 2026"
                />
              </Field>
            </div>
          </Card>
        </Item>

        {/* Rhythm ────────────────────────────────────── */}
        <Item className="col-7">
          <Card lift className="h-full p-6 md:p-8">
            <CardHead
              label="02 — Rhythm"
              title={
                <>
                  When you&rsquo;re <em>sharp</em>
                </>
              }
            />
            <div className="grid gap-5 sm:grid-cols-2">
              <Field label="Work start">
                <Input type="time" value={form.work_start} onChange={(e) => set("work_start", e.target.value)} />
              </Field>
              <Field label="Work end">
                <Input type="time" value={form.work_end} onChange={(e) => set("work_end", e.target.value)} />
              </Field>
              <Field label="Deep work start">
                <Input
                  type="time"
                  value={form.deep_work_start}
                  onChange={(e) => set("deep_work_start", e.target.value)}
                />
              </Field>
              <Field label="Deep work end">
                <Input type="time" value={form.deep_work_end} onChange={(e) => set("deep_work_end", e.target.value)} />
              </Field>
              <Field label="Max tasks / day">
                <Select
                  value={String(form.max_tasks_per_day)}
                  onChange={(e) => set("max_tasks_per_day", Number(e.target.value))}
                >
                  {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((n) => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Focus day">
                <Input type="date" value={form.focus_day} onChange={(e) => set("focus_day", e.target.value)} />
              </Field>
            </div>
          </Card>
        </Item>

        {/* Boundaries ────────────────────────────────── */}
        <Item className="col-5">
          <Card lift className="h-full p-6 md:p-8">
            <CardHead
              label="03 — Boundaries"
              title={
                <>
                  When to stay <em>quiet</em>
                </>
              }
            />
            <div className="grid gap-5 sm:grid-cols-2">
              <Field label="Quiet from">
                <Input
                  type="time"
                  value={form.quiet_hours_start}
                  onChange={(e) => set("quiet_hours_start", e.target.value)}
                />
              </Field>
              <Field label="Quiet until">
                <Input
                  type="time"
                  value={form.quiet_hours_end}
                  onChange={(e) => set("quiet_hours_end", e.target.value)}
                />
              </Field>
              <div className="sm:col-span-2">
                <Field label="Notification tone">
                  <Select
                    value={form.notification_style}
                    onChange={(e) => set("notification_style", e.target.value)}
                  >
                    <option value="gentle">Gentle — nudge me softly</option>
                    <option value="normal">Normal — a reasonable balance</option>
                    <option value="focused">Focused — hold me to it</option>
                  </Select>
                </Field>
              </div>
            </div>
          </Card>
        </Item>

        {/* Document upload ───────────────────────────── */}
        <Item className="col-full">
          <Card lift className="p-6 md:p-8">
            <CardHead
              label="04 — Documents"
              title={
                <>
                  Seed your <em>plan</em>
                </>
              }
            />
            <p className="body mb-5 max-w-prose ink-2">
              Upload a syllabus, study plan, or project brief. We&rsquo;ll break it into tasks and push them to Todoist
              when you save.
            </p>

            <input
              ref={fileRef}
              type="file"
              accept=".pdf,application/pdf"
              className="sr-only"
              onChange={(e) => pickPdf(e.target.files?.[0] ?? null)}
            />

            {pdfFile ? (
              <div className="file-picked">
                <div className="flex min-w-0 items-center gap-3">
                  <FileUp className="h-5 w-5 shrink-0 accent" strokeWidth={1.6} />
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium ink">{pdfFile.name}</p>
                    <p className="mono ink-3 mt-0.5 text-xs">{(pdfFile.size / 1024).toFixed(0)} KB · ready on save</p>
                  </div>
                </div>
                <button
                  type="button"
                  className="btn-ghost file-picked-remove"
                  aria-label="Remove file"
                  onClick={() => {
                    setPdfFile(null);
                    if (fileRef.current) fileRef.current.value = "";
                  }}
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            ) : (
              <button
                type="button"
                className="file-drop"
                onClick={() => fileRef.current?.click()}
                onDragOver={(e) => {
                  e.preventDefault();
                  e.currentTarget.classList.add("is-drag");
                }}
                onDragLeave={(e) => {
                  e.preventDefault();
                  e.currentTarget.classList.remove("is-drag");
                }}
                onDrop={(e) => {
                  e.preventDefault();
                  e.currentTarget.classList.remove("is-drag");
                  pickPdf(e.dataTransfer.files?.[0] ?? null);
                }}
              >
                <FileUp className="h-6 w-6 accent" strokeWidth={1.5} />
                <span className="mt-3 text-sm font-medium ink">Drop a PDF here or click to browse</span>
                <span className="mono ink-3 mt-1 text-xs">Syllabus, roadmap, assignment sheet…</span>
              </button>
            )}
          </Card>
        </Item>

        {/* Save ──────────────────────────────────────── */}
        <Item className="col-full">
          <div className="flex flex-wrap items-center gap-5">
            <Btn type="submit" loading={saving}>
              Save &amp; activate
            </Btn>
            {status ? <p className="msg-ok">{status}</p> : null}
            {error ? <p className="msg-err">{error}</p> : null}
          </div>
        </Item>
      </Stagger>
    </form>
  );
}
