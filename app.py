import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl

from techpromos.factory import obter_scraper

# Configuração de log para a API
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)

app = FastAPI(
    title="TechPromos API",
    description="API para raspagem de preços em marketplaces brasileiros.",
    version="1.0.0"
)

class MonitorarRequest(BaseModel):
    url: str

@app.post("/monitorar")
def monitorar_produto(request: MonitorarRequest):
    """
    Recebe a URL de um produto e retorna os dados raspados.
    """
    url = request.url

    # Obtém o scraper correspondente ao domínio da URL
    try:
        scraper = obter_scraper(url)
    except ValueError as e:
        # Se nenhum scraper suporta o domínio, retorna erro 400
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    # Executa a raspagem
    logger.info("Iniciando raspagem para URL na API: %s", url)
    info = scraper.raspar(url)

    if not info.sucesso:
        # Se falhou em extrair dados, retorna erro 422
        raise HTTPException(
            status_code=422,
            detail=info.erro or "Falha ao extrair os dados do produto."
        )

    return info.to_dict()

@app.get("/")
def home():
    return {"status": "TechPromos API is running", "docs": "/docs"}
