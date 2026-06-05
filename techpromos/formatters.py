"""
Formatadores de saída para os dados de produto.

Fornece diferentes formatos de saída além do JSON padrão:
    - telegram: Mensagem formatada para grupos do Telegram
    - json: JSON estruturado (padrão, para n8n)
"""

from __future__ import annotations

from typing import Optional

from techpromos.scraper.base import ProdutoInfo

# ---------------------------------------------------------------------------
# Configuração do rodapé do Telegram — edite aqui
# ---------------------------------------------------------------------------

TELEGRAM_GRUPO_NOME: str = "TECHPROMOS COM SOBRAL"
TELEGRAM_GRUPO_LINK: str = "https://t.me/techpromos_sobral"


def formatar_telegram(info: ProdutoInfo) -> str:
    """Formata os dados do produto como mensagem para o Telegram.

    Gera uma mensagem pronta para ser enviada em grupos/canais do Telegram,
    no estilo de grupos de ofertas.

    Args:
        info: Objeto ``ProdutoInfo`` com os dados do produto.

    Returns:
        String formatada com emojis, pronta para o Telegram.
    """
    if not info.sucesso:
        return f"❌ Erro ao buscar produto:\n{info.erro or 'Erro desconhecido'}"

    # Monta o bloco de preços
    linhas_preco = []
    
    if info.preco_original and info.preco_original > (info.preco or 0):
        linhas_preco.append(f"De: {_formatar_preco(info.preco_original)}")
        linhas_preco.append(f"Por: {_formatar_preco(info.preco)} (Pix)")
    else:
        linhas_preco.append(f"Por: {_formatar_preco(info.preco)} (Pix)")
        
    if info.preco_parcelado and info.preco_parcelado != info.preco:
        valor_parcelado = _formatar_preco(info.preco_parcelado).replace("R$ ", "")
        linhas_preco.append(f"ou {valor_parcelado} (Parcelado)")

    preco_final_txt = "\n".join(linhas_preco)
    disponivel_txt = "" if info.disponivel else "\n\n⚠️ *Verifique disponibilidade*"

    return (
        f"🔥 {info.produto} 🔥\n"
        f"\n"
        f"💸 {preco_final_txt}"
        f"{disponivel_txt}\n"
        f"\n"
        f"🛒 {info.url}\n"
        f"\n"
        f"🤑 {TELEGRAM_GRUPO_NOME}\n"
        f"{TELEGRAM_GRUPO_LINK} 🔥"
    )


def _formatar_preco(preco: Optional[float]) -> str:
    """Formata o preço no padrão brasileiro (ex: 3.499,90).

    Args:
        preco: Valor numérico do preço.

    Returns:
        String formatada como 'R$ 1.234,56' ou 'Preço indisponível'.
    """
    if preco is None:
        return "Preço indisponível"

    inteiro = int(preco)
    centavos = round((preco - inteiro) * 100)
    inteiro_fmt = f"{inteiro:,}".replace(",", ".")
    return f"R$ {inteiro_fmt},{centavos:02d}"
