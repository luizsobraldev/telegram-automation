"""Debug: mostra o JSON-LD do bloco 0 e busca o winner no HTML."""
import json, re, requests
from bs4 import BeautifulSoup

headers = {
    "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Accept-Encoding": "identity",
}
url = "https://www.mercadolivre.com.br/console-playstation5-slim-digital-pacote-astro-bot-e-gran-turismo-7-branco/p/MLB57081243"
r = requests.get(url, headers=headers, timeout=15)
r.encoding = "utf-8"
soup = BeautifulSoup(r.text, "lxml")

# Mostra o bloco 0 cru
scripts_ld = soup.find_all("script", type="application/ld+json")
print(f"Total JSON-LD blocks: {len(scripts_ld)}")
print("Bloco 0 raw:", repr((scripts_ld[0].string or "")[:300]))

# Busca o winner no HTML (JSON inline)
m = re.search(r'"type":"winner"[^}]+?"price":(\d+)', r.text)
if m:
    print(f"\nWinner price (regex): {m.group(1)}")

# Busca original_price
m2 = re.search(r'"original_price":(\d+)', r.text)
if m2:
    print(f"Original price: {m2.group(1)}")

# Busca o nome no HTML inline
m3 = re.search(r'"name":"([^"]+)","image"', r.text)
if m3:
    print(f"Nome (inline): {m3.group(1)[:80]}")

# Confirma o que o scraper extrai hoje
from techpromos.scraper.mercadolivre import MercadoLivreScraper
s = MercadoLivreScraper()
info = s._extrair(r.text, url)
print(f"\n=== Resultado do scraper ===")
print(f"produto: {info.produto}")
print(f"preco: {info.preco}")
print(f"disponivel: {info.disponivel}")
print(f"erro: {info.erro}")
