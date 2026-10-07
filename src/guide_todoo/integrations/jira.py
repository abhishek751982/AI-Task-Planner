from typing import Any

import httpx

from guide_todoo.config import settings


class JiraClient:
    def __init__(self) -> None:
        if not all([settings.jira_base_url, settings.jira_email, settings.jira_api_token]):
            self.enabled = False
            self._base = ""
        else:
            self.enabled = True
            self._base = settings.jira_base_url.rstrip("/")

    def _auth(self) -> tuple[str, str]:
        return settings.jira_email, settings.jira_api_token

    def fetch_my_issues(self, max_results: int = 50) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        jql = "assignee = currentUser() AND status != Done ORDER BY priority DESC, updated DESC"
        url = f"{self._base}/rest/api/3/search"
        params = {"jql": jql, "maxResults": max_results, "fields": "summary,description,priority,duedate,status"}
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(url, params=params, auth=self._auth())
            resp.raise_for_status()
            data = resp.json()
        issues: list[dict[str, Any]] = []
        for item in data.get("issues", []):
            fields = item.get("fields", {})
            priority = fields.get("priority") or {}
            issues.append(
                {
                    "key": item.get("key"),
                    "title": fields.get("summary", item.get("key")),
                    "description": _plain_description(fields.get("description")),
                    "priority": _priority_map(priority.get("name")),
                    "due_date": fields.get("duedate"),
                    "status": (fields.get("status") or {}).get("name"),
                }
            )
        return issues


def _priority_map(name: str | None) -> int:
    if not name:
        return 2
    lower = name.lower()
    if "highest" in lower or "high" in lower:
        return 1
    if "low" in lower:
        return 3
    return 2


def _plain_description(desc: Any) -> str:
    if desc is None:
        return ""
    if isinstance(desc, str):
        return desc
    # Atlassian Document Format — ponytail: shallow text extraction only
    parts: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if node.get("type") == "text":
                parts.append(str(node.get("text", "")))
            for child in node.get("content", []):
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(desc)
    return " ".join(parts).strip()
