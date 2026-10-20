# ربات قیمت طلا و سکه (Gold Gallery)

هر چند دقیقه GitHub Actions بیدار می‌شود، اگر ساعت ارسال رسیده باشد قیمت‌ها را از TGJU می‌خواند،
عددها را روی عکس قالب (`bot/assets/template-clean.png`) می‌نویسد و در کانال تلگرام می‌فرستد.
تنظیمات از **پنل** (`docs/index.html` روی GitHub Pages) عوض می‌شود.

## راه‌اندازی (یک بار)

1. **ربات تلگرام:** در @BotFather بساز، ربات را ادمین کانال کن.
2. **مخزن GitHub:** یک مخزن **عمومی** (Public) بساز (برای Pages و دقیقه‌ی نامحدود Actions) و همه‌ی این پوشه را در آن آپلود کن (به‌جز `.venv` و `out`).
3. **Secrets:** مخزن ← Settings ← Secrets and variables ← Actions ← New repository secret:
   - `TELEGRAM_BOT_TOKEN` = توکن ربات
   - `TELEGRAM_CHAT_ID` = `@آیدی_کانال` یا شناسه‌ی عددی (`-100…`)
4. **Pages:** Settings ← Pages ← Source: *Deploy from a branch* ← Branch `main` / پوشه‌ی `/docs`.
5. **توکن پنل:** Settings حساب ← Developer settings ← Fine-grained token، فقط همین مخزن، دسترسی‌های
   *Contents: Read and write* و *Actions: Read and write*. این توکن را فقط در پنل می‌چسبانی.
6. Actions ← price-bot ← **Run workflow** (تیک force) برای اولین پست آزمایشی.

## زمان‌سنج مطمئن (cron-job.org) — حتماً انجام بده

تایمر خود GitHub تضمینی نیست: روی مخزن تازه گاهی ساعت‌ها اصلاً اجرا نمی‌کند (۲۰۲۶-۱۰-۲۰ بعد از اولین پست
دستی، ۶ ساعت هیچ اجرای خودکاری نبود). برای همین یک سرویس بیرونی هر ۱۰ دقیقه ربات را بیدار می‌کند؛
ربات خودش تصمیم می‌گیرد ساعت ارسال رسیده یا نه، پس اجرای اضافه پست اضافه نمی‌سازد.

1. یک توکن **جدا** بساز: Developer settings ← Fine-grained token، فقط همین مخزن،
   فقط دسترسی *Actions: Read and write* (بدون Contents)، با تاریخ انقضا (مثلاً ۱ سال؛ یادت باشد تمدیدش کنی).
2. در cron-job.org حساب بساز ← Create cronjob:
   - URL: `https://api.github.com/repos/radingoodarzi/price-bot/actions/workflows/price-bot.yml/dispatches`
   - Schedule: هر ۱۰ دقیقه
   - Advanced ← Request method: `POST`
   - Headers: `Accept: application/vnd.github+json` و `Authorization: Bearer <توکن مرحله‌ی ۱>`
   - Request body: `{"ref":"main"}`
3. Test run: باید پاسخ `204` بدهد و در تب Actions یک اجرای `workflow_dispatch` ببینی.

اگر این توکن لو برود، فقط می‌شود ربات را بیدار کرد (کد و تنظیمات عوض نمی‌شود)؛ و حتی با «ارسال فوری»
حداکثر هر ۵ دقیقه یک پست و ۳۰ پست در روز ممکن است. در آن صورت توکن را پاک کن و یکی تازه بساز.

## فایل‌ها

- `config.json` تنظیمات (پنل ویرایشش می‌کند) — `state.json` وضعیت و گزارش (ربات می‌نویسد)
- `catalog.json` فهرست آیتم‌های TGJU برای پنل (`python bot/main.py --catalog`)
- `bot/templates/gold-gallery.json` مختصات عددها روی عکس — `tools/make_clean_bg.py` پاک‌کردن عددهای نمونه از عکس اصلی

## تست محلی

```
.venv\Scripts\python bot\main.py --dry     # عکس را در out\latest.png می‌سازد، چیزی نمی‌فرستد
```
(با `BROWSER_CHANNEL=msedge` از Edge ویندوز استفاده می‌کند.)
