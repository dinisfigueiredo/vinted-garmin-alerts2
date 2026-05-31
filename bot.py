import json
import os
import re
from pathlib import Path

import requests
from vinted_scraper import VintedScraper

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
DOMAIN = os.getenv("VINTED_DOMAIN", "https://www.vinted.pt")
QUERY = os.getenv("VINTED_QUERY", "garmin 255")
MAX_PRICE = float(os.getenv("MAX_PRICE", "135"))

SEEN_FILE = Path("seen_ids.json")


def load_seen():
    if SEEN_FILE.exists():
        try:
            return set(json.loads(SEEN_FILE.read_text(encoding="utf-8")))
        except Exception:
            return set()
    return set()


def save_seen(seen):
    SEEN_FILE.write_text(
        json.dumps(sorted(seen), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def price_to_float(value):
    if value is None:
        return None
    match = re.search(r"(\d+[.,]?\d*)", str(value))
    if not match:
        return None
    return float(match.group(1).replace(",", "."))


def send_telegram(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    response = requests.post(
        url,
        json={
            "chat_id": CHAT_ID,
            "text": text,
            "disable_web_page_preview": False,
        },
        timeout=30,
    )
    response.raise_for_status()


def main():
    seen = load_seen()
    scraper = VintedScraper(DOMAIN)

    items = scraper.search({"search_text": QUERY})
    new_seen = set(seen)
    sent = 0

    for item in items:
        item_id = str(getattr(item, "id", ""))
        if not item_id or item_id in seen:
            continue

        price = price_to_float(getattr(item, "price", None))
        if price is None or price > MAX_PRICE:
            continue

        title = getattr(item, "title", "Sem título")
        link = getattr(item, "url", "") or getattr(item, "web_url", "") or f"{DOMAIN}/items/{item_id}"

        message = (
            f"Garmin 255 abaixo de {MAX_PRICE:.0f}€\n"
            f"{title}\n"
            f"Preço: {price:.2f}€\n"
            f"{link}"
        )
        send_telegram(message)
        new_seen.add(item_id)
        sent += 1

    save_seen(new_seen)
    print(f"Enviadas {sent} notificações.")


if __name__ == "__main__":
    main()