"""
Testes automatizados para a API FastAPI (app.py).

Utiliza TestClient do FastAPI para testar as rotas sem subir servidor real.
Os scrapers são mockados para garantir testes rápidos e determinísticos.
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
URL_NAO_SUPORTADA = "https://www.sitedesconhecido.com.br/produto"


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
    """Cria um ProdutoInfo com falha na extração."""
    return ProdutoInfo(
        url=URL_ML_VALIDA,
        marketplace="Mercado Livre",
        disponivel=False,
        erro="Não foi possível extrair os dados da página.",
    )


# ---------------------------------------------------------------------------
# Testes — POST /monitorar
# ---------------------------------------------------------------------------


class TestMonitorarSucesso:
    """Testes para cenários de sucesso na rota POST /monitorar."""

    @patch("app.obter_scraper")
    def test_retorna_200_com_dados_do_produto(self, mock_obter):
        """URL válida do ML deve retornar 200 com JSON completo."""
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


class TestMonitorarErros:
    """Testes para cenários de erro na rota POST /monitorar."""

    def test_dominio_nao_suportado_retorna_400(self):
        """URL de domínio não suportado deve retornar 400."""
        response = client.post("/monitorar", json={"url": URL_NAO_SUPORTADA})

        assert response.status_code == 400
        assert "Nenhum scraper disponível" in response.json()["detail"]

    @patch("app.obter_scraper")
    def test_falha_na_extracao_retorna_422(self, mock_obter):
        """Quando o scraper não consegue extrair dados, retorna 422."""
        mock_scraper = MagicMock()
        mock_scraper.raspar.return_value = _criar_produto_falha()
        mock_obter.return_value = mock_scraper

        response = client.post("/monitorar", json={"url": URL_ML_VALIDA})

        assert response.status_code == 422

    def test_body_vazio_retorna_422(self):
        """Requisição sem body deve retornar 422 (Unprocessable Entity)."""
        response = client.post("/monitorar")

        assert response.status_code == 422

    def test_body_sem_campo_url_retorna_422(self):
        """Body JSON sem o campo 'url' deve retornar 422."""
        response = client.post("/monitorar", json={"link": "https://example.com"})

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Testes — GET / e GET /health
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
