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

## فایل‌ها

- `config.json` تنظیمات (پنل ویرایشش می‌کند) — `state.json` وضعیت و گزارش (ربات می‌نویسد)
- `catalog.json` فهرست آیتم‌های TGJU برای پنل (`python bot/main.py --catalog`)
- `bot/templates/gold-gallery.json` مختصات عددها روی عکس — `tools/make_clean_bg.py` پاک‌کردن عددهای نمونه از عکس اصلی

## تست محلی

```
.venv\Scripts\python bot\main.py --dry     # عکس را در out\latest.png می‌سازد، چیزی نمی‌فرستد
```
(با `BROWSER_CHANNEL=msedge` از Edge ویندوز استفاده می‌کند.)
