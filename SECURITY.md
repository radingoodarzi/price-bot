# Security

## Model
- The Telegram bot token and channel id live only in **GitHub Actions secrets** (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`). They are never written to files or logs.
- The workflow runs only for the repository owner (not forks) and only on schedule or manual dispatch. Pull requests from forks never receive secrets.
- The settings panel (`docs/`) is a static page. It talks only to `api.github.com` (enforced by CSP) and needs a **fine-grained token limited to this repository**, stored in the owner's browser only.
- `config.json` is validated before every run: bad times, non-HTTPS / private-network source URLs and invalid divisors stop the post. A hard cap of 30 posts per 24 hours protects the channel from spam.

## If something looks wrong
1. Revoke the bot token in @BotFather (`/revoke`) and update the `TELEGRAM_BOT_TOKEN` secret.
2. Delete the panel token in GitHub → Settings → Developer settings → Fine-grained tokens.
3. Turn the bot off from the panel (or disable the `price-bot` workflow).

## Reporting
Open a private security advisory on this repository, or contact the owner directly.
