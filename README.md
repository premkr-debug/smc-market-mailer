# Market ki Halchal – automated daily creative (free)

## One-time setup (~30 min)
1. Create a GitHub repo (free), upload this folder.
2. From Figma export into `assets/`: `logo.png`, `bull.png`, `bear.png` (transparent PNG) and optionally `bg.png` (800x1308 background).
3. Repo > Settings > Pages > Source: "Deploy from branch", branch `main`, folder `/docs`.
4. Repo > Actions > "Daily market update creative" > Run workflow (test). Image appears at
   `https://<user>.github.io/<repo>/latest.png` and `.../market-update-YYYY-MM-DD.png`.
5. In WebEngage: create the email template with that image URL (linked to your site/CTA),
   and schedule a recurring campaign Mon–Fri at 4:00 PM IST to your client segment.

## Notes
- Script exits silently on market holidays (no new candle) – schedule WebEngage campaign with a
  "skip" or pause on holidays.
- Gold/silver: set repo variables ENABLE_COMMODITIES=1, GOLD_PREMIUM, SILVER_PREMIUM and VERIFY against MCX.
- Local test: `pip install -r requirements.txt && playwright install chromium && FORCE=1 python market_update.py`
