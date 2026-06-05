# TechPromos com Sobral

<div align="center">

**Monitorador de preços em marketplaces com saída para Telegram e n8n**

![Python](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python&logoColor=white)
![BeautifulSoup](https://img.shields.io/badge/BeautifulSoup4-4.12-orange)
![Requests](https://img.shields.io/badge/Requests-2.32-green)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

</div>

---

## Sobre o Projeto

O **TechPromos com Sobral** é uma ferramenta de linha de comando desenvolvida em Python para monitorar preços de produtos em marketplaces brasileiros. Com uma URL de produto, a ferramenta extrai automaticamente nome, preço e disponibilidade, retornando os dados em **JSON** (para integração com automações no n8n) ou como **mensagem formatada pronta para o Telegram**.

Desenvolvido como projeto acadêmico com foco em boas práticas de engenharia de software: separação de responsabilidades, tipagem estática, testes unitários e extensibilidade.

---

## Funcionalidades

- 🔍 Scraping de produtos do **Mercado Livre**
- 📦 Extração de: nome, preço, URL e data/hora da consulta
- 📤 Saída em **JSON** (para n8n, APIs, automações)
- 💬 Saída em **mensagem Telegram** (pronta para copiar e enviar em grupos)
- 📋 Monitoramento de **múltiplos produtos** a partir de um arquivo de lista
- 🔄 Retry automático em caso de falha de conexão
- 📝 Logs com rotação automática de arquivos
- ✅ Tratamento de erros: conexão, produto não encontrado, layout alterado
- 🧩 Arquitetura extensível para novos marketplaces (Shopee, Amazon)

---

## Tecnologias

| Tecnologia | Versão | Uso |
|---|---|---|
| Python | 3.12+ | Linguagem principal |
| [Requests](https://docs.python-requests.org/) | 2.32 | Requisições HTTP com retry |
| [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) | 4.12 | Parse de HTML |
| [lxml](https://lxml.de/) | 5.3 | Parser HTML de alta performance |
| [pytest](https://docs.pytest.org/) | 8.3 | Testes unitários |

---

## Estrutura do Projeto

```
techpromos/
├── techpromos/
│   ├── __init__.py
│   ├── __main__.py        # CLI principal
│   ├── factory.py         # Seleção automática de scraper por URL
│   ├── formatters.py      # Formatadores de saída (JSON, Telegram)
│   ├── logger.py          # Configuração de logs
│   └── scraper/
│       ├── base.py        # Classe abstrata BaseScraper + ProdutoInfo
│       ├── mercadolivre.py  # ✅ Implementado
│       ├── shopee.py      # 🔜 Placeholder
│       └── amazon.py      # 🔜 Placeholder
├── tests/
│   ├── test_base.py
│   ├── test_mercadolivre.py
│   └── test_factory.py
├── produtos.txt           # Lista de URLs para monitorar
├── monitorar.py           # Script para monitorar vários produtos de uma vez
├── requirements.txt
└── README.md
```

---

## Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/techpromos-sobral.git
cd techpromos-sobral

# 2. Crie e ative o ambiente virtual
python -m venv .venv

# Windows (Git Bash)
source .venv/Scripts/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Linux / macOS
source .venv/bin/activate

# 3. Instale as dependências
pip install -r requirements.txt
```

---

## Como Cadastrar Produtos

### Passo 1 — Abra o arquivo `produtos.txt`

O arquivo já vem com um template comentado. Adicione a URL de cada produto que deseja monitorar, **uma por linha**. Linhas começando com `#` são comentários e são ignoradas.

```
# produtos.txt

# === CONSOLES ===
https://www.mercadolivre.com.br/console-playstation5.../p/MLB57081243
https://www.mercadolivre.com.br/xbox-series-x.../p/MLB...

# === MONITORES ===
https://www.mercadolivre.com.br/monitor-gamer-aoc.../p/MLB...

# === PLACAS DE VÍDEO ===
https://www.mercadolivre.com.br/rtx-4060.../p/MLB...
```

> **Como pegar a URL certa:** Abra o produto no Mercado Livre, copie o endereço da barra do navegador e cole no arquivo. Não precisa remover os parâmetros de rastreamento (`?...` ou `#...`), o sistema ignora automaticamente.

### Passo 2 — Rode o monitoramento

```bash
# Formato Telegram (padrão) — pronto para copiar e enviar
python monitorar.py

# Formato JSON — para automações e n8n
python monitorar.py --formato json

# Usando um arquivo diferente do padrão
python monitorar.py --arquivo minha_lista.txt
```

### Exemplo de saída (formato Telegram)

```
──────────────────────────────────────────────────
[1/2] https://www.mercadolivre.com.br/console-playstation5...

🔥 Console Playstation®5 Slim Digital 🔥

💸 R$ 3.950,00

🛒 https://www.mercadolivre.com.br/console-playstation5.../p/MLB57081243

🤑 TECHPROMOS COM SOBRAL
https://t.me/techpromos_sobral 🔥

──────────────────────────────────────────────────
[2/2] https://www.mercadolivre.com.br/monitor-gamer...

🔥 Monitor Gamer AOC 24,5 Polegadas 🔥
...
```

---

## Monitorar Um Produto Só

```bash
# Formato Telegram
python -m techpromos "https://www.mercadolivre.com.br/..." --formato telegram

# Formato JSON
python -m techpromos "https://www.mercadolivre.com.br/..."
```

```json
{
  "produto": "Console Playstation®5 Slim Digital",
  "preco": 3950.0,
  "url": "https://www.mercadolivre.com.br/...",
  "consultado_em": "2026-06-04T22:35:00",
  "marketplace": "Mercado Livre",
  "disponivel": true,
  "erro": null
}
```

---

## Personalização do Telegram

Edite as duas constantes no topo do arquivo `techpromos/formatters.py`:

```python
TELEGRAM_GRUPO_NOME: str = "TECHPROMOS COM SOBRAL"
TELEGRAM_GRUPO_LINK: str = "https://t.me/techpromos_sobral"
```

---

## Integração com n8n

No n8n, adicione um nó **Execute Command** com:

- **Command:** `C:\caminho\.venv\Scripts\python.exe`
- **Arguments:** `monitorar.py --formato json`

Após o nó, adicione um **Code** para parsear o JSON:

```javascript
const saida = JSON.parse($input.item.json.stdout);
return [{ json: saida }];
```

---

## Testes

```bash
# Rodar todos os testes
pytest

# Com cobertura de código
pytest --cov=techpromos --cov-report=term-missing
```

**19 testes unitários** cobrindo extração via JSON-LD, seletores CSS, detecção de erros e seleção de scraper por URL.

---

## Marketplaces

| Marketplace | Status |
|---|---|
| Mercado Livre | ✅ Implementado |
| Shopee | 🔜 Em breve |
| Amazon | 🔜 Em breve |

---

## Licença

Projeto acadêmico — TechPromos com Sobral © 2026.
