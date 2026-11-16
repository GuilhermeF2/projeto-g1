"""Formatação de números no padrão brasileiro (ponto nos milhares, vírgula nos decimais)."""
from __future__ import annotations


def dec(valor: float, casas: int = 1) -> str:
    return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def num(valor: float) -> str:
    return dec(valor, 0)


def bi(valor: float, casas: int = 1) -> str:
    return dec(valor / 1e9, casas)


def pct(fracao: float, casas: int = 1) -> str:
    return dec(fracao * 100, casas) + "%"


MESES_ABREVIADOS = ["jan.", "fev.", "mar.", "abr.", "mai.", "jun.", "jul.", "ago.", "set.", "out.", "nov.", "dez."]


def mes_ano(data) -> str:
    return f"{MESES_ABREVIADOS[data.month - 1]}/{data.year}"
