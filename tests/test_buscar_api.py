"""
Testes automatizados para a rota POST /buscar da API FastAPI.

Utiliza TestClient do FastAPI para testar a rota sem subir servidor real.
O scraper MercadoLivreBusca é mockado para garantir testes rápidos e determinísticos.

Cobre:
  - Retorno 200 com JSON correto (termo, marketplace, resultados)
  - Estrutura de cada item em resultados
  - Respeito ao limite_resultado
  - Valor padrão de limite_resultado (10)
  - Erro 400 para termo vazio
  - Erro 422 quando a busca falha (scraping)
  - Erro 422 quando body está vazio ou sem o campo 'termo'
  - Retorno com lista vazia quando não há resultados
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app import app
from techpromos.scraper.mercadolivre_busca import ProdutoBusca

client = TestClient(app)

# ---------------------------------------------------------------------------
# Fixtures helpers
# ---------------------------------------------------------------------------


def _criar_produto_busca(
    nome: str = "Console PlayStation 5 Slim Digital",
    preco: float = 3998.07,
    preco_original: float = 4599.90,
    preco_parcelado: float = 4299.90,
    url: str = "https://www.mercadolivre.com.br/playstation-5-slim",
    disponivel: bool = True,
) -> ProdutoBusca:
    """Cria um ProdutoBusca de exemplo para uso nos mocks."""
    return ProdutoBusca(
        produto=nome,
        preco=preco,
        preco_original=preco_original,
        preco_parcelado=preco_parcelado,
        url=url,
        disponivel=disponivel,
    )


def _lista_produtos(n: int = 3) -> list[ProdutoBusca]:
    """Gera uma lista de N produtos de exemplo."""
    return [
        _criar_produto_busca(nome=f"Produto Teste {i+1}", preco=1000.0 + i * 100)
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# POST /buscar — Cenários de sucesso
# ---------------------------------------------------------------------------


class TestBuscarSucesso:
    """Testes para cenários de sucesso na rota POST /buscar."""

    @patch("app.MercadoLivreBusca")
    def test_retorna_200_com_lista_de_produtos(self, mock_cls):
        """POST /buscar com termo válido deve retornar 200."""
        mock_instancia = MagicMock()
        mock_instancia.buscar.return_value = _lista_produtos(3)
        mock_cls.return_value = mock_instancia

        response = client.post("/buscar", json={"termo": "PlayStation 5"})

        assert response.status_code == 200

    @patch("app.MercadoLivreBusca")
    def test_json_contem_chaves_termo_marketplace_resultados(self, mock_cls):
        """O JSON de resposta deve conter as chaves: termo, marketplace e resultados."""
        mock_instancia = MagicMock()
        mock_instancia.buscar.return_value = _lista_produtos(2)
        mock_cls.return_value = mock_instancia

        response = client.post("/buscar", json={"termo": "PlayStation 5"})
        data = response.json()

        assert "termo" in data
        assert "marketplace" in data
        assert "resultados" in data

    @patch("app.MercadoLivreBusca")
    def test_termo_retornado_no_json(self, mock_cls):
        """O campo 'termo' no JSON deve refletir o termo enviado."""
        mock_instancia = MagicMock()
        mock_instancia.buscar.return_value = _lista_produtos(1)
        mock_cls.return_value = mock_instancia

        response = client.post("/buscar", json={"termo": "PlayStation 5"})
        data = response.json()

        assert data["termo"] == "PlayStation 5"

    @patch("app.MercadoLivreBusca")
    def test_marketplace_e_mercado_livre(self, mock_cls):
        """O campo 'marketplace' deve ser 'Mercado Livre'."""
        mock_instancia = MagicMock()
        mock_instancia.buscar.return_value = _lista_produtos(1)
        mock_cls.return_value = mock_instancia

        response = client.post("/buscar", json={"termo": "PlayStation 5"})
        data = response.json()

        assert data["marketplace"] == "Mercado Livre"

    @patch("app.MercadoLivreBusca")
    def test_cada_resultado_contem_todas_as_chaves(self, mock_cls):
        """Cada item em 'resultados' deve ter as 6 chaves do contrato."""
        mock_instancia = MagicMock()
        mock_instancia.buscar.return_value = [_criar_produto_busca()]
        mock_cls.return_value = mock_instancia

        response = client.post("/buscar", json={"termo": "PlayStation 5"})
        data = response.json()

        chaves_esperadas = {"produto", "preco", "preco_original", "preco_parcelado", "url", "disponivel"}
        assert len(data["resultados"]) == 1
        assert set(data["resultados"][0].keys()) == chaves_esperadas

    @patch("app.MercadoLivreBusca")
    def test_dados_do_produto_no_resultado(self, mock_cls):
        """Os valores retornados em cada resultado devem corresponder ao produto mockado."""
        mock_instancia = MagicMock()
        mock_instancia.buscar.return_value = [_criar_produto_busca()]
        mock_cls.return_value = mock_instancia

        response = client.post("/buscar", json={"termo": "PlayStation 5"})
        item = response.json()["resultados"][0]

        assert item["produto"] == "Console PlayStation 5 Slim Digital"
        assert item["preco"] == 3998.07
        assert item["preco_original"] == 4599.90
        assert item["preco_parcelado"] == 4299.90
        assert item["disponivel"] is True

    @patch("app.MercadoLivreBusca")
    def test_limite_resultado_e_respeitado(self, mock_cls):
        """O número de resultados deve respeitar o campo limite_resultado."""
        mock_instancia = MagicMock()
        # O mock já retorna 2 (simulando que o scraper respeitou o limite)
        mock_instancia.buscar.return_value = _lista_produtos(2)
        mock_cls.return_value = mock_instancia

        response = client.post("/buscar", json={"termo": "PlayStation 5", "limite_resultado": 2})
        data = response.json()

        # Verifica que a rota chamou o scraper com o limite correto
        mock_instancia.buscar.assert_called_once_with("PlayStation 5", limite=2)
        assert len(data["resultados"]) == 2

    @patch("app.MercadoLivreBusca")
    def test_limite_resultado_padrao_e_10(self, mock_cls):
        """Quando limite_resultado não é informado, o padrão deve ser 10."""
        mock_instancia = MagicMock()
        mock_instancia.buscar.return_value = _lista_produtos(1)
        mock_cls.return_value = mock_instancia

        response = client.post("/buscar", json={"termo": "PlayStation 5"})

        assert response.status_code == 200
        mock_instancia.buscar.assert_called_once_with("PlayStation 5", limite=10)

    @patch("app.MercadoLivreBusca")
    def test_retorna_lista_vazia_quando_sem_resultados(self, mock_cls):
        """Quando o scraper não encontra produtos, resultados deve ser lista vazia."""
        mock_instancia = MagicMock()
        mock_instancia.buscar.return_value = []
        mock_cls.return_value = mock_instancia

        response = client.post("/buscar", json={"termo": "produtoquenaoeexiste12345"})
        data = response.json()

        assert response.status_code == 200
        assert data["resultados"] == []

    @patch("app.MercadoLivreBusca")
    def test_preco_original_pode_ser_null(self, mock_cls):
        """preco_original pode ser null (None) quando não disponível na listagem."""
        mock_instancia = MagicMock()
        mock_instancia.buscar.return_value = [
            _criar_produto_busca(preco_original=None, preco_parcelado=None)
        ]
        mock_cls.return_value = mock_instancia

        response = client.post("/buscar", json={"termo": "PlayStation 5"})
        item = response.json()["resultados"][0]

        assert item["preco_original"] is None
        assert item["preco_parcelado"] is None

    @patch("app.MercadoLivreBusca")
    def test_termo_com_espacos_extras_e_normalizado(self, mock_cls):
        """Espaços extras no termo devem ser removidos antes de chamar o scraper."""
        mock_instancia = MagicMock()
        mock_instancia.buscar.return_value = []
        mock_cls.return_value = mock_instancia

        response = client.post("/buscar", json={"termo": "  PlayStation 5  "})

        assert response.status_code == 200
        # O scraper deve receber o termo sem espaços extras
        mock_instancia.buscar.assert_called_once_with("PlayStation 5", limite=10)


# ---------------------------------------------------------------------------
# POST /buscar — Cenários de erro
# ---------------------------------------------------------------------------


class TestBuscarErros:
    """Testes para cenários de erro na rota POST /buscar."""

    def test_termo_vazio_retorna_400(self):
        """Termo vazio deve retornar 400 Bad Request."""
        response = client.post("/buscar", json={"termo": ""})

        assert response.status_code == 400
        assert "termo" in response.json()["detail"].lower()

    def test_termo_so_espacos_retorna_400(self):
        """Termo com apenas espaços deve retornar 400 (strip resulta em vazio)."""
        response = client.post("/buscar", json={"termo": "   "})

        assert response.status_code == 400

    @patch("app.MercadoLivreBusca")
    def test_falha_no_scraper_retorna_422(self, mock_cls):
        """RuntimeError no scraper deve retornar 422 com mensagem clara."""
        mock_instancia = MagicMock()
        mock_instancia.buscar.side_effect = RuntimeError("Timeout após 15s.")
        mock_cls.return_value = mock_instancia

        response = client.post("/buscar", json={"termo": "PlayStation 5"})

        assert response.status_code == 422
        assert "Mercado Livre" in response.json()["detail"]

    @patch("app.MercadoLivreBusca")
    def test_excecao_generica_retorna_422(self, mock_cls):
        """Exceções inesperadas no scraper devem retornar 422."""
        mock_instancia = MagicMock()
        mock_instancia.buscar.side_effect = Exception("Erro genérico inesperado")
        mock_cls.return_value = mock_instancia

        response = client.post("/buscar", json={"termo": "PlayStation 5"})

        assert response.status_code == 422

    def test_body_vazio_retorna_422(self):
        """Requisição sem body deve retornar 422 (Unprocessable Entity)."""
        response = client.post("/buscar")

        assert response.status_code == 422

    def test_body_sem_campo_termo_retorna_422(self):
        """Body JSON sem o campo 'termo' deve retornar 422."""
        response = client.post("/buscar", json={"busca": "PlayStation 5"})

        assert response.status_code == 422

    def test_limite_resultado_invalido_retorna_422(self):
        """limite_resultado não numérico deve retornar 422."""
        response = client.post("/buscar", json={"termo": "PS5", "limite_resultado": "dez"})

        assert response.status_code == 422
