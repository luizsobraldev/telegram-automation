"""
Ponto de entrada principal do TechPromos com Sobral.

Aceita uma URL como argumento e retorna os dados do produto em JSON
ou como mensagem formatada para o Telegram.

Uso:
    python -m techpromos <URL>
    python -m techpromos <URL> --formato telegram
    python -m techpromos <URL> --nivel-log DEBUG
    python -m techpromos <URL> --sem-arquivo-log

Saída (stdout, JSON):
    {
        "produto": "PlayStation 5 Slim",
        "preco": 3499.90,
        "url": "https://...",
        "consultado_em": "2026-06-04T12:00:00",
        "marketplace": "Mercado Livre",
        "disponivel": true,
        "erro": null
    }

Erros críticos (ex: URL inválida) são escritos no stderr e
o processo termina com código de saída 1.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from urllib.parse import urlparse

from techpromos.factory import obter_scraper
from techpromos.formatters import formatar_telegram
from techpromos.logger import configurar_logging

# Garante que o stdout suporte UTF-8 (emojis) no Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")



def _validar_url(url: str) -> str | None:
    """Valida se a URL é minimamente usável.

    Returns:
        Mensagem de erro se inválida, ou None se válida.
    """
    if not url or url.upper() == url and len(url) < 50 and " " not in url:
        # heurística: strings como URL_DO_PRODUTO são placeholders em caixa alta
        if not url.startswith("http"):
            return (
                f"URL inválida ou placeholder detectado: '{url}'.\n"
                "Passe a URL real de um produto. Exemplo:\n"
                "  python -m techpromos \"https://www.mercadolivre.com.br/playstation-5...\""
            )
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return (
            f"URL deve começar com 'https://' ou 'http://'. Recebido: '{url}'"
        )
    if not parsed.netloc:
        return (
            f"URL sem domínio válido: '{url}'.\n"
            "Passe a URL completa, incluindo 'https://www...'"
        )
    return None


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="techpromos",
        description="TechPromos com Sobral — Monitorador de preços em marketplaces.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "url",
        help="URL completa do produto a ser monitorado.",
    )
    parser.add_argument(
        "--nivel-log",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        metavar="NIVEL",
        help="Nível de detalhe dos logs (padrão: INFO).",
    )
    parser.add_argument(
        "--sem-arquivo-log",
        action="store_true",
        default=False,
        help="Desativa a escrita de logs em arquivo (útil em ambientes containerizados).",
    )
    parser.add_argument(
        "--formato",
        default="json",
        choices=["json", "telegram"],
        help="Formato de saída: 'json' (padrão, para n8n) ou 'telegram' (mensagem pronta).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada principal.

    Args:
        argv: Lista de argumentos (usa sys.argv se None).

    Returns:
        Código de saída: 0 para sucesso, 1 para erro crítico.
    """
    args = _parse_args(argv)

    configurar_logging(
        nivel=args.nivel_log,
        arquivo=not args.sem_arquivo_log,
        console=True,
    )

    # Valida a URL antes de tentar qualquer coisa
    erro_url = _validar_url(args.url)
    if erro_url:
        print(json.dumps({"erro": erro_url}, ensure_ascii=False, indent=2))
        return 1

    try:
        scraper = obter_scraper(args.url)
    except ValueError as exc:
        print(json.dumps({"erro": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    resultado = scraper.raspar(args.url)

    if args.formato == "telegram":
        print(formatar_telegram(resultado))
    else:
        print(json.dumps(resultado.to_dict(), ensure_ascii=False, indent=2))

    return 0 if resultado.sucesso else 1


if __name__ == "__main__":
    sys.exit(main())
