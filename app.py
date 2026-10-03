from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import pandas as pd
import seaborn as sns
import streamlit as st
from sqlalchemy import create_engine

st.set_page_config(
    page_title="Turismo no Brasil (2015-2024)",
    page_icon="🧳",
    layout="wide"
)

sns.set_theme(style="whitegrid")
COR = "#2a9d8f"
COR_DESTAQUE = "#e76f51"

BASE_DIR = Path(__file__).parent
CAMINHO_DADOS = BASE_DIR / "dados" / "simulacao_turismo_brasil.csv"
CAMINHO_BANCO = BASE_DIR / "database" / "turismo_brasil.sqlite"

NOMES_MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


@st.cache_data
def carregar_dados_csv():
    df = pd.read_csv(CAMINHO_DADOS)

    # Limpeza
    df = df.drop_duplicates().dropna()
    df["data"] = pd.to_datetime(df["data"])
    for coluna in ["regiao", "uf", "cidade", "nivel_temporada"]:
        df[coluna] = df[coluna].str.strip()

    # Variáveis derivadas
    df["ano_mes"] = df["data"].dt.to_period("M").dt.to_timestamp()
    df["nome_mes"] = df["mes"].apply(lambda m: NOMES_MESES[m - 1])
    df["turistas_estrangeiros_ajustado"] = df[["turistas", "turistas_estrangeiros"]].min(axis=1)
    df["pct_estrangeiros"] = df["turistas_estrangeiros_ajustado"] / df["turistas"] * 100
    df["receita_por_turista"] = df["faturamento_turismo"] / df["turistas"]
    return df


@st.cache_resource
def criar_banco_sqlite(df):
    CAMINHO_BANCO.parent.mkdir(exist_ok=True)
    engine = create_engine(f"sqlite:///{CAMINHO_BANCO}")
    df.to_sql("turismo", engine, if_exists="replace", index=False)
    return engine


def formatar_numero(valor):
    return f"{valor:,.0f}".replace(",", ".")


def formatar_moeda(valor):
    if abs(valor) >= 1e9:
        texto = f"{valor / 1e9:,.2f} bi"
    elif abs(valor) >= 1e6:
        texto = f"{valor / 1e6:,.2f} mi"
    else:
        texto = f"{valor:,.2f}"
    texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


def formatar_percentual(valor, casas=1):
    return f"{valor:.{casas}f}".replace(".", ",") + "%"


def eixo_milhoes(valor, posicao):
    return f"{valor / 1e6:.0f} mi"


def eixo_bilhoes(valor, posicao):
    return f"{valor / 1e9:.0f} bi"


df = carregar_dados_csv()
engine = criar_banco_sqlite(df)

st.title("🧳 Turismo no Brasil (2015-2024)")
st.write("""
**Problema:** como o turismo evoluiu entre 2015 e 2024 nas principais cidades brasileiras?
Onde estão o fluxo de turistas e o faturamento, existe alta temporada e quais variáveis
(ocupação hoteleira, gasto médio, eventos, temperatura) se relacionam com o resultado?

A base simulada reúne 37 cidades em 5 regiões, com registros mensais de turistas, ocupação
hoteleira, gasto médio, faturamento, eventos e temperatura. Use os filtros ao lado para explorar.
""")

# ---------------- SIDEBAR ----------------
st.sidebar.header("Filtros")

lista_anos = sorted(df["ano"].unique())
lista_regioes = sorted(df["regiao"].unique())
lista_ufs = sorted(df["uf"].unique())
lista_temporadas = ["Baixa", "Média", "Alta"]

ano_sel = st.sidebar.multiselect("Ano", options=lista_anos, default=lista_anos)
regiao_sel = st.sidebar.multiselect("Região", options=lista_regioes, default=lista_regioes)
uf_sel = st.sidebar.multiselect("UF", options=lista_ufs, default=lista_ufs)
temporada_sel = st.sidebar.multiselect("Nível de temporada", options=lista_temporadas, default=lista_temporadas)

df_filtrado = df[
    (df["ano"].isin(ano_sel))
    & (df["regiao"].isin(regiao_sel))
    & (df["uf"].isin(uf_sel))
    & (df["nivel_temporada"].isin(temporada_sel))
]

if df_filtrado.empty:
    st.warning("Nenhum registro encontrado para os filtros selecionados. Ajuste os filtros na barra lateral.")
    st.stop()

st.sidebar.caption(f"{formatar_numero(len(df_filtrado))} de {formatar_numero(len(df))} registros selecionados.")

# ---------------- KPIs ----------------
st.subheader("Indicadores-chave de desempenho")

total_turistas = df_filtrado["turistas"].sum()
total_faturamento = df_filtrado["faturamento_turismo"].sum()
gasto_ponderado = (df_filtrado["turistas"] * df_filtrado["gasto_medio"]).sum() / total_turistas
ocupacao_media = df_filtrado["ocupacao_hoteleira"].mean()
pct_estrangeiros = df_filtrado["turistas_estrangeiros_ajustado"].sum() / total_turistas * 100

turistas_por_ano = df_filtrado.groupby("ano")["turistas"].sum()
if len(turistas_por_ano) > 1:
    variacao_fluxo = (turistas_por_ano.iloc[-1] / turistas_por_ano.iloc[0] - 1) * 100
    delta_fluxo = f"{formatar_percentual(variacao_fluxo)} ({turistas_por_ano.index[0]} → {turistas_por_ano.index[-1]})"
else:
    delta_fluxo = None

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Turistas", formatar_numero(total_turistas), delta=delta_fluxo)
col2.metric("Faturamento", formatar_moeda(total_faturamento))
col3.metric("Gasto médio por turista", formatar_moeda(gasto_ponderado))
col4.metric("Ocupação hoteleira média", formatar_percentual(ocupacao_media))
col5.metric("Turistas estrangeiros", formatar_percentual(pct_estrangeiros))

st.divider()

# ---------------- TABS ----------------
aba1, aba2, aba3, aba4, aba5, aba6, aba7, aba8 = st.tabs([
    "Visão geral",
    "Regiões e UFs",
    "Cidades",
    "Sazonalidade",
    "Série temporal",
    "Correlações",
    "Consulta SQL",
    "Dados"
])

with aba1:
    st.subheader("Evolução anual")

    resumo_ano = (
        df_filtrado.groupby("ano")
        .agg(turistas=("turistas", "sum"), faturamento=("faturamento_turismo", "sum"))
        .reset_index()
    )

    col_a, col_b = st.columns(2)

    with col_a:
        fig, ax = plt.subplots(figsize=(7, 4))
        sns.barplot(data=resumo_ano, x="ano", y="turistas", color=COR, ax=ax)
        ax.set_title("Turistas por ano")
        ax.set_xlabel("Ano")
        ax.set_ylabel("Turistas")
        ax.yaxis.set_major_formatter(mtick.FuncFormatter(eixo_milhoes))
        plt.tight_layout()
        st.pyplot(fig, width="stretch")

    with col_b:
        fig, ax = plt.subplots(figsize=(7, 4))
        sns.lineplot(data=resumo_ano, x="ano", y="faturamento", marker="o", color=COR_DESTAQUE, ax=ax)
        ax.set_title("Faturamento por ano")
        ax.set_xlabel("Ano")
        ax.set_ylabel("Faturamento (R$)")
        ax.yaxis.set_major_formatter(mtick.FuncFormatter(eixo_bilhoes))
        ax.set_xticks(resumo_ano["ano"])
        plt.tight_layout()
        st.pyplot(fig, width="stretch")

    ano_pico = resumo_ano.loc[resumo_ano["turistas"].idxmax(), "ano"]
    ano_receita = resumo_ano.loc[resumo_ano["faturamento"].idxmax(), "ano"]
    st.success(f"No recorte filtrado, o maior fluxo de turistas foi em {ano_pico} e o maior faturamento em {ano_receita}.")
    st.info("""
    Na base completa o fluxo é estável: de 2015 a 2024 o total de turistas varia cerca de +3%, e 2020
    recua apenas 4% em relação a 2019, sem o choque que a pandemia causou no turismo real. O comportamento
    indica uma base simulada, sem tendência forte de crescimento ou de queda.
    """)

with aba2:
    st.subheader("Comparação entre regiões e UFs")

    resumo_regiao = (
        df_filtrado.groupby("regiao")
        .agg(faturamento=("faturamento_turismo", "sum"), cidades=("cidade", "nunique"))
        .reset_index()
    )
    resumo_regiao["faturamento_por_cidade"] = resumo_regiao["faturamento"] / resumo_regiao["cidades"]
    resumo_regiao = resumo_regiao.sort_values("faturamento", ascending=False)

    col_a, col_b = st.columns(2)

    with col_a:
        fig, ax = plt.subplots(figsize=(7, 4))
        sns.barplot(data=resumo_regiao, x="regiao", y="faturamento", color=COR, ax=ax)
        ax.set_title("Faturamento total por região")
        ax.set_xlabel("Região")
        ax.set_ylabel("Faturamento (R$)")
        ax.yaxis.set_major_formatter(mtick.FuncFormatter(eixo_bilhoes))
        plt.tight_layout()
        st.pyplot(fig, width="stretch")

    with col_b:
        fig, ax = plt.subplots(figsize=(7, 4))
        sns.barplot(data=resumo_regiao, x="regiao", y="faturamento_por_cidade", color=COR_DESTAQUE, ax=ax)
        ax.set_title("Faturamento médio por cidade em cada região")
        ax.set_xlabel("Região")
        ax.set_ylabel("Faturamento por cidade (R$)")
        ax.yaxis.set_major_formatter(mtick.FuncFormatter(eixo_bilhoes))
        plt.tight_layout()
        st.pyplot(fig, width="stretch")

    receita_uf = (
        df_filtrado.groupby("uf")["faturamento_turismo"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )

    fig, ax = plt.subplots(figsize=(12, 4))
    sns.barplot(data=receita_uf, x="uf", y="faturamento_turismo", color=COR, ax=ax)
    ax.set_title("Faturamento por UF")
    ax.set_xlabel("UF")
    ax.set_ylabel("Faturamento (R$)")
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(eixo_bilhoes))
    plt.tight_layout()
    st.pyplot(fig, width="stretch")

    regiao_lider = resumo_regiao.iloc[0]
    participacao = regiao_lider["faturamento"] / resumo_regiao["faturamento"].sum() * 100
    st.success(
        f"A região líder é {regiao_lider['regiao']}, com {formatar_moeda(regiao_lider['faturamento'])} "
        f"({formatar_percentual(participacao)} do faturamento filtrado) e {regiao_lider['cidades']} cidades."
    )
    st.info("""
    O Sudeste lidera o faturamento total (cerca de 35%) principalmente por reunir 13 das 37 cidades da base.
    Quando o faturamento é dividido pelo número de cidades, as regiões ficam muito próximas, com diferença
    de poucos pontos percentuais. A liderança vem do tamanho da amostra, não de um desempenho superior por cidade.
    """)

with aba3:
    st.subheader("Ranking de cidades")

    ranking_cidades = (
        df_filtrado.groupby("cidade")["turistas"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
    )

    fig, ax = plt.subplots(figsize=(12, 5))
    sns.barplot(data=ranking_cidades, x="turistas", y="cidade", color=COR, ax=ax)
    ax.set_title("Top 10 cidades por número de turistas")
    ax.set_xlabel("Turistas")
    ax.set_ylabel("Cidade")
    ax.xaxis.set_major_formatter(mtick.FuncFormatter(eixo_milhoes))
    plt.tight_layout()
    st.pyplot(fig, width="stretch")

    tabela_cidades = (
        df_filtrado.groupby(["cidade", "uf", "regiao"])
        .agg(
            turistas=("turistas", "sum"),
            faturamento=("faturamento_turismo", "sum"),
            ocupacao_media=("ocupacao_hoteleira", "mean"),
            gasto_medio=("gasto_medio", "mean")
        )
        .round(2)
        .sort_values("turistas", ascending=False)
        .reset_index()
    )
    st.dataframe(tabela_cidades, width="stretch", hide_index=True)

    cidade_lider = ranking_cidades.iloc[0]
    st.success(f"A cidade mais visitada no recorte é {cidade_lider['cidade']}, com {formatar_numero(cidade_lider['turistas'])} turistas.")
    st.info("""
    Os totais por cidade são muito parecidos entre si: não há uma metrópole que concentre o fluxo, e as
    posições do ranking mudam com os filtros de ano e região. Use a tabela para comparar ocupação e gasto médio.
    """)

with aba4:
    st.subheader("Sazonalidade")

    media_mensal = (
        df_filtrado.groupby(["mes", "nome_mes"])["turistas"]
        .mean()
        .reset_index()
    )
    media_mensal["indice_sazonal"] = media_mensal["turistas"] / media_mensal["turistas"].mean() * 100

    col_a, col_b = st.columns(2)

    with col_a:
        fig, ax = plt.subplots(figsize=(7, 4))
        sns.barplot(data=media_mensal, x="nome_mes", y="indice_sazonal", color=COR, ax=ax)
        ax.axhline(100, color=COR_DESTAQUE, linestyle="--", label="Média = 100")
        ax.set_title("Índice sazonal de turistas por mês")
        ax.set_xlabel("Mês")
        ax.set_ylabel("Índice (média = 100)")
        ax.legend()
        plt.tight_layout()
        st.pyplot(fig, width="stretch")

    with col_b:
        fig, ax = plt.subplots(figsize=(7, 4))
        sns.boxplot(data=df_filtrado, x="nivel_temporada", y="turistas", order=lista_temporadas, color=COR, ax=ax)
        ax.set_title("Turistas por nível de temporada informado")
        ax.set_xlabel("Nível de temporada")
        ax.set_ylabel("Turistas")
        ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda v, p: f"{v / 1e3:.0f} mil"))
        plt.tight_layout()
        st.pyplot(fig, width="stretch")

    mes_maior = media_mensal.loc[media_mensal["indice_sazonal"].idxmax()]
    mes_menor = media_mensal.loc[media_mensal["indice_sazonal"].idxmin()]
    st.success(
        f"O índice sazonal vai de {mes_menor['indice_sazonal']:.0f} ({mes_menor['nome_mes']}) "
        f"a {mes_maior['indice_sazonal']:.0f} ({mes_maior['nome_mes']}) no recorte filtrado."
    )
    st.info("""
    Na base completa o índice sazonal fica entre 94 e 104, uma amplitude pequena: não existe uma alta temporada
    bem definida. A coluna nivel_temporada também não se relaciona com o número de turistas, pois as caixas de
    Baixa, Média e Alta têm distribuições praticamente iguais.
    """)

with aba5:
    st.subheader("Série temporal mensal")

    serie = (
        df_filtrado.groupby("ano_mes")["turistas"]
        .sum()
        .reset_index()
        .sort_values("ano_mes")
    )
    serie["media_movel_12m"] = serie["turistas"].rolling(window=12).mean()

    fig, ax = plt.subplots(figsize=(12, 4))
    sns.lineplot(data=serie, x="ano_mes", y="turistas", color=COR, alpha=0.6, label="Turistas no mês", ax=ax)
    sns.lineplot(data=serie, x="ano_mes", y="media_movel_12m", color=COR_DESTAQUE, linewidth=2.5, label="Média móvel de 12 meses", ax=ax)
    ax.set_title("Turistas por mês e média móvel de 12 meses")
    ax.set_xlabel("Mês")
    ax.set_ylabel("Turistas")
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(eixo_milhoes))
    plt.tight_layout()
    st.pyplot(fig, width="stretch")

    variacao_anual = (
        df_filtrado.groupby("ano")["turistas"]
        .sum()
        .pct_change()
        .mul(100)
        .dropna()
        .reset_index(name="variacao")
    )

    if variacao_anual.empty:
        st.write("Selecione mais de um ano para ver a variação anual.")
    else:
        fig, ax = plt.subplots(figsize=(12, 4))
        sns.barplot(data=variacao_anual, x="ano", y="variacao", color=COR, ax=ax)
        ax.axhline(0, color="black", linewidth=0.8)
        ax.set_title("Variação anual do total de turistas (%)")
        ax.set_xlabel("Ano")
        ax.set_ylabel("Variação (%)")
        plt.tight_layout()
        st.pyplot(fig, width="stretch")

    st.success(f"O recorte tem {len(serie)} meses; o pico mensal foi de {formatar_numero(serie['turistas'].max())} turistas.")
    st.info("""
    A média móvel de 12 meses fica praticamente horizontal, o que confirma a estabilidade do fluxo. As variações
    anuais ficam em poucos pontos percentuais para cima ou para baixo, sem um período de crise ou de recuperação marcante.
    """)

with aba6:
    st.subheader("Correlação estatística")

    colunas_corr = [
        "turistas",
        "turistas_estrangeiros_ajustado",
        "ocupacao_hoteleira",
        "gasto_medio",
        "faturamento_turismo",
        "eventos_realizados",
        "temperatura_media"
    ]
    matriz_corr = df_filtrado[colunas_corr].corr()

    col_a, col_b = st.columns(2)

    with col_a:
        fig, ax = plt.subplots(figsize=(7, 5))
        sns.heatmap(matriz_corr, annot=True, fmt=".2f", cmap="coolwarm", vmin=-1, vmax=1, ax=ax)
        ax.set_title("Matriz de correlação")
        plt.tight_layout()
        st.pyplot(fig, width="stretch")

    with col_b:
        amostra = df_filtrado.sample(min(len(df_filtrado), 1000), random_state=1)
        fig, ax = plt.subplots(figsize=(7, 5))
        sns.scatterplot(data=amostra, x="turistas", y="faturamento_turismo", alpha=0.4, color=COR, ax=ax)
        ax.set_title("Turistas x faturamento (amostra de até 1.000 registros)")
        ax.set_xlabel("Turistas")
        ax.set_ylabel("Faturamento (R$)")
        ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda v, p: f"{v / 1e3:.0f} mil"))
        ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda v, p: f"{v / 1e6:.0f} mi"))
        plt.tight_layout()
        st.pyplot(fig, width="stretch")

    corr_fat = matriz_corr["faturamento_turismo"].drop("faturamento_turismo")
    variavel_forte = corr_fat.abs().idxmax()
    st.success(
        f"A maior correlação com o faturamento é com {variavel_forte}: "
        f"{corr_fat[variavel_forte]:.2f}".replace(".", ",") + "."
    )
    st.info("""
    Na base completa todas as correlações ficam próximas de zero (entre -0,03 e +0,03). Mais turistas, maior ocupação
    ou mais eventos não aparecem associados a maior faturamento, e o faturamento não corresponde a turistas x gasto
    médio. Os valores parecem sorteados de forma independente, o que limita conclusões causais.
    """)

with aba7:
    st.subheader("Consulta SQL no banco SQLite")
    st.write("A tabela `turismo` foi gravada em `database/turismo_brasil.sqlite` com SQLAlchemy. A consulta abaixo usa a base completa, sem os filtros.")

    consulta = """
    SELECT ano,
           regiao,
           SUM(turistas) AS turistas,
           ROUND(SUM(faturamento_turismo) / 1000000000.0, 2) AS faturamento_bi,
           ROUND(AVG(ocupacao_hoteleira), 1) AS ocupacao_media
    FROM turismo
    GROUP BY ano, regiao
    ORDER BY ano, faturamento_bi DESC
    """
    resultado_sql = pd.read_sql(consulta, engine)
    st.dataframe(resultado_sql, width="stretch", hide_index=True)
    st.code(consulta, language="sql")

    st.success(f"A consulta retornou {len(resultado_sql)} linhas (10 anos x 5 regiões).")
    st.info("""
    O mesmo resultado poderia ser obtido com groupby no Pandas. O banco mostra a persistência dos dados tratados
    e permite consultas em SQL sobre a mesma base usada nos gráficos.
    """)

with aba8:
    st.subheader("Dados filtrados")

    colunas_tabela = [
        "ano", "mes", "regiao", "uf", "cidade", "turistas", "turistas_estrangeiros_ajustado",
        "ocupacao_hoteleira", "gasto_medio", "faturamento_turismo", "eventos_realizados",
        "temperatura_media", "nivel_temporada"
    ]
    st.dataframe(df_filtrado[colunas_tabela], width="stretch", hide_index=True)
    st.download_button(
        "Baixar CSV filtrado",
        data=df_filtrado[colunas_tabela].to_csv(index=False).encode("utf-8"),
        file_name="turismo_filtrado.csv",
        mime="text/csv"
    )

    sem_ajuste = (df_filtrado["turistas_estrangeiros"] > df_filtrado["turistas"]).sum()
    st.success(f"{formatar_numero(len(df_filtrado))} registros exibidos; {formatar_numero(sem_ajuste)} deles tiveram turistas estrangeiros ajustados.")
    st.info("""
    Na base completa, 260 registros trazem mais turistas estrangeiros do que turistas totais, o que é inconsistente.
    A coluna original foi mantida e os indicadores usam turistas_estrangeiros_ajustado, limitado ao total de turistas.
    """)

st.divider()
st.subheader("Conclusão executiva")
st.write("""
O turismo da base é estável entre 2015 e 2024, com fluxo anual quase constante (cerca de +3% no período) e queda
de apenas 4% em 2020. Não há alta temporada definida: o índice sazonal fica próximo de 100 em todos os meses.

O Sudeste concentra cerca de 35% do faturamento por reunir 13 das 37 cidades; na média por cidade, as regiões se
equivalem. As correlações entre fluxo, ocupação, gasto, eventos, temperatura e faturamento são praticamente nulas,
então os dados simulados não sustentam relações causais.

**Recomendação:** tratar a base como material de treino de análise e visualização. Em dados reais, vale incluir
sazonalidade e impactos externos, como a pandemia, antes de usar os indicadores em decisões.
""")
