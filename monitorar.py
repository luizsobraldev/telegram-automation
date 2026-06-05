"""
monitorar.py — Monitora todos os produtos listados em produtos.txt

Lê as URLs do arquivo produtos.txt (uma por linha, # = comentário)
e exibe o resultado de cada uma no formato escolhido.

Uso:
    python monitorar.py
    python monitorar.py --formato telegram
    python monitorar.py --formato json
    python monitorar.py --arquivo minha_lista.txt --formato telegram

Saída:
    Imprime o resultado de cada produto separado por linha divisória.
    Produtos com erro são exibidos com aviso, mas o script continua.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

from techpromos.factory import obter_scraper
from techpromos.formatters import formatar_telegram
from techpromos.logger import configurar_logging

# Garante UTF-8 no terminal Windows (suporte a emojis)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SEPARADOR = "─" * 50


def ler_urls(caminho: Path) -> list[str]:
    """Lê as URLs do arquivo de produtos, ignorando comentários e linhas vazias.

    Args:
        caminho: Caminho para o arquivo de texto com as URLs.

    Returns:
        Lista de URLs válidas encontradas no arquivo.
    """
    urls = []
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if linha and not linha.startswith("#"):
            urls.append(linha)
    return urls


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Monitora todos os produtos listados em produtos.txt",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--arquivo",
        default="produtos.txt",
        help="Arquivo com a lista de URLs (padrão: produtos.txt).",
    )
    parser.add_argument(
        "--formato",
        default="telegram",
        choices=["json", "telegram"],
        help="Formato de saída: 'telegram' (padrão) ou 'json'.",
    )
    parser.add_argument(
        "--nivel-log",
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Nível de log (padrão: WARNING — menos verboso durante o monitoramento).",
    )
    args = parser.parse_args()

    configurar_logging(nivel=args.nivel_log, arquivo=False, console=True)

    arquivo = Path(args.arquivo)
    if not arquivo.exists():
        print(f"❌ Arquivo '{arquivo}' não encontrado.")
        print("   Crie o arquivo produtos.txt e adicione uma URL por linha.")
        sys.exit(1)

    urls = ler_urls(arquivo)
    if not urls:
        print(f"⚠️  Nenhuma URL encontrada em '{arquivo}'.")
        print("   Adicione URLs de produtos (uma por linha) e remova o # do início.")
        sys.exit(0)

    print(f"🔍 Monitorando {len(urls)} produto(s)...\n")

    for i, url in enumerate(urls, start=1):
        print(SEPARADOR)
        print(f"[{i}/{len(urls)}] {url[:70]}{'...' if len(url) > 70 else ''}")
        print()

        try:
            scraper = obter_scraper(url)
            resultado = scraper.raspar(url)
        except ValueError as exc:
            print(f"❌ Marketplace não suportado: {exc}")
            continue

        if args.formato == "telegram":
            print(formatar_telegram(resultado))
        else:
            print(json.dumps(resultado.to_dict(), ensure_ascii=False, indent=2))

        print()

    print(SEPARADOR)
    print(f"✅ Concluído — {len(urls)} produto(s) verificado(s).")


if __name__ == "__main__":
    main()
