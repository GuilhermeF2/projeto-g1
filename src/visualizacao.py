"""Figuras do projeto: estáticas (Matplotlib/Seaborn) e interativas (Plotly)."""
from __future__ import annotations

from pathlib import Path
from typing import Final

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap
from plotly.subplots import make_subplots

from src import etl
from src.formatacao import NOMES_MESES, dec, mes_ano, pct

RAIZ: Final = Path(__file__).resolve().parents[1]
PASTA_FIGURAS: Final = RAIZ / "docs" / "assets"

AZUL: Final = "#2a78d6"
AZUL_CLARO: Final = "#86b6ef"
AZUL_ESCURO: Final = "#184f95"
LARANJA: Final = "#eb6834"
CINZA: Final = "#52514e"
GRADE: Final = "#e5e7eb"
TEXTO: Final = "#1f2937"
RAMPA_PORTE: Final = dict(zip(etl.PORTES, ("#9ec5f4", "#5598e7", "#256abf", "#104281"), strict=True))
DIVERGENTE: Final = LinearSegmentedColormap.from_list("laranja_azul", [LARANJA, "#f0efec", AZUL])
FONTE: Final = "-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif"
ROTULOS_CORRELACAO: Final = {
    "valor_contratado_reais": "Valor contratado",
    "juros": "Juros",
    "prazo_carencia_meses": "Prazo de carência",
    "prazo_amortizacao_meses": "Prazo de amortização",
}
FOLGA_EIXO: Final = 1.25


def configurar_tema() -> None:
    """Aplica o tema das figuras estáticas (chamado no início de cada figura, é idempotente)."""
    sns.set_theme(style="whitegrid", rc={"grid.color": GRADE, "axes.edgecolor": GRADE, "axes.labelcolor": CINZA})


def _layout(fig: go.Figure, altura: int = 420) -> go.Figure:
    fig.update_layout(
        height=altura,
        margin={"t": 30, "r": 20, "l": 60, "b": 50},
        font={"family": FONTE, "size": 13, "color": TEXTO},
        plot_bgcolor="white",
        paper_bgcolor="white",
        separators=",.",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
        hoverlabel={"font_family": FONTE},
    )
    fig.update_xaxes(gridcolor=GRADE, linecolor=GRADE, zeroline=False)
    fig.update_yaxes(gridcolor=GRADE, linecolor=GRADE, zeroline=False)
    return fig


def _anotacao(fig: go.Figure, x: object, y: float, texto: str, **opcoes: object) -> None:
    fig.add_annotation(
        x=x, y=y, text=texto, showarrow=True, arrowhead=0, font={"size": 12, "color": CINZA}, **opcoes
    )


def fig_evolucao_anual(df: pd.DataFrame) -> go.Figure:
    anual = etl.resumo_anual(df)
    anual["bi"] = anual["valor_contratado"] / 1e9
    cores = [AZUL_CLARO if ano > etl.ANO_COMPLETO_FINAL else AZUL for ano in anual["ano"]]
    fig = go.Figure(go.Bar(
        x=anual["ano"], y=anual["bi"], marker_color=cores,
        customdata=np.stack([anual["contratos"], anual["subcreditos"]], axis=-1),
        hovertemplate=(
            "<b>%{x}</b><br>Valor contratado: R$ %{y:,.1f} bi<br>Contratos: %{customdata[0]:,.0f}"
            "<br>Subcréditos: %{customdata[1]:,.0f}<extra></extra>"
        ),
    ))
    marcos = etl.pico_e_vale(anual.set_index("ano")["valor_contratado"])
    for rotulo, ano, valor, deslocamento in (
        ("Pico", marcos["ano_pico"], marcos["valor_pico"], -25),
        ("Vale", marcos["ano_vale"], marcos["valor_vale"], -60),
    ):
        _anotacao(fig, ano, valor / 1e9, f"{rotulo}: R$ {dec(valor / 1e9)} bi", ay=deslocamento, bgcolor="white")
    _layout(fig)
    fig.update_layout(showlegend=False, bargap=0.25)
    anos = list(range(int(anual["ano"].min()), int(anual["ano"].max()) + 1, 2))
    rotulos = [f"{ano}*" if ano > etl.ANO_COMPLETO_FINAL else str(ano) for ano in anos]
    fig.update_xaxes(tickmode="array", tickvals=anos, ticktext=rotulos, title="Ano da contratação (* parcial)")
    fig.update_yaxes(title="Valor contratado (R$ bilhões)")
    return fig


def fig_serie_mensal(df: pd.DataFrame) -> go.Figure:
    mensal = etl.resumo_mensal(etl.anos_completos(df))
    mensal["bi"] = mensal[etl.COL_VALOR] / 1e9
    mensal["media_bi"] = mensal["media_movel_12m"] / 1e9
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=mensal["ano_mes"], y=mensal["bi"], name="Valor mensal", mode="lines",
        line={"color": AZUL_CLARO, "width": 1.5},
        hovertemplate="%{x|%m/%Y}<br>R$ %{y:,.1f} bi<extra>Valor mensal</extra>",
    ))
    fig.add_trace(go.Scatter(
        x=mensal["ano_mes"], y=mensal["media_bi"], name="Média móvel de 12 meses", mode="lines",
        line={"color": AZUL_ESCURO, "width": 2.5},
        hovertemplate="%{x|%m/%Y}<br>R$ %{y:,.1f} bi<extra>Média móvel de 12 meses</extra>",
    ))
    pico = mensal.loc[mensal["bi"].idxmax()]
    _anotacao(fig, pico["ano_mes"], pico["bi"], f"{mes_ano(pico['ano_mes'])}: R$ {dec(pico['bi'])} bi", ax=60, ay=0)
    _layout(fig)
    fig.update_xaxes(title="Mês da contratação", tickformat="%Y")
    fig.update_yaxes(title="Valor contratado (R$ bilhões)")
    return fig


def fig_sazonalidade_mensal(df: pd.DataFrame) -> go.Figure:
    participacao = etl.participacao_mensal(df)["valor"] * 100
    cores = [AZUL_ESCURO if mes in etl.TRIMESTRE_FINAL else AZUL_CLARO for mes in participacao.index]
    fig = go.Figure(go.Bar(
        x=list(NOMES_MESES), y=participacao.to_numpy(), marker_color=cores,
        hovertemplate="%{x}: %{y:.1f}% do valor contratado<extra></extra>",
    ))
    uniforme = 100 / len(NOMES_MESES)
    fig.add_hline(
        y=uniforme, line_dash="dash", line_color=CINZA, line_width=1,
        annotation_text=f"distribuição uniforme ({dec(uniforme)}%)", annotation_position="top left",
        annotation_font={"size": 12, "color": CINZA},
    )
    _layout(fig, 380)
    fig.update_layout(showlegend=False, bargap=0.25)
    fig.update_yaxes(title="Participação no valor contratado (%)")
    return fig


def fig_porte(df: pd.DataFrame) -> go.Figure:
    resumo = etl.resumo_por(df, "porte_do_cliente").set_index("porte_do_cliente").loc[list(etl.PORTES)]
    rotulos = [porte.capitalize() for porte in resumo.index]
    cores = [RAMPA_PORTE[porte] for porte in resumo.index]
    participacao = resumo["participacao"] * 100
    mediana = resumo["mediana_subcredito"] / 1e6
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Valor (%)", "Mediana (R$ mi)"))
    fig.add_trace(go.Bar(
        x=rotulos, y=participacao, marker_color=cores, text=[pct(v) for v in resumo["participacao"]],
        textposition="outside", hovertemplate="%{x}: %{y:.1f}%<extra></extra>",
    ), row=1, col=1)
    fig.add_trace(go.Bar(
        x=rotulos, y=mediana, marker_color=cores, text=[dec(v) for v in mediana],
        textposition="outside", hovertemplate="%{x}: R$ %{y:,.2f} mi<extra></extra>",
    ), row=1, col=2)
    _layout(fig, 400)
    fig.update_layout(showlegend=False, bargap=0.3)
    fig.update_yaxes(range=[0, participacao.max() * FOLGA_EIXO], row=1, col=1)
    fig.update_yaxes(range=[0, mediana.max() * FOLGA_EIXO], row=1, col=2)
    return fig


def fig_setor_regiao(df: pd.DataFrame) -> go.Figure:
    setor = etl.resumo_por(df, "setor_bndes").sort_values("valor_contratado")
    regiao = etl.resumo_por(df, "regiao").sort_values("valor_contratado")
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.22, subplot_titles=("Setor (%)", "Região (%)"))
    fig.add_trace(go.Bar(
        y=[setor_bndes.capitalize() for setor_bndes in setor["setor_bndes"]], x=setor["participacao"] * 100,
        orientation="h", marker_color=AZUL, text=[pct(v) for v in setor["participacao"]],
        textposition="outside", hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
    ), row=1, col=1)
    cores = [AZUL_CLARO if nome == etl.SEM_UF_UNICA else AZUL for nome in regiao["regiao"]]
    fig.add_trace(go.Bar(
        y=regiao["regiao"], x=regiao["participacao"] * 100, orientation="h", marker_color=cores,
        text=[pct(v) for v in regiao["participacao"]], textposition="outside",
        hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
    ), row=1, col=2)
    _layout(fig, 400)
    fig.update_layout(showlegend=False, bargap=0.3, margin={"t": 40, "r": 40, "l": 20, "b": 40})
    fig.update_xaxes(range=[0, setor["participacao"].max() * 100 * FOLGA_EIXO], row=1, col=1)
    fig.update_xaxes(range=[0, regiao["participacao"].max() * 100 * FOLGA_EIXO], row=1, col=2)
    return fig


def fig_dispersao(df: pd.DataFrame, amostra: int = etl.AMOSTRA_DISPERSAO) -> go.Figure:
    base = etl.reembolsaveis(df)
    base = base.sample(min(amostra, len(base)), random_state=etl.SEMENTE_AMOSTRA)
    fig = go.Figure()
    for rotulo, inovacao, cor in (
        ("Sem inovação", etl.INOVACAO_NAO, AZUL),
        ("Com inovação", etl.INOVACAO_SIM, LARANJA),
    ):
        grupo = base[base["inovacao"] == inovacao]
        fig.add_trace(go.Scatter(
            x=grupo["prazo_amortizacao_meses"], y=grupo[etl.COL_VALOR] / 1e6, mode="markers", name=rotulo,
            marker={"color": cor, "size": 6, "opacity": 0.5, "line": {"color": "white", "width": 0.5}},
            customdata=np.stack(
                [grupo["porte_do_cliente"].astype(str), grupo["setor_bndes"].astype(str), grupo["juros"]], axis=-1
            ),
            hovertemplate=(
                "Amortização: %{x} meses<br>Valor: R$ %{y:,.2f} mi<br>Porte: %{customdata[0]}"
                "<br>Setor: %{customdata[1]}<br>Juros: %{customdata[2]:.2f}%<extra></extra>"
            ),
        ))
    _layout(fig, 460)
    fig.update_xaxes(title="Prazo de amortização (meses)")
    marcas = [0.001, 0.01, 0.1, 1, 10, 100, 1000, 10000]
    fig.update_yaxes(
        title="Valor contratado (R$ milhões, escala log)", type="log", tickmode="array", tickvals=marcas,
        ticktext=[f"{marca:,}".replace(",", ".") if marca >= 1 else str(marca).replace(".", ",") for marca in marcas],
    )
    return fig


def fig_inovacao(df: pd.DataFrame) -> go.Figure:
    resumo = etl.resumo_inovacao(df).loc[[etl.INOVACAO_NAO, etl.INOVACAO_SIM]]
    rotulos = ["Sem inovação", "Com inovação"]
    paineis = (
        ("R$ mi", resumo["valor_mediano"] / 1e6, 1),
        ("Meses", resumo["amortizacao_mediana"], 0),
        ("Juros (%)", resumo["juros_mediano"], 2),
    )
    fig = make_subplots(rows=1, cols=3, subplot_titles=[titulo for titulo, _, _ in paineis])
    for coluna, (_, serie, casas) in enumerate(paineis, start=1):
        fig.add_trace(go.Bar(
            x=rotulos, y=serie.to_numpy(), marker_color=[AZUL, LARANJA], text=[dec(v, casas) for v in serie],
            textposition="outside", hovertemplate="%{x}: %{y:,.2f}<extra></extra>",
        ), row=1, col=coluna)
        fig.update_yaxes(range=[0, serie.max() * 1.25], row=1, col=coluna)
    _layout(fig, 380)
    fig.update_layout(showlegend=False, bargap=0.4)
    return fig


def est_distribuicao_valores(df: pd.DataFrame) -> plt.Figure:
    configurar_tema()
    fig, eixos = plt.subplots(1, 2, figsize=(12, 4.2))
    sns.histplot(df["log10_valor_contratado"].dropna(), bins=60, color=AZUL, ax=eixos[0])
    inferior, superior = etl.limites_outlier(df["log10_valor_contratado"])
    eixos[0].axvline(inferior, color=LARANJA, linestyle="--", linewidth=1.2, label="Limites de outliers (1,5 × IQR)")
    eixos[0].axvline(superior, color=LARANJA, linestyle="--", linewidth=1.2)
    eixos[0].set_xlabel("log10 do valor contratado por subcrédito (R$)")
    eixos[0].set_ylabel("Subcréditos")
    eixos[0].set_title("Distribuição do valor contratado (escala log)")
    eixos[0].legend(frameon=False, loc="upper left")
    presentes = set(df["porte_do_cliente"].astype(str))
    ordem = [porte.capitalize() for porte in etl.PORTES if porte in presentes]
    paleta = {porte.capitalize(): cor for porte, cor in RAMPA_PORTE.items()}
    sns.boxplot(
        data=df.assign(porte=df["porte_do_cliente"].astype(str).str.capitalize()),
        x="porte", y="log10_valor_contratado", order=ordem, palette=paleta, hue="porte", legend=False,
        ax=eixos[1], fliersize=2, linewidth=1,
    )
    eixos[1].set_xlabel("Porte do cliente")
    eixos[1].set_ylabel("log10 do valor contratado (R$)")
    eixos[1].set_title("Valor contratado por porte")
    fig.tight_layout()
    return fig


def est_lorenz(df: pd.DataFrame) -> plt.Figure:
    configurar_tema()
    por_cliente = etl.valor_por_cliente(df).sort_values()
    acumulado = np.concatenate([[0], np.cumsum(por_cliente.to_numpy()) / por_cliente.sum()])
    populacao = np.linspace(0, 1, len(acumulado))
    fig, eixo = plt.subplots(figsize=(6.2, 5))
    eixo.plot(populacao, acumulado, color=AZUL, linewidth=2.2, label="Clientes do BNDES")
    eixo.plot([0, 1], [0, 1], color=CINZA, linestyle="--", linewidth=1, label="Igualdade perfeita")
    eixo.fill_between(populacao, acumulado, populacao, color=AZUL, alpha=0.12)
    eixo.set_xlabel("Proporção acumulada de clientes (do menor para o maior)")
    eixo.set_ylabel("Proporção acumulada do valor contratado")
    eixo.text(0.05, 0.82, f"Gini = {dec(etl.gini(por_cliente), 2)}", fontsize=12, color=TEXTO)
    eixo.legend(loc="lower right", frameon=False)
    fig.tight_layout()
    return fig


def est_correlacao(df: pd.DataFrame) -> plt.Figure:
    configurar_tema()
    correlacao = etl.correlacao_spearman(etl.reembolsaveis(df))
    correlacao = correlacao.rename(index=ROTULOS_CORRELACAO, columns=ROTULOS_CORRELACAO)
    fig, eixo = plt.subplots(figsize=(6.2, 5))
    sns.heatmap(
        correlacao, annot=True, fmt=".2f", cmap=DIVERGENTE, vmin=-1, vmax=1, linewidths=2, linecolor="white",
        cbar_kws={"label": "Correlação de Spearman"}, ax=eixo,
    )
    eixo.set_title("Operações reembolsáveis")
    eixo.tick_params(axis="x", rotation=25)
    fig.tight_layout()
    return fig


def salvar_figura(fig: plt.Figure, nome: str, dpi: int = 200) -> Path:
    """Grava a figura em docs/assets e a fecha, para não acumular figuras abertas na memória."""
    PASTA_FIGURAS.mkdir(parents=True, exist_ok=True)
    caminho = PASTA_FIGURAS / nome
    fig.savefig(caminho, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return caminho
