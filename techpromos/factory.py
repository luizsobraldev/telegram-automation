"""
Fábrica de scrapers: seleciona o scraper correto pela URL informada.

Permite que o n8n (ou qualquer cliente) envie qualquer URL de marketplace
sem precisar saber qual scraper usar — a seleção é automática.
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

from techpromos.scraper.base import BaseScraper
from techpromos.scraper.mercadolivre import MercadoLivreScraper

logger = logging.getLogger(__name__)

# Mapeamento de domínio → classe do scraper
# Adicione novos marketplaces aqui quando implementados.
_REGISTRO: dict[str, type[BaseScraper]] = {
    "mercadolivre.com.br": MercadoLivreScraper,
    "produto.mercadolivre.com.br": MercadoLivreScraper,
    # "shopee.com.br": ShopeeScraper,   # descomente quando implementado
    # "amazon.com.br": AmazonScraper,   # descomente quando implementado
}


def obter_scraper(url: str) -> BaseScraper:
    """Retorna a instância de scraper adequada para a URL fornecida.

    A seleção é feita pelo domínio da URL (sem 'www.').

    Args:
        url: URL completa do produto (ex: 'https://www.mercadolivre.com.br/...').

    Returns:
        Instância de ``BaseScraper`` pronta para uso.

    Raises:
        ValueError: Se o domínio da URL não for suportado por nenhum scraper.

    Example::

        scraper = obter_scraper("https://www.mercadolivre.com.br/...")
        resultado = scraper.raspar(url)
    """
    dominio = urlparse(url).netloc.removeprefix("www.")
    logger.debug("Buscando scraper para domínio: '%s'", dominio)

    # Busca exata primeiro, depois por sufixo (subdomínios)
    scraper_cls = _REGISTRO.get(dominio)
    if scraper_cls is None:
        for dominio_reg, cls in _REGISTRO.items():
            if dominio.endswith(dominio_reg):
                scraper_cls = cls
                break

    if scraper_cls is None:
        dominios_suportados = ", ".join(sorted(_REGISTRO.keys()))
        raise ValueError(
            f"Nenhum scraper disponível para '{dominio}'. "
            f"Marketplaces suportados: {dominios_suportados}"
        )

    logger.info("Scraper selecionado: %s para '%s'", scraper_cls.__name__, dominio)
    return scraper_cls()
