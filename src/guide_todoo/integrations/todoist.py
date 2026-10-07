from datetime import date, datetime
from typing import Any

import httpx

from guide_todoo.config import settings

_BASE = "https://api.todoist.com/api/v1"


class TodoistClient:
    def __init__(self) -> None:
        self.enabled = bool(settings.todoist_api_token)
        self._project_id: str | None = None

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {settings.todoist_api_token}"}

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        if not self.enabled:
            raise RuntimeError("TODOIST_API_TOKEN is not set.")
        with httpx.Client(timeout=30.0) as client:
            resp = client.request(method, f"{_BASE}{path}", headers=self._headers(), **kwargs)
            resp.raise_for_status()
            if resp.status_code == 204 or not resp.content:
                return None
            return resp.json()

    def ensure_project(self) -> str:
        if self._project_id:
            return self._project_id
        data = self._request("GET", "/projects")
        projects = data.get("results", data) if isinstance(data, dict) else data
        for project in projects:
            if project.get("name") == settings.todoist_project_name:
                self._project_id = str(project["id"])
                return self._project_id
        created = self._request("POST", "/projects", json={"name": settings.todoist_project_name})
        self._project_id = str(created["id"])
        return self._project_id

    def get_task(self, task_id: str) -> dict[str, Any]:
        return self._request("GET", f"/tasks/{task_id}")

    def list_active_tasks(self) -> list[dict[str, Any]]:
        project_id = self.ensure_project()
        data = self._request("GET", "/tasks", params={"project_id": project_id})
        if isinstance(data, dict):
            return data.get("results", [])
        return data if isinstance(data, list) else []

    def list_all_active_tasks(self) -> list[dict[str, Any]]:
        data = self._request("GET", "/tasks")
        if isinstance(data, dict):
            return data.get("results", [])
        return data if isinstance(data, list) else []

    def list_completed_tasks(self, *, since: date, until: date) -> list[dict[str, Any]]:
        project_id = self.ensure_project()
        try:
            data = self._request(
                "GET",
                "/tasks/completed/by_completion_date",
                params={"project_id": project_id, "since": since.isoformat(), "until": until.isoformat()},
            )
        except httpx.HTTPStatusError:
            data = self._request(
                "GET",
                "/tasks/completed/by_completion_date",
                params={"since": since.isoformat(), "until": until.isoformat()},
            )
        if isinstance(data, dict):
            return data.get("items", data.get("results", []))
        return data if isinstance(data, list) else []

    def create_task(
        self,
        title: str,
        *,
        description: str = "",
        due_date: date | None = None,
        due_datetime: datetime | None = None,
        priority: int = 2,
    ) -> str:
        payload: dict[str, Any] = {
            "content": title,
            "project_id": self.ensure_project(),
            "priority": _to_todoist_priority(priority),
        }
        if description:
            payload["description"] = description
        if due_datetime:
            payload["due_datetime"] = due_datetime.strftime("%Y-%m-%dT%H:%M:%S")
        elif due_date:
            payload["due_date"] = due_date.isoformat()
        created = self._request("POST", "/tasks", json=payload)
        return str(created["id"])

    def close_task(self, task_id: str) -> None:
        self._request("POST", f"/tasks/{task_id}/close")

    def update_task(
        self,
        task_id: str,
        *,
        due_date: date | None = None,
        due_datetime: datetime | None = None,
        content: str | None = None,
    ) -> None:
        payload: dict[str, Any] = {}
        if content:
            payload["content"] = content
        if due_datetime:
            payload["due_datetime"] = due_datetime.strftime("%Y-%m-%dT%H:%M:%S")
        elif due_date:
            payload["due_date"] = due_date.isoformat()
        if payload:
            self._request("POST", f"/tasks/{task_id}", json=payload)

    def add_comment_task(self, title: str, body: str) -> str:
        content = f"{title}: {body[:200]}" if body else title
        return self.create_task(content, description=body)


def _from_todoist_priority(priority: int) -> int:
    return max(1, min(3, 5 - int(priority or 2)))


def _to_todoist_priority(priority: int) -> int:
    # Guide Todoo: 1=urgent → Todoist 4 (highest)
    return max(1, min(4, 5 - priority))


_client: TodoistClient | None = None


def get_client() -> TodoistClient:
    global _client
    if _client is None:
        _client = TodoistClient()
    return _client
