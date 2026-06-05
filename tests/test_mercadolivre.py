"""
Testes unitários para o MercadoLivreScraper.

Utiliza HTML estático simulado para testar a extração sem
dependência de rede (testes rápidos e determinísticos).

Cobre as duas estratégias: JSON-LD (schema.org) e seletores CSS (fallback).
"""

from __future__ import annotations

import json
import pytest

from techpromos.scraper.mercadolivre import MercadoLivreScraper
from techpromos.scraper.base import ProdutoInfo

URL_FAKE = "https://www.mercadolivre.com.br/produto-teste"


# ---------------------------------------------------------------------------
# Helpers para montar HTML de fixture
# ---------------------------------------------------------------------------

def _html_com_jsonld(nome: str, preco: float, disponivel: bool = True) -> str:
    availability = "https://schema.org/InStock" if disponivel else "https://schema.org/OutOfStock"
    ld = json.dumps({
        "@context": "https://schema.org",
        "@type": "Product",
        "name": nome,
        "offers": {
            "@type": "Offer",
            "price": preco,
            "availability": availability,
        }
    })
    return f'<html><head><script type="application/ld+json">{ld}</script></head><body><h1>{nome}</h1></body></html>'


HTML_CSS_VALIDO = """
<html><body>
  <h1 class="ui-pdp-title">Produto Via CSS</h1>
  <div class="ui-pdp-price__main-container">
    <span class="andes-money-amount__fraction">1.299</span>
    <span class="andes-money-amount__cents">99</span>
  </div>
</body></html>
"""

HTML_SEM_DADOS = """
<html><body><p>Página em manutenção</p></body></html>
"""

HTML_INDISPONIVEL_CSS = """
<html><body>
  <h1 class="ui-pdp-title">Produto Esgotado</h1>
  <div class="ui-pdp-buybox--unavailable">Indisponível</div>
  <span class="andes-money-amount__fraction">500</span>
</body></html>
"""


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------

class TestMercadoLivreScraper:

    @pytest.fixture
    def scraper(self):
        return MercadoLivreScraper()

    # --- JSON-LD ---

    def test_extrai_via_jsonld(self, scraper):
        html = _html_com_jsonld("PlayStation 5 Slim", 3950.0)
        info = scraper._extrair(html, URL_FAKE)
        assert info.produto == "PlayStation 5 Slim"
        assert info.preco == 3950.0
        assert info.disponivel is True
        assert info.erro is None

    def test_jsonld_produto_indisponivel(self, scraper):
        html = _html_com_jsonld("Produto Esgotado", 999.0, disponivel=False)
        info = scraper._extrair(html, URL_FAKE)
        assert info.produto == "Produto Esgotado"
        assert info.disponivel is False

    def test_jsonld_preco_inteiro(self, scraper):
        html = _html_com_jsonld("Produto", 1500)
        info = scraper._extrair(html, URL_FAKE)
        assert info.preco == 1500.0

    # --- CSS fallback ---

    def test_extrai_via_css_quando_sem_jsonld(self, scraper):
        info = scraper._extrair(HTML_CSS_VALIDO, URL_FAKE)
        assert info.produto == "Produto Via CSS"
        assert info.preco == 1299.99

    def test_detecta_indisponivel_css(self, scraper):
        info = scraper._extrair(HTML_INDISPONIVEL_CSS, URL_FAKE)
        assert info.disponivel is False

    # --- Erro ---

    def test_erro_quando_sem_dados(self, scraper):
        info = scraper._extrair(HTML_SEM_DADOS, URL_FAKE)
        assert info.sucesso is False
        assert info.erro is not None

    # --- Utilitários ---

    def test_limpar_numero(self, scraper):
        assert scraper._limpar_numero("3.499") == "3499"
        assert scraper._limpar_numero("90") == "90"
        assert scraper._limpar_numero("1.200.000") == "1200000"

    def test_marketplace_definido(self, scraper):
        assert scraper.marketplace == "Mercado Livre"

    def test_user_agent_e_googlebot(self, scraper):
        ua = scraper.session.headers.get("User-Agent", "")
        assert "Googlebot" in ua
