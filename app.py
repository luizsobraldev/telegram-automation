"""
TechPromos com Sobral — API FastAPI

API de coleta de preços em marketplaces brasileiros.
Projetada para ser chamada pelo n8n, que orquestra o monitoramento
e envia notificações para o Telegram.

Uso (local):
    uvicorn app:app --reload --port 8000

Deploy (Railway):
    web: uvicorn app:app --host 0.0.0.0 --port $PORT
"""

import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from techpromos.factory import obter_scraper
from techpromos.logger import configurar_logging

# ---------------------------------------------------------------------------
# Logging — usa o sistema padronizado do projeto
# ---------------------------------------------------------------------------

configurar_logging(nivel="INFO", arquivo=False, console=True)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Aplicação FastAPI
# ---------------------------------------------------------------------------

app = FastAPI(
    title="TechPromos API",
    description=(
        "API para coleta de preços em marketplaces brasileiros. "
        "Recebe a URL de um produto via POST /monitorar e retorna os dados em JSON. "
        "Projetada para integração com n8n + Telegram."
    ),
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class MonitorarRequest(BaseModel):
    """Corpo da requisição para a rota /monitorar."""

    url: str


# ---------------------------------------------------------------------------
# Rotas
# ---------------------------------------------------------------------------


@app.post("/monitorar")
def monitorar_produto(request: MonitorarRequest):
    """Recebe a URL de um produto e retorna os dados raspados.

    Fluxo:
        1. Identifica o marketplace pela URL.
        2. Executa a raspagem (scraping).
        3. Retorna os dados em JSON.

    Returns:
        JSON com os campos: produto, preco, preco_original,
        preco_parcelado, url, consultado_em, marketplace,
        disponivel, erro.
    """
    url = request.url
    logger.info("POST /monitorar | URL recebida: %s", url)

    # --- Etapa 1: Selecionar scraper ---
    try:
        scraper = obter_scraper(url)
        logger.info(
            "Scraper selecionado: %s para URL: %s",
            scraper.__class__.__name__, url,
        )
    except ValueError as e:
        logger.warning("Dominio nao suportado | URL: %s | Erro: %s", url, e)
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    # --- Etapa 2: Executar raspagem ---
    logger.info("Iniciando raspagem para URL na API: %s", url)
    info = scraper.raspar(url)

    if not info.sucesso:
        logger.warning(
            "Falha na extracao | URL: %s | Erro: %s",
            url, info.erro,
        )
        raise HTTPException(
            status_code=422,
            detail=info.erro or "Falha ao extrair os dados do produto.",
        )

    logger.info(
        "Raspagem concluida com sucesso | Produto: %s | Preco: %s | URL: %s",
        info.produto, info.preco, url,
    )
    return info.to_dict()


@app.get("/")
def home():
    """Rota raiz — confirma que a API está ativa."""
    return {"status": "TechPromos API is running", "docs": "/docs"}


@app.get("/health")
def health():
    """Health check para o Railway e balanceadores de carga."""
    return {"status": "ok", "service": "TechPromos API"}
