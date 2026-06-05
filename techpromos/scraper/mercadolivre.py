"""
Scraper para o Mercado Livre (mercadolivre.com.br).

Estratégia de extração:
    O Mercado Livre renderiza o preço via JavaScript para User-Agents normais.
    Para contornar isso sem Playwright, utilizamos um User-Agent de crawler
    (Googlebot), que faz o servidor retornar o HTML pré-renderizado com
    dados estruturados em JSON-LD (schema.org).

    Ordem de tentativa para título:
        1. JSON-LD (schema.org/Product ou schema.org/Offer) — mais confiável.
        2. Seletores CSS de fallback (.ui-pdp-title, .andes-money-amount__fraction).
        3. Metatag og:title + <title> para o nome (último recurso).

    Resiliência:
        - Parser HTML com fallback automático (lxml → html.parser).
        - Título extraído por 3 métodos independentes antes de reportar erro.
        - Mensagem de erro detalhada para diagnóstico em produção.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

from bs4 import BeautifulSoup, FeatureNotFound, Tag

from techpromos.scraper.base import BaseScraper, ProdutoInfo

logger = logging.getLogger(__name__)

# Parsers em ordem de preferência (lxml é mais rápido, html.parser é built-in)
_PARSERS = ["lxml", "html.parser"]

# User-Agent que faz o ML servir HTML pré-renderizado com JSON-LD
_UA_CRAWLER = (
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
)


class MercadoLivreScraper(BaseScraper):
    """Scraper especializado para páginas de produto do Mercado Livre.

    Utiliza User-Agent de crawler para receber o HTML pré-renderizado
    com dados estruturados (JSON-LD / schema.org), evitando a necessidade
    de renderização JavaScript.

    Suporta:
        - Páginas de catálogo: /p/MLB...
        - Páginas de anúncio individual: /MLB...
        - URLs com parâmetros de rastreamento (ignorados automaticamente)

    Example::

        scraper = MercadoLivreScraper()
        resultado = scraper.raspar(
            "https://www.mercadolivre.com.br/playstation-5-slim.../p/MLB57081243"
        )
        print(resultado.to_dict())
    """

    marketplace: str = "Mercado Livre"

    def __init__(self, **kwargs) -> None:
        # Usa UA de crawler + desabilita gzip para garantir decodificação correta
        # O ML com gzip retorna binário que o apparent_encoding detecta errado.
        super().__init__(
            headers_extras={
                "User-Agent": _UA_CRAWLER,
                "Accept-Encoding": "identity",  # sem compressão = UTF-8 puro
            },
            **kwargs,
        )

    def _requisitar(self, url: str) -> str:
        """Sobrescreve o método base para forçar decodificação UTF-8.

        O ML sempre retorna UTF-8. Forçar a codificação evita que o
        ``apparent_encoding`` tente adivinhar e produza lixo.

        Args:
            url: URL a ser requisitada.

        Returns:
            HTML como string UTF-8.
        """
        logger.info("[%s] GET %s", self.marketplace, url)
        resposta = self.session.get(url, timeout=self.timeout)
        logger.info(
            "[%s] HTTP %d | URL final: %s | %d bytes",
            self.marketplace, resposta.status_code, resposta.url, len(resposta.content),
        )
        resposta.raise_for_status()
        resposta.encoding = "utf-8"
        return resposta.text

    def _extrair(self, html: str, url: str) -> ProdutoInfo:
        """Extrai título e preço da página do Mercado Livre.

        Tenta primeiro via JSON-LD (mais robusto a mudanças de layout).
        Cai em seletores CSS como fallback.

        Args:
            html: Conteúdo HTML da página do produto.
            url: URL original da requisição.

        Returns:
            ``ProdutoInfo`` preenchido com os dados encontrados.
        """
        soup = self._parse_html(html)

        # --- Tentativa 1: JSON-LD (schema.org) ---
        resultado = self._extrair_via_jsonld(soup, url)

        # --- Tentativa 2: Seletores CSS ---
        logger.debug("[%s] Executando extração via CSS.", self.marketplace)
        resultado_css = self._extrair_via_css(soup, url)

        # Combina o que cada método encontrou (ex: título do JSON-LD, preço não encontrado)
        produto = (resultado and resultado.produto) or resultado_css.produto
        preco = (resultado and resultado.preco) or resultado_css.preco
        preco_original = resultado_css.preco_original
        preco_parcelado = resultado_css.preco_parcelado
        
        disponivel = True
        if resultado and not resultado.disponivel:
            disponivel = False
        if not resultado_css.disponivel:
            disponivel = False

        # --- Tentativa 3: Metatags (og:title, <title>) como último recurso ---
        if produto is None:
            produto = self._extrair_titulo_metatag(soup)

        if produto is None:
            logger.warning(
                "[%s] Título não encontrado por nenhum método "
                "(JSON-LD, CSS, metatag). HTML length=%d | URL: %s",
                self.marketplace, len(html), url,
            )
            return ProdutoInfo(
                url=url,
                marketplace=self.marketplace,
                disponivel=False,
                erro=(
                    "Não foi possível extrair os dados do produto. "
                    "O Mercado Livre pode ter bloqueado a requisição "
                    "ou alterado a estrutura da página."
                ),
            )

        erro = None if preco is not None else "Preço não encontrado na página."
        return ProdutoInfo(
            produto=produto,
            preco=preco,
            preco_original=preco_original,
            preco_parcelado=preco_parcelado,
            url=url,
            marketplace=self.marketplace,
            disponivel=disponivel,
            erro=erro,
        )

    # ------------------------------------------------------------------
    # Extração via JSON-LD
    # ------------------------------------------------------------------

    def _extrair_via_jsonld(self, soup: BeautifulSoup, url: str) -> Optional[ProdutoInfo]:
        """Extrai dados a partir de blocos JSON-LD (schema.org).

        Percorre todos os ``<script type='application/ld+json'>`` da página
        procurando objetos do tipo ``Product`` ou com campo ``offers``.

        Args:
            soup: HTML parseado.
            url: URL original (para log).

        Returns:
            ``ProdutoInfo`` se encontrou dados, ou None.
        """
        scripts = soup.find_all("script", type="application/ld+json")
        logger.debug("[%s] JSON-LD scripts encontrados: %d", self.marketplace, len(scripts))

        for script in scripts:
            try:
                dados = json.loads(script.string or "")
            except (json.JSONDecodeError, TypeError):
                continue

            # Pode ser lista ou dict
            objetos = dados if isinstance(dados, list) else [dados]

            for obj in objetos:
                tipo = obj.get("@type", "")
                nome = obj.get("name")
                ofertas = obj.get("offers") or (obj if "price" in obj else None)

                if nome and ofertas:
                    preco = self._preco_do_offer(ofertas)
                    disponivel = self._disponivel_do_offer(ofertas)
                    logger.debug(
                        "[%s] JSON-LD: nome='%s' preco=%s",
                        self.marketplace, nome, preco,
                    )
                    return ProdutoInfo(
                        produto=nome,
                        preco=preco,
                        url=url,
                        marketplace=self.marketplace,
                        disponivel=disponivel,
                    )

        return None

    def _preco_do_offer(self, ofertas: dict | list) -> Optional[float]:
        """Extrai o preço do objeto ``offers`` do JSON-LD.

        Args:
            ofertas: Dict ou lista de dicts com dados da oferta.

        Returns:
            Preço como float, ou None.
        """
        if isinstance(ofertas, list):
            ofertas = ofertas[0] if ofertas else {}
        preco_raw = ofertas.get("price")
        try:
            return float(preco_raw)
        except (TypeError, ValueError):
            return None

    def _disponivel_do_offer(self, ofertas: dict | list) -> bool:
        """Detecta disponibilidade a partir do campo ``availability`` do JSON-LD.

        Args:
            ofertas: Dict ou lista de dicts do campo ``offers``.

        Returns:
            True se disponível, False caso contrário.
        """
        if isinstance(ofertas, list):
            ofertas = ofertas[0] if ofertas else {}
        disponibilidade = str(ofertas.get("availability", "InStock")).lower()
        return "instock" in disponibilidade or "disponivel" in disponibilidade

    # ------------------------------------------------------------------
    # Extração via seletores CSS (fallback)
    # ------------------------------------------------------------------

    _SEL_TITULO: str = ".ui-pdp-title"
    _SEL_FRAÇÃO: str = ".andes-money-amount__fraction"
    _SEL_CENTAVOS: str = ".andes-money-amount__cents"
    _SEL_INDISPONIVEL: list[str] = [
        ".ui-pdp-buybox--unavailable",
        ".ui-pdp-stock-unavailable",
    ]

    def _extrair_via_css(self, soup: BeautifulSoup, url: str) -> ProdutoInfo:
        """Extrai dados via seletores CSS como fallback ao JSON-LD e para preços extras.

        Args:
            soup: HTML parseado.
            url: URL original.

        Returns:
            ``ProdutoInfo`` com os campos encontrados (pode estar incompleto).
        """
        titulo = self._extrair_titulo_css(soup)
        preco = self._extrair_preco_seletor(soup, ".ui-pdp-price__second-line")
        if not preco:  # fallback
            preco = self._extrair_preco_seletor(soup, "")
            
        preco_original = self._extrair_preco_seletor(soup, ".ui-pdp-price__original-value")
        preco_parcelado = self._extrair_preco_seletor(soup, ".ui-pdp-price__subtitles")
        disponivel = not self._detectar_indisponivel(soup)

        erro = None
        if titulo is None and preco is None:
            erro = "Nenhum dado encontrado via seletores CSS."
        elif preco is None:
            erro = "Preço não encontrado via seletores CSS."

        return ProdutoInfo(
            produto=titulo,
            preco=preco,
            preco_original=preco_original,
            preco_parcelado=preco_parcelado,
            url=url,
            marketplace=self.marketplace,
            disponivel=disponivel,
            erro=erro,
        )

    def _extrair_titulo_css(self, soup: BeautifulSoup) -> Optional[str]:
        """Extrai o título via seletores CSS."""
        # Tenta seletor oficial, depois h1 genérico
        for sel in [self._SEL_TITULO, "h1"]:
            el: Optional[Tag] = soup.select_one(sel)
            if el:
                texto = el.get_text(strip=True)
                if texto:
                    return texto
        return None

    def _extrair_preco_seletor(self, soup: BeautifulSoup, seletor_pai: str) -> Optional[float]:
        """Extrai o preço via seletores CSS combinando um contêiner pai."""
        container = soup.select_one(seletor_pai) if seletor_pai else soup
        if not container:
            return None

        fracao_tag = container.select_one(self._SEL_FRAÇÃO)
        if not fracao_tag:
            return None

        centavos_tag = container.select_one(self._SEL_CENTAVOS)
        parte_inteira = self._limpar_numero(fracao_tag.get_text(strip=True))
        parte_centavos = (
            self._limpar_numero(centavos_tag.get_text(strip=True))
            if centavos_tag else "00"
        )
        parte_centavos = parte_centavos.ljust(2, "0")[:2]

        try:
            return float(f"{parte_inteira}.{parte_centavos}")
        except ValueError:
            return None

    def _detectar_indisponivel(self, soup: BeautifulSoup) -> bool:
        """Verifica se o produto está indisponível."""
        for seletor in self._SEL_INDISPONIVEL:
            if soup.select_one(seletor):
                return True
        return False

    # ------------------------------------------------------------------
    # Extração via metatags (último recurso)
    # ------------------------------------------------------------------

    def _extrair_titulo_metatag(self, soup: BeautifulSoup) -> Optional[str]:
        """Extrai o título via og:title ou <title> como último recurso.

        Útil quando o ML serve uma página com layout diferente (ex: IPs de
        datacenter) que não contém os seletores CSS padrão nem JSON-LD.

        Args:
            soup: HTML parseado.

        Returns:
            Título do produto, ou None se não encontrado.
        """
        # og:title
        og = soup.find("meta", property="og:title")
        if og:
            conteudo = og.get("content", "").strip()
            if conteudo:
                # Remove sufixos como " | Mercado Livre" ou " - R$ ..."
                titulo = re.split(r"\s*[|]\s*", conteudo)[0].strip()
                titulo = re.sub(r"\s*-\s*R\$\s*[\d.,]+\s*$", "", titulo).strip()
                if titulo:
                    logger.info("[%s] Titulo extraido via og:title: '%s'", self.marketplace, titulo)
                    return titulo

        # <title>
        title_tag = soup.find("title")
        if title_tag:
            texto = title_tag.get_text(strip=True)
            if texto:
                titulo = re.split(r"\s*[|]\s*", texto)[0].strip()
                titulo = re.sub(r"\s*-\s*R\$\s*[\d.,]+\s*$", "", titulo).strip()
                if titulo:
                    logger.info("[%s] Titulo extraido via <title>: '%s'", self.marketplace, titulo)
                    return titulo

        return None

    # ------------------------------------------------------------------
    # Parser HTML resiliente
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_html(html: str) -> BeautifulSoup:
        """Parseia o HTML usando o melhor parser disponível.

        Tenta ``lxml`` primeiro (mais rápido), e cai para ``html.parser``
        (built-in do Python) se ``lxml`` não estiver instalado.

        Args:
            html: Conteúdo HTML como string.

        Returns:
            Objeto ``BeautifulSoup`` parseado.
        """
        for parser in _PARSERS:
            try:
                return BeautifulSoup(html, parser)
            except FeatureNotFound:
                logger.warning("Parser '%s' nao disponivel, tentando proximo.", parser)
                continue
        # Fallback absoluto
        return BeautifulSoup(html, "html.parser")

    @staticmethod
    def _limpar_numero(texto: str) -> str:
        """Remove não-dígitos de uma string numérica. Ex: '3.499' → '3499'."""
        return re.sub(r"\D", "", texto)
