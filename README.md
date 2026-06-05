# TechPromos com Luiz

<div align="center">

**API de coleta de preços em marketplaces para integração com n8n + Telegram**

![Python](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111%2B-009688?logo=fastapi&logoColor=white)
![Railway](https://img.shields.io/badge/Deploy-Railway-blueviolet?logo=railway)

</div>

---

## 🎯 O que é o TechPromos com Luiz?

O **TechPromos com Luiz** é uma API REST desenvolvida em Python com FastAPI que coleta dados de produtos em marketplaces brasileiros.

### Qual problema ele resolve?

Automatiza o processo de monitoramento de preços. A API recebe a URL de um produto, faz a coleta dos dados (nome, preço à vista, preço original, preço parcelado, disponibilidade) e retorna tudo em JSON. O **n8n** cuida de toda a orquestração: define quais produtos monitorar, agenda as execuções e envia as ofertas para o canal do **Telegram**.

---

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                     Fluxo de execução                       │
│                                                             │
│   n8n configura a URL do produto                            │
│           ↓                                                 │
│   n8n chama POST /monitorar                                 │
│           ↓                                                 │
│   API Python coleta os dados do marketplace                 │
│           ↓                                                 │
│   API retorna JSON com os dados do produto                  │
│           ↓                                                 │
│   n8n formata e envia para o canal do Telegram              │
└─────────────────────────────────────────────────────────────┘
```

| Componente | Responsabilidade |
|---|---|
| **Python / FastAPI** | Serviço de coleta e processamento dos dados do produto (web scraping) |
| **n8n** | Orquestração: configura os produtos monitorados, agenda execuções, aplica regras e envia notificações |
| **Telegram** | Canal de saída das ofertas para o usuário final |

> **Importante:** As URLs dos produtos são configuradas exclusivamente no workflow do n8n. O Python atua como serviço de coleta de dados — ele não armazena, não agenda e não decide quais produtos monitorar. O n8n é responsável pela orquestração e configuração dos produtos.

---

## 🚀 Instalação (Desenvolvimento Local)

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/techpromos-luiz.git
cd techpromos-luiz

# 2. Crie e ative o ambiente virtual
python -m venv .venv

# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# 3. Instale as dependências
pip install -r requirements.txt
```

---

## ▶️ Como Usar

### Iniciar a API localmente

```bash
uvicorn app:app --reload --port 8000
```

A documentação interativa (Swagger UI) fica disponível em: `http://localhost:8000/docs`

### Testar a rota POST /monitorar

**PowerShell:**

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/monitorar" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"url": "https://www.mercadolivre.com.br/headset-sem-fio-pulse-elite-sony-cor-branco/p/MLB35725883"}'
```

**curl (Linux / macOS / Git Bash):**

```bash
curl -X POST http://localhost:8000/monitorar \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.mercadolivre.com.br/headset-sem-fio-pulse-elite-sony-cor-branco/p/MLB35725883"}'
```

### Entrada esperada

```json
{
  "url": "https://www.mercadolivre.com.br/headset-sem-fio-pulse-elite-sony-cor-branco/p/MLB35725883"
}
```

### Saída esperada

```json
{
  "produto": "Headset Sem Fio Pulse Elite - Sony Cor Branco",
  "preco": 743.91,
  "preco_original": 999.90,
  "preco_parcelado": 799.90,
  "url": "https://www.mercadolivre.com.br/...",
  "consultado_em": "2026-06-05T10:30:00",
  "marketplace": "Mercado Livre",
  "disponivel": true,
  "erro": null
}
```

---

## 🔧 Rotas da API

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/monitorar` | Recebe a URL do produto e retorna os dados coletados em JSON |
| `GET`  | `/`          | Confirma que a API está online |
| `GET`  | `/health`    | Health check para Railway e balanceadores de carga |
| `GET`  | `/docs`      | Documentação interativa (Swagger UI) |

---

## ☁️ Deploy no Railway

O projeto está pronto para deploy no Railway. O `Procfile` já está configurado:

```
web: uvicorn app:app --host 0.0.0.0 --port $PORT
```

### Passo a passo

1. Conecte o repositório GitHub ao Railway.
2. O Railway detecta automaticamente o `Procfile` e inicia a API.
3. Copie a URL pública gerada (ex: `https://sua-api.up.railway.app`).
4. Configure essa URL no workflow do n8n.

---

## 🔗 Integração com n8n

No seu workflow do n8n, adicione um nó **HTTP Request** com a seguinte configuração:

| Campo | Valor |
|---|---|
| **Method** | `POST` |
| **URL** | `https://sua-api.up.railway.app/monitorar` |
| **Body Content Type** | JSON |

**Body:**

```json
{
  "url": "https://www.mercadolivre.com.br/seu-produto"
}
```

A API retorna os dados completos em JSON. Use os nós seguintes do n8n (ex: IF, Telegram) para processar o retorno e enviar as ofertas para o canal.

Para adicionar novos produtos ao monitoramento, basta configurar as URLs diretamente no workflow do n8n.

---

## 🧪 Testes

```bash
# Rodar toda a suíte de testes
python -m pytest tests/ -v

# Com cobertura de código
python -m pytest tests/ -v --cov=techpromos --cov-report=term-missing
```

---

## ⚙️ Tecnologias

| Tecnologia | Uso |
|---|---|
| **Python 3.12+** | Linguagem principal |
| **FastAPI** | Framework da API REST |
| **Requests** | Requisições HTTP com retry automático |
| **BeautifulSoup4 + lxml** | Parse do HTML e extração de dados (JSON-LD + CSS) |
| **Pytest** | Testes automatizados |
| **n8n** | Orquestração de workflows (externo) |

---

## 📁 Estrutura do Projeto

```
├── app.py                     # API FastAPI — ponto de entrada da aplicação
├── Procfile                   # Comando de inicialização para o Railway
├── requirements.txt           # Dependências do projeto
├── pyproject.toml             # Configuração do pytest e cobertura
├── techpromos/
│   ├── __init__.py            # Metadados do pacote
│   ├── factory.py             # Fábrica de scrapers (seleção automática por domínio)
│   ├── logger.py              # Configuração padronizada de logging
│   └── scraper/
│       ├── __init__.py        # Exports do módulo de scrapers
│       ├── base.py            # Classe base abstrata + modelo ProdutoInfo
│       └── mercadolivre.py    # Scraper do Mercado Livre
└── tests/
    ├── test_api.py            # Testes das rotas da API
    ├── test_base.py           # Testes do modelo ProdutoInfo
    ├── test_factory.py        # Testes da fábrica de scrapers
    └── test_mercadolivre.py   # Testes do scraper do Mercado Livre
```
