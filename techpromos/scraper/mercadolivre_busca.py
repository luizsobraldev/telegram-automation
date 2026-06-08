"""
Scraper de busca para o Mercado Livre (lista.mercadolivre.com.br).

Responsabilidade:
    Receber um termo de busca e retornar uma lista de produtos encontrados
    na página de listagem do Mercado Livre.

    Diferente de mercadolivre.py (que extrai dados de um produto individual),
    este módulo trabalha com a listagem de resultados de pesquisa.

Estratégia de extração:
    1. Monta a URL de busca: https://lista.mercadolivre.com.br/{termo-slugificado}
    2. Requisita o HTML usando User-Agent de crawler (Googlebot) para receber
       HTML pré-renderizado com dados estruturados.
    3. Extrai os itens da listagem via seletores CSS dos cards de resultado.
    4. Aplica fallback entre múltiplos seletores para resiliência a mudanças de layout.

Resiliência:
    - Múltiplos seletores CSS em ordem de preferência.
    - Fallback de parser HTML (lxml → html.parser).
    - URL de produto limpa, removendo tracking parameters.
    - Logging detalhado para diagnóstico em produção.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlencode, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup, FeatureNotFound
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_BASE_URL_BUSCA = "https://lista.mercadolivre.com.br"

# User-Agent de crawler para receber HTML pré-renderizado (mesmo do scraper de produto)
_UA_CRAWLER = (
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
)

_HEADERS = {
    "User-Agent": _UA_CRAWLER,
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Accept-Encoding": "identity",  # sem compressão = UTF-8 puro
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

_TIMEOUT = 15  # segundos
_RETRIES = 2
_BACKOFF = 0.5

# Parsers em ordem de preferência
_PARSERS = ["lxml", "html.parser"]

# ---------------------------------------------------------------------------
# Seletores CSS — em ordem de confiabilidade
# ---------------------------------------------------------------------------

# Container de cada item na listagem
_SEL_ITEM = [
    ".ui-search-layout__item",
    ".ui-search-result",
    "li.ui-search-result",
]

# Título do produto dentro do card
_SEL_TITULO = [
    ".poly-component__title",
    ".poly-component__title-wrapper a",
    ".ui-search-item__title",
    "h2.ui-search-item__title",
    ".poly-box a[href] h2",
]

# Link do produto
_SEL_LINK = [
    "a.poly-component__title",
    ".poly-component__title-wrapper a",
    "a.ui-search-result__link",
    "h2.ui-search-item__title + a",
    ".ui-search-item__group--title a",
]

# Fração inteira do preço (ex: "3.998")
_SEL_FRACAO = ".andes-money-amount__fraction"
# Centavos do preço (ex: "07")
_SEL_CENTAVOS = ".andes-money-amount__cents"

# Container do preço principal atual
_SEL_PRECO_CONTAINER = [
    ".poly-price__current",
    ".ui-search-price__second-line",
    ".price-tag",
    ".ui-search-price",
]

# Container do preço original (riscado)
_SEL_PRECO_ORIGINAL = [
    ".poly-price__original",
    ".ui-search-price__original-value",
    ".andes-money-amount--previous",
]

# Container do preço parcelado
_SEL_PRECO_PARCELADO = [
    ".poly-price__installments",
    ".ui-search-installments",
    ".ui-search-price__second-line",
]


# ---------------------------------------------------------------------------
# Dataclass de resultado
# ---------------------------------------------------------------------------


@dataclass
class ProdutoBusca:
    """Representa um produto encontrado em uma listagem de busca.

    Attributes:
        produto: Nome/título do produto.
        preco: Preço atual do produto.
        preco_original: Preço original (antes do desconto), quando disponível.
        preco_parcelado: Preço parcelado (total ou valor da parcela), quando disponível.
        url: URL funcional do produto no marketplace.
        disponivel: Se o produto está disponível para compra.
    """

    produto: str
    preco: Optional[float]
    preco_original: Optional[float]
    preco_parcelado: Optional[float]
    url: str
    disponivel: bool = True

    def to_dict(self) -> dict:
        """Serializa para dicionário compatível com JSON."""
        return {
            "produto": self.produto,
            "preco": self.preco,
            "preco_original": self.preco_original,
            "preco_parcelado": self.preco_parcelado,
            "url": self.url,
            "disponivel": self.disponivel,
        }


# ---------------------------------------------------------------------------
# Scraper de busca
# ---------------------------------------------------------------------------


class MercadoLivreBusca:
    """Busca produtos por termo na listagem do Mercado Livre.

    Não herda de ``BaseScraper`` porque o contrato é diferente:
    retorna uma lista de ``ProdutoBusca`` em vez de um único ``ProdutoInfo``.

    Example::

        busca = MercadoLivreBusca()
        resultados = busca.buscar("PlayStation 5", limite=5)
        for produto in resultados:
            print(produto.to_dict())
    """

    marketplace: str = "Mercado Livre"

    def __init__(self) -> None:
        self.session = self._criar_sessao()

    # ------------------------------------------------------------------
    # Interface pública
    # ------------------------------------------------------------------

    def buscar(self, termo: str, limite: int = 10) -> list[ProdutoBusca]:
        """Busca produtos no Mercado Livre por termo de pesquisa.

        Args:
            termo: Termo de busca (ex: "PlayStation 5").
            limite: Número máximo de resultados a retornar.

        Returns:
            Lista de ``ProdutoBusca``. Pode ser vazia se nada for encontrado.

        Raises:
            RuntimeError: Se a requisição falhar ou o HTML não puder ser parseado.
        """
        url_busca = self._montar_url(termo)
        logger.info(
            "[Busca] Termo: '%s' | URL: %s | Limite: %d",
            termo, url_busca, limite,
        )

        html = self._requisitar(url_busca)
        resultados = self._extrair_resultados(html, limite)

        logger.info(
            "[Busca] Termo: '%s' | %d resultado(s) encontrado(s)",
            termo, len(resultados),
        )
        return resultados

    # ------------------------------------------------------------------
    # Montagem da URL de busca
    # ------------------------------------------------------------------

    @staticmethod
    def _montar_url(termo: str) -> str:
        """Converte o termo de busca em URL da listagem do Mercado Livre.

        Processo:
            1. Normaliza o texto removendo acentos (NFD → ASCII).
            2. Converte para minúsculas.
            3. Substitui espaços e caracteres não-alfanuméricos por hífens.
            4. Remove hífens duplicados nas extremidades.

        Args:
            termo: Termo de busca bruto (ex: "PlayStation 5").

        Returns:
            URL completa da listagem (ex: "https://lista.mercadolivre.com.br/playstation-5").

        Example::

            url = MercadoLivreBusca._montar_url("PlayStation 5")
            # "https://lista.mercadolivre.com.br/playstation-5"
        """
        # Normaliza unicode: remove acentos (NFD decompõe, encode ASCII remove diacríticos)
        nfkd = unicodedata.normalize("NFKD", termo)
        sem_acentos = nfkd.encode("ascii", "ignore").decode("ascii")

        # Minúsculas
        slug = sem_acentos.lower()

        # Substitui qualquer coisa que não seja letra/número por hífen
        slug = re.sub(r"[^a-z0-9]+", "-", slug)

        # Remove hífens nas extremidades
        slug = slug.strip("-")

        return f"{_BASE_URL_BUSCA}/{slug}"

    # ------------------------------------------------------------------
    # Requisição HTTP
    # ------------------------------------------------------------------

    def _requisitar(self, url: str) -> str:
        """Realiza requisição HTTP e retorna o HTML.

        Args:
            url: URL da página de busca.

        Returns:
            Conteúdo HTML como string UTF-8.

        Raises:
            RuntimeError: Em caso de erro de conexão, timeout ou HTTP >= 400.
        """
        try:
            logger.info("[Busca] GET %s", url)
            resposta = self.session.get(url, timeout=_TIMEOUT)
            logger.info(
                "[Busca] HTTP %d | %d bytes recebidos | URL final: %s",
                resposta.status_code, len(resposta.content), resposta.url,
            )
            resposta.raise_for_status()
            resposta.encoding = "utf-8"
            return resposta.text

        except requests.exceptions.Timeout:
            raise RuntimeError(
                f"Timeout após {_TIMEOUT}s aguardando resposta do Mercado Livre."
            )
        except requests.exceptions.ConnectionError as exc:
            raise RuntimeError(f"Erro de conexão ao acessar o Mercado Livre: {exc}")
        except requests.exceptions.HTTPError as exc:
            raise RuntimeError(
                f"Erro HTTP {exc.response.status_code} ao buscar no Mercado Livre: {exc}"
            )
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"Erro na requisição ao Mercado Livre: {exc}")

    # ------------------------------------------------------------------
    # Extração dos resultados
    # ------------------------------------------------------------------

    def _extrair_resultados(self, html: str, limite: int) -> list[ProdutoBusca]:
        """Extrai a lista de produtos do HTML da página de busca.

        Args:
            html: Conteúdo HTML da página de listagem.
            limite: Número máximo de produtos a extrair.

        Returns:
            Lista de ``ProdutoBusca`` com até ``limite`` itens.
        """
        soup = self._parse_html(html)

        # Tenta cada seletor de item até encontrar resultados
        itens = []
        for seletor in _SEL_ITEM:
            itens = soup.select(seletor)
            if itens:
                logger.debug("[Busca] Seletor de item '%s' encontrou %d cards.", seletor, len(itens))
                break

        if not itens:
            logger.warning("[Busca] Nenhum card de produto encontrado no HTML. HTML length=%d", len(html))
            return []

        resultados: list[ProdutoBusca] = []
        for idx, item in enumerate(itens):
            if len(resultados) >= limite:
                break

            produto = self._extrair_item(item, idx)
            if produto is not None:
                resultados.append(produto)

        return resultados

    def _extrair_item(self, item, idx: int) -> Optional[ProdutoBusca]:
        """Extrai os dados de um único card de produto.

        Args:
            item: Elemento BeautifulSoup do card.
            idx: Índice do item (para log).

        Returns:
            ``ProdutoBusca`` ou None se os dados mínimos não forem encontrados.
        """
        # --- Título ---
        titulo = self._extrair_titulo(item)
        if not titulo:
            logger.debug("[Busca] Item %d: título não encontrado, ignorando.", idx)
            return None

        # --- URL ---
        url = self._extrair_url(item)
        if not url:
            logger.debug("[Busca] Item %d: URL não encontrada, ignorando.", idx)
            return None

        # --- Preços ---
        preco = self._extrair_preco(item, _SEL_PRECO_CONTAINER)
        preco_original = self._extrair_preco(item, _SEL_PRECO_ORIGINAL)
        preco_parcelado = self._extrair_preco(item, _SEL_PRECO_PARCELADO)

        # Se preco_parcelado == preco, não duplicar
        if preco_parcelado is not None and preco_parcelado == preco:
            preco_parcelado = None

        logger.debug(
            "[Busca] Item %d: '%s' | preco=%s | url=%s",
            idx, titulo[:50], preco, url[:60],
        )

        return ProdutoBusca(
            produto=titulo,
            preco=preco,
            preco_original=preco_original,
            preco_parcelado=preco_parcelado,
            url=url,
            disponivel=True,
        )

    # ------------------------------------------------------------------
    # Extração de campos individuais
    # ------------------------------------------------------------------

    def _extrair_titulo(self, item) -> Optional[str]:
        """Extrai o título do produto do card, tentando múltiplos seletores."""
        for seletor in _SEL_TITULO:
            el = item.select_one(seletor)
            if el:
                texto = el.get_text(strip=True)
                if texto:
                    return texto
        return None

    def _extrair_url(self, item) -> Optional[str]:
        """Extrai e limpa a URL do produto.

        Tenta múltiplos seletores e remove parâmetros de tracking da URL.
        """
        # Tenta seletores específicos de link
        for seletor in _SEL_LINK:
            el = item.select_one(seletor)
            if el and el.get("href"):
                return self._limpar_url(el["href"])

        # Fallback: primeiro <a> com href válido no card
        for tag_a in item.find_all("a", href=True):
            href = tag_a["href"]
            if href.startswith("http") and "mercadolivre" in href:
                return self._limpar_url(href)

        return None

    def _extrair_preco(self, item, seletores: list[str]) -> Optional[float]:
        """Extrai preço de um container identificado por lista de seletores.

        Combina a fração inteira com os centavos para montar o float.

        Args:
            item: Card de produto (BeautifulSoup element).
            seletores: Lista de seletores CSS do container do preço.

        Returns:
            Preço como float ou None se não encontrado.
        """
        for seletor in seletores:
            container = item.select_one(seletor)
            if not container:
                continue

            fracao_tag = container.select_one(_SEL_FRACAO)
            if not fracao_tag:
                continue

            centavos_tag = container.select_one(_SEL_CENTAVOS)
            parte_inteira = self._limpar_numero(fracao_tag.get_text(strip=True))
            parte_centavos = (
                self._limpar_numero(centavos_tag.get_text(strip=True))
                if centavos_tag
                else "00"
            )
            parte_centavos = parte_centavos.ljust(2, "0")[:2]

            try:
                return float(f"{parte_inteira}.{parte_centavos}")
            except ValueError:
                continue

        return None

    # ------------------------------------------------------------------
    # Utilitários
    # ------------------------------------------------------------------

    @staticmethod
    def _limpar_url(url: str) -> str:
        """Remove parâmetros de tracking da URL, mantendo apenas o caminho limpo.

        Mantém o scheme, host e path. Remove query string e fragmento.

        Args:
            url: URL original (pode conter tracking params).

        Returns:
            URL limpa e funcional.
        """
        try:
            parsed = urlparse(url)
            # Reconstrói sem query string e sem fragmento
            limpa = urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
            return limpa
        except Exception:
            return url

    @staticmethod
    def _limpar_numero(texto: str) -> str:
        """Remove não-dígitos de uma string numérica. Ex: '3.499' → '3499'."""
        return re.sub(r"\D", "", texto)

    @staticmethod
    def _parse_html(html: str) -> BeautifulSoup:
        """Parseia HTML usando o melhor parser disponível (lxml → html.parser)."""
        for parser in _PARSERS:
            try:
                return BeautifulSoup(html, parser)
            except FeatureNotFound:
                logger.warning("[Busca] Parser '%s' não disponível, tentando próximo.", parser)
        return BeautifulSoup(html, "html.parser")

    def _criar_sessao(self) -> requests.Session:
        """Cria sessão HTTP com retry automático e headers configurados."""
        sessao = requests.Session()
        sessao.headers.update(_HEADERS)

        retry_strategy = Retry(
            total=_RETRIES,
            backoff_factor=_BACKOFF,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        sessao.mount("https://", adapter)
        sessao.mount("http://", adapter)

        return sessao
