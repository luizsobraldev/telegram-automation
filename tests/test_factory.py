"""
Testes para o módulo factory (seleção automática de scraper por URL).
"""

from __future__ import annotations

import pytest

from techpromos.factory import obter_scraper
from techpromos.scraper.mercadolivre import MercadoLivreScraper


class TestObterScraper:

    def test_url_mercadolivre_retorna_scraper_correto(self):
        scraper = obter_scraper("https://www.mercadolivre.com.br/produto")
        assert isinstance(scraper, MercadoLivreScraper)

    def test_url_mercadolivre_sem_www(self):
        scraper = obter_scraper("https://mercadolivre.com.br/produto")
        assert isinstance(scraper, MercadoLivreScraper)

    def test_url_nao_suportada_levanta_valueerror(self):
        with pytest.raises(ValueError, match="Nenhum scraper disponível"):
            obter_scraper("https://www.shopee.com.br/produto")

    def test_url_completamente_desconhecida(self):
        with pytest.raises(ValueError):
            obter_scraper("https://www.unknownsite.com/produto")
