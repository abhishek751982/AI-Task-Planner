import type { NextConfig } from "next";

const backend = process.env.API_URL || "http://127.0.0.1:8787";

const apiPaths = [
  "health",
  "onboard",
  "profile",
  "ingest",
  "jira",
  "sync",
  "plan",
  "tasks",
  "review",
  "reminders",
  "auth",
  "stats",
  "leetcode",
  "calendar",
  "brief",
  "bridge",
  "webhooks",
  "api",
];

const nextConfig: NextConfig = {
  async rewrites() {
    if (process.env.VERCEL) return [];
    return apiPaths.flatMap((path) => [
      { source: `/${path}`, destination: `${backend}/${path}` },
      { source: `/${path}/:subpath*`, destination: `${backend}/${path}/:subpath*` },
    ]);
  },
};

export default nextConfig;
