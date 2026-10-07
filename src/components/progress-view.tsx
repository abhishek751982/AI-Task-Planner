"use client";

import { useEffect, useState } from "react";
import { EmptyIllustration } from "@/components/ambient";
import { CountUp, Item, Stagger } from "@/components/motion";
import { Bar, Card, CardHead, Eyebrow, Pill, Ring, Skeleton } from "@/components/ui";
import { api, type Progress as GoalProgress } from "@/lib/api";

const DIFFICULTY_ORDER = ["Easy", "Medium", "Hard"];

export function ProgressView() {
  const [progress, setProgress] = useState<GoalProgress | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .progress()
      .then(setProgress)
      .catch(() => undefined)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="bento">
        <Skeleton className="col-8 h-80" />
        <Skeleton className="col-4 h-80" />
        <Skeleton className="col-full h-40" />
      </div>
    );
  }

  const pct = progress?.progress_pct ?? 0;
  const byDiff = progress?.leetcode.by_difficulty ?? {};
  const diffEntries = Object.entries(byDiff).sort(
    (a, b) => DIFFICULTY_ORDER.indexOf(a[0]) - DIFFICULTY_ORDER.indexOf(b[0]),
  );
  const leetTotal = progress?.leetcode.total ?? 0;

  return (
    <Stagger className="bento">
      {/* Mission ─────────────────────────────────────── */}
      <Item className="col-8">
        <Card hero className="flex h-full flex-col justify-between gap-8 p-6 md:p-10">
          <div>
            <Eyebrow>The mission</Eyebrow>
            <p className="display-sm mt-4 max-w-[22ch]">
              {progress?.main_goal || (
                <>
                  Nothing set <em>yet</em>
                </>
              )}
            </p>
          </div>

          <div className="grid grid-cols-3 gap-6">
            {[
              { label: "Complete", value: pct, suffix: "%" },
              { label: "Done", value: progress?.completed ?? 0 },
              { label: "Remaining", value: progress?.pending ?? 0 },
            ].map(({ label, value, suffix }) => (
              <div key={label}>
                <p className="stat">
                  <CountUp value={value} suffix={suffix ?? ""} />
                </p>
                <p className="stat-label mt-3">{label}</p>
              </div>
            ))}
          </div>

          <Bar value={pct} />
        </Card>
      </Item>

      {/* Ring ────────────────────────────────────────── */}
      <Item className="col-4">
        <Card lift className="flex h-full flex-col items-center justify-center gap-6 p-6 md:p-8">
          <Ring value={pct} size={190}>
            <div>
              <p className="stat">
                <CountUp value={pct} />
              </p>
              <p className="stat-label mt-3">percent</p>
            </div>
          </Ring>
          <p className="body text-center max-w-[24ch]">
            {pct >= 100
              ? "Finished. Take the evening off."
              : pct > 0
                ? "Steady. Keep the pace gentle and consistent."
                : "Nothing logged yet — the first task is the hard one."}
          </p>
        </Card>
      </Item>

      {/* LeetCode ────────────────────────────────────── */}
      <Item className="col-full">
        <Card className="p-6 md:p-8">
          <CardHead
            label="Practice"
            title={
              <>
                LeetCode <em>ledger</em>
              </>
            }
            aside={<Pill tone={leetTotal > 0 ? "ok" : "default"}>{leetTotal} solved</Pill>}
          />

          {diffEntries.length === 0 ? (
            <div className="empty">
              <EmptyIllustration />
              <p className="body max-w-[34ch]">No solves logged yet. Add your first one from Config.</p>
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-3">
              {diffEntries.map(([diff, count]) => (
                <div key={diff} className="sunk p-5">
                  <p className="stat-sm">
                    <CountUp value={count} />
                  </p>
                  <p className="stat-label mt-2">{diff}</p>
                  <div className="mt-4">
                    <Bar value={leetTotal ? (count / leetTotal) * 100 : 0} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </Item>
    </Stagger>
  );
}
