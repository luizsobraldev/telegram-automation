# TechPromos com Luiz

API REST em Python/FastAPI para coleta de preços em marketplaces brasileiros.
Recebe a URL de um produto, faz web scraping e retorna os dados em JSON.

Projetada para integração com **n8n** + **Telegram**.

---

## 🏗️ Arquitetura

```
n8n → POST /monitorar → API coleta os dados → JSON → n8n → Telegram
```

| Componente | Responsabilidade |
|---|---|
| **Python / FastAPI** | Coleta e processamento dos dados do produto |
| **n8n** | Orquestração, agendamento e envio de notificações |
| **Telegram** | Canal de saída das ofertas |

---

## 🔧 Rotas

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/monitorar` | Recebe URL do produto e retorna dados em JSON |
| `GET`  | `/`          | Status da API |
| `GET`  | `/health`    | Health check |
| `GET`  | `/docs`      | Documentação interativa (Swagger UI) |

### Entrada

```json
{ "url": "https://www.mercadolivre.com.br/..." }
```

### Saída

```json
{
  "produto": "Headset Sem Fio Pulse Elite - Sony",
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

## ⚙️ Tecnologias

| Tecnologia | Uso |
|---|---|
| Python 3.12+ | Linguagem principal |
| FastAPI | Framework da API |
| Requests | Requisições HTTP |
| BeautifulSoup4 + lxml | Parse HTML e extração de dados |
| Pytest | Testes automatizados |

---

## ☁️ Deploy

Railway com `Procfile`:

```
web: uvicorn app:app --host 0.0.0.0 --port $PORT
```
