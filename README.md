# TechPromos com Luiz

API REST em Python/FastAPI para coleta e descoberta de preços em marketplaces brasileiros.

Recebe uma URL de produto ou um termo de busca, realiza web scraping e retorna os dados em JSON.

Projetada para integração com **n8n** + **Google Sheets** + **Telegram**.

---

## 🏗️ Arquitetura

```
Google Sheets (termos de busca e regras)
        ↓
       n8n (lê termos, aplica filtros, envia Telegram)
        ↓
  POST /monitorar   ou   POST /buscar
        ↓
  API FastAPI (scraping no Mercado Livre)
        ↓
       JSON
        ↓
       n8n
        ↓
     Telegram
```

| Componente | Responsabilidade |
|---|---|
| **Google Sheets** | Armazena termos de busca, regras de filtro e configurações |
| **n8n** | Orquestra agendamento, filtros e envio de notificações |
| **Python / FastAPI** | Coleta e processamento dos dados dos produtos |
| **Telegram** | Canal de saída das ofertas |

> **Importante:** A API **não aplica filtros** de preço, palavras obrigatórias ou palavras bloqueadas.
> Esses filtros são responsabilidade do n8n, que lê as regras diretamente do Google Sheets.
> A API também **não envia mensagens** para o Telegram.

---

## 🔧 Rotas

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/monitorar` | Consulta um produto específico por URL e retorna os dados em JSON |
| `POST` | `/buscar` | Busca produtos automaticamente por termo e retorna lista de resultados |
| `GET` | `/` | Status da API |
| `GET` | `/health` | Health check |
| `GET` | `/docs` | Documentação interativa (Swagger UI) |

---

## 📌 Diferença entre /monitorar e /buscar

### POST /monitorar — Monitoramento por URL

Use quando você já sabe exatamente qual produto quer acompanhar.

- **Entrada:** URL exata de um produto no Mercado Livre
- **Saída:** Dados de **um único produto** (nome, preço, preço original, preço parcelado, disponibilidade)
- **Uso:** Monitorar um produto específico que você já encontrou e quer acompanhar

**Entrada:**
```json
{
  "url": "https://www.mercadolivre.com.br/p/MLB57081243"
}
```

**Saída:**
```json
{
  "produto": "Console PlayStation 5 Slim Digital",
  "preco": 3998.07,
  "preco_original": 4599.90,
  "preco_parcelado": 4299.90,
  "url": "https://www.mercadolivre.com.br/...",
  "consultado_em": "2026-06-07T21:00:00",
  "marketplace": "Mercado Livre",
  "disponivel": true,
  "erro": null
}
```

---

### POST /buscar — Descoberta automática por termo

Use quando você quer encontrar automaticamente os melhores produtos para um termo de busca.

- **Entrada:** Termo de busca (palavra-chave)
- **Saída:** **Lista de produtos** encontrados na página de resultados do Mercado Livre
- **Uso:** Descoberta automática de ofertas a partir de termos configurados no Google Sheets

**Entrada:**
```json
{
  "termo": "PlayStation 5",
  "limite_resultado": 10
}
```

O campo `limite_resultado` é opcional. O valor padrão é `10`.

**Saída:**
```json
{
  "termo": "PlayStation 5",
  "marketplace": "Mercado Livre",
  "resultados": [
    {
      "produto": "Console PlayStation 5 Slim Digital",
      "preco": 3998.07,
      "preco_original": 4599.90,
      "preco_parcelado": 4299.90,
      "url": "https://www.mercadolivre.com.br/...",
      "disponivel": true
    }
  ]
}
```

Os campos `preco_original` e `preco_parcelado` podem ser `null` quando não disponíveis na listagem.

---

## 🔄 Fluxo de busca automática com n8n

O fluxo completo esperado no n8n para busca automática:

```
Schedule Trigger (ex: a cada 1 hora)
        ↓
Google Sheets — Ler buscas configuradas
        ↓
Filtrar ATIVO = "Sim"
        ↓
HTTP Request — POST /buscar
  {
    "termo": "PlayStation 5",
    "limite_resultado": 10
  }
        ↓
Separar itens da lista resultados
        ↓
Filtrar por PRECO_MINIMO e PRECO_MAXIMO
        ↓
Filtrar por PALAVRAS_OBRIGATORIAS (ex: ps5, slim, console)
        ↓
Filtrar por PALAVRAS_BLOQUEADAS (ex: usado, defeito, capa)
        ↓
Verificar PRECO_ALVO atingido
        ↓
Formatar mensagem
        ↓
Telegram — Enviar oferta
        ↓
Google Sheets — Atualizar status (opcional)
```

### Estrutura sugerida da planilha Google Sheets

| Campo | Exemplo | Descrição |
|---|---|---|
| `ATIVO` | Sim | Se essa busca está ativa |
| `NOME` | PlayStation 5 | Termo de busca para a rota /buscar |
| `PRECO_MINIMO` | 3799 | Filtro de preço mínimo (aplicado no n8n) |
| `PRECO_MAXIMO` | 4000 | Filtro de preço máximo (aplicado no n8n) |
| `PRECO_ALVO` | 3899 | Preço alvo para alerta (aplicado no n8n) |
| `LIMITE_RESULTADO` | 10 | Limite de resultados por busca |
| `PALAVRAS_OBRIGATORIAS` | ps5,slim,console | Palavras que devem estar no título (n8n) |
| `PALAVRAS_BLOQUEADAS` | usado,defeito,capa | Palavras que descartam o produto (n8n) |

---

## 🧪 Como testar

### Pelo Swagger (interface gráfica)

Acesse `http://localhost:8000/docs` e use a interface interativa para testar as rotas.

### Via curl (linha de comando)

**Testar /buscar:**
```bash
curl -X POST "http://localhost:8000/buscar" \
  -H "Content-Type: application/json" \
  -d '{"termo": "PlayStation 5", "limite_resultado": 5}'
```

**Testar /monitorar:**
```bash
curl -X POST "http://localhost:8000/monitorar" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.mercadolivre.com.br/p/MLB57081243"}'
```

**Health check:**
```bash
curl http://localhost:8000/health
```

### Rodando os testes automatizados

```bash
pytest tests/ -v
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
