import json
import os
import re
from pathlib import Path
import requests

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
    
    # Criar uma sessão para guardar os cookies automáticos da Vinted
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "pt-PT,pt;q=0.9,en;q=0.8",
    })

    try:
        # Passo 1: Visitar o site principal para obter os cookies de sessão obrigatórios
        session.get(DOMAIN, timeout=15)
        
        # Passo 2: Chamar a API de pesquisa pública da Vinted
        api_url = f"{DOMAIN}/api/v2/catalog/items"
        params = {"search_text": QUERY, "per_page": "20"}
        
        response = session.get(api_url, params=params, timeout=15)
        response.raise_for_status()
        items = response.json().get("items", [])
    except Exception as e:
        print(f"Erro ao aceder à Vinted: {e}")
        return

    new_seen = set(seen)
    sent = 0

    for item in items:
        item_id = str(item.get("id", ""))
        if not item_id or item_id in seen:
            continue

        # A API devolve o preço diretamente em string ou dict (ex: "120.00" ou {"amount": "120.00"})
        price_data = item.get("price")
        if isinstance(price_data, dict):
            price = price_to_float(price_data.get("amount"))
        else:
            price = price_to_float(price_data)

        if price is None or price > MAX_PRICE:
            continue

        title = item.get("title", "Sem título")
        # Links na API costumam vir como caminhos relativos
        url_path = item.get("url", "")
        link = url_path if url_path.startswith("http") else f"{DOMAIN}{url_path}"

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