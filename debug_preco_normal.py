import requests
url = 'https://www.mercadolivre.com.br/console-playstation5-slim-digital-pacote-astro-bot-e-gran-turismo-7-branco/p/MLB57081243'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'}
r = requests.get(url, headers=headers)
with open('debug_normal.html', 'w', encoding='utf-8') as f:
    f.write(r.text)
