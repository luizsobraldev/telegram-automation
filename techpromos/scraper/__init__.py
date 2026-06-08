"""
Módulo de scrapers para marketplaces.

Scrapers disponíveis:
    - MercadoLivreScraper: Scraper para produto individual do Mercado Livre
    - MercadoLivreBusca: Scraper de busca por termo no Mercado Livre
    - (futuro) ShopeeScraper: Scraper para Shopee
    - (futuro) AmazonScraper: Scraper para Amazon
"""

from techpromos.scraper.mercadolivre import MercadoLivreScraper
from techpromos.scraper.mercadolivre_busca import MercadoLivreBusca, ProdutoBusca
from techpromos.scraper.base import BaseScraper, ProdutoInfo

__all__ = [
    "BaseScraper",
    "ProdutoInfo",
    "MercadoLivreScraper",
    "MercadoLivreBusca",
    "ProdutoBusca",
]
