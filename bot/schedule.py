"""Decides whether a post is due."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def now_in(cfg):
    return datetime.now(ZoneInfo(cfg.get("timezone", "Asia/Tehran")))


def due_slots(cfg, state, now=None, force=False):
    """Return list of slot keys that are due. ['manual'] when forced."""
    if force:
        return ["manual"]
    if not cfg.get("enabled", True):
        return []
    sch = cfg.get("schedule", {})
    days = sch.get("days") or []  # ISO weekdays 1=Mon..7=Sun; empty = every day
    now = now or now_in(cfg)
    if days and now.isoweekday() not in days:
        return []
    grace = int(sch.get("grace_minutes", 60))
    done = set(state.get("done_slots", []))
    out = []
    for t in sorted(set(sch.get("times", []))):
        try:
            h, m = (int(x) for x in t.split(":"))
        except ValueError:
            continue
        slot = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if slot <= now <= slot + timedelta(minutes=grace):
            key = slot.strftime("%Y-%m-%d %H:%M")
            if key not in done:
                out.append(key)
    return out


def prune_slots(slots, keep_days=3):
    cutoff = (datetime.now() - timedelta(days=keep_days)).strftime("%Y-%m-%d")
    return [s for s in slots if s == "manual" or s[:10] >= cutoff]
