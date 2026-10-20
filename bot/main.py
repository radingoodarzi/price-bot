"""Price bot entry point.

  python bot/main.py --check            -> sets due=true/false for the workflow
  python bot/main.py --run              -> post if a slot is due
  python bot/main.py --run --force      -> post right now
  python bot/main.py --dry              -> build the image only (out/latest.png), no Telegram, no state change
  python bot/main.py --catalog          -> refresh catalog.json (list of TGJU items for the panel)
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from render import build_html, caption_text, fmt_price, render_png  # noqa: E402
from schedule import due_slots, now_in, prune_slots  # noqa: E402
from sources import Fetcher  # noqa: E402
from telegram import send_photo  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config.json"
STATE = ROOT / "state.json"
OUT = ROOT / "out"
LOG_KEEP = 30


def load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def save_state(state):
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")


def set_output(key, value):
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(f"{key}={value}\n")


def add_log(state, now, status, message):
    state["last_status"] = status
    state["last_message"] = message
    state["last_run_at"] = now.isoformat(timespec="seconds")
    state.setdefault("log", []).insert(0, {"at": state["last_run_at"], "status": status, "message": message})
    del state["log"][LOG_KEEP:]


def collect_rows(cfg):
    """Read one price per template slot. The template has fixed rows, so ANY failure aborts the post."""
    fetcher = Fetcher()
    rows, errors = [], []
    for slot in cfg.get("slots", []):
        src = slot.get("source", {})
        try:
            got = fetcher.read(src)
        except Exception as exc:
            errors.append(f"{slot.get('label', slot.get('key'))}: {exc}")
            continue
        rows.append(
            {
                "key": slot["key"],
                "label": slot.get("label", slot["key"]),
                "unit": slot.get("unit", ""),
                "price": got["price"],
                "price_text": fmt_price(got["price"], src.get("decimals", 0)),
            }
        )
    return rows, errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--catalog", action="store_true")
    args = ap.parse_args()

    if args.catalog:
        rows = Fetcher().tgju()
        data = [{"slug": s, "name": r["name"]} for s, r in rows.items()]
        (ROOT / "catalog.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        print(len(data), "rows written to catalog.json")
        return 0

    cfg = load(CONFIG, {})
    state = load(STATE, {})
    force = args.force or os.environ.get("FORCE", "").lower() == "true"
    now = now_in(cfg)
    slots = due_slots(cfg, state, now, force=force)

    if args.check:
        print("due:", slots or "none")
        set_output("due", "true" if slots else "false")
        return 0

    if not slots and not args.dry:
        print("nothing due")
        return 0

    rows, errors = collect_rows(cfg)
    if errors:
        msg = "قیمت همه‌ی ردیف‌ها خوانده نشد؛ چیزی پست نشد. " + " | ".join(errors)
        print(msg)
        if not args.dry and state.get("last_message") != msg:
            add_log(state, now, "error", msg)
            save_state(state)
        return 1

    values = {r["key"]: r["price"] for r in rows}
    last = state.get("last_values", {})
    if (
        not args.dry
        and not force
        and cfg.get("schedule", {}).get("skip_unchanged", True)
        and last
        and all(last.get(k) == v for k, v in values.items())
    ):
        state["done_slots"] = prune_slots(state.get("done_slots", []) + slots)
        add_log(state, now, "skipped", "قیمت‌ها نسبت به پست قبلی تغییری نکرده بودند؛ پست نشد.")
        save_state(state)
        print("unchanged, skipped")
        return 0

    OUT.mkdir(exist_ok=True)
    png = OUT / "latest.png"
    render_png(build_html(rows, now), png)
    caption = caption_text(cfg, rows, now)
    if args.dry:
        print("image:", png)
        print(caption)
        return 0

    try:
        send_photo(os.environ["TELEGRAM_BOT_TOKEN"], os.environ["TELEGRAM_CHAT_ID"], png, caption)
    except KeyError as exc:
        msg = f"Secret تنظیم نشده: {exc.args[0]}"
        print(msg)
        add_log(state, now, "error", msg)
        save_state(state)
        return 1
    except Exception as exc:
        msg = str(exc)
        print(msg)
        if state.get("last_message") != msg:
            add_log(state, now, "error", msg)
            save_state(state)
        return 1

    state["done_slots"] = prune_slots(state.get("done_slots", []) + slots)
    state["last_values"] = values
    state["last_post_at"] = now.isoformat(timespec="seconds")
    add_log(state, now, "posted", "پست شد")
    save_state(state)
    print("posted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
