"""Sends a photo to a Telegram channel. Never prints the token."""
import requests


def send_photo(token, chat_id, png_path, caption=""):
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
    if not data.get("ok"):
        raise RuntimeError("تلگرام: " + str(data.get("description", r.status_code)))
    return data["result"]["message_id"]
