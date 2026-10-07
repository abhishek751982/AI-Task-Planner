import subprocess
from datetime import datetime


def _escape_applescript(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def ensure_list_exists(list_name: str) -> None:
    script = f'''
    tell application "Reminders"
        if not (exists list "{_escape_applescript(list_name)}") then
            make new list with properties {{name:"{_escape_applescript(list_name)}"}}
        end if
    end tell
    '''
    _run(script)


def create_reminder(
    title: str,
    *,
    list_name: str,
    body: str = "",
    due: datetime | None = None,
) -> str:
    ensure_list_exists(list_name)
    props = [f'name:"{_escape_applescript(title)}"']
    if body:
        props.append(f'body:"{_escape_applescript(body)}"')
    if due:
        props.append(f'due date:date "{due.strftime("%A, %B %d, %Y %I:%M:%S %p")}"')
    props_str = ", ".join(props)
    script = f'''
    tell application "Reminders"
        tell list "{_escape_applescript(list_name)}"
            set r to make new reminder with properties {{{props_str}}}
            return id of r
        end tell
    end tell
    '''
    return _run(script).strip()


def complete_reminder_by_title(title: str, list_name: str) -> bool:
    script = f'''
    tell application "Reminders"
        tell list "{_escape_applescript(list_name)}"
            repeat with r in reminders
                if name of r is "{_escape_applescript(title)}" then
                    set completed of r to true
                    return "ok"
                end if
            end repeat
        end tell
    end tell
    return "missing"
    '''
    return _run(script).strip() == "ok"


def list_incomplete_reminders(list_name: str) -> list[dict[str, str]]:
    script = f'''
    tell application "Reminders"
        tell list "{_escape_applescript(list_name)}"
            set out to ""
            repeat with r in reminders
                if completed of r is false then
                    set out to out & (name of r) & linefeed
                end if
            end repeat
            return out
        end tell
    end tell
    '''
    raw = _run(script).strip()
    if not raw:
        return []
    return [{"title": line.strip()} for line in raw.splitlines() if line.strip()]


def _run(script: str) -> str:
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Apple Reminders failed: {result.stderr.strip() or result.stdout}")
    return result.stdout
