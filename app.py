import copy
import io
import re
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
import plotly.express as px
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
CORES_REGIAO = {
    "Norte": "#2a9d8f",
    "Nordeste": "#e76f51",
    "Centro-Oeste": "#e9c46a",
    "Sudeste": "#264653",
    "Sul": "#8ab17d"
}

BASE_DIR = Path(__file__).parent
CAMINHO_DADOS = BASE_DIR / "dados" / "simulacao_turismo_brasil.csv"
CAMINHO_BANCO = BASE_DIR / "database" / "turismo_brasil.sqlite"

NOMES_MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

NOMES_COLUNAS = {
    "ano": "Ano",
    "mes": "Mês",
    "data": "Data",
    "regiao": "Região",
    "uf": "UF",
    "cidade": "Cidade",
    "turistas": "Turistas",
    "turistas_estrangeiros": "Turistas estrangeiros",
    "turistas_estrangeiros_ajustado": "Turistas estrangeiros (ajustado)",
    "ocupacao_hoteleira": "Ocupação hoteleira (%)",
    "gasto_medio": "Gasto médio (R$)",
    "faturamento_turismo": "Faturamento (R$)",
    "eventos_realizados": "Eventos realizados",
    "temperatura_media": "Temperatura média (°C)",
    "nivel_temporada": "Nível de temporada",
    "pct_estrangeiros": "Estrangeiros (%)",
    "receita_por_turista": "Receita por turista (R$)",
    "faturamento": "Faturamento (R$)",
    "ocupacao_media": "Ocupação média (%)"
}

CAPITAIS = ["São Paulo", "Rio de Janeiro", "Brasília", "Salvador", "Fortaleza"]

COORDENADAS = {
    "Manaus": (-3.119, -60.022), "Belém": (-1.456, -48.502), "Santarém": (-2.443, -54.708),
    "Porto Velho": (-8.761, -63.900), "Palmas": (-10.184, -48.333),
    "Salvador": (-12.971, -38.501), "Feira de Santana": (-12.267, -38.967),
    "Recife": (-8.054, -34.881), "Jaboatão dos Guararapes": (-8.113, -35.015),
    "Fortaleza": (-3.732, -38.527), "Juazeiro do Norte": (-7.213, -39.315),
    "São Luís": (-2.530, -44.303), "João Pessoa": (-7.115, -34.863),
    "Brasília": (-15.794, -47.882), "Goiânia": (-16.686, -49.264),
    "Aparecida de Goiânia": (-16.823, -49.247), "Cuiabá": (-15.601, -56.097),
    "Campo Grande": (-20.469, -54.620),
    "São Paulo": (-23.550, -46.633), "Campinas": (-22.909, -47.063),
    "Ribeirão Preto": (-21.177, -47.810), "Rio de Janeiro": (-22.907, -43.173),
    "Niterói": (-22.883, -43.104), "Nova Iguaçu": (-22.759, -43.451),
    "Petrópolis": (-22.505, -43.179), "Belo Horizonte": (-19.917, -43.935),
    "Uberlândia": (-18.919, -48.277), "Juiz de Fora": (-21.764, -43.350),
    "Vitória": (-20.315, -40.312), "Vila Velha": (-20.329, -40.292),
    "Serra": (-20.121, -40.307), "Curitiba": (-25.428, -49.273),
    "Londrina": (-23.310, -51.162), "Florianópolis": (-27.595, -48.548),
    "Joinville": (-26.304, -48.846), "Porto Alegre": (-30.035, -51.218),
    "Caxias do Sul": (-29.168, -51.179)
}

st.markdown("""
<style>
.block-container { padding-top: 3.5rem; max-width: 1400px; }
[data-testid="stMetricValue"] { font-size: 1.55rem; }
[data-testid="stMetricValue"] > div { overflow: visible; text-overflow: clip; }
[data-testid="stMetricLabel"] p { white-space: normal; }
span[data-baseweb="tag"], span[data-tag] { background-color: #2a9d8f !important; }
@keyframes subir { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: none; } }
@keyframes aparecer { from { opacity: 0; } to { opacity: 1; } }
.hero {
    background: linear-gradient(120deg, #264653 0%, #2a9d8f 60%, #e9c46a 140%);
    border-radius: 18px; padding: 1.4rem 2.2rem 1.6rem; margin-bottom: 1.2rem; color: #fff;
    box-shadow: 0 10px 30px rgba(38, 70, 83, .25); animation: subir .7s ease both;
}
.hero p { margin: 0; font-size: 1.1rem; opacity: .95; }
.hero .tag {
    display: inline-block; margin: .9rem .4rem 0 0; padding: .2rem .85rem; border-radius: 999px;
    background: rgba(255, 255, 255, .18); font-size: .85rem;
}
[data-testid="stMetric"] {
    background: rgba(42, 157, 143, .08); border: 1px solid rgba(42, 157, 143, .28);
    border-left: 5px solid #2a9d8f; border-radius: 14px; padding: 14px 16px;
    animation: subir .6s ease both; transition: transform .2s ease, box-shadow .2s ease;
}
[data-testid="stColumn"]:nth-child(2) [data-testid="stMetric"] { animation-delay: .08s; }
[data-testid="stColumn"]:nth-child(3) [data-testid="stMetric"] { animation-delay: .16s; }
[data-testid="stColumn"]:nth-child(4) [data-testid="stMetric"] { animation-delay: .24s; }
[data-testid="stColumn"]:nth-child(5) [data-testid="stMetric"] { animation-delay: .32s; }
[data-testid="stMetric"]:hover { transform: translateY(-5px); box-shadow: 0 10px 24px rgba(42, 157, 143, .28); }
button[data-baseweb="tab"], [data-testid="stTab"] { border-radius: 10px 10px 0 0; transition: background .2s ease; }
button[data-baseweb="tab"]:hover, [data-testid="stTab"]:hover { background: rgba(42, 157, 143, .12); }
button[data-baseweb="tab"][aria-selected="true"], [data-testid="stTab"][aria-selected="true"] { background: rgba(42, 157, 143, .18); }
[data-testid="stTab"][aria-selected="true"], [data-testid="stTab"][aria-selected="true"] p { color: #1f7a6f !important; }
[data-testid="stTab"]:hover:not([aria-selected="true"]), [data-testid="stTab"]:hover:not([aria-selected="true"]) p { color: #31333f !important; }
[data-testid="stTab"]:focus, [data-testid="stTab"]:focus-visible, [data-testid="stTab"]:active {
    outline: none !important; box-shadow: none !important; border-color: transparent !important;
}
.react-aria-SelectionIndicator { background-color: #2a9d8f !important; }
[data-testid="stSidebar"] { border-right: 1px solid rgba(42, 157, 143, .25); }
[data-testid="stAlert"] { border-radius: 12px; animation: subir .5s ease both; }
</style>
""", unsafe_allow_html=True)

ESCALONADO_CSS = ""
for posicao in range(2, 41):
    ESCALONADO_CSS += (
        f'[class*="st-key-anim-bar"][class*="-plotly"] .barlayer .point:nth-child({posicao}) path '
        f'{{ animation-delay: {(posicao - 1) * 0.06:.2f}s; }}\n'
    )
for posicao in range(2, 9):
    ESCALONADO_CSS += (
        f'[class*="st-key-anim-bar"][class*="-plotly"] .barlayer .trace:nth-child({posicao}) .point path '
        f'{{ animation-delay: {(posicao - 1) * 0.12:.2f}s; }}\n'
    )

st.markdown("""
<style>
@keyframes crescer-v { from { transform: scaleY(0); } to { transform: scaleY(1); } }
@keyframes crescer-h { from { transform: scaleX(0); } to { transform: scaleX(1); } }
@keyframes revelar-direita { from { clip-path: inset(0 100% 0 0); } to { clip-path: inset(0 0 0 0); } }
@keyframes surgir { from { opacity: 0; } to { opacity: 1; } }

[class*="st-key-anim-barv"][class*="-plotly"] .barlayer .point path {
    transform-box: fill-box; transform-origin: 50% 100%;
    animation: crescer-v .9s cubic-bezier(.22, 1, .36, 1) backwards;
}
[class*="st-key-anim-barh"][class*="-plotly"] .barlayer .point path {
    transform-box: fill-box; transform-origin: 0% 50%;
    animation: crescer-h .9s cubic-bezier(.22, 1, .36, 1) backwards;
}
[class*="st-key-anim-linha"][class*="-plotly"] .scatterlayer { animation: revelar-direita 1.1s ease-out backwards; }
[class*="st-key-anim-pop"][class*="-plotly"] .scatterlayer .points { animation: surgir .9s ease-out backwards; }
[class*="st-key-anim-calor"][class*="-plotly"] .heatmaplayer { animation: surgir .9s ease-out backwards; }
[class*="st-key-anim-arvore"][class*="-plotly"] .slice { animation: surgir .9s ease-out backwards; }

.fig-svg svg { width: 100%; height: auto; display: block; }
.fig-svg [id="anim-barv"] path {
    transform-box: fill-box; transform-origin: 50% 100%;
    animation: crescer-v .9s cubic-bezier(.22, 1, .36, 1) backwards;
    animation-delay: calc(var(--i, 1) * .06s - .06s);
}
.fig-svg [id="anim-barh"] path {
    transform-box: fill-box; transform-origin: 0% 50%;
    animation: crescer-h .9s cubic-bezier(.22, 1, .36, 1) backwards;
    animation-delay: calc(var(--i, 1) * .06s - .06s);
}
.fig-svg [id="anim-linha"] { animation: revelar-direita 1.1s ease-out backwards; }
.fig-svg [id="anim-caixa"], .fig-svg [id="anim-pop"] {
    animation: surgir .9s ease-out backwards;
    animation-delay: calc(var(--i, 1) * .03s - .03s);
}

@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation: none !important; transition: none !important; }
}
""" + ESCALONADO_CSS + "</style>", unsafe_allow_html=True)


def mostrar_figura(fig, chave, tipo):
    for ax in fig.axes:
        if tipo in ("barv", "barh"):
            artistas = list(ax.patches)
        elif tipo == "linha":
            artistas = list(ax.lines)
        elif tipo == "caixa":
            artistas = list(ax.patches) + list(ax.lines)
        else:
            artistas = list(ax.collections)
        for artista in artistas:
            artista.set_gid(f"anim-{tipo}")

    buffer = io.StringIO()
    with plt.rc_context({"svg.hashsalt": chave}):
        fig.savefig(buffer, format="svg")
    plt.close(fig)

    svg = buffer.getvalue()
    svg = svg[svg.index("<svg"):]
    svg = re.sub(r"<style.*?</style>", "", svg, flags=re.S)
    svg = re.sub(r"<metadata>.*?</metadata>", "", svg, flags=re.S)
    svg = svg.replace("DejaVuSans", f"DV{abs(hash(chave))}")

    contador = [0]

    def numerar(correspondencia):
        contador[0] += 1
        return f'id="anim-{tipo}" style="--i:{contador[0]}"'

    svg = re.sub(f'id="anim-{tipo}"', numerar, svg)
    svg = re.sub(r">\s+<", "><", svg)
    st.markdown(f'<div class="fig-svg">{svg}</div>', unsafe_allow_html=True)


def mostrar_plotly(fig, chave, tipo, altura=420, ano_ms=600, voltar=True):
    with st.container(key=f"anim-{tipo}-plotly-{chave}-{ID_FILTRO}"):
        st.plotly_chart(ajustar_grafico(fig, altura, ano_ms, voltar), width="stretch")


def formatar_dica(fig, modelo):
    fig.update_traces(hovertemplate=modelo)
    for quadro in fig.frames:
        for traco in quadro.data:
            traco.hovertemplate = modelo


@st.cache_resource
def montar_corrida(faturamento_regiao_ano, modo_corrida):
    dados_corrida = (
        faturamento_regiao_ano
        .reset_index()
        .melt(id_vars="ano", var_name="regiao", value_name="faturamento")
    )
    dados_corrida["rotulo"] = dados_corrida["faturamento"].apply(formatar_moeda)

    fig = px.bar(
        dados_corrida,
        x="faturamento",
        y="regiao",
        color="regiao",
        orientation="h",
        text="rotulo",
        animation_frame="ano",
        animation_group="regiao",
        range_x=[0, dados_corrida["faturamento"].max() * 1.25],
        color_discrete_map=CORES_REGIAO,
        title=f"{modo_corrida} por região (clique em ▶ ou arraste o ano)",
        labels={"faturamento": "Faturamento (R$)", "regiao": "Região"}
    )
    fig.update_yaxes(categoryorder="total ascending")
    formatar_dica(fig, "<b>%{y}</b><br>Faturamento: R$ %{x:,.0f}<extra></extra>")
    fig.update_traces(textposition="outside", cliponaxis=False)
    for quadro in fig.frames:
        for barra in quadro.data:
            barra.textposition = "outside"
            barra.cliponaxis = False
    fig.update_layout(showlegend=False)
    ajustar_grafico(fig, 430)
    return fig


def corrida_regioes():
    st.markdown("#### Corrida das regiões: barras horizontais animadas")
    faturamento_ano = df_filtrado.pivot_table(
        index="ano",
        columns="regiao",
        values="faturamento_turismo",
        aggfunc="sum",
        fill_value=0
    )

    aba_acumulado, aba_ano = st.tabs(["Faturamento acumulado", "Faturamento do ano"])
    with aba_acumulado:
        fig = montar_corrida(faturamento_ano.cumsum(), "Faturamento acumulado")
        mostrar_plotly(fig, "corrida-acumulado", "barh", 430)
    with aba_ano:
        fig = montar_corrida(faturamento_ano, "Faturamento do ano")
        mostrar_plotly(fig, "corrida-ano", "barh", 430)


@st.cache_data
def carregar_dados_csv():
    df = pd.read_csv(CAMINHO_DADOS)

    df = df.drop_duplicates().dropna()
    df["data"] = pd.to_datetime(df["data"])
    for coluna in ["regiao", "uf", "cidade", "nivel_temporada"]:
        df[coluna] = df[coluna].str.strip()

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


def ajustar_grafico(fig, altura=420, ano_ms=600, voltar=True):
    margem_topo = fig.layout.margin.t if fig.layout.margin.t else 60
    fig.update_layout(height=altura, margin=dict(t=margem_topo, l=10, r=10, b=10), legend_title_text="", separators=",.")
    for controle in fig.layout.sliders:
        controle.currentvalue.prefix = ""
    if fig.layout.updatemenus:
        # ano_ms = tempo entre dois anos; as pausas intercaladas completam esse tempo
        quadro_ms = 300 if ano_ms <= 600 else 500
        fig.layout.updatemenus[0].buttons[0].args[1]["frame"]["duration"] = quadro_ms
        fig.layout.updatemenus[0].buttons[0].args[1]["transition"]["duration"] = quadro_ms
        fig.layout.updatemenus[0].buttons[0].args[1]["transition"]["easing"] = "cubic-in-out"
        intercalar_pausas(fig, ano_ms // quadro_ms - 1, voltar, 3000 // quadro_ms - 1)
    limitar_zoom(fig)
    return fig


def limitar_zoom(fig):
    for nome, atributo in (("xaxis", "x"), ("yaxis", "y")):
        eixo = fig.layout[nome]
        if eixo.minallowed is not None:
            continue

        valores = []
        for barra in fig.data:
            dados = getattr(barra, atributo, None)
            if dados is not None and len(dados) > 0:
                valores.append(np.asarray(dados))
        if not valores:
            continue

        categorico = eixo.type == "category" or any(
            not (np.issubdtype(v.dtype, np.number) or np.issubdtype(v.dtype, np.datetime64)) for v in valores
        )
        if categorico:
            categorias_iniciais = set(np.concatenate([v.astype(str) for v in valores]))
            categorias_todas = set(categorias_iniciais)
            for quadro in fig.frames:
                for barra in quadro.data:
                    dados = getattr(barra, atributo, None)
                    if dados is not None and len(dados) > 0:
                        categorias_todas |= set(np.asarray(dados).astype(str))
            if categorias_todas != categorias_iniciais:
                continue
            inicio, fim = -0.5, len(categorias_iniciais) - 0.5
        elif eixo.range is not None:
            inicio, fim = eixo.range
        else:
            todos = np.concatenate(valores)
            if np.issubdtype(todos.dtype, np.datetime64):
                todos = todos[~np.isnat(todos)]
                inicio, fim = [str(np.datetime_as_string(v, unit="s")) for v in (todos.min(), todos.max())]
            else:
                todos = todos.astype(float)
                todos = todos[~np.isnan(todos)]
                inicio, fim = todos.min(), todos.max()
                if any(getattr(b, "type", "") == "bar" for b in fig.data):
                    inicio, fim = min(inicio, 0), fim * 20 / 19
                else:
                    folga = (fim - inicio) * 0.05
                    inicio, fim = inicio - folga, fim + folga

        fig.update_layout({nome: dict(range=[inicio, fim], minallowed=min(inicio, fim), maxallowed=max(inicio, fim))})


def intercalar_pausas(fig, pausas=1, voltar=True, pausas_fim=1):
    # O Plotly usa o mesmo tempo em todos os quadros: quadros de pausa alongam cada ano
    quadros = list(fig.frames)
    if len(quadros) < 3 or pausas < 1 or any(str(quadro.name).startswith("pausa-") for quadro in quadros):
        return
    novos = [quadros[0]]
    for posicao in range(1, len(quadros)):
        novos.append(quadros[posicao])
        if posicao < len(quadros) - 1:
            for numero in range(pausas):
                pausa = copy.deepcopy(quadros[posicao])
                pausa.name = f"pausa-{quadros[posicao].name}-{numero}"
                novos.append(pausa)
    if voltar:
        for numero in range(pausas_fim):
            pausa = copy.deepcopy(quadros[-1])
            pausa.name = f"pausa-{quadros[-1].name}-{numero}"
            novos.append(pausa)
        retorno = copy.deepcopy(quadros[0])
        retorno.name = quadros[0].name
        novos.append(retorno)
    fig.frames = novos


df = carregar_dados_csv()
engine = criar_banco_sqlite(df)

AJUSTES_JS = r"""
<script>
if (!window.__ajustesDashboard) {
    window.__ajustesDashboard = true;
    const sufixos = {k: " mil", M: " mi", B: " bi", G: " bi", T: " tri"};
    const textos = {"Select all": "Selecionar tudo", "Clear all": "Limpar tudo", "No results": "Sem resultados"};
    let agendado = false;

    function ajustar() {
        agendado = false;
        document.querySelectorAll(".xtick text, .ytick text, .y2tick text, .cbaxis text").forEach(function (rotulo) {
            const partes = rotulo.textContent.match(/^([−-]?[\d.,]+)([kMBGT])$/);
            if (partes) rotulo.textContent = partes[1] + sufixos[partes[2]];
        });
        document.querySelectorAll('[role="option"], [role="listbox"], [data-baseweb="popover"]').forEach(function (lista) {
            const caminhada = document.createTreeWalker(lista, NodeFilter.SHOW_TEXT);
            while (caminhada.nextNode()) {
                const no = caminhada.currentNode;
                const traduzido = textos[no.nodeValue.trim()];
                if (traduzido) no.nodeValue = traduzido;
            }
        });
    }

    new MutationObserver(function () {
        if (!agendado) {
            agendado = true;
            requestAnimationFrame(ajustar);
        }
    }).observe(document.body, {childList: true, subtree: true, characterData: true});

    document.addEventListener("click", function (evento) {
        if (!evento.target.closest('[role="option"]')) return;
        const campo = document.activeElement;
        if (!campo || !campo.closest('[data-testid="stMultiSelect"]')) return;
        setTimeout(function () {
            campo.dispatchEvent(new KeyboardEvent("keydown", {key: "Escape", code: "Escape", keyCode: 27, bubbles: true}));
            campo.blur();
        }, 80);
    }, true);
}
</script>
"""

st.title("🧳 Turismo no Brasil (2015-2024)")
st.html(AJUSTES_JS, unsafe_allow_javascript=True)

st.markdown("""
<div class="hero">
    <p>Painel interativo de fluxo de turistas, faturamento e sazonalidade em 37 cidades brasileiras.</p>
    <span class="tag">37 cidades</span>
    <span class="tag">120 meses</span>
    <span class="tag">4.440 registros</span>
    <span class="tag">Python · Pandas · Seaborn · Plotly · Streamlit</span>
</div>
""", unsafe_allow_html=True)

st.write("""
**Problema:** como o turismo evoluiu entre 2015 e 2024 nas principais cidades brasileiras?
Onde estão o fluxo de turistas e o faturamento, existe alta temporada e quais variáveis
(ocupação hoteleira, gasto médio, eventos, temperatura) se relacionam com o resultado?

A base simulada reúne 37 cidades em 5 regiões, com registros mensais de turistas, ocupação
hoteleira, gasto médio, faturamento, eventos e temperatura. Use os filtros ao lado e passe o mouse
sobre os gráficos para explorar. Os gráficos com botão ▶ são animados por ano.
""")

# ---------------- SIDEBAR ----------------
st.sidebar.header("Filtros")

lista_anos = sorted(df["ano"].unique())
lista_regioes = sorted(df["regiao"].unique())
lista_ufs = sorted(df["uf"].unique())
lista_cidades = sorted(df["cidade"].unique())
lista_temporadas = ["Baixa", "Média", "Alta"]

ano_sel = st.sidebar.multiselect("Ano", options=lista_anos, default=lista_anos, filter_mode=None)
regiao_sel = st.sidebar.multiselect("Região", options=lista_regioes, default=lista_regioes, filter_mode=None)
uf_sel = st.sidebar.multiselect("UF", options=lista_ufs, default=lista_ufs, filter_mode=None)
cidade_sel = st.sidebar.multiselect("Cidade", options=lista_cidades, default=lista_cidades, filter_mode=None)
temporada_sel = st.sidebar.multiselect("Nível de temporada", options=lista_temporadas, default=lista_temporadas, filter_mode=None)

df_filtrado = df[
    (df["ano"].isin(ano_sel))
    & (df["regiao"].isin(regiao_sel))
    & (df["uf"].isin(uf_sel))
    & (df["cidade"].isin(cidade_sel))
    & (df["nivel_temporada"].isin(temporada_sel))
]

if df_filtrado.empty:
    st.warning("Nenhum registro encontrado para os filtros selecionados. Ajuste os filtros na barra lateral.")
    st.stop()

ID_FILTRO = abs(hash((tuple(ano_sel), tuple(regiao_sel), tuple(uf_sel), tuple(cidade_sel), tuple(temporada_sel))))

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
aba1, aba2, aba3, aba4, aba5, aba6, aba7, aba8, aba9 = st.tabs([
    "Visão geral",
    "Regiões e UFs",
    "Cidades",
    "Mapa",
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
        mostrar_figura(fig, "visao-turistas", "barv")

    with col_b:
        fig, ax = plt.subplots(figsize=(7, 4))
        sns.lineplot(data=resumo_ano, x="ano", y="faturamento", marker="o", color=COR_DESTAQUE, ax=ax)
        ax.set_title("Faturamento por ano")
        ax.set_xlabel("Ano")
        ax.set_ylabel("Faturamento (R$)")
        ax.yaxis.set_major_formatter(mtick.FuncFormatter(eixo_bilhoes))
        ax.set_xticks(resumo_ano["ano"])
        plt.tight_layout()
        mostrar_figura(fig, "visao-faturamento", "linha")

    st.markdown("#### Versão interativa (passe o mouse para ver os valores)")
    col_a, col_b = st.columns(2)

    with col_a:
        with st.container(key=f"anim-barv-plotly-turistas-{ID_FILTRO}"):
            fig = px.bar(
                resumo_ano,
                x="ano",
                y="turistas",
                title="Turistas por ano",
                labels={"ano": "Ano", "turistas": "Turistas"},
                color_discrete_sequence=[COR]
            )
            fig.update_xaxes(type="category")
            formatar_dica(fig, "<b>Ano %{x}</b><br>Turistas: %{y:,.0f}<extra></extra>")
            st.plotly_chart(ajustar_grafico(fig), width="stretch")

    with col_b:
        with st.container(key=f"anim-linha-plotly-faturamento-{ID_FILTRO}"):
            fig = px.line(
                resumo_ano,
                x="ano",
                y="faturamento",
                markers=True,
                title="Faturamento por ano",
                labels={"ano": "Ano", "faturamento": "Faturamento (R$)"},
                color_discrete_sequence=[COR_DESTAQUE]
            )
            fig.update_xaxes(type="category")
            formatar_dica(fig, "<b>Ano %{x}</b><br>Faturamento: R$ %{y:,.0f}<extra></extra>")
            st.plotly_chart(ajustar_grafico(fig), width="stretch")

    corrida_regioes()

    st.markdown("#### Faturamento por região ao longo dos anos (animado)")
    animacao_regiao = (
        df_filtrado.groupby(["ano", "regiao"])["faturamento_turismo"]
        .sum()
        .reset_index()
    )
    fig = px.bar(
        animacao_regiao,
        x="regiao",
        y="faturamento_turismo",
        color="regiao",
        animation_frame="ano",
        range_y=[0, animacao_regiao["faturamento_turismo"].max() * 1.15],
        color_discrete_map=CORES_REGIAO,
        category_orders={"regiao": lista_regioes},
        title="Clique em ▶ para ver a evolução ano a ano",
        labels={"regiao": "Região", "faturamento_turismo": "Faturamento (R$)"}
    )
    formatar_dica(fig, "<b>%{x}</b><br>Faturamento: R$ %{y:,.0f}<extra></extra>")
    mostrar_plotly(fig, "regioes-anos", "barv", 460)

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
        mostrar_figura(fig, "regiao-total", "barv")

    with col_b:
        fig, ax = plt.subplots(figsize=(7, 4))
        sns.barplot(data=resumo_regiao, x="regiao", y="faturamento_por_cidade", color=COR_DESTAQUE, ax=ax)
        ax.set_title("Faturamento médio por cidade em cada região")
        ax.set_xlabel("Região")
        ax.set_ylabel("Faturamento por cidade (R$)")
        ax.yaxis.set_major_formatter(mtick.FuncFormatter(eixo_bilhoes))
        plt.tight_layout()
        mostrar_figura(fig, "regiao-cidade", "barv")

    st.markdown("#### Versão interativa")
    col_a, col_b = st.columns(2)

    with col_a:
        fig = px.bar(
            resumo_regiao,
            x="regiao",
            y="faturamento",
            color="regiao",
            color_discrete_map=CORES_REGIAO,
            title="Faturamento total por região",
            labels={"regiao": "Região", "faturamento": "Faturamento (R$)"}
        )
        fig.update_layout(showlegend=False)
        formatar_dica(fig, "<b>%{x}</b><br>Faturamento: R$ %{y:,.0f}<extra></extra>")
        mostrar_plotly(fig, "regiao-total", "barv")

    with col_b:
        fig = px.bar(
            resumo_regiao,
            x="regiao",
            y="faturamento_por_cidade",
            color="regiao",
            color_discrete_map=CORES_REGIAO,
            title="Faturamento médio por cidade em cada região",
            labels={"regiao": "Região", "faturamento_por_cidade": "Faturamento por cidade (R$)"}
        )
        fig.update_layout(showlegend=False)
        formatar_dica(fig, "<b>%{x}</b><br>Faturamento por cidade: R$ %{y:,.0f}<extra></extra>")
        mostrar_plotly(fig, "regiao-cidade", "barv")

    st.markdown("#### Mapa de árvore: região > UF > cidade (clique para aprofundar)")
    arvore = (
        df_filtrado.groupby(["regiao", "uf", "cidade"])["faturamento_turismo"]
        .sum()
        .reset_index()
    )
    arvore["faturamento_bi"] = arvore["faturamento_turismo"] / 1_000_000_000
    fig = px.treemap(
        arvore,
        path=[px.Constant("Brasil"), "regiao", "uf", "cidade"],
        values="faturamento_bi",
        color="regiao",
        color_discrete_map=CORES_REGIAO
    )
    fig.update_traces(
        hovertemplate="<b>%{label}</b><br>Faturamento: R$ %{value:.2f} bi<br>%{percentRoot:.1%} do total<extra></extra>"
    )
    mostrar_plotly(fig, "regiao-arvore", "arvore", 500)

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
    mostrar_figura(fig, "uf", "barv")

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

@st.fragment
def comparar_cidades():
    st.markdown("#### Compare cidades")
    col_f1, col_f2 = st.columns([2, 1])
    cidades_comp = col_f1.multiselect(
        "Cidades para comparar",
        options=sorted(df_filtrado["cidade"].unique()),
        default=[cidade for cidade in CAPITAIS if cidade in df_filtrado["cidade"].unique()],
        filter_mode=None,
        key="cidades_comparar"
    )
    metrica_comp = col_f2.selectbox(
        "Métrica",
        ["Turistas", "Faturamento (R$)", "Ocupação hoteleira (%)", "Gasto médio (R$)"],
        filter_mode=None
    )

    if cidades_comp:
        coluna_comp = {
            "Turistas": "turistas",
            "Faturamento (R$)": "faturamento_turismo",
            "Ocupação hoteleira (%)": "ocupacao_hoteleira",
            "Gasto médio (R$)": "gasto_medio"
        }[metrica_comp]
        agregacao = "sum" if coluna_comp in ["turistas", "faturamento_turismo"] else "mean"
        comparacao = (
            df_filtrado[df_filtrado["cidade"].isin(cidades_comp)]
            .groupby(["ano", "cidade"])[coluna_comp]
            .agg(agregacao)
            .reset_index()
        )
        fig = px.line(
            comparacao,
            x="ano",
            y=coluna_comp,
            color="cidade",
            markers=True,
            title=f"{metrica_comp} por ano",
            labels={"ano": "Ano", coluna_comp: metrica_comp, "cidade": "Cidade"}
        )
        fig.update_xaxes(type="category")
        casas = ",.0f" if metrica_comp in ("Turistas", "Faturamento (R$)") else ",.1f"
        formatar_dica(fig, f"<b>%{{fullData.name}}</b><br>Ano %{{x}}<br>{metrica_comp}: %{{y:{casas}}}<extra></extra>")
        mostrar_plotly(fig, "cidades-comparacao", "linha")
    else:
        st.write("Selecione ao menos uma cidade para ver a comparação.")


with aba3:
    st.subheader("Ranking e comparação de cidades")

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
    mostrar_figura(fig, "cidades-ranking", "barh")

    st.markdown("#### Corrida das cidades: top 10 em turistas, ano a ano (animado)")
    mapa_regiao = df.drop_duplicates("cidade").set_index("cidade")["regiao"]
    corrida = (
        df_filtrado.groupby(["ano", "cidade"])["turistas"]
        .sum()
        .reset_index()
        .sort_values(["ano", "turistas"], ascending=[True, False])
        .groupby("ano")
        .head(10)
    )
    corrida["regiao"] = corrida["cidade"].map(mapa_regiao)

    # Eixo = posição: com os nomes no eixo o Plotly acumula as cidades de todos os anos
    corrida["posicao"] = corrida.groupby("ano")["turistas"].rank(ascending=False, method="first").astype(int)
    ultima_posicao = corrida["posicao"].max()
    corrida["grupo"] = corrida["cidade"]

    # Linhas extras fora do gráfico: toda região precisa existir em todos os anos, senão faltam barras
    extras = [
        {"ano": ano, "cidade": "", "turistas": 0, "regiao": regiao, "posicao": ultima_posicao + 5, "grupo": f"vazio-{regiao}"}
        for ano in corrida["ano"].unique()
        for regiao in corrida["regiao"].unique()
        if not ((corrida["ano"] == ano) & (corrida["regiao"] == regiao)).any()
    ]
    corrida = pd.concat([corrida, pd.DataFrame(extras)], ignore_index=True)

    fig = px.bar(
        corrida,
        x="turistas",
        y="posicao",
        color="regiao",
        orientation="h",
        text="cidade",
        custom_data=["cidade", "ano"],
        animation_frame="ano",
        animation_group="grupo",
        range_x=[0, corrida["turistas"].max() * 1.1],
        color_discrete_map=CORES_REGIAO,
        category_orders={"regiao": lista_regioes},
        labels={"turistas": "Turistas", "posicao": "Posição", "regiao": "Região"}
    )
    fig.update_yaxes(range=[ultima_posicao + 0.5, 0.5], dtick=1)
    formatar_dica(
        fig,
        "<b>%{customdata[0]}</b><br>Região: %{fullData.name}<br>Posição em %{customdata[1]}: %{y}º"
        "<br>Turistas: %{x:,.0f}<extra></extra>"
    )
    fig.update_traces(textposition="inside", insidetextanchor="start", cliponaxis=False)
    for quadro in fig.frames:
        for barra in quadro.data:
            barra.textposition = "inside"
            barra.insidetextanchor = "start"
            barra.cliponaxis = False
    mostrar_plotly(fig, "corrida-cidades", "barh", 500, ano_ms=3000)

    comparar_cidades()

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
        .rename(columns=NOMES_COLUNAS)
    )
    st.dataframe(tabela_cidades, width="stretch", hide_index=True)

    cidade_lider = ranking_cidades.iloc[0]
    st.success(f"A cidade mais visitada no recorte é {cidade_lider['cidade']}, com {formatar_numero(cidade_lider['turistas'])} turistas.")
    st.info("""
    Os totais por cidade são muito parecidos entre si: não há uma metrópole que concentre o fluxo, e as
    posições do ranking mudam de um ano para o outro, como mostra a corrida animada. Use a comparação
    para ver como cada cidade se comporta e a tabela para conferir ocupação e gasto médio.
    """)

def montar_mapa(dados_mapa, coluna_mapa, metrica_mapa, animar_mapa):
    argumentos_mapa = {"animation_frame": "ano"} if animar_mapa else {}
    fig = px.scatter_map(
        dados_mapa,
        lat="latitude",
        lon="longitude",
        size=coluna_mapa,
        color="regiao",
        hover_name="cidade",
        hover_data={"uf": True, "latitude": False, "longitude": False},
        color_discrete_map=CORES_REGIAO,
        size_max=40,
        zoom=3.1,
        center={"lat": -15.0, "lon": -52.0},
        map_style="open-street-map",
        labels={coluna_mapa: metrica_mapa, "regiao": "Região", "uf": "UF"},
        **argumentos_mapa
    )
    # Limites em ±179: com ±180 o maplibre falha em aba escondida e o mapa fica em branco
    casas_mapa = ",.0f" if coluna_mapa in ("faturamento_turismo", "turistas") else ",.1f"
    formatar_dica(
        fig,
        f"<b>%{{hovertext}}</b> (%{{customdata[0]}})<br>Região: %{{fullData.name}}"
        f"<br>{metrica_mapa}: %{{marker.size:{casas_mapa}}}<extra></extra>"
    )
    fig.update_layout(map=dict(bounds=dict(west=-179, east=179, south=-85, north=85)))
    return fig


@st.fragment
def mapa_cidades():
    col_m1, col_m2 = st.columns([2, 1])
    metrica_mapa = col_m1.selectbox(
        "Indicador do mapa",
        ["Faturamento (R$)", "Turistas", "Ocupação hoteleira média (%)", "Gasto médio (R$)"],
        filter_mode=None
    )
    animar_mapa = col_m2.toggle("Animar por ano", value=False)

    coluna_mapa = {
        "Faturamento (R$)": "faturamento_turismo",
        "Turistas": "turistas",
        "Ocupação hoteleira média (%)": "ocupacao_hoteleira",
        "Gasto médio (R$)": "gasto_medio"
    }[metrica_mapa]
    agregacao_mapa = "sum" if coluna_mapa in ["faturamento_turismo", "turistas"] else "mean"

    agrupar = ["ano", "cidade", "uf", "regiao"] if animar_mapa else ["cidade", "uf", "regiao"]
    dados_mapa = (
        df_filtrado.groupby(agrupar)[coluna_mapa]
        .agg(agregacao_mapa)
        .reset_index()
    )
    dados_mapa["latitude"] = dados_mapa["cidade"].map(lambda c: COORDENADAS[c][0])
    dados_mapa["longitude"] = dados_mapa["cidade"].map(lambda c: COORDENADAS[c][1])

    if animar_mapa:
        dados_mapa = dados_mapa.sort_values("ano")

    fig = montar_mapa(dados_mapa, coluna_mapa, metrica_mapa, animar_mapa)
    st.plotly_chart(ajustar_grafico(fig, 620), width="stretch")

    cidade_topo = dados_mapa.groupby("cidade")[coluna_mapa].agg(agregacao_mapa).idxmax()
    st.success(f"No indicador escolhido ({metrica_mapa}), o maior valor do recorte está em {cidade_topo}.")
    st.info("""
    O tamanho de cada bolha representa o indicador e a cor indica a região. Os círculos têm tamanhos parecidos,
    o que confirma a ausência de uma cidade dominante, e a distribuição geográfica é mais densa no Sudeste e
    no litoral do Nordeste, onde há mais cidades na base.
    """)


with aba4:
    st.subheader("Mapa interativo das cidades")
    mapa_cidades()

with aba5:
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
        mostrar_figura(fig, "sazonal-indice", "barv")

    with col_b:
        fig, ax = plt.subplots(figsize=(7, 4))
        sns.boxplot(data=df_filtrado, x="nivel_temporada", y="turistas", order=lista_temporadas, color=COR, ax=ax)
        ax.set_title("Turistas por nível de temporada informado")
        ax.set_xlabel("Nível de temporada")
        ax.set_ylabel("Turistas")
        ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda v, p: f"{v / 1e3:.0f} mil"))
        plt.tight_layout()
        mostrar_figura(fig, "sazonal-caixa", "caixa")

    st.markdown("#### Versão interativa e mapa de calor")
    col_a, col_b = st.columns(2)

    with col_a:
        fig = px.bar(
            media_mensal,
            x="nome_mes",
            y="indice_sazonal",
            title="Índice sazonal de turistas por mês (média = 100)",
            labels={"nome_mes": "Mês", "indice_sazonal": "Índice sazonal"},
            color_discrete_sequence=[COR]
        )
        fig.add_hline(y=100, line_dash="dash", line_color=COR_DESTAQUE)
        fig.update_xaxes(categoryorder="array", categoryarray=NOMES_MESES)
        formatar_dica(fig, "<b>%{x}</b><br>Índice sazonal: %{y:.1f}<extra></extra>")
        mostrar_plotly(fig, "sazonal-indice", "barv")

    with col_b:
        mapa_calor = df_filtrado.pivot_table(index="ano", columns="mes", values="turistas", aggfunc="mean")
        mapa_calor.columns = [NOMES_MESES[m - 1] for m in mapa_calor.columns]
        fig = px.imshow(
            mapa_calor,
            aspect="auto",
            color_continuous_scale="Teal",
            title="Média de turistas por ano e mês (mapa de calor)",
            labels={"x": "Mês", "y": "Ano", "color": "Turistas"}
        )
        fig.update_yaxes(type="category")
        formatar_dica(fig, "<b>%{x} de %{y}</b><br>Média de turistas: %{z:,.0f}<extra></extra>")
        mostrar_plotly(fig, "sazonal-calor", "calor")

    mes_maior = media_mensal.loc[media_mensal["indice_sazonal"].idxmax()]
    mes_menor = media_mensal.loc[media_mensal["indice_sazonal"].idxmin()]
    st.success(
        f"O índice sazonal vai de {mes_menor['indice_sazonal']:.0f} ({mes_menor['nome_mes']}) "
        f"a {mes_maior['indice_sazonal']:.0f} ({mes_maior['nome_mes']}) no recorte filtrado."
    )
    st.info("""
    Na base completa o índice sazonal fica entre 94 e 104, uma amplitude pequena: não existe uma alta temporada
    bem definida. A coluna Nível de temporada também não se relaciona com o número de turistas, pois as caixas de
    Baixa, Média e Alta têm distribuições praticamente iguais. O mapa de calor, sem faixas de cor bem marcadas, confirma isso.
    """)

@st.fragment
def serie_interativa():
    st.markdown("#### Versão interativa")
    mostrar_media = st.toggle("Mostrar média móvel de 12 meses", value=True)

    serie_exibicao = serie.rename(columns={"turistas": "Turistas no mês", "media_movel_12m": "Média móvel de 12 meses"})
    colunas_serie = ["Turistas no mês", "Média móvel de 12 meses"] if mostrar_media else ["Turistas no mês"]
    fig = px.line(
        serie_exibicao,
        x="ano_mes",
        y=colunas_serie,
        title="Turistas por mês (use o seletor abaixo do gráfico para dar zoom em um período)",
        labels={"ano_mes": "Mês", "value": "Turistas", "variable": "Série"},
        color_discrete_sequence=[COR, COR_DESTAQUE]
    )
    fig.update_xaxes(rangeslider_visible=True, tickformat="%m/%Y")
    formatar_dica(fig, "<b>%{fullData.name}</b><br>Mês: %{x|%m/%Y}<br>Turistas: %{y:,.0f}<extra></extra>")
    mostrar_plotly(fig, "serie-mensal", "linha", 480)


with aba6:
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
    mostrar_figura(fig, "serie", "linha")

    serie_interativa()

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
        mostrar_figura(fig, "variacao", "barv")

    st.success(f"O recorte tem {len(serie)} meses; o pico mensal foi de {formatar_numero(serie['turistas'].max())} turistas.")
    st.info("""
    A média móvel de 12 meses fica praticamente horizontal, o que confirma a estabilidade do fluxo. As variações
    anuais ficam em poucos pontos percentuais para cima ou para baixo, sem um período de crise ou de recuperação marcante.
    """)

@st.fragment
def dispersao_interativa():
    st.markdown("#### Dispersão interativa: escolha as variáveis")
    col_x, col_y = st.columns(2)
    var_x = col_x.selectbox("Eixo X", colunas_corr, index=0, format_func=NOMES_COLUNAS.get, filter_mode=None)
    var_y = col_y.selectbox("Eixo Y", colunas_corr, index=4, format_func=NOMES_COLUNAS.get, filter_mode=None)
    amostra_interativa = df_filtrado.sample(min(len(df_filtrado), 1500), random_state=1)
    fig = px.scatter(
        amostra_interativa,
        x=var_x,
        y=var_y,
        color="regiao",
        hover_name="cidade",
        opacity=0.55,
        color_discrete_map=CORES_REGIAO,
        title="Dispersão interativa (amostra de até 1.500 registros)",
        labels=NOMES_COLUNAS
    )
    formatar_dica(
        fig,
        f"<b>%{{hovertext}}</b><br>Região: %{{fullData.name}}<br>{NOMES_COLUNAS[var_x]}: %{{x:,.2~f}}"
        f"<br>{NOMES_COLUNAS[var_y]}: %{{y:,.2~f}}<extra></extra>"
    )
    mostrar_plotly(fig, "correlacao-dispersao", "pop", 460)


with aba7:
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
        fig, ax = plt.subplots(figsize=(7, 5.2))
        sns.heatmap(matriz_corr.rename(index=NOMES_COLUNAS, columns=NOMES_COLUNAS), annot=True, fmt=".2f", cmap="coolwarm", vmin=-1, vmax=1, ax=ax)
        ax.set_title("Matriz de correlação")
        plt.tight_layout()
        mostrar_figura(fig, "corr-heatmap", "pop")

    with col_b:
        amostra = df_filtrado.sample(min(len(df_filtrado), 1000), random_state=1)
        fig, ax = plt.subplots(figsize=(7, 5.2))
        sns.scatterplot(data=amostra, x="turistas", y="faturamento_turismo", alpha=0.4, color=COR, ax=ax)
        ax.set_title("Turistas x faturamento (amostra de até 1.000 registros)")
        ax.set_xlabel("Turistas")
        ax.set_ylabel("Faturamento (R$)")
        ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda v, p: f"{v / 1e3:.0f} mil"))
        ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda v, p: f"{v / 1e6:.0f} mi"))
        plt.tight_layout()
        mostrar_figura(fig, "corr-dispersao", "pop")

    dispersao_interativa()

    corr_fat = matriz_corr["faturamento_turismo"].drop("faturamento_turismo")
    variavel_forte = corr_fat.abs().idxmax()
    st.success(
        f"A maior correlação com o faturamento é com {NOMES_COLUNAS[variavel_forte]}: "
        f"{corr_fat[variavel_forte]:.2f}".replace(".", ",") + "."
    )
    st.info("""
    Na base completa todas as correlações ficam próximas de zero (entre -0,03 e +0,03). Mais turistas, maior ocupação
    ou mais eventos não aparecem associados a maior faturamento, e o faturamento não corresponde a turistas x gasto
    médio. Escolha outros pares de variáveis na dispersão: a nuvem de pontos sempre fica espalhada, sem padrão.
    """)

@st.fragment
def consulta_sql():
    opcao_consulta = st.selectbox(
        "Escolha a consulta",
        ["Faturamento por ano e região", "Top 10 cidades por faturamento", "Médias por mês do ano"],
        filter_mode=None
    )

    if opcao_consulta == "Faturamento por ano e região":
        consulta = """
        SELECT ano AS "Ano",
               regiao AS "Região",
               SUM(turistas) AS "Turistas",
               ROUND(SUM(faturamento_turismo) / 1000000000.0, 2) AS "Faturamento (R$ bi)",
               ROUND(AVG(ocupacao_hoteleira), 1) AS "Ocupação média (%)"
        FROM turismo
        GROUP BY ano, regiao
        ORDER BY ano, "Faturamento (R$ bi)" DESC
        """
    elif opcao_consulta == "Top 10 cidades por faturamento":
        consulta = """
        SELECT cidade AS "Cidade",
               uf AS "UF",
               SUM(turistas) AS "Turistas",
               ROUND(SUM(faturamento_turismo) / 1000000000.0, 2) AS "Faturamento (R$ bi)"
        FROM turismo
        GROUP BY cidade, uf
        ORDER BY "Faturamento (R$ bi)" DESC
        LIMIT 10
        """
    else:
        consulta = """
        SELECT mes AS "Mês",
               ROUND(AVG(turistas)) AS "Turistas médios",
               ROUND(AVG(ocupacao_hoteleira), 1) AS "Ocupação média (%)",
               ROUND(AVG(gasto_medio), 2) AS "Gasto médio (R$)"
        FROM turismo
        GROUP BY mes
        ORDER BY mes
        """

    resultado_sql = pd.read_sql(consulta, engine)
    st.dataframe(resultado_sql, width="stretch", hide_index=True)
    st.code(consulta, language="sql")

    st.success(f"A consulta retornou {len(resultado_sql)} linhas.")
    st.info("""
    O mesmo resultado poderia ser obtido com groupby no Pandas. O banco mostra a persistência dos dados tratados
    e permite consultas em SQL sobre a mesma base usada nos gráficos.
    """)


with aba8:
    st.subheader("Consulta SQL no banco SQLite")
    st.write("A tabela `turismo` foi gravada em `database/turismo_brasil.sqlite` com SQLAlchemy. As consultas abaixo usam a base completa, sem os filtros.")

    consulta_sql()

with aba9:
    st.subheader("Dados filtrados")

    colunas_tabela = [
        "ano", "mes", "regiao", "uf", "cidade", "turistas", "turistas_estrangeiros_ajustado",
        "ocupacao_hoteleira", "gasto_medio", "faturamento_turismo", "eventos_realizados",
        "temperatura_media", "nivel_temporada"
    ]
    tabela_dados = df_filtrado[colunas_tabela].rename(columns=NOMES_COLUNAS)
    st.dataframe(tabela_dados, width="stretch", hide_index=True)
    st.download_button(
        "Baixar CSV filtrado",
        data=tabela_dados.to_csv(index=False).encode("utf-8"),
        file_name="turismo_filtrado.csv",
        mime="text/csv"
    )

    sem_ajuste = (df_filtrado["turistas_estrangeiros"] > df_filtrado["turistas"]).sum()
    st.success(f"{formatar_numero(len(df_filtrado))} registros exibidos; {formatar_numero(sem_ajuste)} deles tiveram turistas estrangeiros ajustados.")
    st.info("""
    Na base completa, 260 registros trazem mais turistas estrangeiros do que turistas totais, o que é inconsistente.
    A coluna original foi mantida e os indicadores usam Turistas estrangeiros (ajustado), limitado ao total de turistas.
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
