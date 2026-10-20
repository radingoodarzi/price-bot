"""Run: python -m unittest discover -s tests -v"""
import sys
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bot"))

from main import config_problem, posts_last_24h, too_soon  # noqa: E402
from render import fmt_price, jalali_stamp  # noqa: E402
from schedule import due_slots  # noqa: E402
from sources import parse_tgju, to_number  # noqa: E402

TZ = ZoneInfo("Asia/Tehran")


def base_cfg(**over):
    cfg = {
        "enabled": True,
        "schedule": {"times": ["09:00", "12:00"], "grace_minutes": 60},
        "slots": [{"key": "a", "label": "A", "source": {"type": "tgju", "slug": "geram18", "divisor": 10}}],
    }
    cfg.update(over)
    return cfg


class Config(unittest.TestCase):
    def test_ok(self):
        self.assertEqual(config_problem(base_cfg()), "")

    def test_bad_time(self):
        cfg = base_cfg()
        cfg["schedule"]["times"] = ["25:99"]
        self.assertIn("نامعتبر", config_problem(cfg))

    def test_too_many_times(self):
        cfg = base_cfg()
        cfg["schedule"]["times"] = [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 15, 30)]
        self.assertTrue(config_problem(cfg))

    def test_divisor(self):
        cfg = base_cfg()
        cfg["slots"][0]["source"]["divisor"] = 0
        self.assertTrue(config_problem(cfg))

    def test_css_must_be_public_https(self):
        for url in ("http://example.com", "https://localhost/x", "https://127.0.0.1/", "https://192.168.1.5/", "https://169.254.169.254/"):
            cfg = base_cfg()
            cfg["slots"][0]["source"] = {"type": "css", "url": url, "selector": ".p", "divisor": 1}
            self.assertTrue(config_problem(cfg), url)
        cfg = base_cfg()
        cfg["slots"][0]["source"] = {"type": "css", "url": "https://example.com/p", "selector": ".p", "divisor": 1}
        self.assertEqual(config_problem(cfg), "")


class Schedule(unittest.TestCase):
    def test_due_within_grace_once(self):
        cfg = base_cfg()
        now = datetime(2026, 10, 20, 12, 20, tzinfo=TZ)
        self.assertEqual(due_slots(cfg, {}, now), ["2026-10-20 12:00"])
        self.assertEqual(due_slots(cfg, {"done_slots": ["2026-10-20 12:00"]}, now), [])

    def test_not_due_after_grace_or_when_off(self):
        cfg = base_cfg()
        self.assertEqual(due_slots(cfg, {}, datetime(2026, 10, 20, 14, 0, tzinfo=TZ)), [])
        cfg["enabled"] = False
        self.assertEqual(due_slots(cfg, {}, datetime(2026, 10, 20, 12, 5, tzinfo=TZ)), [])

    def test_days_filter(self):
        cfg = base_cfg()
        cfg["schedule"]["days"] = [1]  # Monday only; 2026-10-20 is a Tuesday
        self.assertEqual(due_slots(cfg, {}, datetime(2026, 10, 20, 12, 5, tzinfo=TZ)), [])

    def test_force(self):
        self.assertEqual(due_slots(base_cfg(enabled=False), {}, force=True), ["manual"])

    def test_rate_window(self):
        now = datetime(2026, 10, 20, 12, 0, tzinfo=TZ)
        state = {"recent_posts": ["2026-10-20T11:00:00+03:30", "2026-10-18T11:00:00+03:30", "bad"]}
        self.assertEqual(len(posts_last_24h(state, now)), 1)

    def test_min_gap(self):
        now = datetime(2026, 10, 20, 12, 0, tzinfo=TZ)
        self.assertTrue(too_soon({"last_post_at": "2026-10-20T11:58:00+03:30"}, now))
        self.assertFalse(too_soon({"last_post_at": "2026-10-20T11:50:00+03:30"}, now))
        self.assertFalse(too_soon({}, now))


class Parsing(unittest.TestCase):
    def test_numbers(self):
        self.assertEqual(to_number("۲۶٬۴۶۰٬۱۳۲"), 26460132.0)
        self.assertEqual(to_number("4,123.1"), 4123.1)
        self.assertIsNone(to_number("n/a"))

    def test_tgju_row(self):
        html = (
            '<table><tr data-market-row="geram18"><th>طلا ۱۸</th><td>265,144,000</td>'
            '<td><span class="high">(1.29%) 3,366,000</span></td><td>261,794,000</td><td>265,952,000</td></tr></table>'
        )
        row = parse_tgju(html)["geram18"]
        self.assertEqual(row["price"], 265144000.0)
        self.assertEqual(row["direction"], "up")
        self.assertEqual(row["percent"], 1.29)

    def test_format(self):
        self.assertEqual(fmt_price(268300000), "۲۶۸,۳۰۰,۰۰۰")
        self.assertEqual(fmt_price(4123.1, 1), "۴,۱۲۳.۱")
        date, time_ = jalali_stamp(datetime(2026, 10, 20, 16, 5))
        self.assertEqual((date, time_), ("۱۴۰۵/۰۷/۲۸", "۱۶:۰۵"))


if __name__ == "__main__":
    unittest.main()
