"""
Módulo de scrapers para marketplaces.

Scrapers disponíveis:
    - MercadoLivreScraper: Scraper para Mercado Livre
    - (futuro) ShopeeScraper: Scraper para Shopee
    - (futuro) AmazonScraper: Scraper para Amazon
"""

from techpromos.scraper.mercadolivre import MercadoLivreScraper
from techpromos.scraper.base import BaseScraper, ProdutoInfo

__all__ = [
    "BaseScraper",
    "ProdutoInfo",
    "MercadoLivreScraper",
]
