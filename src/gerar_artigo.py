"""Gera docs/index.html (artigo acadêmico) a partir da base tratada.

Uso: python -m src.gerar_artigo
Todos os números do texto vêm de etl.calcular_indicadores, então o artigo acompanha os dados.
"""
from __future__ import annotations

import html
import inspect
import json
import logging
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Final

import pandas as pd
import plotly
import plotly.graph_objects as go

from src import etl
from src import visualizacao as viz
from src.formatacao import (
    MESES_EXTENSO,
    NUMEROS_EXTENSO,
    bi,
    dec,
    dia_mes_extenso,
    mes_ano_extenso,
    nome_proprio,
    num,
    pct,
)

LOGGER = logging.getLogger(__name__)

RAIZ: Final = Path(__file__).resolve().parents[1]
DESTINO: Final = RAIZ / "docs" / "index.html"
ARQUIVO_CSS: Final = RAIZ / "src" / "artigo.css"

AUTOR: Final = "Guilherme Felix"
INSTITUICAO: Final = "Universidade LaSalle"
CURSO: Final = "Bacharelado em Sistemas de Informação, 6º período"
DISCIPLINA: Final = "Linguagem de Programação (Análise e Visualização de Dados com Python)"
PROFESSOR: Final = "Alexandre Neves Louzada"
SEMESTRE: Final = "Semestre 2026.2"
REPOSITORIO: Final = "https://github.com/GuilhermeF2/projeto-g1"
URL_FONTE: Final = "https://dadosabertos.bndes.gov.br/dataset/operacoes-financiamento"
DATA_ACESSO: Final = "16 nov. 2026"
VERSAO_PYTHON: Final = "3.12"
PALAVRAS_CHAVE: Final = ("BNDES", "financiamento", "dados abertos", "análise exploratória", "Python", "princípios FAIR")
TITULO_ARTIGO: Final = (
    "Concentração e regimes do crédito não automático do BNDES (2002-2026): "
    "uma análise exploratória em Python sob princípios FAIR"
)
TITULO_PAGINA: Final = "Financiamentos do BNDES (2002-2026): análise exploratória em Python sob princípios FAIR"
DESCRICAO_PAGINA: Final = (
    "Análise exploratória dos financiamentos não automáticos do BNDES (2002-2026) com Python, sob princípios FAIR."
)
LIMITE_CORRELACAO_FRACA: Final = 0.3
LIMITE_CLIENTE_DOMINANTE: Final = 0.10
QUANTIDADE_PERIODOS_TEXTO: Final = 4
PALAVRAS_RESUMO_MIN: Final = 150
PALAVRAS_RESUMO_MAX: Final = 250
CONFIG_PLOTLY: Final = {"responsive": True, "displayModeBar": False}

VALOR, JUROS, CARENCIA, AMORTIZACAO = etl.COLUNAS_CORRELACAO
PARES_CORRELACAO: Final = (
    (VALOR, AMORTIZACAO), (VALOR, CARENCIA), (VALOR, JUROS),
    (CARENCIA, AMORTIZACAO), (JUROS, CARENCIA), (JUROS, AMORTIZACAO),
)


def esc(texto: object) -> str:
    return html.escape(str(texto))


def linha_de(resumo: pd.DataFrame, chave: str) -> pd.Series:
    """Linha de um resumo de etl.resumo_por, localizada pelo valor da primeira coluna."""
    return resumo.set_index(resumo.columns[0]).loc[chave]


def correlacao_de(matriz: pd.DataFrame, par: tuple[str, str]) -> float:
    return float(matriz.loc[par[0], par[1]])


def bloco_plotly(identificador: str, figura: go.Figure, descricao: str) -> str:
    """Gráfico Plotly em contêiner acessível; a serialização (com escape de HTML) é do próprio Plotly."""
    grafico = figura.to_html(
        full_html=False, include_plotlyjs=False, div_id=identificador, config=CONFIG_PLOTLY
    )
    return (
        f'<div class="chart-container" role="img" aria-label="{esc(descricao)}">\n{grafico}\n'
        "<noscript>Este gráfico interativo precisa de JavaScript; a legenda e o texto descrevem o resultado."
        "</noscript>\n</div>"
    )


def trecho_codigo(*funcoes: Callable) -> str:
    codigo = "\n\n".join(inspect.getsource(funcao).rstrip() for funcao in funcoes)
    return f"<pre><code>{html.escape(codigo)}</code></pre>"


def validar_afirmacoes(ind: dict) -> None:
    """Confere se as frases qualitativas do texto continuam verdadeiras para os dados; senão, interrompe."""
    inov = ind["inovacao"]
    sim, nao = inov.loc[etl.INOVACAO_SIM], inov.loc[etl.INOVACAO_NAO]
    correlacoes = [abs(correlacao_de(ind["correlacao_reembolsaveis"], par)) for par in PARES_CORRELACAO]
    maior_porte = linha_de(ind["porte"], etl.PORTES[-1])["participacao"]
    maior_setor = ind["setor"]["participacao"].max()
    maior_regiao = ind["regiao"]["participacao"].max()
    afirmacoes = {
        "o apoio à inovação tem valor mediano menor": sim["valor_mediano"] < nao["valor_mediano"],
        "o apoio à inovação tem amortização mais curta": sim["amortizacao_mediana"] < nao["amortizacao_mediana"],
        "os juros medianos da inovação ficam acima": sim["juros_mediano"] > nao["juros_mediano"],
        "as correlações das reembolsáveis são fracas (|r| < 0,3)": max(correlacoes) < LIMITE_CORRELACAO_FRACA,
        "nenhum cliente domina sozinho (menos de 10% do total)":
            ind["maiores_clientes"].iloc[0] / ind["total_contratado"] < LIMITE_CLIENTE_DOMINANTE,
        "o porte é a dimensão mais concentrada": maior_porte > maior_setor > maior_regiao,
        "o texto de RQ1 usa quatro períodos": len(ind["medias_periodos"]) == QUANTIDADE_PERIODOS_TEXTO,
        "o pico é anterior ao vale e à recuperação": ind["ano_pico"] < ind["ano_vale"] < ind["ano_pico_recente"],
    }
    falsas = [texto for texto, valida in afirmacoes.items() if not valida]
    if falsas:
        raise ValueError(f"O texto do artigo afirma algo que os dados não sustentam: {falsas}")


def montar_resumo(ind: dict) -> str:
    """Resumo do artigo; deve ter entre 150 e 250 palavras."""
    porte = linha_de(ind["porte"], etl.PORTES[-1])["participacao"]
    infraestrutura = linha_de(ind["setor"], etl.SETOR_INFRAESTRUTURA)["participacao"]
    pares = [correlacao_de(ind["correlacao_reembolsaveis"], par) for par in PARES_CORRELACAO]
    regimes = NUMEROS_EXTENSO[len(etl.PERIODOS)]
    resumo = (
        f"Este estudo analisa {num(ind['subcreditos'])} subcréditos de financiamentos não automáticos do Banco "
        f"Nacional de Desenvolvimento Econômico e Social (BNDES), contratados entre "
        f"{mes_ano_extenso(ind['primeira_data'])} e {mes_ano_extenso(ind['ultima_data'])} e publicados como dados "
        f"abertos. Foi construído um pipeline determinístico em Python (pandas e NumPy) que lê o arquivo em "
        f"Windows-1252, converte tipos, padroniza categorias e sinaliza inconsistências sem descartar linhas, "
        f"gravando a base tratada em formatos abertos. A análise responde a três perguntas: a evolução do valor "
        f"contratado, a concentração por porte, setor, região e cliente, e a relação entre valor, prazo e juros. "
        f"O valor anual passou por {regimes} regimes, com pico de R$ {bi(ind['valor_pico'])} bilhões em "
        f"{ind['ano_pico']} e vale de R$ {bi(ind['valor_vale'])} bilhões em {ind['ano_vale']}, e "
        f"{pct(ind['participacao_quarto_trimestre'])} do valor é contratado de outubro a dezembro. A concentração "
        f"é elevada: clientes grandes respondem por {pct(porte)} do valor, a infraestrutura por "
        f"{pct(infraestrutura)} e o coeficiente de Gini entre clientes é {dec(ind['gini_clientes'], 2)}. Nas "
        f"operações reembolsáveis, valor, prazo e juros se associam de forma fraca (correlação de Spearman entre "
        f"{dec(min(pares), 2)} e {dec(max(pares), 2)}), e o apoio à inovação tem valores e prazos menores. Os "
        f"resultados são descritivos, com limitações de cobertura e de valores nominais. Código, dados e artigo "
        f"seguem os princípios FAIR."
    )
    palavras = len(resumo.split())
    if not PALAVRAS_RESUMO_MIN <= palavras <= PALAVRAS_RESUMO_MAX:
        raise ValueError(f"O resumo tem {palavras} palavras; o esperado é de 150 a 250.")
    return resumo


def montar_figuras(df: pd.DataFrame, ind: dict) -> dict[str, str]:
    inicio, fim = ind["primeira_data"].year, etl.ANO_COMPLETO_FINAL
    pico, vale = ind["ano_pico"], ind["ano_vale"]
    return {
        "anual": bloco_plotly(
            "fig-anual", viz.fig_evolucao_anual(df),
            f"Gráfico de barras do valor contratado por ano, de {inicio} a {ind['ultima_data'].year}, "
            f"com pico em {pico} e vale em {vale}.",
        ),
        "mensal": bloco_plotly(
            "fig-mensal", viz.fig_serie_mensal(df),
            f"Gráfico de linhas do valor contratado por mês e da média móvel de 12 meses, de {inicio} a {fim}.",
        ),
        "sazonal": bloco_plotly(
            "fig-sazonal", viz.fig_sazonalidade_mensal(df),
            "Gráfico de barras da participação de cada mês do ano no valor contratado, com destaque para outubro, "
            "novembro e dezembro.",
        ),
        "porte": bloco_plotly(
            "fig-porte", viz.fig_porte(df),
            "Dois gráficos de barras: participação de cada porte de cliente no valor contratado e mediana por "
            "subcrédito.",
        ),
        "setor": bloco_plotly(
            "fig-setor", viz.fig_setor_regiao(df),
            "Dois gráficos de barras horizontais: participação de cada setor e de cada região no valor contratado.",
        ),
        "dispersao": bloco_plotly(
            "fig-dispersao", viz.fig_dispersao(df),
            "Gráfico de dispersão do prazo de amortização contra o valor contratado nas operações reembolsáveis, "
            "separando as com e sem apoio à inovação.",
        ),
        "inovacao": bloco_plotly(
            "fig-inovacao", viz.fig_inovacao(df),
            "Três gráficos de barras comparando valor, prazo de amortização e juros medianos com e sem apoio à "
            "inovação.",
        ),
    }


def secao_cabecalho(resumo: str) -> str:
    palavras = ", ".join(PALAVRAS_CHAVE)
    return f"""
    <header>
      <h1 class="paper-title">{TITULO_ARTIGO}</h1>

      <div class="meta-block authors">{AUTOR}</div>

      <div class="meta-block affiliations">
        {CURSO} — {INSTITUICAO}<br>
        Disciplina: {DISCIPLINA}<br>
        Professor: {PROFESSOR} · {SEMESTRE}
      </div>

      <div class="badges">
        <span class="badge">Código: MIT</span>
        <span class="badge">Dados: ODbL (BNDES)</span>
        <span class="badge">Texto e figuras: CC BY 4.0</span>
        <span class="badge">Python {VERSAO_PYTHON}</span>
        <span class="badge">FAIR</span>
      </div>

      <a href="{REPOSITORIO}" class="repo-badge" target="_blank" rel="noopener noreferrer">
        📦 Ver Repositório GitHub (Código e Dados)
      </a>
    </header>

    <div class="abstract-box">
      <h3>Resumo</h3>
      <p>{resumo}</p>
      <div class="keywords">
        <strong>Palavras-chave:</strong> {palavras}.
      </div>
    </div>

    <nav class="toc" aria-label="Sumário">
      <h4>Sumário</h4>
      <ol>
        <li><a href="#intro">Introdução</a></li>
        <li><a href="#metodologia">Metodologia e Pipeline de Dados</a></li>
        <li><a href="#resultados">Resultados e Discussão</a></li>
        <li><a href="#conclusao">Conclusão</a></li>
        <li><a href="#fair">Disponibilidade dos Dados e Declaração FAIR</a></li>
        <li><a href="#referencias">Referências</a></li>
      </ol>
    </nav>
"""


def secao_introducao(ind: dict) -> str:
    inicio = ind["primeira_data"].year
    return f"""
    <section id="intro">
      <h2>1. Introdução</h2>
      <p>
        O BNDES é um dos principais instrumentos de crédito de longo prazo do país e publica, em seu portal de dados
        abertos, o detalhe das operações que contrata. A disponibilidade dos dados, porém, não basta: é preciso um
        fluxo de trabalho que trate as peculiaridades do arquivo, registre cada decisão e permita que outra pessoa
        chegue aos mesmos números (WILKINSON et al., 2016). Este trabalho parte das operações de financiamento
        <em>não automáticas</em>, em que cada contrato é analisado individualmente pelo banco, e examina como o
        volume contratado se comporta ao longo do tempo, como ele se distribui entre os clientes e quais condições
        financeiras acompanham o valor.
      </p>
      <p>O estudo responde a três perguntas de pesquisa:</p>
      <ul class="lista">
        <li><strong>RQ1.</strong> Como evoluiu o valor contratado entre {inicio} e {etl.ANO_COMPLETO_FINAL}, e quais
          períodos concentram picos e vales?</li>
        <li><strong>RQ2.</strong> Quão concentrado é o valor contratado por porte do cliente, setor, região e
          cliente?</li>
        <li><strong>RQ3.</strong> Como valor, prazo e juros se relacionam nas operações reembolsáveis, e o que muda no
          apoio à inovação?</li>
      </ul>
    </section>
"""


def secao_metodologia(ind: dict, relatorio: dict) -> str:
    marcadores = relatorio["placeholders_convertidos_em_nulo"]
    sinalizadas = relatorio["linhas_sinalizadas"]
    return f"""
    <section id="metodologia">
      <h2>2. Metodologia e Pipeline de Dados</h2>
      <h3 class="sub">2.1 Fonte e granularidade</h3>
      <p>
        Os dados são o recurso <em>Operações não automáticas</em> do conjunto <em>Operações de Financiamento</em>,
        publicado pelo BNDES sob licença ODbL (BNDES, 2026), acessado em {DATA_ACESSO}. O arquivo tem
        {num(ind['subcreditos'])} linhas e {relatorio['colunas_originais']} colunas, de
        {ind['primeira_data']:%d/%m/%Y} a {ind['ultima_data']:%d/%m/%Y}. Cada linha é um <strong>subcrédito</strong>:
        um contrato pode ter vários, com condições distintas, e a soma deles é o valor do contrato. A base reúne
        {num(ind['contratos'])} contratos, {num(ind['clientes'])} clientes (CNPJ) e {num(ind['municipios'])}
        municípios. Por isso a unidade de análise é o subcrédito, e os valores são somados por contrato ou cliente
        quando a pergunta exige.
      </p>
      <h3 class="sub">2.2 Leitura e tratamento</h3>
      <p>
        O arquivo não é trivial: usa ponto e vírgula, codificação Windows-1252 (não UTF-8), vírgula decimal e o
        marcador <code>----------</code> no lugar de valores ausentes, com espaços à direita nas células. Todas as
        colunas são lidas como texto e convertidas de forma explícita, com pandas (MCKINNEY, 2010) e NumPy (HARRIS
        et al., 2020). O tratamento segue uma regra: <strong>nenhuma linha é descartada</strong>. Cada inconsistência
        vira uma coluna de sinalização, e as contagens ficam em <code>relatorio_etl.json</code>, junto com o SHA-256
        do arquivo bruto.
      </p>
      {trecho_codigo(etl.carregar_bruto, etl.converter_tipos)}
      <p>
        {NUMEROS_EXTENSO[len(marcadores)].capitalize()} colunas trazem marcadores de ausente: a instituição credenciada
        ({num(marcadores['instituicao_financeira_credenciada'])} linhas) é ausente por construção nas operações
        diretas; o tipo de excepcionalidade só existe para contratos a partir de 2020; a fonte de recurso e a
        situação do contrato não têm explicação no dicionário e foram tratadas como não informadas. Os marcadores
        viram nulo, sem imputação. Também foram criadas a região do país a partir da UF, o prazo total, a taxa de
        execução (desembolsado sobre contratado) e três sinalizações:
      </p>
      {trecho_codigo(etl.limites_outlier, etl.sinalizar_inconsistencias)}
      <p>
        Foram sinalizadas {num(sinalizadas['repetida'])} linhas idênticas a outra anterior (que podem ser subcréditos
        legítimos de mesmo valor), {num(sinalizadas['desembolso_acima_contratado'])} linhas em que o desembolso supera
        o contratado ({pct(ind['desembolso_acima'])}; o dicionário do BNDES atribui isso à correção por indexador) e
        {num(sinalizadas['outlier_valor'])} outliers de valor, que somam {pct(ind['valor_outliers'])} do total. Como
        o valor por subcrédito é muito assimétrico (mediana de R$ {dec(ind['mediana_subcredito'] / 1e6)} milhões e
        média de R$ {dec(ind['media_subcredito'] / 1e6)} milhões), as análises usam medianas, escala logarítmica e a
        correlação de Spearman. A base tratada é gravada em Parquet e em CSV comprimido, com dicionário de dados em
        Markdown. As figuras estáticas usam Matplotlib (HUNTER, 2007) e seaborn (WASKOM, 2021), e as interativas,
        Plotly (PLOTLY TECHNOLOGIES INC., 2015).
      </p>
    </section>
"""


def secao_rq1(ind: dict, figuras: dict[str, str]) -> str:
    inicio, fim = ind["primeira_data"].year, etl.ANO_COMPLETO_FINAL
    ultimo_mes = MESES_EXTENSO[ind["ultima_data"].month - 1]
    medias = [(f"{ini}-{fim_periodo}", valor) for (ini, fim_periodo), valor in ind["medias_periodos"].items()]
    (p1, m1), (p2, m2), (p3, m3), (p4, m4) = medias
    return f"""
      <h3 class="sub">3.1 RQ1: evolução do valor contratado</h3>
      <figure>
        {figuras['anual']}
        <figcaption>Figura 1: Valor contratado por ano, em R$ bilhões nominais. A barra clara é
          {ind['ultima_data'].year}*, parcial até {ultimo_mes}.</figcaption>
      </figure>
      <p>
        O valor anual não segue uma tendência única. A média anual é de R$ {bi(m1)} bilhões em {p1}, sobe para
        R$ {bi(m2)} bilhões em {p2}, com pico de <strong>R$ {bi(ind['valor_pico'])} bilhões em
        {ind['ano_pico']}</strong>, cai para R$ {bi(m3)} bilhões em {p3}, com vale de R$ {bi(ind['valor_vale'])}
        bilhões em {ind['ano_vale']}, e volta a R$ {bi(m4)} bilhões em {p4}. Em {ind['ano_pico_recente']} o valor
        chega a R$ {bi(ind['valor_pico_recente'])} bilhões. Os dados mostram <em>quando</em> o volume mudou, não
        <em>por que</em>: associar cada regime a políticas públicas ou ao ciclo econômico exigiria dados externos.
      </p>
      <figure>
        {figuras['mensal']}
        <figcaption>Figura 2: Valor contratado por mês e média móvel de 12 meses ({inicio}-{fim}).</figcaption>
      </figure>
      <p>
        A série mensal é muito irregular, e poucas operações movem o total. O mês de maior valor é
        {mes_ano_extenso(ind['mes_pico'])}, com R$ {bi(ind['valor_mes_pico'])} bilhões, e o maior cliente daquele mês,
        {esc(nome_proprio(ind['cliente_mes_pico']))}, responde sozinho por
        R$ {bi(ind['valor_cliente_mes_pico'])} bilhões.
        A média móvel suaviza esse ruído e deixa visíveis os regimes da Figura 1.
      </p>
      <figure>
        {figuras['sazonal']}
        <figcaption>Figura 3: Participação de cada mês do ano no valor contratado entre {inicio} e {fim}. Out.-dez.
          em azul escuro.</figcaption>
      </figure>
      <p>
        Há uma marca sazonal clara: <strong>{pct(ind['participacao_quarto_trimestre'])} do valor</strong> é
        contratado de outubro a dezembro, contra os {pct(etl.LIMIAR_TRIMESTRE_UNIFORME, 0)} que uma distribuição
        uniforme daria a um trimestre, e dezembro sozinho concentra {pct(ind['participacao_dezembro_valor'])} do
        valor e {pct(ind['participacao_dezembro_subcreditos'])} dos subcréditos. O padrão não depende de um ano
        atípico: o quarto trimestre passa de {pct(etl.LIMIAR_TRIMESTRE_UNIFORME, 0)} em
        {ind['anos_q4_acima_uniforme']} dos {ind['anos_completos']} anos completos, e sem {ind['ano_pico']} a
        participação continua em {pct(ind['quarto_trimestre_sem_ano_pico'])}. É compatível com o fechamento de
        contratos ao fim do ano, mas a base não permite confirmar a causa.
      </p>
"""


def tabela_porte(ind: dict) -> str:
    linhas = "".join(
        f"<tr><td>{porte.capitalize()}</td><td>{num(linha_de(ind['porte'], porte)['subcreditos'])}</td>"
        f"<td>{bi(linha_de(ind['porte'], porte)['valor_contratado'])}</td>"
        f"<td>{pct(linha_de(ind['porte'], porte)['participacao'])}</td>"
        f"<td>{dec(linha_de(ind['porte'], porte)['mediana_subcredito'] / 1e6, 2)}</td></tr>"
        for porte in reversed(etl.PORTES)
    )
    return f"""<div class="tabela-rolagem">
        <table class="dados">
          <caption>Valor contratado por porte do cliente</caption>
          <thead><tr><th scope="col">Porte</th><th scope="col">Subcréditos</th><th scope="col">Valor (R$ bi)</th>
            <th scope="col">Participação</th><th scope="col">Mediana (R$ mi)</th></tr></thead>
          <tbody>{linhas}</tbody>
        </table>
      </div>"""


def secao_rq2(ind: dict, figuras: dict[str, str]) -> str:
    porte = linha_de(ind["porte"], etl.PORTES[-1])
    micro = linha_de(ind["porte"], etl.PORTES[0])
    setor, regiao, uf = ind["setor"], ind["regiao"], ind["uf"]
    sem_uf = linha_de(regiao, etl.SEM_UF_UNICA)["participacao"]
    maiores = ind["maiores_clientes"]
    lista_maiores = ", ".join(f"{esc(nome_proprio(nome))} (R$ {bi(valor)} bi)" for nome, valor in maiores.items())
    gini_texto = dec(ind["gini_clientes"], 2)
    alt_lorenz = f"Curva de Lorenz do valor contratado por cliente, com Gini de {gini_texto}"
    return f"""
      <h3 class="sub">3.2 RQ2: concentração do valor contratado</h3>
      <figure>
        {figuras['porte']}
        <figcaption>Figura 4: Participação de cada porte no valor contratado (%) e mediana por subcrédito
          (R$ milhões).</figcaption>
      </figure>
      {tabela_porte(ind)}
      <p>
        Os clientes de porte grande ficam com {pct(porte['participacao'])} do valor, e a mediana por subcrédito é de
        R$ {dec(porte['mediana_subcredito'] / 1e6)} milhões, contra R$ {dec(micro['mediana_subcredito'] / 1e6)}
        milhão das microempresas. A concentração por porte é a mais intensa das dimensões analisadas.
      </p>
      <figure>
        {figuras['setor']}
        <figcaption>Figura 5: Participação por setor BNDES e por região do país no valor contratado (%).</figcaption>
      </figure>
      <p>
        Por setor, a infraestrutura responde por {pct(linha_de(setor, etl.SETOR_INFRAESTRUTURA)['participacao'])} do
        valor, a indústria por {pct(linha_de(setor, etl.SETOR_INDUSTRIA)['participacao'])}, comércio e serviços por
        {pct(linha_de(setor, etl.SETOR_COMERCIO_SERVICOS)['participacao'])} e a agropecuária por
        {pct(linha_de(setor, etl.SETOR_AGROPECUARIA)['participacao'])}. Por região, o {etl.REGIAO_PRINCIPAL} lidera
        com {pct(linha_de(regiao, etl.REGIAO_PRINCIPAL)['participacao'])}, com São Paulo
        ({pct(linha_de(uf, 'SP')['participacao'])}) e Rio de Janeiro ({pct(linha_de(uf, 'RJ')['participacao'])}) à
        frente. Um dado relevante é que {pct(sem_uf)} do valor está em operações sem UF única (código
        <code>IE</code>), em geral de empresas com projetos em vários estados; por isso a leitura regional
        subestima o peso real das regiões.
      </p>
      <figure>
        <img src="assets/fig_lorenz.png" alt="{alt_lorenz}" loading="lazy" width="620">
        <figcaption>Figura 6: Curva de Lorenz do valor contratado por cliente (Gini = {gini_texto}).</figcaption>
      </figure>
      <p>
        Entre os {num(ind['clientes'])} clientes, o coeficiente de Gini é {gini_texto}: o 1% maior
        ({ind['quantidade_topo_clientes']} clientes) concentra {pct(ind['top1pct_clientes'])} do valor, e os dez
        maiores, {pct(ind['top10_clientes'])}. Os cinco maiores são {lista_maiores}. Ainda assim, nenhum cliente
        domina sozinho: o maior tem {pct(maiores.iloc[0] / ind['total_contratado'])} do total.
      </p>
"""


def secao_rq3(ind: dict, figuras: dict[str, str]) -> str:
    corr, corr_geral = ind["correlacao_reembolsaveis"], ind["correlacao_geral"]
    inov = ind["inovacao"]
    sim, nao = inov.loc[etl.INOVACAO_SIM], inov.loc[etl.INOVACAO_NAO]
    alt_correlacao = "Matriz de correlação de Spearman entre valor, juros e prazos nas operações reembolsáveis"
    return f"""
      <h3 class="sub">3.3 RQ3: valor, prazo e juros</h3>
      <p>
        As operações <em>não reembolsáveis</em> ({pct(ind['participacao_nao_reembolsavel_linhas'])} das linhas e
        {pct(ind['participacao_nao_reembolsavel_valor'])} do valor) têm juros e prazos iguais a zero por definição.
        Misturadas às demais, elas inflam a correlação entre valor e prazo de amortização para
        {dec(correlacao_de(corr_geral, (VALOR, AMORTIZACAO)), 2)}. A análise a seguir usa só as
        {num(ind['reembolsaveis'])} operações reembolsáveis.
      </p>
      <figure>
        <img src="assets/fig_correlacao.png" alt="{alt_correlacao}" loading="lazy" width="560">
        <figcaption>Figura 7: Correlação de Spearman entre valor, juros e prazos nas operações
          reembolsáveis.</figcaption>
      </figure>
      <p>
        As relações são fracas: valor × amortização {dec(correlacao_de(corr, (VALOR, AMORTIZACAO)), 2)}, valor ×
        carência {dec(correlacao_de(corr, (VALOR, CARENCIA)), 2)} e valor × juros
        {dec(correlacao_de(corr, (VALOR, JUROS)), 2)}. O tamanho da operação quase não explica o custo, e o prazo é
        a única condição que cresce de forma perceptível com o valor.
      </p>
      <figure>
        {figuras['dispersao']}
        <figcaption>Figura 8: Valor contratado e prazo de amortização nas operações reembolsáveis (amostra de
          {num(etl.AMOSTRA_DISPERSAO)} subcréditos, escala logarítmica no eixo vertical).</figcaption>
      </figure>
      <figure>
        {figuras['inovacao']}
        <figcaption>Figura 9: Valor mediano (R$ milhões), prazo de amortização mediano (meses) e juros medianos
          (%) nas operações reembolsáveis, com e sem apoio à inovação.</figcaption>
      </figure>
      <p>
        No apoio à inovação ({pct(ind['participacao_inovacao_linhas'])} das linhas), o valor mediano é menor
        (R$ {dec(sim['valor_mediano'] / 1e6)} milhões contra R$ {dec(nao['valor_mediano'] / 1e6)} milhões), a
        amortização é mais curta ({dec(sim['amortizacao_mediana'], 0)} contra {dec(nao['amortizacao_mediana'], 0)}
        meses) e os juros medianos ficam um pouco acima ({dec(sim['juros_mediano'], 2)}% contra
        {dec(nao['juros_mediano'], 2)}%). A comparação é descritiva: porte, setor e instrumento financeiro também
        diferem entre os grupos, e não foram controlados.
      </p>
"""


def secao_resultados(ind: dict, figuras: dict[str, str]) -> str:
    fim = etl.ANO_COMPLETO_FINAL
    return f"""
    <section id="resultados">
      <h2>3. Resultados e Discussão</h2>
      <p>
        O valor total contratado na base é de R$ {bi(ind['total_contratado'])} bilhões, dos quais
        R$ {bi(ind['total_desembolsado'])} bilhões foram desembolsados ({pct(ind['taxa_execucao'])}). Como
        os dados de {ind['ultima_data'].year} terminam em {dia_mes_extenso(ind['ultima_data'])}, as comparações
        anuais usam
        {ind['primeira_data'].year}-{fim}. Os gráficos são interativos: passe o mouse para ver os valores.
      </p>
{secao_rq1(ind, figuras)}{secao_rq2(ind, figuras)}{secao_rq3(ind, figuras)}    </section>
"""


def secao_conclusao(ind: dict) -> str:
    porte = linha_de(ind["porte"], etl.PORTES[-1])["participacao"]
    infraestrutura = linha_de(ind["setor"], etl.SETOR_INFRAESTRUTURA)["participacao"]
    principal = linha_de(ind["regiao"], etl.REGIAO_PRINCIPAL)["participacao"]
    sem_uf = linha_de(ind["regiao"], etl.SEM_UF_UNICA)["participacao"]
    sens = ind["sensibilidade_sem_repetidas"]
    return f"""
    <section id="conclusao">
      <h2>4. Conclusão</h2>
      <p>
        O valor contratado em operações não automáticas do BNDES passa por regimes distintos entre
        {ind['primeira_data'].year} e {etl.ANO_COMPLETO_FINAL}, com pico em {ind['ano_pico']} e vale em
        {ind['ano_vale']}, e concentra {pct(ind['participacao_quarto_trimestre'])} do total no quarto trimestre. A
        concentração é forte em clientes de grande porte ({pct(porte)}), em infraestrutura ({pct(infraestrutura)}) e
        no {etl.REGIAO_PRINCIPAL} ({pct(principal)}), e o Gini entre clientes é {dec(ind['gini_clientes'], 2)}. Nas
        operações reembolsáveis, valor, prazo e juros se relacionam de forma fraca, e o apoio à inovação tem
        operações menores e de prazo mais curto.
      </p>
      <p>
        <strong>Limitações.</strong> A base cobre só as operações não automáticas, não o total de financiamentos do
        banco; {ind['ultima_data'].year} está incompleto; os valores são nominais, sem correção pela inflação; a
        região é derivada da UF e {pct(sem_uf)} do valor não tem UF única; e as associações são descritivas, sem
        controle de variáveis. Na análise de sensibilidade, excluir as linhas repetidas reduz o total em
        {pct(abs(sens['variacao_total']))} e deixa as conclusões praticamente iguais: o pico segue em
        {sens['ano_pico']} e o vale em {sens['ano_vale']}, o quarto trimestre passa de
        {pct(ind['participacao_quarto_trimestre'])} para {pct(sens['participacao_quarto_trimestre'])}, o Gini entre
        clientes vai de {dec(ind['gini_clientes'], 3)} a {dec(sens['gini_clientes'], 3)} e a participação dos
        clientes grandes, de {pct(porte, 2)} para {pct(sens['participacao_porte_maior'], 2)}.
      </p>
      <p>
        <strong>Trabalhos futuros.</strong> Deflacionar os valores (por exemplo, pelo IPCA), incluir as operações
        indiretas automáticas (arquivo de cerca de 1,2 GB, que exigiria processamento em blocos), comparar com
        indicadores regionais e testar modelos que controlem porte, setor e instrumento ao estimar prazo e juros.
      </p>
    </section>
"""


def secao_fair() -> str:
    tamanho_bruto_mb = etl.CAMINHO_BRUTO.stat().st_size / 1e6
    return f"""
    <section id="fair">
      <h2>5. Disponibilidade dos Dados e Declaração FAIR</h2>
      <div class="fair-box">
        <h3>Declaração de Aderência FAIR</h3>
        <ul>
          <li><strong>Findable (Localizável):</strong> o <code>README.md</code> traz resumo, palavras-chave,
            identificação de autoria, disciplina e semestre, e o link permanente da fonte original dos dados
            ({URL_FONTE}).</li>
          <li><strong>Accessible (Acessível):</strong> repositório público, dados brutos incluídos
            ({num(tamanho_bruto_mb)} MB), sem autenticação ou credenciais; o artigo é servido pelo GitHub
            Pages, com layout responsivo.</li>
          <li><strong>Interoperable (Interoperável):</strong> dicionário de dados em
            <code>data/data_dictionary.md</code>; dados tratados em Parquet e CSV comprimido; relatório do
            tratamento em JSON.</li>
          <li><strong>Reusable (Reutilizável):</strong> código sob licença MIT, texto e figuras sob CC BY 4.0, dados
            sob ODbL (BNDES); <code>requirements.txt</code> com todas as versões congeladas.</li>
        </ul>
      </div>
      <p style="margin-top:1.2rem">Para clonar o repositório e reproduzir o pipeline, a análise e este artigo:</p>
      <pre><code>git clone {REPOSITORIO}.git
cd projeto-g1
python -m venv .venv
.venv\\Scripts\\activate          # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python -m src.etl                # data/raw -> data/processed
jupyter notebook notebooks/analise_exploratoria.ipynb
python -m src.gerar_artigo       # regenera docs/index.html</code></pre>
    </section>
"""


def secao_referencias() -> str:
    return f"""
    <section id="referencias" class="references">
      <h2>6. Referências</h2>
      <ol>
        <li>BNDES. <em>Dados Abertos: Operações de Financiamento</em>. Rio de Janeiro: Banco Nacional de
          Desenvolvimento Econômico e Social, 2026. Disponível em: &lt;{URL_FONTE}&gt;. Acesso em: {DATA_ACESSO}.</li>
        <li>HARRIS, C. R. et al. Array programming with NumPy. <em>Nature</em>, v. 585, p. 357-362, 2020.</li>
        <li>HUNTER, J. D. Matplotlib: a 2D graphics environment. <em>Computing in Science &amp; Engineering</em>,
          v. 9, n. 3, p. 90-95, 2007.</li>
        <li>MCKINNEY, W. Data structures for statistical computing in Python. In: PYTHON IN SCIENCE CONFERENCE, 9.,
          2010, Austin. <em>Proceedings</em> [...]. Austin: SciPy, 2010. p. 56-61.</li>
        <li>PLOTLY TECHNOLOGIES INC. <em>Collaborative data science</em>. Montreal: Plotly Technologies Inc.,
          2015. Disponível em:
          &lt;https://plotly.com&gt;.</li>
        <li>WASKOM, M. L. seaborn: statistical data visualization. <em>Journal of Open Source Software</em>, v. 6,
          n. 60, p. 3021, 2021.</li>
        <li>WILKINSON, M. D. et al. The FAIR Guiding Principles for scientific data management and stewardship.
          <em>Scientific Data</em>, v. 3, p. 160018, 2016.</li>
      </ol>
    </section>
"""


def montar_pagina(corpo: str) -> str:
    css = ARQUIVO_CSS.read_text(encoding="utf-8")
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="{esc(DESCRICAO_PAGINA)}">
  <meta name="keywords" content="{esc(', '.join(PALAVRAS_CHAVE))}">
  <meta name="author" content="{esc(AUTOR)}">
  <link rel="icon" href="data:,">
  <title>{esc(TITULO_PAGINA)}</title>
  <script src="assets/plotly.min.js"></script>
  <style>{css}  </style>
</head>
<body>

  <div class="container">{corpo}  </div>

</body>
</html>
"""


def gerar() -> str:
    df = etl.carregar_processado()
    ind = etl.calcular_indicadores(df)
    validar_afirmacoes(ind)
    relatorio = json.loads((etl.PASTA_PROCESSADA / "relatorio_etl.json").read_text(encoding="utf-8"))
    figuras = montar_figuras(df, ind)
    corpo = "".join((
        secao_cabecalho(montar_resumo(ind)),
        secao_introducao(ind),
        secao_metodologia(ind, relatorio),
        secao_resultados(ind, figuras),
        secao_conclusao(ind),
        secao_fair(),
        secao_referencias(),
    ))
    return montar_pagina(corpo)


def copiar_plotly() -> None:
    """Copia o plotly.min.js do pacote instalado, para o artigo funcionar sem CDN."""
    origem = Path(plotly.__file__).parent / "package_data" / "plotly.min.js"
    shutil.copyfile(origem, DESTINO.parent / "assets" / "plotly.min.js")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    (DESTINO.parent / "assets").mkdir(parents=True, exist_ok=True)
    copiar_plotly()
    DESTINO.write_text(gerar(), encoding="utf-8")
    LOGGER.info("Artigo gerado em %s", DESTINO)


if __name__ == "__main__":
    main()
