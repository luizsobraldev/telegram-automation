"""
Placeholder para o scraper da Shopee (shopee.com.br).

TODO: Implementar quando o suporte à Shopee for necessário.

A Shopee renderiza o conteúdo via JavaScript (SPA com React), portanto
este scraper provavelmente precisará de uma das seguintes abordagens:

    1. Playwright / Selenium (browser headless) para renderizar o JS.
    2. Interceptação da API interna da Shopee (requer engenharia reversa).
    3. Serviço de proxy com renderização JS (ex: ScrapingBee, Zyte).

Referências para implementação futura:
    - API não oficial: https://shopee.com.br/api/v4/item/get?itemid=...
    - Seletor de título (quando renderizado): #main .product-briefing h1
"""

from __future__ import annotations

import logging

from techpromos.scraper.base import BaseScraper, ProdutoInfo

logger = logging.getLogger(__name__)


class ShopeeScraper(BaseScraper):
    """Scraper para Shopee — AINDA NÃO IMPLEMENTADO.

    Levanta ``NotImplementedError`` ao ser utilizado.
    Veja o docstring do módulo para orientações de implementação.
    """

    marketplace: str = "Shopee"

    def _extrair(self, html: str, url: str) -> ProdutoInfo:
        """Não implementado.

        Raises:
            NotImplementedError: Sempre. Shopee requer renderização JS.
        """
        raise NotImplementedError(
            "O scraper da Shopee ainda não foi implementado. "
            "A Shopee utiliza renderização JavaScript (SPA), "
            "o que requer Playwright ou acesso à API interna. "
            "Consulte o docstring do módulo para orientações."
        )
