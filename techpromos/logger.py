"""
Módulo de configuração de logging para o projeto TechPromos.

Configura handlers para console (colorido) e arquivo rotativo,
com níveis e formatos padronizados.
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_FILE = LOG_DIR / "techpromos.log"
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
MAX_BYTES = 5 * 1024 * 1024   # 5 MB por arquivo
BACKUP_COUNT = 3               # mantém 3 arquivos de backup


def configurar_logging(
    nivel: str = "INFO",
    arquivo: bool = True,
    console: bool = True,
) -> None:
    """Configura o sistema de logging do projeto.

    Deve ser chamada uma única vez na inicialização da aplicação.

    Args:
        nivel: Nível de log ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL').
        arquivo: Se True, escreve logs em arquivo rotativo em ``logs/``.
        console: Se True, exibe logs no console (stdout).

    Example::

        from techpromos.logger import configurar_logging
        configurar_logging(nivel="DEBUG")
    """
    nivel_numerico = getattr(logging, nivel.upper(), logging.INFO)

    # Logger raiz do projeto (captura tudo de 'techpromos.*')
    logger_raiz = logging.getLogger("techpromos")
    logger_raiz.setLevel(nivel_numerico)

    # Evita duplicar handlers se chamado mais de uma vez
    if logger_raiz.handlers:
        return

    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    if console:
        handler_console = logging.StreamHandler(sys.stdout)
        handler_console.setLevel(nivel_numerico)
        handler_console.setFormatter(formatter)
        logger_raiz.addHandler(handler_console)

    if arquivo:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        handler_arquivo = logging.handlers.RotatingFileHandler(
            LOG_FILE,
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
        handler_arquivo.setLevel(nivel_numerico)
        handler_arquivo.setFormatter(formatter)
        logger_raiz.addHandler(handler_arquivo)

    logger_raiz.debug("Logging configurado. Nível: %s | Arquivo: %s", nivel, arquivo)
