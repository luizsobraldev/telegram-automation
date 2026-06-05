"""
Placeholder para o scraper da Amazon Brasil (amazon.com.br).

TODO: Implementar quando o suporte à Amazon for necessário.

A Amazon aplica anti-bot agressivo. Abordagens recomendadas:

    1. Rotação de User-Agent + proxies residenciais.
    2. API oficial do Amazon Product Advertising (PA-API 5.0):
       https://webservices.amazon.com/paapi5/documentation/
    3. Serviços de scraping gerenciados (ex: Rainforest API, Oxylabs).

Seletores CSS quando disponíveis (sujeitos a mudanças frequentes):
    - Título:  #productTitle
    - Preço:   .a-price-whole + .a-price-fraction
               ou #priceblock_ourprice
"""

from __future__ import annotations

import logging

from techpromos.scraper.base import BaseScraper, ProdutoInfo

logger = logging.getLogger(__name__)


class AmazonScraper(BaseScraper):
    """Scraper para Amazon Brasil — AINDA NÃO IMPLEMENTADO.

    Levanta ``NotImplementedError`` ao ser utilizado.
    Veja o docstring do módulo para orientações de implementação.
    """

    marketplace: str = "Amazon"

    def _extrair(self, html: str, url: str) -> ProdutoInfo:
        """Não implementado.

        Raises:
            NotImplementedError: Sempre. Amazon requer estratégia anti-bot.
        """
        raise NotImplementedError(
            "O scraper da Amazon ainda não foi implementado. "
            "A Amazon aplica medidas anti-bot que requerem "
            "proxies rotativos ou uso da PA-API oficial. "
            "Consulte o docstring do módulo para orientações."
        )
