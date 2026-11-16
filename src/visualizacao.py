"""Figuras do projeto: estáticas (Matplotlib/Seaborn) e interativas (Plotly)."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap
from plotly.subplots import make_subplots

from src import etl
from src.formatacao import dec, mes_ano, pct

RAIZ = Path(__file__).resolve().parents[1]
PASTA_FIGURAS = RAIZ / "docs" / "assets"

AZUL = "#2a78d6"
AZUL_CLARO = "#86b6ef"
AZUL_ESCURO = "#184f95"
LARANJA = "#eb6834"
CINZA = "#52514e"
GRADE = "#e5e7eb"
RAMPA_PORTE = {"MICRO": "#9ec5f4", "PEQUENA": "#5598e7", "MÉDIA": "#256abf", "GRANDE": "#104281"}
ORDEM_PORTE = ["MICRO", "PEQUENA", "MÉDIA", "GRANDE"]
DIVERGENTE = LinearSegmentedColormap.from_list("laranja_azul", [LARANJA, "#f0efec", AZUL])
FONTE = "-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif"

sns.set_theme(style="whitegrid", rc={"grid.color": GRADE, "axes.edgecolor": GRADE, "axes.labelcolor": CINZA})


def _layout(fig: go.Figure, altura: int = 420) -> go.Figure:
    fig.update_layout(
        height=altura,
        margin=dict(t=30, r=20, l=60, b=50),
        font=dict(family=FONTE, size=13, color="#1f2937"),
        plot_bgcolor="white",
        paper_bgcolor="white",
        separators=",.",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        hoverlabel=dict(font_family=FONTE),
    )
    fig.update_xaxes(gridcolor=GRADE, linecolor=GRADE, zeroline=False)
    fig.update_yaxes(gridcolor=GRADE, linecolor=GRADE, zeroline=False)
    return fig


def fig_evolucao_anual(df: pd.DataFrame) -> go.Figure:
    anual = etl.resumo_anual(df)
    anual["bi"] = anual["valor_contratado"] / 1e9
    parcial = anual["ano"] > etl.ANO_COMPLETO_FINAL
    cores = [AZUL_CLARO if p else AZUL for p in parcial]
    fig = go.Figure(go.Bar(
        x=anual["ano"], y=anual["bi"], marker_color=cores,
        customdata=np.stack([anual["contratos"], anual["subcreditos"]], axis=-1),
        hovertemplate="<b>%{x}</b><br>Valor contratado: R$ %{y:,.1f} bi<br>Contratos: %{customdata[0]:,.0f}"
                      "<br>Subcréditos: %{customdata[1]:,.0f}<extra></extra>",
    ))
    pico = anual.loc[anual["bi"].idxmax()]
    vale = anual[(anual["ano"] >= etl.ANO_INICIO_VALE) & (anual["ano"] <= etl.ANO_COMPLETO_FINAL)].nsmallest(1, "bi").iloc[0]
    for linha, texto, deslocamento in ((pico, "Pico", -25), (vale, "Vale", -60)):
        fig.add_annotation(x=linha["ano"], y=linha["bi"], text=f"{texto}: R$ {dec(linha['bi'])} bi",
                           showarrow=True, arrowhead=0, ay=deslocamento, font=dict(size=12, color=CINZA),
                           bgcolor="white")
    _layout(fig)
    fig.update_layout(showlegend=False, bargap=0.25)
    anos = list(range(2002, int(anual["ano"].max()) + 1, 2))
    rotulos = [f"{ano}*" if ano > etl.ANO_COMPLETO_FINAL else str(ano) for ano in anos]
    fig.update_xaxes(tickmode="array", tickvals=anos, ticktext=rotulos, title="Ano da contratação (* parcial)")
    fig.update_yaxes(title="Valor contratado (R$ bilhões)")
    return fig


def fig_serie_mensal(df: pd.DataFrame) -> go.Figure:
    mensal = etl.resumo_mensal(etl.anos_completos(df))
    mensal["bi"] = mensal["valor_contratado_reais"] / 1e9
    mensal["media_bi"] = mensal["media_movel_12m"] / 1e9
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=mensal["ano_mes"], y=mensal["bi"], name="Valor mensal", mode="lines",
                             line=dict(color=AZUL_CLARO, width=1.5),
                             hovertemplate="%{x|%m/%Y}<br>R$ %{y:,.1f} bi<extra>Valor mensal</extra>"))
    fig.add_trace(go.Scatter(x=mensal["ano_mes"], y=mensal["media_bi"], name="Média móvel de 12 meses",
                             mode="lines", line=dict(color=AZUL_ESCURO, width=2.5),
                             hovertemplate="%{x|%m/%Y}<br>R$ %{y:,.1f} bi<extra>Média móvel de 12 meses</extra>"))
    pico = mensal.loc[mensal["bi"].idxmax()]
    fig.add_annotation(x=pico["ano_mes"], y=pico["bi"], text=f"{mes_ano(pico['ano_mes'])}: R$ {dec(pico['bi'])} bi",
                       showarrow=True, arrowhead=0, ax=60, ay=0, font=dict(size=12, color=CINZA))
    _layout(fig)
    fig.update_xaxes(title="Mês da contratação", tickformat="%Y")
    fig.update_yaxes(title="Valor contratado (R$ bilhões)")
    return fig


def fig_sazonalidade_mensal(df: pd.DataFrame) -> go.Figure:
    por_mes = etl.anos_completos(df).groupby("mes", observed=True)["valor_contratado_reais"].sum()
    participacao = por_mes / por_mes.sum() * 100
    nomes = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    cores = [AZUL_ESCURO if mes >= 10 else AZUL_CLARO for mes in participacao.index]
    fig = go.Figure(go.Bar(
        x=nomes, y=participacao.values, marker_color=cores,
        hovertemplate="%{x}: %{y:.1f}% do valor contratado<extra></extra>",
    ))
    fig.add_hline(y=100 / 12, line_dash="dash", line_color=CINZA, line_width=1,
                  annotation_text="distribuição uniforme (8,3%)", annotation_position="top left",
                  annotation_font=dict(size=12, color=CINZA))
    _layout(fig, 380)
    fig.update_layout(showlegend=False, bargap=0.25)
    fig.update_yaxes(title="Participação no valor contratado (%)")
    return fig


def fig_porte(df: pd.DataFrame) -> go.Figure:
    resumo = etl.resumo_por(df, "porte_do_cliente").set_index("porte_do_cliente").loc[ORDEM_PORTE]
    rotulos = [p.capitalize() for p in resumo.index]
    cores = [RAMPA_PORTE[p] for p in resumo.index]
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Valor (%)", "Mediana (R$ mi)"))
    fig.add_trace(go.Bar(x=rotulos, y=resumo["participacao"] * 100, marker_color=cores,
                         text=[pct(v) for v in resumo["participacao"]], textposition="outside",
                         hovertemplate="%{x}: %{y:.1f}%<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Bar(x=rotulos, y=resumo["mediana_subcredito"] / 1e6, marker_color=cores,
                         text=[dec(v / 1e6) for v in resumo["mediana_subcredito"]],
                         textposition="outside",
                         hovertemplate="%{x}: R$ %{y:,.2f} mi<extra></extra>"), row=1, col=2)
    _layout(fig, 400)
    fig.update_layout(showlegend=False, bargap=0.3)
    fig.update_yaxes(range=[0, 112], row=1, col=1)
    fig.update_yaxes(range=[0, 13.5], row=1, col=2)
    return fig


def fig_setor_regiao(df: pd.DataFrame) -> go.Figure:
    setor = etl.resumo_por(df, "setor_bndes").sort_values("valor_contratado")
    regiao = etl.resumo_por(df, "regiao").sort_values("valor_contratado")
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.22,
                        subplot_titles=("Setor (%)", "Região (%)"))
    fig.add_trace(go.Bar(y=[s.capitalize() for s in setor["setor_bndes"]], x=setor["participacao"] * 100,
                         orientation="h", marker_color=AZUL,
                         text=[pct(v) for v in setor["participacao"]], textposition="outside",
                         hovertemplate="%{y}: %{x:.1f}%<extra></extra>"), row=1, col=1)
    cores = [AZUL_CLARO if r == etl.SEM_UF_UNICA else AZUL for r in regiao["regiao"]]
    fig.add_trace(go.Bar(y=regiao["regiao"], x=regiao["participacao"] * 100, orientation="h", marker_color=cores,
                         text=[pct(v) for v in regiao["participacao"]], textposition="outside",
                         hovertemplate="%{y}: %{x:.1f}%<extra></extra>"), row=1, col=2)
    _layout(fig, 400)
    fig.update_layout(showlegend=False, bargap=0.3, margin=dict(t=40, r=40, l=20, b=40))
    fig.update_xaxes(range=[0, 75], row=1, col=1)
    fig.update_xaxes(range=[0, 50], row=1, col=2)
    return fig


def fig_dispersao(df: pd.DataFrame, amostra: int = etl.AMOSTRA_DISPERSAO) -> go.Figure:
    base = etl.reembolsaveis(df)
    base = base.sample(min(amostra, len(base)), random_state=42)
    fig = go.Figure()
    for rotulo, valor_inovacao, cor in (("Sem inovação", "NÃO", AZUL), ("Com inovação", "SIM", LARANJA)):
        grupo = base[base["inovacao"] == valor_inovacao]
        fig.add_trace(go.Scatter(
            x=grupo["prazo_amortizacao_meses"], y=grupo["valor_contratado_reais"] / 1e6, mode="markers", name=rotulo,
            marker=dict(color=cor, size=6, opacity=0.5, line=dict(color="white", width=0.5)),
            customdata=np.stack([grupo["porte_do_cliente"].astype(str), grupo["setor_bndes"].astype(str),
                                 grupo["juros"]], axis=-1),
            hovertemplate="Amortização: %{x} meses<br>Valor: R$ %{y:,.2f} mi<br>Porte: %{customdata[0]}"
                          "<br>Setor: %{customdata[1]}<br>Juros: %{customdata[2]:.2f}%<extra></extra>"))
    _layout(fig, 460)
    fig.update_xaxes(title="Prazo de amortização (meses)")
    marcas = [0.001, 0.01, 0.1, 1, 10, 100, 1000, 10000]
    fig.update_yaxes(title="Valor contratado (R$ milhões, escala log)", type="log", tickmode="array", tickvals=marcas,
                     ticktext=[f"{m:,}".replace(",", ".") if m >= 1 else str(m).replace(".", ",") for m in marcas])
    return fig


def fig_inovacao(df: pd.DataFrame) -> go.Figure:
    base = etl.reembolsaveis(df)
    resumo = base.groupby("inovacao", observed=True).agg(
        valor=("valor_contratado_reais", "median"),
        prazo=("prazo_amortizacao_meses", "median"),
        juros=("juros", "median"),
    ).loc[["NÃO", "SIM"]]
    rotulos = ["Sem inovação", "Com inovação"]
    painéis = (("R$ mi", resumo["valor"] / 1e6, 1),
               ("Meses", resumo["prazo"], 0),
               ("Juros (%)", resumo["juros"], 2))
    fig = make_subplots(rows=1, cols=3, subplot_titles=[p[0] for p in painéis])
    for coluna, (_, serie, casas) in enumerate(painéis, start=1):
        fig.add_trace(go.Bar(x=rotulos, y=serie.values, marker_color=[AZUL, LARANJA],
                             text=[dec(v, casas) for v in serie.values], textposition="outside",
                             hovertemplate="%{x}: %{y:,.2f}<extra></extra>"), row=1, col=coluna)
        fig.update_yaxes(range=[0, serie.max() * 1.25], row=1, col=coluna)
    _layout(fig, 380)
    fig.update_layout(showlegend=False, bargap=0.4)
    return fig


def est_distribuicao_valores(df: pd.DataFrame) -> plt.Figure:
    fig, eixos = plt.subplots(1, 2, figsize=(12, 4.2))
    sns.histplot(df["log10_valor_contratado"].dropna(), bins=60, color=AZUL, ax=eixos[0])
    limites = etl.limites_outlier(df["log10_valor_contratado"])
    eixos[0].axvline(limites[0], color=LARANJA, linestyle="--", linewidth=1.2, label="Limites de outliers (1,5 × IQR)")
    eixos[0].axvline(limites[1], color=LARANJA, linestyle="--", linewidth=1.2)
    eixos[0].set_xlabel("log10 do valor contratado por subcrédito (R$)")
    eixos[0].set_ylabel("Subcréditos")
    eixos[0].set_title("Distribuição do valor contratado (escala log)")
    eixos[0].legend(frameon=False, loc="upper left")
    ordem = [p.capitalize() for p in ORDEM_PORTE if p in set(df["porte_do_cliente"].astype(str))]
    paleta = {p.capitalize(): cor for p, cor in RAMPA_PORTE.items()}
    sns.boxplot(data=df.assign(porte=df["porte_do_cliente"].astype(str).str.capitalize()),
                x="porte", y="log10_valor_contratado", order=ordem, palette=paleta, hue="porte", legend=False,
                ax=eixos[1], fliersize=2, linewidth=1)
    eixos[1].set_xlabel("Porte do cliente")
    eixos[1].set_ylabel("log10 do valor contratado (R$)")
    eixos[1].set_title("Valor contratado por porte")
    fig.tight_layout()
    return fig


def est_lorenz(df: pd.DataFrame) -> plt.Figure:
    por_cliente = df.groupby("cnpj", observed=True)["valor_contratado_reais"].sum().sort_values()
    acumulado = np.concatenate([[0], np.cumsum(por_cliente.values) / por_cliente.sum()])
    populacao = np.linspace(0, 1, len(acumulado))
    fig, eixo = plt.subplots(figsize=(6.2, 5))
    eixo.plot(populacao, acumulado, color=AZUL, linewidth=2.2, label="Clientes do BNDES")
    eixo.plot([0, 1], [0, 1], color=CINZA, linestyle="--", linewidth=1, label="Igualdade perfeita")
    eixo.fill_between(populacao, acumulado, populacao, color=AZUL, alpha=0.12)
    eixo.set_xlabel("Proporção acumulada de clientes (do menor para o maior)")
    eixo.set_ylabel("Proporção acumulada do valor contratado")
    eixo.text(0.05, 0.82, f"Gini = {dec(etl.gini(por_cliente), 2)}", fontsize=12, color="#1f2937")
    eixo.legend(loc="lower right", frameon=False)
    fig.tight_layout()
    return fig


def est_correlacao(df: pd.DataFrame) -> plt.Figure:
    nomes = {"valor_contratado_reais": "Valor contratado", "juros": "Juros",
             "prazo_carencia_meses": "Prazo de carência", "prazo_amortizacao_meses": "Prazo de amortização"}
    correlacao = etl.correlacao_spearman(etl.reembolsaveis(df)).rename(index=nomes, columns=nomes)
    fig, eixo = plt.subplots(figsize=(6.2, 5))
    sns.heatmap(correlacao, annot=True, fmt=".2f", cmap=DIVERGENTE, vmin=-1, vmax=1, linewidths=2,
                linecolor="white", cbar_kws={"label": "Correlação de Spearman"}, ax=eixo)
    eixo.set_title("Operações reembolsáveis")
    eixo.tick_params(axis="x", rotation=25)
    fig.tight_layout()
    return fig


def salvar_figura(fig: plt.Figure, nome: str, dpi: int = 200) -> Path:
    PASTA_FIGURAS.mkdir(parents=True, exist_ok=True)
    caminho = PASTA_FIGURAS / nome
    fig.savefig(caminho, dpi=dpi, bbox_inches="tight", facecolor="white")
    return caminho
