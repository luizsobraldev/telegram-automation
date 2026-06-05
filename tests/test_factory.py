"""
Testes para o modulo factory (selecao automatica de scraper por URL).

Cobre os tres formatos de URL do Mercado Livre:
  - URL curta: /p/MLB...
  - URL longa: /slug.../p/MLB...
  - URL de anuncio: produto.mercadolivre.com.br/MLB-...-_JM
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

    def test_url_curta_p_mlb(self):
        """URL curta: /p/MLB..."""
        scraper = obter_scraper("https://www.mercadolivre.com.br/p/MLB57081243")
        assert isinstance(scraper, MercadoLivreScraper)

    def test_url_longa_slug_p_mlb(self):
        """URL longa com slug: /.../p/MLB..."""
        url = (
            "https://www.mercadolivre.com.br/console-playstation5-slim-"
            "digital-pacote-astro-bot-e-gran-turismo-7-branco/p/MLB57081243"
        )
        scraper = obter_scraper(url)
        assert isinstance(scraper, MercadoLivreScraper)

    def test_url_anuncio_produto_subdominio(self):
        """URL de anuncio: produto.mercadolivre.com.br/MLB-...-_JM"""
        url = (
            "https://produto.mercadolivre.com.br/MLB-123456789-"
            "playstation-5-slim-digital-_JM"
        )
        scraper = obter_scraper(url)
        assert isinstance(scraper, MercadoLivreScraper)

    def test_url_nao_suportada_levanta_valueerror(self):
        with pytest.raises(ValueError, match="Nenhum scraper"):
            obter_scraper("https://www.shopee.com.br/produto")

    def test_url_completamente_desconhecida(self):
        with pytest.raises(ValueError):
            obter_scraper("https://www.unknownsite.com/produto")
