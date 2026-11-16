"""Formatação de números e datas no padrão brasileiro."""
from __future__ import annotations

from datetime import date

NOMES_MESES = ("Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez")
MESES_ABREVIADOS = ("jan.", "fev.", "mar.", "abr.", "mai.", "jun.", "jul.", "ago.", "set.", "out.", "nov.", "dez.")
MESES_EXTENSO = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)
NUMEROS_EXTENSO = {1: "um", 2: "dois", 3: "três", 4: "quatro", 5: "cinco", 6: "seis", 7: "sete", 8: "oito"}


def dec(valor: float, casas: int = 1) -> str:
    """Número com ponto nos milhares e vírgula nos decimais."""
    return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def num(valor: float) -> str:
    return dec(valor, 0)


def bi(valor: float, casas: int = 1) -> str:
    """Valor em reais exibido em bilhões."""
    return dec(valor / 1e9, casas)


def pct(fracao: float, casas: int = 1) -> str:
    return dec(fracao * 100, casas) + "%"


def mes_ano(data: date) -> str:
    return f"{MESES_ABREVIADOS[data.month - 1]}/{data.year}"


def mes_ano_extenso(data: date) -> str:
    return f"{MESES_EXTENSO[data.month - 1]} de {data.year}"


def dia_mes_extenso(data: date) -> str:
    return f"{data.day} de {MESES_EXTENSO[data.month - 1]}"
