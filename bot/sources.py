"""Fetching and parsing prices from websites."""
import re
import time

import requests
from bs4 import BeautifulSoup

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
TGJU_URL = "https://www.tgju.org/"
# The HTML of TGJU_URL carries the previous close; the page fills in live prices from this feed with JS.
TGJU_LIVE_URL = "https://call1.tgju.org/ajax.json"

_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def to_number(text):
    """First number found in text (Persian digits and thousand separators OK)."""
    if text is None:
        return None
    t = str(text).translate(_DIGITS)
    for ch in (",", "٬", "،"):
        t = t.replace(ch, "")
    m = re.search(r"-?\d+(?:\.\d+)?", t)
    return float(m.group()) if m else None


def fetch_html(url, tries=3):
    last = None
    for i in range(tries):
        try:
            r = requests.get(
                url,
                headers={"User-Agent": BROWSER_UA, "Accept-Language": "fa,en;q=0.8"},
                timeout=25,
            )
            r.raise_for_status()
            return r.content
        except requests.RequestException as exc:
            last = exc
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"cannot fetch {url}: {last}")


def parse_tgju(html):
    """Return {slug: {name, price, percent, direction, low, high}} from the TGJU home page."""
    soup = BeautifulSoup(html, "html.parser")
    rows = {}
    for tr in soup.find_all("tr", attrs={"data-market-row": True}):
        slug = tr["data-market-row"]
        if slug in rows:
            continue
        th = tr.find("th")
        tds = tr.find_all("td")
        if not th or len(tds) < 4:
            continue
        price = to_number(tds[0].get_text())
        if price is None:
            continue
        span = tds[1].find("span")
        classes = span.get("class", []) if span else []
        direction = "up" if "high" in classes else "down" if "low" in classes else "flat"
        pm = re.search(r"\(([\d.,]+)%\)", tds[1].get_text())
        percent = to_number(pm.group(1)) if pm else None
        rows[slug] = {
            "name": th.get_text(strip=True),
            "price": price,
            "percent": percent,
            "direction": direction,
            "low": to_number(tds[2].get_text()),
            "high": to_number(tds[3].get_text()),
        }
    return rows


def fetch_json(url, tries=3):
    last = None
    for i in range(tries):
        try:
            r = requests.get(
                url,
                headers={"User-Agent": BROWSER_UA, "Referer": TGJU_URL, "Accept": "application/json"},
                timeout=25,
            )
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as exc:
            last = exc
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"cannot fetch {url}: {last}")


def parse_tgju_live(data):
    """Return {slug: {price, percent, direction, low, high, ts}} from TGJU's live feed."""
    rows = {}
    for slug, v in ((data or {}).get("current") or {}).items():
        if not isinstance(v, dict):
            continue
        price = to_number(v.get("p"))
        if price is None:
            continue
        dt = v.get("dt")
        rows[slug] = {
            "price": price,
            "percent": v.get("dp"),
            "direction": "up" if dt == "high" else "down" if dt == "low" else "flat",
            "low": to_number(v.get("l")),
            "high": to_number(v.get("h")),
            "ts": v.get("ts"),
        }
    return rows


class SourceError(Exception):
    pass


class Fetcher:
    """Fetches every page only once per run."""

    def __init__(self):
        self._pages = {}
        self._tgju = None
        self._live = None

    def _page(self, url):
        if url not in self._pages:
            self._pages[url] = fetch_html(url)
        return self._pages[url]

    def tgju(self):
        if self._tgju is None:
            self._tgju = parse_tgju(self._page(TGJU_URL))
            if len(self._tgju) < 10:
                raise SourceError("ساختار TGJU عوض شده (ردیف کم است)")
        return self._tgju

    def tgju_live(self):
        if self._live is None:
            self._live = parse_tgju_live(fetch_json(TGJU_LIVE_URL))
            if len(self._live) < 10:
                raise SourceError("قیمت زنده‌ی TGJU خوانده نشد (ردیف کم است)")
        return self._live

    def read(self, item):
        """Return dict(price, percent, direction) already divided by item['divisor']."""
        div = float(item.get("divisor") or 1)
        kind = item.get("type", "tgju")
        if kind == "tgju":
            row = self.tgju_live().get(item.get("slug", ""))
            if not row:
                raise SourceError(f"آیتم «{item.get('slug')}» در TGJU پیدا نشد")
            return {
                "price": row["price"] / div,
                "percent": row["percent"],
                "direction": row["direction"],
            }
        if kind == "css":
            soup = BeautifulSoup(self._page(item["url"]), "html.parser")
            el = soup.select_one(item["selector"])
            if el is None:
                raise SourceError(f"سلکتور «{item['selector']}» در {item['url']} پیدا نشد")
            price = to_number(el.get_text())
            if price is None:
                raise SourceError(f"عدد داخل «{item['selector']}» خوانده نشد")
            return {"price": price / div, "percent": None, "direction": None}
        raise SourceError(f"نوع منبع ناشناخته: {kind}")
