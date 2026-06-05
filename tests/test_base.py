"""
Testes unitários para o módulo techpromos.scraper.base.
"""

from __future__ import annotations

import pytest

from techpromos.scraper.base import ProdutoInfo


class TestProdutoInfo:
    """Testa o dataclass ProdutoInfo."""

    def test_sucesso_quando_produto_e_preco_preenchidos(self):
        info = ProdutoInfo(produto="PS5 Slim", preco=3499.90, url="https://example.com")
        assert info.sucesso is True

    def test_falha_quando_produto_ausente(self):
        info = ProdutoInfo(preco=3499.90)
        assert info.sucesso is False

    def test_falha_quando_preco_ausente(self):
        info = ProdutoInfo(produto="PS5 Slim")
        assert info.sucesso is False

    def test_falha_quando_erro_preenchido(self):
        info = ProdutoInfo(produto="PS5 Slim", preco=3499.90, erro="Timeout")
        assert info.sucesso is False

    def test_to_dict_contem_chaves_esperadas(self):
        info = ProdutoInfo(produto="PS5 Slim", preco=3499.90)
        d = info.to_dict()
        assert "produto" in d
        assert "preco" in d
        assert "url" in d
        assert "consultado_em" in d
        assert "marketplace" in d
        assert "disponivel" in d
        assert "erro" in d

    def test_consultado_em_formato_iso(self):
        import re
        info = ProdutoInfo()
        # ISO 8601: YYYY-MM-DDTHH:MM:SS
        assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", info.consultado_em)
