"""Formatação de números e datas no padrão brasileiro."""
from __future__ import annotations

from datetime import date

NOMES_MESES = ("Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez")
MESES_ABREVIADOS = ("jan.", "fev.", "mar.", "abr.", "mai.", "jun.", "jul.", "ago.", "set.", "out.", "nov.", "dez.")
MESES_EXTENSO = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)
PALAVRAS_MINUSCULAS = frozenset({"de", "da", "do", "das", "dos", "e"})
ACENTOS_CONHECIDOS = {"SAO": "São", "PETROLEO": "Petróleo"}
NOMES_CONHECIDOS = {"PETROLEO BRASILEIRO S A PETROBRAS": "Petróleo Brasileiro S.A. (Petrobras)"}
NUMEROS_EXTENSO = {1: "um", 2: "dois", 3: "três", 4: "quatro", 5: "cinco", 6: "seis", 7: "sete", 8: "oito"}


def dec(valor: float, casas: int = 1) -> str:
    """Número com ponto nos milhares, vírgula nos decimais e sinal de menos tipográfico (−)."""
    return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".").replace("-", "−")


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


def nome_proprio(nome: str) -> str:
    """Nome de cliente em maiúsculas (como vem do BNDES) em formato de texto corrido.

    Mantém "de/da/do/e" em minúsculas, escreve "S/A" e "S A" como "S.A." e restaura os acentos
    que o arquivo de origem não traz para as palavras de ACENTOS_CONHECIDOS.
    """
    if nome in NOMES_CONHECIDOS:
        return NOMES_CONHECIDOS[nome]
    palavras = nome.replace(" S A", " S.A.").replace(" S/A", " S.A.").split()
    resultado = []
    for posicao, palavra in enumerate(palavras):
        if palavra in ACENTOS_CONHECIDOS:
            resultado.append(ACENTOS_CONHECIDOS[palavra])
        elif posicao and palavra.lower() in PALAVRAS_MINUSCULAS:
            resultado.append(palavra.lower())
        elif palavra == "SA":
            resultado.append("S.A.")
        elif palavra.endswith(".") and len(palavra) <= 4:
            resultado.append(palavra)
        else:
            resultado.append(palavra.capitalize())
    return " ".join(resultado)
