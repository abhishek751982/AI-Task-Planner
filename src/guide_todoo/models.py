from pydantic import BaseModel, Field


class ParsedTask(BaseModel):
    title: str
    description: str = ""
    priority: int = Field(default=2, ge=1, le=3)
    due_date: str | None = None
    subtasks: list["ParsedTask"] = Field(default_factory=list)


ParsedTask.model_rebuild()


class DailyPlanItem(BaseModel):
    task_id: int | None = None
    title: str
    scheduled_time: str | None = None
    reason: str = ""


class DailyPlanResult(BaseModel):
    summary: str
    items: list[DailyPlanItem]
    focus: str = ""


class ActivitySplit(BaseModel):
    work: int = Field(default=50, ge=0, le=100)
    study: int = Field(default=30, ge=0, le=100)
    personal: int = Field(default=20, ge=0, le=100)


class OnboardingRequest(BaseModel):
    role: str = Field(description="student | professional | both")
    work_start: str = Field(default="09:00", description="HH:MM")
    work_end: str = Field(default="18:00", description="HH:MM")
    work_days: list[str] = Field(default_factory=lambda: ["mon", "tue", "wed", "thu", "fri"])
    deep_work_start: str = Field(default="07:00")
    deep_work_end: str = Field(default="09:00")
    side_goal_hours_per_day: float = Field(default=2.0, ge=0, le=12)
    activity_split: ActivitySplit = Field(default_factory=ActivitySplit)
    main_goal: str = Field(default="", description="e.g. Crack FAANG interviews by Dec 2026")
    notification_style: str = Field(default="normal", description="gentle | normal | focused")
    quiet_hours_start: str = Field(default="22:00")
    quiet_hours_end: str = Field(default="07:00")
    focus_day: str | None = Field(default=None, description="YYYY-MM-DD heavy work day — max 1 side task")
    morning_plan_hour: int = Field(default=8, ge=0, le=23)
    max_tasks_per_day: int = Field(default=4, ge=1, le=10)
    timezone: str = Field(default="Asia/Kolkata")
