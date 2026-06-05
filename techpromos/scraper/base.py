"""
Classe base abstrata para todos os scrapers de marketplace.

Define o contrato que todos os scrapers devem seguir,
garantindo consistência na interface e no formato de saída.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT: int = 15  # segundos
DEFAULT_RETRIES: int = 3
RETRY_BACKOFF_FACTOR: float = 0.5

HEADERS_PADRAO: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


# ---------------------------------------------------------------------------
# Modelo de dados
# ---------------------------------------------------------------------------


@dataclass
class ProdutoInfo:
    """Representa as informações extraídas de um produto.

    Attributes:
        produto: Nome/título do produto.
        preco: Preço atual do produto.
        url: URL de onde os dados foram extraídos.
        consultado_em: Data e hora da consulta (ISO 8601).
        marketplace: Nome do marketplace de origem.
        disponivel: Se o produto está disponível para compra.
        erro: Mensagem de erro, caso a extração tenha falhado.
    """

    produto: Optional[str] = None
    preco: Optional[float] = None
    url: Optional[str] = None
    consultado_em: str = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )
    marketplace: Optional[str] = None
    disponivel: bool = True
    erro: Optional[str] = None

    def to_dict(self) -> dict:
        """Serializa o objeto para dicionário (formato JSON-compatível).

        Returns:
            Dicionário com os dados do produto.
        """
        return {
            "produto": self.produto,
            "preco": self.preco,
            "url": self.url,
            "consultado_em": self.consultado_em,
            "marketplace": self.marketplace,
            "disponivel": self.disponivel,
            "erro": self.erro,
        }

    @property
    def sucesso(self) -> bool:
        """Retorna True se a extração foi bem-sucedida (sem erro e com dados)."""
        return self.erro is None and self.produto is not None and self.preco is not None


# ---------------------------------------------------------------------------
# Scraper base
# ---------------------------------------------------------------------------


class BaseScraper(ABC):
    """Classe base abstrata para scrapers de marketplace.

    Fornece:
        - Sessão HTTP com retry automático e headers padrão.
        - Método ``raspar(url)`` que coordena o fluxo de extração.
        - Hooks abstratos que subclasses devem implementar.

    Usage::

        scraper = MercadoLivreScraper()
        resultado = scraper.raspar("https://...")
        print(resultado.to_dict())
    """

    #: Nome do marketplace — deve ser sobrescrito pela subclasse.
    marketplace: str = "Desconhecido"

    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
        headers_extras: Optional[dict[str, str]] = None,
    ) -> None:
        """Inicializa o scraper com sessão HTTP configurada.

        Args:
            timeout: Tempo máximo de espera por resposta (segundos).
            retries: Número de tentativas em caso de falha transitória.
            headers_extras: Headers HTTP adicionais (mesclados aos padrão).
        """
        self.timeout = timeout
        self.session = self._criar_sessao(retries, headers_extras or {})
        logger.debug("Scraper '%s' inicializado (timeout=%ds).", self.marketplace, timeout)

    # ------------------------------------------------------------------
    # Interface pública
    # ------------------------------------------------------------------

    def raspar(self, url: str) -> ProdutoInfo:
        """Coordena o fluxo completo de raspagem para uma URL.

        Realiza a requisição HTTP, faz o parse do HTML e extrai os dados
        do produto. Todos os erros são capturados e retornados no campo
        ``erro`` do objeto ``ProdutoInfo``.

        Args:
            url: URL completa do produto no marketplace.

        Returns:
            ``ProdutoInfo`` com os dados extraídos ou com campo ``erro``
            preenchido em caso de falha.
        """
        logger.info("[%s] Iniciando raspagem: %s", self.marketplace, url)

        try:
            html = self._requisitar(url)
            info = self._extrair(html, url)
            info.marketplace = self.marketplace
            info.url = url

            if info.sucesso:
                logger.info(
                    "[%s] Produto encontrado: '%s' — R$ %.2f",
                    self.marketplace,
                    info.produto,
                    info.preco,
                )
            else:
                logger.warning("[%s] Produto não encontrado em: %s", self.marketplace, url)

            return info

        except requests.exceptions.ConnectionError as exc:
            return self._erro(url, f"Erro de conexão: {exc}")

        except requests.exceptions.Timeout:
            return self._erro(url, f"Timeout após {self.timeout}s aguardando resposta.")

        except requests.exceptions.HTTPError as exc:
            return self._erro(url, f"Erro HTTP {exc.response.status_code}: {exc}")

        except requests.exceptions.RequestException as exc:
            return self._erro(url, f"Erro na requisição: {exc}")

        except Exception as exc:  # noqa: BLE001
            logger.exception("[%s] Erro inesperado ao raspar %s", self.marketplace, url)
            return self._erro(url, f"Erro inesperado: {type(exc).__name__}: {exc}")

    # ------------------------------------------------------------------
    # Hooks abstratos — subclasses devem implementar
    # ------------------------------------------------------------------

    @abstractmethod
    def _extrair(self, html: str, url: str) -> ProdutoInfo:
        """Extrai as informações do produto a partir do HTML da página.

        Args:
            html: Conteúdo HTML da página do produto.
            url: URL original da requisição (para referência).

        Returns:
            ``ProdutoInfo`` com os campos preenchidos.
        """
        ...

    # ------------------------------------------------------------------
    # Métodos auxiliares internos
    # ------------------------------------------------------------------

    def _requisitar(self, url: str) -> str:
        """Realiza a requisição HTTP e retorna o conteúdo HTML.

        Args:
            url: URL a ser requisitada.

        Returns:
            Conteúdo HTML da resposta como string.

        Raises:
            requests.exceptions.HTTPError: Se a resposta tiver status >= 400.
        """
        logger.debug("[%s] GET %s", self.marketplace, url)
        resposta = self.session.get(url, timeout=self.timeout)
        resposta.raise_for_status()
        resposta.encoding = resposta.apparent_encoding or "utf-8"
        return resposta.text

    def _criar_sessao(
        self,
        retries: int,
        headers_extras: dict[str, str],
    ) -> requests.Session:
        """Cria e configura a sessão HTTP com retry automático.

        Args:
            retries: Número de tentativas para erros transitórios.
            headers_extras: Headers adicionais a mesclar nos padrão.

        Returns:
            Sessão ``requests.Session`` configurada.
        """
        sessao = requests.Session()
        sessao.headers.update({**HEADERS_PADRAO, **headers_extras})

        retry_strategy = Retry(
            total=retries,
            backoff_factor=RETRY_BACKOFF_FACTOR,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        sessao.mount("https://", adapter)
        sessao.mount("http://", adapter)

        return sessao

    def _erro(self, url: str, mensagem: str) -> ProdutoInfo:
        """Cria um ``ProdutoInfo`` de falha com a mensagem de erro.

        Args:
            url: URL que estava sendo raspada.
            mensagem: Descrição do erro ocorrido.

        Returns:
            ``ProdutoInfo`` com campo ``erro`` preenchido.
        """
        logger.error("[%s] %s | URL: %s", self.marketplace, mensagem, url)
        return ProdutoInfo(
            url=url,
            marketplace=self.marketplace,
            disponivel=False,
            erro=mensagem,
        )
