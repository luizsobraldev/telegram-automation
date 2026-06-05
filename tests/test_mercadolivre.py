"""
Testes unitários para o MercadoLivreScraper.

Utiliza HTML estático simulado para testar a extração sem
dependência de rede (testes rápidos e determinísticos).

Cobre as três estratégias: JSON-LD (schema.org), seletores CSS (fallback),
e metatags (og:title / <title>) como último recurso para título.
"""

from __future__ import annotations

import json
import pytest

from techpromos.scraper.mercadolivre import MercadoLivreScraper
from techpromos.scraper.base import ProdutoInfo


# ---------------------------------------------------------------------------
# URLs de teste cobrindo os três formatos do Mercado Livre
# ---------------------------------------------------------------------------

URL_FAKE = "https://www.mercadolivre.com.br/produto-teste"
URL_CURTA = "https://www.mercadolivre.com.br/p/MLB57081243"
URL_LONGA = (
    "https://www.mercadolivre.com.br/console-playstation5-slim-digital-"
    "pacote-astro-bot-e-gran-turismo-7-branco/p/MLB57081243"
)
URL_ANUNCIO = (
    "https://produto.mercadolivre.com.br/MLB-123456789-"
    "playstation-5-slim-digital-_JM"
)


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


def _html_somente_metatags(nome: str, preco_texto: str = "R$ 3.998") -> str:
    """HTML sem JSON-LD e sem seletores CSS, apenas metatags."""
    return (
        f'<html><head>'
        f'<meta property="og:title" content="{nome} - {preco_texto}" />'
        f'<title>{nome} | Parcelamento sem juros | Mercado Livre</title>'
        f'</head><body><p>Conteudo generico</p></body></html>'
    )


def _html_somente_title_tag(nome: str) -> str:
    """HTML com apenas <title>, sem og:title, JSON-LD ou CSS."""
    return (
        f'<html><head>'
        f'<title>{nome} | Mercado Livre</title>'
        f'</head><body><p>Pagina</p></body></html>'
    )


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
<html><body><p>Pagina em manutencao</p></body></html>
"""

HTML_INDISPONIVEL_CSS = """
<html><body>
  <h1 class="ui-pdp-title">Produto Esgotado</h1>
  <div class="ui-pdp-buybox--unavailable">Indisponivel</div>
  <span class="andes-money-amount__fraction">500</span>
</body></html>
"""

HTML_COMPLETO = """
<html><head>
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "Product",
    "name": "Console PlayStation 5 Slim",
    "offers": {
      "@type": "Offer",
      "price": 3998.07,
      "availability": "https://schema.org/InStock"
    }
  }
  </script>
  <meta property="og:title" content="Console PlayStation 5 Slim - R$ 4.299" />
  <title>Console PlayStation 5 Slim | Parcelamento sem juros | Mercado Livre</title>
</head><body>
  <h1 class="ui-pdp-title">Console PlayStation 5 Slim</h1>
  <div class="ui-pdp-price__original-value">
    <span class="andes-money-amount__fraction">4.599</span>
    <span class="andes-money-amount__cents">90</span>
  </div>
  <div class="ui-pdp-price__second-line">
    <span class="andes-money-amount__fraction">3.998</span>
    <span class="andes-money-amount__cents">07</span>
  </div>
  <div class="ui-pdp-price__subtitles">
    <span class="andes-money-amount__fraction">4.299</span>
    <span class="andes-money-amount__cents">90</span>
  </div>
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

    # --- Metatag fallback (Tentativa 3) ---

    def test_extrai_titulo_via_og_title(self, scraper):
        """Quando JSON-LD e CSS nao encontram titulo, usa og:title."""
        html = _html_somente_metatags("Console PS5 Slim")
        info = scraper._extrair(html, URL_FAKE)
        assert info.produto == "Console PS5 Slim"

    def test_extrai_titulo_via_title_tag(self, scraper):
        """Quando JSON-LD, CSS e og:title nao existem, usa <title>."""
        html = _html_somente_title_tag("Console PS5 Slim")
        info = scraper._extrair(html, URL_FAKE)
        assert info.produto == "Console PS5 Slim"

    def test_og_title_remove_preco_sufixo(self, scraper):
        """og:title com preco no final deve ter o preco removido."""
        html = _html_somente_metatags("Produto Teste", "R$ 1.299,99")
        info = scraper._extrair(html, URL_FAKE)
        assert info.produto == "Produto Teste"
        assert "R$" not in (info.produto or "")

    def test_title_tag_remove_pipe_sufixo(self, scraper):
        """<title> com '|' separador deve retornar apenas a parte antes do pipe."""
        html = _html_somente_title_tag("Notebook Gamer")
        info = scraper._extrair(html, URL_FAKE)
        assert info.produto == "Notebook Gamer"
        assert "Mercado Livre" not in (info.produto or "")

    # --- Erro ---

    def test_erro_quando_sem_dados(self, scraper):
        info = scraper._extrair(HTML_SEM_DADOS, URL_FAKE)
        assert info.sucesso is False
        assert info.erro is not None

    def test_erro_mensagem_detalhada(self, scraper):
        """Quando nenhum dado e encontrado, erro menciona bloqueio."""
        info = scraper._extrair(HTML_SEM_DADOS, URL_FAKE)
        assert "bloqueado" in info.erro.lower() or "extrair" in info.erro.lower()

    # --- Extracao completa (JSON-LD + CSS combinados) ---

    def test_extracao_completa_com_todos_precos(self, scraper):
        """HTML completo deve retornar preco, preco_original e preco_parcelado."""
        info = scraper._extrair(HTML_COMPLETO, URL_FAKE)
        assert info.produto == "Console PlayStation 5 Slim"
        assert info.preco == 3998.07
        assert info.preco_original == 4599.90
        assert info.preco_parcelado == 4299.90
        assert info.disponivel is True
        assert info.erro is None

    # --- Formatos de URL ---

    def test_extrair_com_url_curta(self, scraper):
        """URL curta /p/MLB... deve funcionar normalmente."""
        html = _html_com_jsonld("PS5 Slim", 3998.07)
        info = scraper._extrair(html, URL_CURTA)
        assert info.produto == "PS5 Slim"
        assert info.url == URL_CURTA

    def test_extrair_com_url_longa(self, scraper):
        """URL longa .../p/MLB... deve funcionar normalmente."""
        html = _html_com_jsonld("PS5 Slim", 3998.07)
        info = scraper._extrair(html, URL_LONGA)
        assert info.produto == "PS5 Slim"
        assert info.url == URL_LONGA

    def test_extrair_com_url_anuncio(self, scraper):
        """URL de anuncio /MLB-...-_JM deve funcionar normalmente."""
        html = _html_com_jsonld("PS5 Slim", 3998.07)
        info = scraper._extrair(html, URL_ANUNCIO)
        assert info.produto == "PS5 Slim"
        assert info.url == URL_ANUNCIO

    # --- Parser HTML resiliente ---

    def test_parse_html_funciona(self, scraper):
        """_parse_html deve retornar um soup valido."""
        html = _html_com_jsonld("Produto Fallback", 100.0)
        soup = scraper._parse_html(html)
        assert soup is not None
        assert soup.find("script", type="application/ld+json") is not None

    # --- Utilitarios ---

    def test_limpar_numero(self, scraper):
        assert scraper._limpar_numero("3.499") == "3499"
        assert scraper._limpar_numero("90") == "90"
        assert scraper._limpar_numero("1.200.000") == "1200000"

    def test_marketplace_definido(self, scraper):
        assert scraper.marketplace == "Mercado Livre"

    def test_user_agent_e_googlebot(self, scraper):
        ua = scraper.session.headers.get("User-Agent", "")
        assert "Googlebot" in ua
