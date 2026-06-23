#!/usr/bin/env python3
"""Minecraft playtime monitor for macOS.

Launched by launchd every minute. If Minecraft Java is running, add one
minute to today's accumulated time and emit a notification at threshold
points (remaining minutes, curfew, over-limit). The process is never
killed; this tool only notifies.
"""
import json
import subprocess
import sys
import traceback
from datetime import datetime, date
from pathlib import Path

# ---- Configuration (edit as needed) ----
WEEKLY_LIMITS = {
    "monday": 90,
    "tuesday": 90,
    "wednesday": 90,
    "thursday": 90,
    "friday": 90,
    "saturday": 120,
    "sunday": 120,
}
CURFEW_HOUR = 22
NOTIFY_REMAINING_MINUTES = [60, 10, 5, 1]
NOTIFY_REPEAT_INTERVAL = 10
PROCESS_PATTERN = "java.*minecraft"
# ----------------------------------------

DATA_DIR = Path.home() / ".local" / "share" / "minecraft-playtime-monitor"
STATE_PATH = DATA_DIR / "state.json"
LOG_PATH = DATA_DIR / "monitor.log"

WEEKDAY_KEYS = [
    "monday", "tuesday", "wednesday", "thursday",
    "friday", "saturday", "sunday",
]


def ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def new_state(today):
    return {
        "date": today,
        "accumulated_minutes": 0,
        "notified_remaining": [],
        "last_curfew_notify_minute": None,
        "last_over_limit_notify_minute": None,
    }


def load_state():
    if not STATE_PATH.exists():
        return new_state("")
    with open(STATE_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)


def is_running(pattern):
    result = subprocess.run(
        ["pgrep", "-f", pattern],
        capture_output=True, text=True, check=False,
    )
    return result.returncode == 0


def notify(title, message):
    safe = message.replace('"', '\\"')
    script = f'display notification "{safe}" with title "{title}" sound name "Glass"'
    subprocess.run(["osascript", "-e", script], check=False)


def log_error(message):
    timestamp = datetime.now().isoformat(timespec="seconds")
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")


def main():
    ensure_data_dir()
    state = load_state()
    now = datetime.now()
    today = date.today().isoformat()

    if state.get("date") != today:
        state = new_state(today)

    if not is_running(PROCESS_PATTERN):
        save_state(state)
        return

    state["accumulated_minutes"] += 1
    elapsed = state["accumulated_minutes"]

    weekday_key = WEEKDAY_KEYS[now.weekday()]
    daily_limit = WEEKLY_LIMITS[weekday_key]
    remaining = daily_limit - elapsed

    if now.hour >= CURFEW_HOUR:
        last = state.get("last_curfew_notify_minute")
        if last is None or elapsed - last >= NOTIFY_REPEAT_INTERVAL:
            notify("Minecraft", f"It's past {CURFEW_HOUR}:00. Time to wrap up.")
            state["last_curfew_notify_minute"] = elapsed
            save_state(state)
            return

    if remaining <= 0:
        last = state.get("last_over_limit_notify_minute")
        if last is None or elapsed - last >= NOTIFY_REPEAT_INTERVAL:
            notify("Minecraft", f"Today's {daily_limit}-minute limit is up. Find a good stopping point.")
            state["last_over_limit_notify_minute"] = elapsed
            save_state(state)
            return

    for n in NOTIFY_REMAINING_MINUTES:
        if remaining == n and n not in state["notified_remaining"]:
            notify("Minecraft", f"{n} minute(s) left.")
            state["notified_remaining"].append(n)

    save_state(state)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        try:
            ensure_data_dir()
            log_error(traceback.format_exc())
        except Exception:
            pass
        sys.exit(1)
