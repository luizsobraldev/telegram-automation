"""
Testes unitários para o MercadoLivreBusca (scraper de busca por termo).

Utiliza HTML estático simulado para testar a extração sem dependência de rede.
Os mocks de requisição HTTP são feitos via patch de session.get.

Cobre:
  - Montagem da URL de busca a partir do termo
  - Extração de produtos do HTML de listagem
  - Extração de preço atual, original e parcelado
  - Extração de URL do produto
  - Respeito ao limite de resultados
  - Retorno de lista vazia quando sem resultados
  - Tratamento de timeout e erro de conexão
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from techpromos.scraper.mercadolivre_busca import MercadoLivreBusca, ProdutoBusca


# ---------------------------------------------------------------------------
# Helpers — HTML simulado
# ---------------------------------------------------------------------------

def _html_card(
    titulo: str = "Console PlayStation 5 Slim",
    preco_inteiro: str = "3.998",
    preco_centavos: str = "07",
    preco_original_inteiro: str | None = "4.599",
    preco_original_centavos: str | None = "90",
    preco_parcelado_inteiro: str | None = "4.299",
    preco_parcelado_centavos: str | None = "90",
    url: str = "https://www.mercadolivre.com.br/produto-teste",
) -> str:
    """Gera HTML de um card de produto da listagem do ML."""
    original_html = ""
    if preco_original_inteiro:
        original_html = f"""
        <div class="poly-price__original">
          <span class="andes-money-amount__fraction">{preco_original_inteiro}</span>
          <span class="andes-money-amount__cents">{preco_original_centavos or '00'}</span>
        </div>
        """

    parcelado_html = ""
    if preco_parcelado_inteiro:
        parcelado_html = f"""
        <div class="poly-price__installments">
          <span class="andes-money-amount__fraction">{preco_parcelado_inteiro}</span>
          <span class="andes-money-amount__cents">{preco_parcelado_centavos or '00'}</span>
        </div>
        """

    return f"""
    <div class="poly-card__content">
      <a class="poly-component__title" href="{url}">{titulo}</a>
      <div class="poly-price__current">
        <span class="andes-money-amount__fraction">{preco_inteiro}</span>
        <span class="andes-money-amount__cents">{preco_centavos}</span>
      </div>
      {original_html}
      {parcelado_html}
    </div>
    """


def _html_listagem(cards: list[str]) -> str:
    """Monta HTML de página de listagem com múltiplos cards."""
    itens = "\n".join(
        f'<li class="ui-search-layout__item">{card}</li>'
        for card in cards
    )
    return f"""
    <html>
    <head><title>Resultados para PlayStation 5 | Mercado Livre</title></head>
    <body>
      <section class="ui-search-results">
        <ol class="ui-search-layout">
          {itens}
        </ol>
      </section>
    </body>
    </html>
    """


def _html_sem_resultados() -> str:
    """HTML de página sem produtos encontrados."""
    return """
    <html>
    <body>
      <div class="ui-search-rescue">
        <p>Não encontramos resultados para sua busca.</p>
      </div>
    </body>
    </html>
    """


def _mock_response(html: str, status_code: int = 200):
    """Cria um mock de requests.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = html
    resp.content = html.encode("utf-8")
    resp.url = "https://lista.mercadolivre.com.br/playstation-5"
    resp.encoding = "utf-8"
    resp.raise_for_status = MagicMock()  # não levanta exceção
    return resp


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def busca():
    """Instância do MercadoLivreBusca para uso nos testes."""
    return MercadoLivreBusca()


# ---------------------------------------------------------------------------
# Testes — Montagem da URL
# ---------------------------------------------------------------------------


class TestMontarUrl:
    """Testes para o método _montar_url."""

    def test_termo_simples(self):
        url = MercadoLivreBusca._montar_url("PlayStation 5")
        assert url == "https://lista.mercadolivre.com.br/playstation-5"

    def test_termo_com_acento(self):
        url = MercadoLivreBusca._montar_url("Televisão 4K")
        assert url == "https://lista.mercadolivre.com.br/televisao-4k"

    def test_termo_com_caracteres_especiais(self):
        url = MercadoLivreBusca._montar_url("iPhone 15 Pro Max!")
        assert url == "https://lista.mercadolivre.com.br/iphone-15-pro-max"

    def test_termo_em_maiusculas(self):
        url = MercadoLivreBusca._montar_url("NOTEBOOK GAMER")
        assert url == "https://lista.mercadolivre.com.br/notebook-gamer"

    def test_termo_com_multiplos_espacos(self):
        url = MercadoLivreBusca._montar_url("PS5   Slim")
        assert url == "https://lista.mercadolivre.com.br/ps5-slim"

    def test_termo_com_hifen(self):
        url = MercadoLivreBusca._montar_url("Wi-Fi 6")
        assert url == "https://lista.mercadolivre.com.br/wi-fi-6"

    def test_url_base_correta(self):
        url = MercadoLivreBusca._montar_url("qualquer coisa")
        assert url.startswith("https://lista.mercadolivre.com.br/")

    def test_termo_simples_sem_espacos(self):
        url = MercadoLivreBusca._montar_url("tablet")
        assert url == "https://lista.mercadolivre.com.br/tablet"


# ---------------------------------------------------------------------------
# Testes — Extração de produtos
# ---------------------------------------------------------------------------


class TestExtrairResultados:
    """Testes para extração de produtos do HTML de listagem."""

    def test_extrai_produto_com_dados_completos(self, busca):
        """Deve extrair nome, preço atual, original e parcelado."""
        html = _html_listagem([_html_card()])
        resultados = busca._extrair_resultados(html, limite=10)

        assert len(resultados) == 1
        item = resultados[0]
        assert item.produto == "Console PlayStation 5 Slim"
        assert item.preco == 3998.07
        assert item.preco_original == 4599.90
        assert item.preco_parcelado == 4299.90

    def test_extrai_url_do_produto(self, busca):
        """Deve extrair a URL do produto."""
        html = _html_listagem([_html_card(url="https://www.mercadolivre.com.br/ps5-slim")])
        resultados = busca._extrair_resultados(html, limite=10)

        assert len(resultados) == 1
        assert resultados[0].url == "https://www.mercadolivre.com.br/ps5-slim"

    def test_extrai_multiplos_produtos(self, busca):
        """Deve extrair múltiplos produtos de múltiplos cards."""
        cards = [
            _html_card(titulo=f"Produto {i}", url=f"https://www.mercadolivre.com.br/p{i}")
            for i in range(5)
        ]
        html = _html_listagem(cards)
        resultados = busca._extrair_resultados(html, limite=10)

        assert len(resultados) == 5

    def test_respeita_limite_resultado(self, busca):
        """Deve retornar no máximo N produtos conforme o limite."""
        cards = [
            _html_card(titulo=f"Produto {i}", url=f"https://www.mercadolivre.com.br/p{i}")
            for i in range(10)
        ]
        html = _html_listagem(cards)
        resultados = busca._extrair_resultados(html, limite=3)

        assert len(resultados) == 3

    def test_retorna_lista_vazia_para_html_sem_produtos(self, busca):
        """HTML sem cards de produto deve retornar lista vazia."""
        html = _html_sem_resultados()
        resultados = busca._extrair_resultados(html, limite=10)

        assert resultados == []

    def test_preco_original_none_quando_ausente(self, busca):
        """preco_original deve ser None quando não presente no card."""
        html = _html_listagem([
            _html_card(preco_original_inteiro=None, preco_original_centavos=None)
        ])
        resultados = busca._extrair_resultados(html, limite=10)

        assert len(resultados) == 1
        assert resultados[0].preco_original is None

    def test_preco_parcelado_none_quando_ausente(self, busca):
        """preco_parcelado deve ser None quando não presente no card."""
        html = _html_listagem([
            _html_card(preco_parcelado_inteiro=None, preco_parcelado_centavos=None)
        ])
        resultados = busca._extrair_resultados(html, limite=10)

        assert len(resultados) == 1
        assert resultados[0].preco_parcelado is None

    def test_disponivel_true_por_padrao(self, busca):
        """Produtos da listagem devem ser disponivel=True por padrão."""
        html = _html_listagem([_html_card()])
        resultados = busca._extrair_resultados(html, limite=10)

        assert resultados[0].disponivel is True


# ---------------------------------------------------------------------------
# Testes — URL limpa
# ---------------------------------------------------------------------------


class TestLimparUrl:
    """Testes para remoção de parâmetros de tracking da URL."""

    def test_remove_query_string(self):
        url_com_tracking = "https://www.mercadolivre.com.br/produto?tracking_id=abc&source=xyz"
        url_limpa = MercadoLivreBusca._limpar_url(url_com_tracking)
        assert url_limpa == "https://www.mercadolivre.com.br/produto"

    def test_remove_fragmento(self):
        url_com_fragmento = "https://www.mercadolivre.com.br/produto#secao"
        url_limpa = MercadoLivreBusca._limpar_url(url_com_fragmento)
        assert url_limpa == "https://www.mercadolivre.com.br/produto"

    def test_url_sem_tracking_nao_muda(self):
        url_limpa = "https://www.mercadolivre.com.br/playstation-5/p/MLB57081243"
        assert MercadoLivreBusca._limpar_url(url_limpa) == url_limpa

    def test_url_invalida_retorna_original(self):
        """URL inválida deve ser retornada sem modificações."""
        url_invalida = "nao-e-uma-url"
        # Não deve lançar exceção
        resultado = MercadoLivreBusca._limpar_url(url_invalida)
        assert resultado == url_invalida


# ---------------------------------------------------------------------------
# Testes — Tratamento de erros de rede
# ---------------------------------------------------------------------------


class TestErrosDeRede:
    """Testes para tratamento de falhas de conexão e HTTP."""

    def test_timeout_levanta_runtime_error(self, busca):
        """Timeout deve ser convertido em RuntimeError."""
        with patch.object(busca.session, "get", side_effect=requests.exceptions.Timeout()):
            with pytest.raises(RuntimeError, match="Timeout"):
                busca._requisitar("https://lista.mercadolivre.com.br/ps5")

    def test_connection_error_levanta_runtime_error(self, busca):
        """Erro de conexão deve ser convertido em RuntimeError."""
        with patch.object(busca.session, "get", side_effect=requests.exceptions.ConnectionError("sem rede")):
            with pytest.raises(RuntimeError, match="conexão"):
                busca._requisitar("https://lista.mercadolivre.com.br/ps5")

    def test_http_error_levanta_runtime_error(self, busca):
        """HTTPError (ex: 403 CAPTCHA) deve ser convertido em RuntimeError."""
        resp_mock = MagicMock()
        resp_mock.status_code = 403
        http_error = requests.exceptions.HTTPError(response=resp_mock)
        with patch.object(busca.session, "get", side_effect=http_error):
            with pytest.raises(RuntimeError, match="HTTP"):
                busca._requisitar("https://lista.mercadolivre.com.br/ps5")


# ---------------------------------------------------------------------------
# Testes — Método buscar (integração interna com mock de rede)
# ---------------------------------------------------------------------------


class TestBuscar:
    """Testes do método público buscar(), com HTTP mockado."""

    def test_buscar_retorna_lista_de_produtos(self, busca):
        """buscar() deve retornar lista de ProdutoBusca."""
        html = _html_listagem([
            _html_card(titulo="PS5 Slim", url="https://www.mercadolivre.com.br/ps5")
        ])
        with patch.object(busca, "_requisitar", return_value=html):
            resultados = busca.buscar("PlayStation 5", limite=10)

        assert isinstance(resultados, list)
        assert len(resultados) == 1
        assert isinstance(resultados[0], ProdutoBusca)

    def test_buscar_passa_limite_para_extracao(self, busca):
        """buscar() deve respeitar o limite informado."""
        cards = [
            _html_card(titulo=f"Produto {i}", url=f"https://www.mercadolivre.com.br/p{i}")
            for i in range(8)
        ]
        html = _html_listagem(cards)
        with patch.object(busca, "_requisitar", return_value=html):
            resultados = busca.buscar("notebook", limite=4)

        assert len(resultados) == 4

    def test_buscar_monta_url_correta(self, busca):
        """buscar() deve chamar _requisitar com a URL montada a partir do termo."""
        html = _html_listagem([_html_card()])
        with patch.object(busca, "_requisitar", return_value=html) as mock_req:
            busca.buscar("PlayStation 5", limite=5)

        mock_req.assert_called_once_with(
            "https://lista.mercadolivre.com.br/playstation-5"
        )

    def test_buscar_retorna_vazio_para_html_sem_produtos(self, busca):
        """buscar() deve retornar lista vazia quando não há resultados."""
        with patch.object(busca, "_requisitar", return_value=_html_sem_resultados()):
            resultados = busca.buscar("produtoquenaoeexiste99999", limite=10)

        assert resultados == []

    def test_buscar_propaga_runtime_error(self, busca):
        """buscar() deve propagar RuntimeError levantado pela requisição."""
        with patch.object(busca, "_requisitar", side_effect=RuntimeError("Timeout")):
            with pytest.raises(RuntimeError, match="Timeout"):
                busca.buscar("PlayStation 5", limite=5)


# ---------------------------------------------------------------------------
# Testes — Utilitários
# ---------------------------------------------------------------------------


class TestUtilitarios:
    """Testes para métodos utilitários do scraper."""

    def test_limpar_numero(self):
        assert MercadoLivreBusca._limpar_numero("3.998") == "3998"
        assert MercadoLivreBusca._limpar_numero("07") == "07"
        assert MercadoLivreBusca._limpar_numero("1.200.000") == "1200000"

    def test_parse_html_retorna_soup(self, busca):
        """_parse_html deve retornar um objeto BeautifulSoup válido."""
        soup = busca._parse_html("<html><body><p>Teste</p></body></html>")
        assert soup is not None
        assert soup.find("p") is not None

    def test_marketplace_definido(self, busca):
        assert busca.marketplace == "Mercado Livre"

    def test_user_agent_e_googlebot(self, busca):
        ua = busca.session.headers.get("User-Agent", "")
        assert "Googlebot" in ua
