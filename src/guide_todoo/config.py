from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# ponytail: preset free providers — all OpenAI-compatible
LLM_PRESETS: dict[str, dict[str, str]] = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model": "gemini-2.0-flash",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "model": "meta-llama/llama-3.3-70b-instruct:free",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
    },
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM — pick a free provider: groq | gemini | openrouter | openai
    llm_provider: str = "groq"
    llm_api_key: str = ""
    llm_model: str = ""
    llm_base_url: str | None = None

    # Legacy OpenAI env names still work
    openai_api_key: str = ""
    openai_model: str = ""
    openai_base_url: str | None = None

    # local = osascript on this Mac | bridge = Mac agent pulls from cloud API
    reminders_mode: str = "local"
    reminders_list: str = "Guide Todoo"
    bridge_secret: str = ""
    bridge_api_url: str = "http://127.0.0.1:8787"
    cron_secret: str = ""  # Vercel Cron: set CRON_SECRET in dashboard

    # todoist | reminders | off
    tasks_backend: str = "todoist"
    todoist_api_token: str = ""
    todoist_project_name: str = "Guide Todoo"

    jira_base_url: str = ""
    jira_email: str = ""
    jira_api_token: str = ""

    database_url: str = ""

    reports_dir: Path = Path("data/reports")

    morning_plan_hour: int = 8
    eod_summary_hour: int = 20
    timezone: str = "Asia/Kolkata"
    max_tasks_per_day: int = 4
    planning_horizon_weeks: int = 12

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://127.0.0.1:8787/auth/google/callback"
    app_base_url: str = "http://127.0.0.1:8787"
    todoist_webhook_secret: str = ""
    session_secret: str = "change-me"

    @property
    def resolved_google_redirect_uri(self) -> str:
        if self.google_redirect_uri and "your-app" not in self.google_redirect_uri:
            return self.google_redirect_uri
        return f"{self.app_base_url.rstrip('/')}/auth/google/callback"

    @property
    def resolved_api_key(self) -> str:
        return self.llm_api_key or self.openai_api_key

    @property
    def resolved_model(self) -> str:
        if self.llm_model:
            return self.llm_model
        if self.openai_model:
            return self.openai_model
        preset = LLM_PRESETS.get(self.llm_provider, LLM_PRESETS["groq"])
        return preset["model"]

    @property
    def resolved_base_url(self) -> str:
        if self.llm_base_url:
            return self.llm_base_url
        if self.openai_base_url:
            return self.openai_base_url
        preset = LLM_PRESETS.get(self.llm_provider, LLM_PRESETS["groq"])
        return preset["base_url"]

    @property
    def resolved_cron_secret(self) -> str:
        return self.cron_secret or self.bridge_secret


    @property
    def use_todoist(self) -> bool:
        return self.tasks_backend == "todoist" and bool(self.todoist_api_token)

    @property
    def push_reminders_locally(self) -> bool:
        return self.reminders_mode == "local" and self.tasks_backend != "todoist"


settings = Settings()
