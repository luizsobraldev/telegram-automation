"""
Testes automatizados para a API FastAPI (app.py).

Utiliza TestClient do FastAPI para testar as rotas sem subir servidor real.
Os scrapers sao mockados para garantir testes rapidos e deterministicos.

Cobre:
  - Retorno 200 com JSON completo para URL valida
  - Todos os 3 formatos de URL do ML (curta, longa, anuncio)
  - Erros: dominio nao suportado, falha na extracao, body invalido
  - Rotas auxiliares (/, /health)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app import app
from techpromos.scraper.base import ProdutoInfo

client = TestClient(app)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

URL_ML_VALIDA = "https://www.mercadolivre.com.br/produto-teste/p/MLB12345"
URL_ML_CURTA = "https://www.mercadolivre.com.br/p/MLB57081243"
URL_ML_LONGA = (
    "https://www.mercadolivre.com.br/console-playstation5-slim-"
    "digital-pacote-astro-bot-e-gran-turismo-7-branco/p/MLB57081243"
)
URL_ML_ANUNCIO = (
    "https://produto.mercadolivre.com.br/MLB-123456789-"
    "playstation-5-slim-digital-_JM"
)
URL_NAO_SUPORTADA = "https://www.sitedesconhecido.com.br/produto"
URL_INVALIDA = "nao-e-uma-url"


def _criar_produto_sucesso() -> ProdutoInfo:
    """Cria um ProdutoInfo de sucesso para usar nos mocks."""
    return ProdutoInfo(
        produto="Headset Pulse Elite Sony",
        preco=743.91,
        preco_original=999.90,
        preco_parcelado=799.90,
        url=URL_ML_VALIDA,
        marketplace="Mercado Livre",
        disponivel=True,
    )


def _criar_produto_falha() -> ProdutoInfo:
    """Cria um ProdutoInfo com falha na extracao."""
    return ProdutoInfo(
        url=URL_ML_VALIDA,
        marketplace="Mercado Livre",
        disponivel=False,
        erro="Nao foi possivel extrair os dados da pagina.",
    )


# ---------------------------------------------------------------------------
# Testes - POST /monitorar (sucesso)
# ---------------------------------------------------------------------------


class TestMonitorarSucesso:
    """Testes para cenarios de sucesso na rota POST /monitorar."""

    @patch("app.obter_scraper")
    def test_retorna_200_com_dados_do_produto(self, mock_obter):
        """URL valida do ML deve retornar 200 com JSON completo."""
        mock_scraper = MagicMock()
        mock_scraper.raspar.return_value = _criar_produto_sucesso()
        mock_obter.return_value = mock_scraper

        response = client.post("/monitorar", json={"url": URL_ML_VALIDA})

        assert response.status_code == 200
        data = response.json()
        assert data["produto"] == "Headset Pulse Elite Sony"
        assert data["preco"] == 743.91
        assert data["preco_original"] == 999.90
        assert data["preco_parcelado"] == 799.90
        assert data["marketplace"] == "Mercado Livre"
        assert data["disponivel"] is True
        assert data["erro"] is None

    @patch("app.obter_scraper")
    def test_retorno_contem_todas_as_chaves_esperadas(self, mock_obter):
        """O JSON de resposta deve conter todas as chaves do contrato."""
        mock_scraper = MagicMock()
        mock_scraper.raspar.return_value = _criar_produto_sucesso()
        mock_obter.return_value = mock_scraper

        response = client.post("/monitorar", json={"url": URL_ML_VALIDA})
        data = response.json()

        chaves_esperadas = {
            "produto", "preco", "preco_original", "preco_parcelado",
            "url", "consultado_em", "marketplace", "disponivel", "erro",
        }
        assert set(data.keys()) == chaves_esperadas

    @patch("app.obter_scraper")
    def test_url_curta_p_mlb_retorna_200(self, mock_obter):
        """URL curta /p/MLB... deve ser aceita e retornar 200."""
        mock_scraper = MagicMock()
        mock_scraper.raspar.return_value = _criar_produto_sucesso()
        mock_obter.return_value = mock_scraper

        response = client.post("/monitorar", json={"url": URL_ML_CURTA})

        assert response.status_code == 200
        assert response.json()["produto"] == "Headset Pulse Elite Sony"

    @patch("app.obter_scraper")
    def test_url_longa_slug_p_mlb_retorna_200(self, mock_obter):
        """URL longa com slug /.../p/MLB... deve ser aceita e retornar 200."""
        mock_scraper = MagicMock()
        mock_scraper.raspar.return_value = _criar_produto_sucesso()
        mock_obter.return_value = mock_scraper

        response = client.post("/monitorar", json={"url": URL_ML_LONGA})

        assert response.status_code == 200
        assert response.json()["produto"] == "Headset Pulse Elite Sony"

    @patch("app.obter_scraper")
    def test_url_anuncio_produto_subdominio_retorna_200(self, mock_obter):
        """URL de anuncio produto.mercadolivre.com.br/MLB-...-_JM deve retornar 200."""
        mock_scraper = MagicMock()
        mock_scraper.raspar.return_value = _criar_produto_sucesso()
        mock_obter.return_value = mock_scraper

        response = client.post("/monitorar", json={"url": URL_ML_ANUNCIO})

        assert response.status_code == 200
        assert response.json()["produto"] == "Headset Pulse Elite Sony"


# ---------------------------------------------------------------------------
# Testes - POST /monitorar (erros)
# ---------------------------------------------------------------------------


class TestMonitorarErros:
    """Testes para cenarios de erro na rota POST /monitorar."""

    def test_dominio_nao_suportado_retorna_400(self):
        """URL de dominio nao suportado deve retornar 400."""
        response = client.post("/monitorar", json={"url": URL_NAO_SUPORTADA})

        assert response.status_code == 400
        assert "Nenhum scraper" in response.json()["detail"]

    @patch("app.obter_scraper")
    def test_falha_na_extracao_retorna_422(self, mock_obter):
        """Quando o scraper nao consegue extrair dados, retorna 422."""
        mock_scraper = MagicMock()
        mock_scraper.raspar.return_value = _criar_produto_falha()
        mock_obter.return_value = mock_scraper

        response = client.post("/monitorar", json={"url": URL_ML_VALIDA})

        assert response.status_code == 422

    def test_body_vazio_retorna_422(self):
        """Requisicao sem body deve retornar 422 (Unprocessable Entity)."""
        response = client.post("/monitorar")

        assert response.status_code == 422

    def test_body_sem_campo_url_retorna_422(self):
        """Body JSON sem o campo 'url' deve retornar 422."""
        response = client.post("/monitorar", json={"link": "https://example.com"})

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Testes - GET / e GET /health
# ---------------------------------------------------------------------------


class TestRotasAuxiliares:
    """Testes para rotas auxiliares (home e health check)."""

    def test_home_retorna_200(self):
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "TechPromos API is running"

    def test_health_retorna_200(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "TechPromos API"
