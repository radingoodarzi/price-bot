"""Writes the new numbers onto the fixed template image (HTML overlay + Playwright screenshot)."""
import base64
import json
import os
from pathlib import Path

import jdatetime
from jinja2 import Environment, FileSystemLoader, select_autoescape

HERE = Path(__file__).parent
_FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def fa(text):
    return str(text).translate(_FA)


def fmt_price(value, decimals=0):
    return fa(f"{value:,.{int(decimals or 0)}f}")


def jalali_stamp(now):
    j = jdatetime.datetime.fromgregorian(datetime=now.replace(tzinfo=None))
    return fa(f"{j.year:04d}/{j.month:02d}/{j.day:02d}"), fa(now.strftime("%H:%M"))


def _b64(path):
    return base64.b64encode(Path(path).read_bytes()).decode()


def load_template(name="gold-gallery"):
    return json.loads((HERE / "templates" / f"{name}.json").read_text(encoding="utf-8"))


def build_html(rows, now, name="gold-gallery"):
    t = load_template(name)
    if len(rows) != len(t["price_y"]):
        raise ValueError(f"قالب {len(t['price_y'])} ردیف دارد ولی {len(rows)} قیمت داده شد")
    env = Environment(loader=FileSystemLoader(str(HERE / "templates")), autoescape=select_autoescape(["html"]))
    date, time_ = jalali_stamp(now)
    return env.get_template(f"{name}.html").render(
        t=t,
        font=_b64(HERE / "assets" / "Vazirmatn-wght.woff2"),
        bg=_b64(HERE / "assets" / t["image"]),
        prices=[r["price_text"] for r in rows],
        date=date,
        time=time_,
    )


def render_png(html_text, out_path, name="gold-gallery"):
    from playwright.sync_api import sync_playwright

    t = load_template(name)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=os.environ.get("BROWSER_CHANNEL") or None)  # e.g. msedge for local tests
        page = browser.new_page(viewport={"width": t["width"], "height": t["height"]}, device_scale_factor=1)
        page.set_content(html_text, wait_until="load")
        page.wait_for_selector("body[data-ready='1']", timeout=15000)
        page.screenshot(path=str(out_path), clip={"x": 0, "y": 0, "width": t["width"], "height": t["height"]})
        browser.close()


def caption_text(cfg, rows, now):
    date, time_ = jalali_stamp(now)
    lines = [f"▫️ {r['label']}: {r['price_text']} {r.get('unit', '')}".strip() for r in rows]
    tpl = cfg.get("caption") or "{date} — {time}\n\n{lines}"
    return tpl.replace("{date}", date).replace("{time}", time_).replace("{lines}", "\n".join(lines))
