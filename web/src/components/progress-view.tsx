"use client";

import { useEffect, useState } from "react";
import { GlassCard, GlassCardContent, GlassCardHeader, Progress } from "@glinui/ui";
import { api, type Progress as GoalProgress } from "@/lib/api";

export function ProgressView() {
  const [progress, setProgress] = useState<GoalProgress | null>(null);

  useEffect(() => {
    api.progress().then(setProgress).catch(() => undefined);
  }, []);

  const byDiff = progress?.leetcode.by_difficulty || {};

  return (
    <div className="grid gap-6 md:grid-cols-2">
      <GlassCard>
        <GlassCardHeader>
          <h2 className="text-lg font-medium text-white">Main goal</h2>
        </GlassCardHeader>
        <GlassCardContent className="space-y-4">
          <p className="text-white/80">{progress?.main_goal || "No goal set"}</p>
          <Progress value={progress?.progress_pct || 0} />
          <p className="text-sm text-white/60">
            {progress?.completed ?? 0} done · {progress?.pending ?? 0} pending
          </p>
        </GlassCardContent>
      </GlassCard>

      <GlassCard>
        <GlassCardHeader>
          <h2 className="text-lg font-medium text-white">LeetCode</h2>
        </GlassCardHeader>
        <GlassCardContent className="space-y-2 text-sm text-white/80">
          <p>Total solves: {progress?.leetcode.total ?? 0}</p>
          {Object.entries(byDiff).map(([diff, count]) => (
            <p key={diff}>
              {diff}: {count}
            </p>
          ))}
        </GlassCardContent>
      </GlassCard>
    </div>
  );
}
