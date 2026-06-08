"""
TechPromos com Sobral — API FastAPI

API de coleta de preços em marketplaces brasileiros.
Projetada para ser chamada pelo n8n, que orquestra o monitoramento
e envia notificações para o Telegram.

Rotas:
    POST /monitorar  — Consulta dados de um produto específico por URL.
    POST /buscar     — Busca produtos por termo e retorna lista de resultados.

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
from techpromos.scraper.mercadolivre_busca import MercadoLivreBusca

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
        "POST /monitorar consulta um produto específico por URL. "
        "POST /buscar busca produtos automaticamente por termo. "
        "Projetada para integração com n8n + Google Sheets + Telegram."
    ),
    version="2.0.0",
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class MonitorarRequest(BaseModel):
    """Corpo da requisição para a rota /monitorar."""

    url: str


class BuscarRequest(BaseModel):
    """Corpo da requisição para a rota /buscar."""

    termo: str
    limite_resultado: int = 10


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


@app.post("/buscar")
def buscar_produtos(request: BuscarRequest):
    """Busca produtos no Mercado Livre por termo de pesquisa.

    Fluxo:
        1. Valida o termo recebido.
        2. Monta a URL de busca do Mercado Livre.
        3. Extrai a lista de produtos da página de resultados.
        4. Retorna a lista em JSON (sem aplicar filtros de preço ou palavras).

    A filtragem por preço mínimo, preço máximo, palavras obrigatórias e
    palavras bloqueadas é responsabilidade do n8n, que lê essas regras
    diretamente do Google Sheets.

    Returns:
        JSON com os campos: termo, marketplace e resultados (lista de produtos).
    """
    termo = request.termo.strip()
    limite = request.limite_resultado

    logger.info("POST /buscar | Termo: '%s' | Limite: %d", termo, limite)

    if not termo:
        logger.warning("POST /buscar | Termo vazio recebido.")
        raise HTTPException(
            status_code=400,
            detail="O campo 'termo' não pode ser vazio.",
        )

    busca = MercadoLivreBusca()

    try:
        resultados = busca.buscar(termo, limite=limite)
    except RuntimeError as exc:
        logger.warning("POST /buscar | Falha na busca | Termo: '%s' | Erro: %s", termo, exc)
        raise HTTPException(
            status_code=422,
            detail=(
                "Não foi possível buscar produtos no Mercado Livre. "
                "O site pode ter bloqueado a requisição ou alterado a estrutura da página."
            ),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("POST /buscar | Erro inesperado | Termo: '%s'", termo)
        raise HTTPException(
            status_code=422,
            detail=f"Erro inesperado ao buscar produtos: {type(exc).__name__}: {exc}",
        )

    logger.info(
        "POST /buscar | Concluido | Termo: '%s' | %d resultado(s) retornado(s)",
        termo, len(resultados),
    )
    return {
        "termo": termo,
        "marketplace": "Mercado Livre",
        "resultados": [r.to_dict() for r in resultados],
    }


@app.get("/")
def home():
    """Rota raiz — confirma que a API está ativa."""
    return {"status": "TechPromos API is running", "docs": "/docs"}


@app.get("/health")
def health():
    """Health check para o Railway e balanceadores de carga."""
    return {"status": "ok", "service": "TechPromos API"}
