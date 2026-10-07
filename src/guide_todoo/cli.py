import argparse
import sys
from pathlib import Path

import uvicorn

from guide_todoo.config import settings
from guide_todoo.ingest.pdf import extract_text_from_pdf
from guide_todoo.planner import generate_daily_plan, ingest_chat, ingest_pdf_text, sync_jira
from guide_todoo.bridge import run_loop, sync_once
from guide_todoo.review import end_of_day_summary, generate_monthly_report


def _bind_user(args: argparse.Namespace) -> None:
    from guide_todoo import db
    from guide_todoo.scope import current_user_id

    email = getattr(args, "user", None)
    if email:
        user = db.get_user_by_email(email.strip().lower())
        if not user:
            raise RuntimeError(f"No account for {email}. Create one in the app first.")
    else:
        users = db.list_users()
        if len(users) != 1:
            raise RuntimeError("Pass --user you@email.com. Create an account in the app first.")
        user = users[0]
    current_user_id.set(user["id"])


def cmd_serve(_: argparse.Namespace) -> None:
    uvicorn.run("guide_todoo.api:app", host="127.0.0.1", port=8787, reload=False)


def cmd_pdf(args: argparse.Namespace) -> None:
    _bind_user(args)
    path = Path(args.file)
    text = extract_text_from_pdf(path.read_bytes())
    tasks = ingest_pdf_text(text, path.name)
    print(f"Created {len(tasks)} tasks from {path.name}")
    for t in tasks:
        print(f"  - [{t['id']}] {t['title']}")


def cmd_chat(args: argparse.Namespace) -> None:
    _bind_user(args)
    tasks = ingest_chat(args.message)
    print(f"Created {len(tasks)} tasks")
    for t in tasks:
        print(f"  - [{t['id']}] {t['title']}")


def cmd_plan(args: argparse.Namespace) -> None:
    _bind_user(args)
    result = generate_daily_plan()
    print(result["plan"])


def cmd_jira(args: argparse.Namespace) -> None:
    _bind_user(args)
    created = sync_jira()
    print(f"Synced {len(created)} Jira issues")


def cmd_summary(args: argparse.Namespace) -> None:
    _bind_user(args)
    result = end_of_day_summary()
    print(result["report"])


def cmd_monthly(args: argparse.Namespace) -> None:
    _bind_user(args)
    result = generate_monthly_report()
    print(result["report"])
    print(f"\nSaved to {result['path']}")


def cmd_bridge(args: argparse.Namespace) -> None:
    if args.once:
        print(f"Synced {sync_once()} reminders")
    else:
        run_loop(args.interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Guide Todoo — AI task assistant")
    sub = parser.add_subparsers(dest="command", required=True)
    user_args = argparse.ArgumentParser(add_help=False)
    user_args.add_argument("--user", help="Account email when more than one user exists")

    p_serve = sub.add_parser("serve", help="Start API server on :8787")
    p_serve.set_defaults(func=cmd_serve)

    p_pdf = sub.add_parser("pdf", parents=[user_args], help="Ingest a PDF file")
    p_pdf.add_argument("file", help="Path to PDF")
    p_pdf.set_defaults(func=cmd_pdf)

    p_chat = sub.add_parser("chat", parents=[user_args], help="Add tasks from natural language")
    p_chat.add_argument("message", help="Task description")
    p_chat.set_defaults(func=cmd_chat)

    p_plan = sub.add_parser("plan", parents=[user_args], help="Generate today's daily plan")
    p_plan.set_defaults(func=cmd_plan)

    p_jira = sub.add_parser("jira", parents=[user_args], help="Sync Jira issues")
    p_jira.set_defaults(func=cmd_jira)

    p_summary = sub.add_parser("summary", parents=[user_args], help="End-of-day summary + score")
    p_summary.set_defaults(func=cmd_summary)

    p_monthly = sub.add_parser("monthly", parents=[user_args], help="Generate monthly analysis")
    p_monthly.set_defaults(func=cmd_monthly)

    p_bridge = sub.add_parser("bridge", help="Mac agent: sync cloud tasks → Apple Reminders")
    p_bridge.add_argument("--interval", type=int, default=60, help="Poll interval seconds")
    p_bridge.add_argument("--once", action="store_true", help="Sync once and exit")
    p_bridge.set_defaults(func=cmd_bridge)

    args = parser.parse_args()
    try:
        args.func(args)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        if "API key" in str(exc):
            print("Copy .env.example to .env and set LLM_API_KEY (Groq/Gemini/OpenRouter).", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
