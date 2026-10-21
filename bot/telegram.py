"""Sends a photo to a Telegram channel. Never prints the token."""
import requests


class ChatMigrated(Exception):
    """The group became a supergroup; the post went to new_id, but the secret still holds the old id."""

    def __init__(self, new_id, message_id):
        super().__init__(new_id)
        self.new_id, self.message_id = new_id, message_id


def send_photo(token, chat_id, png_path, caption=""):
    try:
        return _send_photo(token, chat_id, png_path, caption)
    except _Migrate as m:
        # Telegram tells us the new id; post there right away instead of losing this post
        raise ChatMigrated(m.new_id, _send_photo(token, m.new_id, png_path, caption)) from None


class _Migrate(Exception):
    def __init__(self, new_id):
        super().__init__(new_id)
        self.new_id = new_id


def _send_photo(token, chat_id, png_path, caption):
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    try:
        with open(png_path, "rb") as fh:
            r = requests.post(
                url,
                data={"chat_id": chat_id, "caption": caption[:1024]},
                files={"photo": ("prices.png", fh, "image/png")},
                timeout=60,
            )
    except requests.RequestException as exc:
        raise RuntimeError("اتصال به تلگرام برقرار نشد: " + type(exc).__name__) from None
    try:
        data = r.json()
    except ValueError:
        raise RuntimeError(f"پاسخ نامعتبر از تلگرام (HTTP {r.status_code})") from None
    new_id = (data.get("parameters") or {}).get("migrate_to_chat_id")
    if not data.get("ok") and new_id:
        raise _Migrate(new_id)
    if not data.get("ok"):
        raise RuntimeError("تلگرام: " + str(data.get("description", r.status_code)))
    return data["result"]["message_id"]
