#!/usr/bin/env python3
"""Minecraft playtime monitor for macOS.

Launched by launchd every minute. If Minecraft Java is running, add one
minute to today's accumulated time and emit a notification at threshold
points (remaining minutes, curfew, over-limit). The process is never
killed; this tool only notifies.
"""
import argparse
import json
import subprocess
import sys
import traceback
from datetime import datetime, date
from pathlib import Path

DATA_DIR = Path.home() / ".local" / "share" / "minecraft-playtime-monitor"
STATE_PATH = DATA_DIR / "state.json"
LOG_PATH = DATA_DIR / "monitor.log"

WEEKDAY_KEYS = [
    "monday", "tuesday", "wednesday", "thursday",
    "friday", "saturday", "sunday",
]


def parse_weekly_limits(value):
    parts = value.split(",")
    if len(parts) != 7:
        raise argparse.ArgumentTypeError(
            f"expected 7 comma-separated values (Mon..Sun), got {len(parts)}"
        )
    try:
        minutes = [int(p) for p in parts]
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"non-integer value: {e}")
    if any(m < 0 for m in minutes):
        raise argparse.ArgumentTypeError("weekly-limits must be non-negative")
    return dict(zip(WEEKDAY_KEYS, minutes))


def parse_int_list(value):
    if value == "":
        return []
    try:
        items = [int(p) for p in value.split(",")]
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"non-integer value: {e}")
    if any(n < 0 for n in items):
        raise argparse.ArgumentTypeError("values must be non-negative")
    return items


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Track Minecraft Java playtime and notify on limits.",
    )
    parser.add_argument(
        "--weekly-limits",
        type=parse_weekly_limits,
        default=parse_weekly_limits("90,90,90,90,90,120,120"),
        metavar="MON,TUE,WED,THU,FRI,SAT,SUN",
        help="Seven non-negative daily limits in minutes, comma-separated as Mon..Sun.",
    )
    parser.add_argument(
        "--curfew-hour",
        type=int,
        default=22,
        metavar="H",
        help="Hour (0-23) at or after which a curfew notification fires.",
    )
    parser.add_argument(
        "--notify-remaining",
        type=parse_int_list,
        default=[60, 10, 5, 1],
        metavar="N,N,...",
        help="Remaining-minute thresholds that trigger a one-shot notification.",
    )
    parser.add_argument(
        "--notify-repeat-interval",
        type=int,
        default=10,
        metavar="N",
        help="Playtime minutes between repeated curfew / over-limit notifications.",
    )
    parser.add_argument(
        "--process-pattern",
        default="java.*minecraft",
        metavar="REGEX",
        help="pgrep -f pattern used to detect the Minecraft process.",
    )
    args = parser.parse_args(argv)
    if not 0 <= args.curfew_hour <= 23:
        parser.error("--curfew-hour must be in 0..23")
    if args.notify_repeat_interval <= 0:
        parser.error("--notify-repeat-interval must be positive")
    return args


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


def main(argv=None):
    args = parse_args(argv)
    ensure_data_dir()
    state = load_state()
    now = datetime.now()
    today = date.today().isoformat()

    if state.get("date") != today:
        state = new_state(today)

    if not is_running(args.process_pattern):
        save_state(state)
        return

    state["accumulated_minutes"] += 1
    elapsed = state["accumulated_minutes"]

    weekday_key = WEEKDAY_KEYS[now.weekday()]
    daily_limit = args.weekly_limits[weekday_key]
    remaining = daily_limit - elapsed

    if now.hour >= args.curfew_hour:
        last = state.get("last_curfew_notify_minute")
        if last is None or elapsed - last >= args.notify_repeat_interval:
            notify("Minecraft", f"It's past {args.curfew_hour}:00. Time to wrap up.")
            state["last_curfew_notify_minute"] = elapsed
            save_state(state)
            return

    if remaining <= 0:
        last = state.get("last_over_limit_notify_minute")
        if last is None or elapsed - last >= args.notify_repeat_interval:
            over = elapsed - daily_limit
            notify(
                "Minecraft",
                f"Today's {daily_limit}-minute limit exceeded. "
                f"{elapsed} min played ({over} min over).",
            )
            state["last_over_limit_notify_minute"] = elapsed
            save_state(state)
            return

    for n in args.notify_remaining:
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
