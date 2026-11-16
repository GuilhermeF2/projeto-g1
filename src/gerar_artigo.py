"""Gera docs/index.html (artigo acadêmico) a partir da base tratada.

Uso: python -m src.gerar_artigo
Todos os números do texto vêm de etl.calcular_indicadores, então o artigo acompanha os dados.
"""
from __future__ import annotations

import html
import inspect
import json
from datetime import date
from pathlib import Path

import shutil

import plotly

from src import etl, visualizacao as viz

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "docs" / "index.html"

AUTOR = "Guilherme Felix"
CURSO = "Bacharelado em Sistemas de Informação, 6º período"
DISCIPLINA = "Linguagem de Programação (Análise e Visualização de Dados com Python)"
PROFESSOR = "Alexandre Neves Louzada"
SEMESTRE = "Semestre 2026.2"
INSTITUICAO = "Universidade LaSalle"
REPOSITORIO = "https://github.com/GuilhermeF2/projeto-g1"
URL_FONTE = "https://dadosabertos.bndes.gov.br/dataset/operacoes-financiamento"
DATA_ACESSO = "16 nov. 2026"
PALAVRAS_CHAVE = ["BNDES", "financiamento", "dados abertos", "análise exploratória", "Python", "princípios FAIR"]


def num(valor: float) -> str:
    return f"{valor:,.0f}".replace(",", ".")


def dec(valor: float, casas: int = 1) -> str:
    return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def bi(valor: float, casas: int = 1) -> str:
    return dec(valor / 1e9, casas)


def pct(fracao: float, casas: int = 1) -> str:
    return dec(fracao * 100, casas) + "%"


BARRA = chr(92)


def json_seguro(objeto) -> str:
    texto = json.dumps(objeto, ensure_ascii=False)
    return texto.replace("<", BARRA + "u003c").replace(">", BARRA + "u003e").replace("&", BARRA + "u0026")


def bloco_plotly(identificador: str, figura) -> str:
    estrutura = json.loads(figura.to_json())
    dados = json_seguro(estrutura["data"])
    layout = json_seguro(estrutura["layout"])
    return (
        f'<div id="{identificador}" class="chart-container"></div>\n'
        f"<script>Plotly.newPlot('{identificador}', {dados}, {layout}, "
        f"{{responsive: true, displayModeBar: false}});</script>"
    )


def trecho_codigo(*funcoes) -> str:
    codigo = "\n\n".join(inspect.getsource(funcao).rstrip() for funcao in funcoes)
    return f"<pre><code>{html.escape(codigo)}</code></pre>"


def montar_resumo(i: dict) -> str:
    porte = i["porte"].set_index("porte_do_cliente")
    setor = i["setor"].set_index("setor_bndes")
    corr = i["correlacao_reembolsaveis"]
    pares = [corr.iloc[0, 1], corr.iloc[0, 2], corr.iloc[0, 3], corr.iloc[1, 2], corr.iloc[1, 3], corr.iloc[2, 3]]
    return (
        f"Este estudo analisa {num(i['subcreditos'])} subcréditos de financiamentos não automáticos do Banco Nacional de "
        f"Desenvolvimento Econômico e Social (BNDES), contratados entre janeiro de 2002 e setembro de 2026 e publicados "
        f"como dados abertos. Foi construído um pipeline determinístico em Python (pandas e NumPy) que lê o arquivo em "
        f"Windows-1252, converte tipos, padroniza categorias e sinaliza inconsistências sem descartar linhas, gravando a "
        f"base tratada em formatos abertos. A análise responde a três perguntas: a evolução do valor contratado, a "
        f"concentração por porte, setor, região e cliente, e a relação entre valor, prazo e juros. O valor anual passou "
        f"por quatro regimes, com pico de R$ {bi(i['valor_pico'])} bilhões em {i['ano_pico']} e vale de R$ "
        f"{bi(i['valor_vale'])} bilhões em {i['ano_vale']}, e {pct(i['participacao_quarto_trimestre'])} do valor é "
        f"contratado de outubro a dezembro. A concentração é elevada: clientes grandes respondem por "
        f"{pct(porte.loc['GRANDE', 'participacao'])} do valor, a infraestrutura por {pct(setor.loc['INFRAESTRUTURA', 'participacao'])} "
        f"e o coeficiente de Gini entre clientes é {dec(i['gini_clientes'], 2)}. Nas operações reembolsáveis, valor, prazo e "
        f"juros se associam de forma fraca (correlação de Spearman entre {dec(min(pares), 2)} e {dec(max(pares), 2)}), e o "
        f"apoio à inovação tem valores e prazos menores. Os resultados são descritivos, com limitações de cobertura e de "
        f"valores nominais. Código, dados e artigo seguem os princípios FAIR."
    )


CSS = """
    :root {
      --primary: #1e3a8a; --primary-light: #3b82f6; --text: #1f2937; --text-muted: #4b5563; --bg: #f8fafc;
      --surface: #ffffff; --border: #e2e8f0; --code-bg: #f1f5f9;
      --font-serif: "Merriweather", Georgia, serif;
      --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: var(--font-serif); font-size: 1.05rem; line-height: 1.8; color: var(--text);
           background-color: var(--bg); padding: 2rem 1rem; }
    .container { max-width: 900px; margin: 0 auto; background: var(--surface); padding: 3.5rem 4rem;
                 border-radius: 8px; box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05); border: 1px solid var(--border); }
    header { border-bottom: 2px solid var(--border); padding-bottom: 2rem; margin-bottom: 2.5rem; }
    h1.paper-title { font-family: var(--font-sans); font-size: 2.1rem; font-weight: 700; line-height: 1.3;
                     color: var(--primary); margin-bottom: 1.2rem; }
    .meta-block { font-family: var(--font-sans); font-size: 0.95rem; color: var(--text-muted); margin-bottom: 0.8rem; }
    .authors { font-weight: 600; color: var(--text); }
    .affiliations { font-style: italic; }
    .badges { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 1rem; font-family: var(--font-sans); }
    .badge { padding: 0.2rem 0.6rem; border-radius: 4px; font-size: 0.78rem; font-weight: 600;
             background: var(--code-bg); border: 1px solid var(--border); color: var(--primary); }
    .repo-badge { display: inline-block; margin-top: 1rem; padding: 0.4rem 0.8rem; background: var(--code-bg);
                  border: 1px solid var(--border); border-radius: 4px; text-decoration: none; color: var(--primary);
                  font-family: var(--font-sans); font-size: 0.85rem; font-weight: 500; transition: background 0.2s ease; }
    .repo-badge:hover { background: #e2e8f0; }
    .abstract-box { font-family: var(--font-sans); background-color: var(--bg); border-left: 4px solid var(--primary-light);
                    padding: 1.25rem 1.5rem; margin-bottom: 2.5rem; border-radius: 0 4px 4px 0; }
    .abstract-box h3 { font-size: 1rem; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem;
                       color: var(--primary); }
    .abstract-box p { font-size: 0.95rem; line-height: 1.6; text-align: justify; margin-bottom: 0; }
    .keywords { margin-top: 0.8rem; font-size: 0.9rem; color: var(--text-muted); }
    nav.toc { font-family: var(--font-sans); background: #fdfefe; border: 1px solid var(--border); border-radius: 6px;
              padding: 1.2rem 1.8rem; margin-bottom: 2.5rem; }
    nav.toc h4 { font-size: 1rem; color: var(--primary); margin-bottom: 0.6rem; }
    nav.toc ol { padding-left: 1.2rem; }
    nav.toc li { margin: 0.3rem 0; }
    nav.toc a { color: var(--text-muted); text-decoration: none; font-size: 0.92rem; }
    nav.toc a:hover { color: var(--primary-light); text-decoration: underline; }
    section { margin-bottom: 2.5rem; }
    h2 { font-family: var(--font-sans); font-size: 1.45rem; font-weight: 600; color: var(--primary);
         border-bottom: 1px solid var(--border); padding-bottom: 0.4rem; margin-bottom: 1rem; margin-top: 2rem; }
    h3.sub { font-family: var(--font-sans); font-size: 1.15rem; font-weight: 600; color: var(--text); margin: 1.6rem 0 0.6rem; }
    p { margin-bottom: 1.2rem; text-align: justify; }
    p, li { overflow-wrap: anywhere; }
    ul.lista { margin: 0 0 1.2rem 1.4rem; }
    ul.lista li { margin-bottom: 0.4rem; }
    figure { margin: 2rem 0; text-align: center; }
    figure img { max-width: 100%; height: auto; border: 1px solid var(--border); border-radius: 6px; background: #fff; }
    .chart-container { width: 100%; min-height: 380px; border: 1px solid var(--border); border-radius: 6px; background: #fff; }
    figcaption { font-family: var(--font-sans); font-size: 0.85rem; color: var(--text-muted); margin-top: 0.6rem; text-align: center; }
    pre, code { font-family: Consolas, "Courier New", monospace; font-size: 0.85rem; background-color: var(--code-bg); }
    code { padding: 0.2rem 0.4rem; border-radius: 3px; }
    pre { padding: 1rem; border-radius: 6px; overflow-x: auto; margin-bottom: 1.2rem; border: 1px solid var(--border); line-height: 1.5; }
    pre code { padding: 0; background: none; }
    .fair-box { font-family: var(--font-sans); border: 1px solid #bfdbfe; background-color: #eff6ff; border-radius: 6px;
                padding: 1.25rem; margin-top: 2rem; }
    .fair-box h3 { font-size: 1rem; color: #1e40af; margin-bottom: 0.5rem; }
    .fair-box ul { margin-left: 1.2rem; font-size: 0.92rem; color: #1e3a8a; }
    .fair-box li { margin-bottom: 0.4rem; }
    .references ol { padding-left: 1.2rem; font-size: 0.9rem; color: var(--text-muted); }
    .references li { margin-bottom: 0.6rem; }
    table.dados { font-family: var(--font-sans); border-collapse: collapse; width: 100%; font-size: 0.9rem; margin: 1rem 0 1.4rem; }
    table.dados th, table.dados td { border-bottom: 1px solid var(--border); padding: 0.45rem 0.6rem; text-align: right; }
    table.dados th:first-child, table.dados td:first-child { text-align: left; }
    table.dados th { color: var(--primary); }
    .tabela-rolagem { overflow-x: auto; }
    @media (max-width: 768px) {
      body { padding: 1rem 0.5rem; }
      .container { padding: 1.5rem; }
      h1.paper-title { font-size: 1.6rem; }
      .chart-container { min-height: 320px; }
    }
"""


def gerar() -> str:
    df = etl.carregar_processado()
    i = etl.calcular_indicadores(df)
    relatorio = json.loads((etl.PASTA_PROCESSADA / "relatorio_etl.json").read_text(encoding="utf-8"))

    porte = i["porte"].set_index("porte_do_cliente")
    setor = i["setor"].set_index("setor_bndes")
    regiao = i["regiao"].set_index("regiao")
    uf = i["uf"].set_index("uf")
    anual = i["anual"]
    corr = i["correlacao_reembolsaveis"]
    corr_geral = i["correlacao_geral"]
    inov = i["inovacao"]
    mensal_q4 = i["participacao_quarto_trimestre"]
    maiores = i["maiores_clientes"]
    n_top1 = max(1, int(i["clientes"] * 0.01))

    resumo = montar_resumo(i)
    palavras_resumo = len(resumo.split())
    assert 150 <= palavras_resumo <= 250, palavras_resumo

    figuras = {
        "fig-anual": bloco_plotly("fig-anual", viz.fig_evolucao_anual(df)),
        "fig-mensal": bloco_plotly("fig-mensal", viz.fig_serie_mensal(df)),
        "fig-sazonal": bloco_plotly("fig-sazonal", viz.fig_sazonalidade_mensal(df)),
        "fig-porte": bloco_plotly("fig-porte", viz.fig_porte(df)),
        "fig-setor": bloco_plotly("fig-setor", viz.fig_setor_regiao(df)),
        "fig-dispersao": bloco_plotly("fig-dispersao", viz.fig_dispersao(df)),
        "fig-inovacao": bloco_plotly("fig-inovacao", viz.fig_inovacao(df)),
    }

    linhas_porte = "".join(
        f"<tr><td>{p.capitalize()}</td><td>{num(porte.loc[p, 'subcreditos'])}</td>"
        f"<td>{bi(porte.loc[p, 'valor_contratado'])}</td><td>{pct(porte.loc[p, 'participacao'])}</td>"
        f"<td>{dec(porte.loc[p, 'mediana_subcredito'] / 1e6, 2)}</td></tr>"
        for p in viz.ORDEM_PORTE[::-1]
    )

    afiliacao = f"{CURSO}" + (f" — {INSTITUICAO}" if INSTITUICAO else "")
    pares_corr = {
        "valor × amortização": corr.iloc[0, 3], "valor × carência": corr.iloc[0, 2], "valor × juros": corr.iloc[0, 1],
        "carência × amortização": corr.iloc[2, 3], "juros × carência": corr.iloc[1, 2], "juros × amortização": corr.iloc[1, 3],
    }

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="Análise exploratória dos financiamentos não automáticos do BNDES (2002-2026) com Python, sob princípios FAIR.">
  <meta name="keywords" content="{', '.join(PALAVRAS_CHAVE)}">
  <meta name="author" content="{AUTOR}">
  <link rel="icon" href="data:,">
  <title>Financiamentos do BNDES (2002-2026): análise exploratória em Python sob princípios FAIR</title>
  <script src="assets/plotly.min.js"></script>
  <style>{CSS}  </style>
</head>
<body>

  <div class="container">
    <header>
      <h1 class="paper-title">Concentração e regimes do crédito não automático do BNDES (2002-2026): uma análise exploratória em Python sob princípios FAIR</h1>

      <div class="meta-block authors">{AUTOR}</div>

      <div class="meta-block affiliations">
        {afiliacao}<br>
        Disciplina: {DISCIPLINA}<br>
        Professor: {PROFESSOR} · {SEMESTRE}
      </div>

      <div class="badges">
        <span class="badge">Código: MIT</span>
        <span class="badge">Dados: ODbL (BNDES)</span>
        <span class="badge">Texto e figuras: CC BY 4.0</span>
        <span class="badge">Python 3.12</span>
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
        <strong>Palavras-chave:</strong> {', '.join(PALAVRAS_CHAVE)}.
      </div>
    </div>

    <nav class="toc">
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

    <section id="intro">
      <h2>1. Introdução</h2>
      <p>
        O BNDES é um dos principais instrumentos de crédito de longo prazo do país e publica, em seu portal de dados abertos, o
        detalhe das operações que contrata. A disponibilidade dos dados, porém, não basta: é preciso um fluxo de trabalho que
        trate as peculiaridades do arquivo, registre cada decisão e permita que outra pessoa chegue aos mesmos números
        (WILKINSON et al., 2016). Este trabalho parte das operações de financiamento <em>não automáticas</em>, em que cada
        contrato é analisado individualmente pelo banco, e examina como o volume contratado se comporta ao longo do tempo,
        como ele se distribui entre os clientes e quais condições financeiras acompanham o valor.
      </p>
      <p>O estudo responde a três perguntas de pesquisa:</p>
      <ul class="lista">
        <li><strong>RQ1.</strong> Como evoluiu o valor contratado entre 2002 e 2025, e quais períodos concentram picos e vales?</li>
        <li><strong>RQ2.</strong> Quão concentrado é o valor contratado por porte do cliente, setor, região e cliente?</li>
        <li><strong>RQ3.</strong> Como valor, prazo e juros se relacionam nas operações reembolsáveis, e o que muda no apoio à inovação?</li>
      </ul>
    </section>

    <section id="metodologia">
      <h2>2. Metodologia e Pipeline de Dados</h2>
      <h3 class="sub">2.1 Fonte e granularidade</h3>
      <p>
        Os dados são o recurso <em>Operações não automáticas</em> do conjunto <em>Operações de Financiamento</em>, publicado pelo
        BNDES sob licença ODbL (BNDES, 2026), acessado em {DATA_ACESSO}. O arquivo tem {num(relatorio['linhas'])} linhas e
        {relatorio['colunas_originais']} colunas, de {i['primeira_data']:%d/%m/%Y} a {i['ultima_data']:%d/%m/%Y}. Cada linha é um
        <strong>subcrédito</strong>: um contrato pode ter vários, com condições distintas, e a soma deles é o valor do contrato. A
        base reúne {num(i['contratos'])} contratos, {num(i['clientes'])} clientes (CNPJ) e {num(i['municipios'])} municípios. Por isso a
        unidade de análise é o subcrédito, e os valores são somados por contrato ou cliente quando a pergunta exige.
      </p>
      <h3 class="sub">2.2 Leitura e tratamento</h3>
      <p>
        O arquivo não é trivial: usa ponto e vírgula, codificação Windows-1252 (não UTF-8), vírgula decimal e o marcador
        <code>----------</code> no lugar de valores ausentes, com espaços à direita nas células. Todas as colunas são lidas como
        texto e convertidas de forma explícita. O tratamento segue uma regra: <strong>nenhuma linha é descartada</strong>. Cada
        inconsistência vira uma coluna de sinalização, e as contagens ficam em <code>relatorio_etl.json</code>, junto com o
        SHA-256 do arquivo bruto.
      </p>
      {trecho_codigo(etl.carregar_bruto, etl.converter_tipos)}
      <p>
        Cinco colunas trazem marcadores de ausente: a instituição credenciada ({num(relatorio['placeholders_convertidos_em_nulo']['instituicao_financeira_credenciada'])}
        linhas) é ausente por construção nas operações diretas; o tipo de excepcionalidade só existe para contratos a partir de
        2020; a fonte de recurso e a situação do contrato não têm explicação no dicionário e foram tratadas como não informadas.
        Os marcadores viram nulo, sem imputação. Também foram criadas a região do país a partir da UF, o prazo total, a taxa de
        execução (desembolsado sobre contratado) e três sinalizações:
      </p>
      {trecho_codigo(etl.sinalizar_inconsistencias)}
      <p>
        Foram sinalizadas {num(relatorio['linhas_sinalizadas']['repetida'])} linhas idênticas a outra anterior (que podem ser
        subcréditos legítimos de mesmo valor), {num(relatorio['linhas_sinalizadas']['desembolso_acima_contratado'])} linhas em que o
        desembolso supera o contratado ({pct(i['desembolso_acima'])}; o dicionário do BNDES atribui isso à correção por
        indexador) e {num(relatorio['linhas_sinalizadas']['outlier_valor'])} outliers de valor, que somam
        {pct(i['valor_outliers'])} do total. Como o valor por subcrédito é muito assimétrico (mediana de R$ 9,2 milhões e média
        acima de R$ 51 milhões), as análises usam medianas, escala logarítmica e a correlação de Spearman. A base tratada é
        gravada em Parquet e em CSV comprimido, com dicionário de dados em Markdown.
      </p>
    </section>

    <section id="resultados">
      <h2>3. Resultados e Discussão</h2>
      <p>
        O valor total contratado na base é de R$ {bi(i['total_contratado'])} bilhões, dos quais R$ {bi(i['total_desembolsado'])}
        bilhões foram desembolsados ({pct(i['taxa_execucao'])}). Como 2026 termina em 30 de setembro, as comparações anuais usam
        2002-2025. Os gráficos são interativos: passe o mouse para ver os valores.
      </p>

      <h3 class="sub">3.1 RQ1: evolução do valor contratado</h3>
      <figure>
        {figuras['fig-anual']}
        <figcaption>Figura 1: Valor contratado por ano, em R$ bilhões nominais. A barra clara é 2026*, parcial até setembro.</figcaption>
      </figure>
      <p>
        O valor anual não segue uma tendência única. A média anual é de R$ {bi(i['media_2002_2008'])} bilhões em 2002-2008, sobe para
        R$ {bi(i['media_2009_2014'])} bilhões em 2009-2014, com pico de <strong>R$ {bi(i['valor_pico'])} bilhões em {i['ano_pico']}</strong>,
        cai para R$ {bi(i['media_2015_2019'])} bilhões em 2015-2019, com vale de R$ {bi(i['valor_vale'])} bilhões em {i['ano_vale']}, e
        volta a R$ {bi(i['media_2020_2025'])} bilhões em 2020-2025. Em 2024 o valor chega a R$ {bi(anual.loc[2024, 'valor_contratado'])}
        bilhões. Os dados mostram <em>quando</em> o volume mudou, não <em>por que</em>: associar cada regime a políticas
        públicas ou ao ciclo econômico exigiria dados externos.
      </p>
      <figure>
        {figuras['fig-mensal']}
        <figcaption>Figura 2: Valor contratado por mês e média móvel de 12 meses (2002-2025).</figcaption>
      </figure>
      <p>
        A série mensal é muito irregular, e poucas operações movem o total. O mês de maior valor é {dec(i['valor_mes_pico'] / 1e9)}
        bilhões em {i['mes_pico']:%m/%Y}, e o maior cliente daquele mês, {html.escape(i['cliente_mes_pico'].title())}, responde sozinho por
        R$ {bi(i['valor_cliente_mes_pico'])} bilhões. A média móvel suaviza esse ruído e deixa visíveis os regimes da Figura 1.
      </p>
      <figure>
        {figuras['fig-sazonal']}
        <figcaption>Figura 3: Participação de cada mês do ano no valor contratado entre 2002 e 2025. Out.-dez. em azul escuro.</figcaption>
      </figure>
      <p>
        Há uma marca sazonal clara: <strong>{pct(mensal_q4)} do valor</strong> é contratado de outubro a dezembro, contra os 25% que
        uma distribuição uniforme daria a um trimestre, e dezembro sozinho concentra {pct(i['participacao_dezembro_valor'])} do valor e
        {pct(i['participacao_dezembro_subcreditos'])} dos subcréditos. O padrão não depende de um ano atípico: o quarto trimestre
        passa de 25% em {i['anos_q4_acima_uniforme']} dos {i['anos_completos']} anos completos, e sem 2012 a participação continua em
        {pct(i['quarto_trimestre_sem_2012'])}. É compatível com o fechamento de contratos ao fim do ano, mas a base não permite
        confirmar a causa.
      </p>

      <h3 class="sub">3.2 RQ2: concentração do valor contratado</h3>
      <figure>
        {figuras['fig-porte']}
        <figcaption>Figura 4: Participação de cada porte no valor contratado (%) e mediana por subcrédito (R$ milhões).</figcaption>
      </figure>
      <div class="tabela-rolagem">
        <table class="dados">
          <thead><tr><th>Porte</th><th>Subcréditos</th><th>Valor (R$ bi)</th><th>Participação</th><th>Mediana (R$ mi)</th></tr></thead>
          <tbody>{linhas_porte}</tbody>
        </table>
      </div>
      <p>
        Os clientes de porte grande ficam com {pct(porte.loc['GRANDE', 'participacao'])} do valor, e a mediana por subcrédito é
        de R$ {dec(porte.loc['GRANDE', 'mediana_subcredito'] / 1e6)} milhões, contra R$ {dec(porte.loc['MICRO', 'mediana_subcredito'] / 1e6)}
        milhão das microempresas. A concentração por porte é a mais intensa das dimensões analisadas.
      </p>
      <figure>
        {figuras['fig-setor']}
        <figcaption>Figura 5: Participação por setor BNDES e por região do país no valor contratado (%).</figcaption>
      </figure>
      <p>
        Por setor, a infraestrutura responde por {pct(setor.loc['INFRAESTRUTURA', 'participacao'])} do valor, a indústria por
        {pct(setor.loc['INDUSTRIA', 'participacao'])}, comércio e serviços por {pct(setor.loc['COMERCIO/SERVICOS', 'participacao'])} e a
        agropecuária por {pct(setor.loc['AGROPECUÁRIA', 'participacao'])}. Por região, o Sudeste lidera com
        {pct(regiao.loc['Sudeste', 'participacao'])}, com São Paulo ({pct(uf.loc['SP', 'participacao'])}) e Rio de Janeiro
        ({pct(uf.loc['RJ', 'participacao'])}) à frente. Um dado relevante é que {pct(regiao.loc[etl.SEM_UF_UNICA, 'participacao'])}
        do valor está em operações sem UF única (código <code>IE</code>), em geral de empresas com projetos em vários estados;
        por isso a leitura regional subestima o peso real das regiões.
      </p>
      <figure>
        <img src="assets/fig_lorenz.png" alt="Curva de Lorenz do valor contratado por cliente, com Gini de {dec(i['gini_clientes'], 2)}" loading="lazy" width="620">
        <figcaption>Figura 6: Curva de Lorenz do valor contratado por cliente (Gini = {dec(i['gini_clientes'], 2)}).</figcaption>
      </figure>
      <p>
        Entre os {num(i['clientes'])} clientes, o coeficiente de Gini é {dec(i['gini_clientes'], 2)}: o 1% maior ({n_top1} clientes)
        concentra {pct(i['top1pct_clientes'])} do valor, e os dez maiores, {pct(i['top10_clientes'])}. Os cinco maiores são
        {', '.join(f"{html.escape(nome.title())} (R$ {bi(valor)} bi)" for nome, valor in maiores.items())}. Ainda assim, nenhum cliente domina
        sozinho: o maior tem {pct(maiores.iloc[0] / i['total_contratado'])} do total.
      </p>

      <h3 class="sub">3.3 RQ3: valor, prazo e juros</h3>
      <p>
        As operações <em>não reembolsáveis</em> ({pct(i['participacao_nao_reembolsavel_linhas'])} das linhas e
        {pct(i['participacao_nao_reembolsavel_valor'])} do valor) têm juros e prazos iguais a zero por definição. Misturadas às demais,
        elas inflam a correlação entre valor e prazo de amortização para {dec(corr_geral.iloc[0, 3], 2)}. A análise a seguir usa só as
        {num(i['reembolsaveis'])} operações reembolsáveis.
      </p>
      <figure>
        <img src="assets/fig_correlacao.png" alt="Matriz de correlação de Spearman entre valor, juros e prazos nas operações reembolsáveis" loading="lazy" width="560">
        <figcaption>Figura 7: Correlação de Spearman entre valor, juros e prazos nas operações reembolsáveis.</figcaption>
      </figure>
      <p>
        As relações são fracas: valor × amortização {dec(pares_corr['valor × amortização'], 2)}, valor × carência
        {dec(pares_corr['valor × carência'], 2)} e valor × juros {dec(pares_corr['valor × juros'], 2)}. O tamanho da operação
        quase não explica o custo, e o prazo é a única condição que cresce de forma perceptível com o valor.
      </p>
      <figure>
        {figuras['fig-dispersao']}
        <figcaption>Figura 8: Valor contratado e prazo de amortização nas operações reembolsáveis (amostra de 3.000 subcréditos, escala logarítmica no eixo vertical).</figcaption>
      </figure>
      <figure>
        {figuras['fig-inovacao']}
        <figcaption>Figura 9: Valor mediano (R$ milhões), prazo de amortização mediano (meses) e juros medianos (% a.a.) nas operações reembolsáveis, com e sem apoio à inovação.</figcaption>
      </figure>
      <p>
        No apoio à inovação ({pct(i['participacao_inovacao_linhas'])} das linhas), o valor mediano é menor (R$ {dec(inov.loc['SIM', 'valor_mediano'] / 1e6)}
        milhões contra R$ {dec(inov.loc['NÃO', 'valor_mediano'] / 1e6)} milhões), a amortização é mais curta
        ({dec(inov.loc['SIM', 'amortizacao_mediana'], 0)} contra {dec(inov.loc['NÃO', 'amortizacao_mediana'], 0)} meses) e os juros
        medianos ficam um pouco acima ({dec(inov.loc['SIM', 'juros_mediano'], 2)}% contra {dec(inov.loc['NÃO', 'juros_mediano'], 2)}%).
        A comparação é descritiva: porte, setor e instrumento financeiro também diferem entre os grupos, e não foram controlados.
      </p>
    </section>

    <section id="conclusao">
      <h2>4. Conclusão</h2>
      <p>
        O valor contratado em operações não automáticas do BNDES passa por regimes distintos entre 2002 e 2025, com pico em
        {i['ano_pico']} e vale em {i['ano_vale']}, e concentra {pct(mensal_q4)} do total no quarto trimestre. A concentração é forte
        em clientes de grande porte ({pct(porte.loc['GRANDE', 'participacao'])}), em infraestrutura
        ({pct(setor.loc['INFRAESTRUTURA', 'participacao'])}) e no Sudeste ({pct(regiao.loc['Sudeste', 'participacao'])}), e o Gini entre
        clientes é {dec(i['gini_clientes'], 2)}. Nas operações reembolsáveis, valor, prazo e juros se relacionam de forma fraca, e
        o apoio à inovação tem operações menores e de prazo mais curto.
      </p>
      <p>
        <strong>Limitações.</strong> A base cobre só as operações não automáticas, não o total de financiamentos do banco; 2026 está
        incompleto; os valores são nominais, sem correção pela inflação; a região é derivada da UF e {pct(regiao.loc[etl.SEM_UF_UNICA, 'participacao'])}
        do valor não tem UF única; e as associações são descritivas, sem controle de variáveis. A análise de sensibilidade mostra que
        excluir as linhas repetidas mudaria o total em {pct(i['valor_linhas_repetidas'])}, sem alterar as conclusões.
      </p>
      <p>
        <strong>Trabalhos futuros.</strong> Deflacionar os valores (por exemplo, pelo IPCA), incluir as operações indiretas
        automáticas (arquivo de cerca de 1,2 GB, que exigiria processamento em blocos), comparar com indicadores regionais e testar
        modelos que controlem porte, setor e instrumento ao estimar prazo e juros.
      </p>
    </section>

    <section id="fair">
      <h2>5. Disponibilidade dos Dados e Declaração FAIR</h2>
      <div class="fair-box">
        <h3>Declaração de Aderência FAIR</h3>
        <ul>
          <li><strong>Findable (Localizável):</strong> o <code>README.md</code> traz resumo, palavras-chave, identificação de autoria, disciplina e semestre, e o link permanente da fonte original dos dados ({URL_FONTE}).</li>
          <li><strong>Accessible (Acessível):</strong> repositório público, dados brutos incluídos (20 MB), sem autenticação ou credenciais; o artigo é servido pelo GitHub Pages, com layout responsivo.</li>
          <li><strong>Interoperable (Interoperável):</strong> dicionário de dados em <code>data/data_dictionary.md</code>; dados tratados em Parquet e CSV comprimido; relatório do tratamento em JSON.</li>
          <li><strong>Reusable (Reutilizável):</strong> código sob licença MIT, texto e figuras sob CC BY 4.0, dados sob ODbL (BNDES); <code>requirements.txt</code> com todas as versões congeladas.</li>
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

    <section id="referencias" class="references">
      <h2>6. Referências</h2>
      <ol>
        <li>BNDES. <em>Dados Abertos: Operações de Financiamento</em>. Rio de Janeiro: Banco Nacional de Desenvolvimento Econômico e Social, 2026. Disponível em: &lt;{URL_FONTE}&gt;. Acesso em: {DATA_ACESSO}.</li>
        <li>HUNTER, J. D. Matplotlib: a 2D graphics environment. <em>Computing in Science &amp; Engineering</em>, v. 9, n. 3, p. 90-95, 2007.</li>
        <li>MCKINNEY, W. Data structures for statistical computing in Python. In: PYTHON IN SCIENCE CONFERENCE, 9., 2010, Austin. <em>Proceedings</em> [...]. Austin: SciPy, 2010. p. 56-61.</li>
        <li>PLOTLY TECHNOLOGIES INC. <em>Collaborative data science</em>. Montreal, 2015. Disponível em: &lt;https://plot.ly&gt;.</li>
        <li>WASKOM, M. L. seaborn: statistical data visualization. <em>Journal of Open Source Software</em>, v. 6, n. 60, p. 3021, 2021.</li>
        <li>WILKINSON, M. D. et al. The FAIR Guiding Principles for scientific data management and stewardship. <em>Scientific Data</em>, v. 3, p. 160018, 2016.</li>
      </ol>
    </section>
  </div>

</body>
</html>
"""


def copiar_plotly() -> None:
    origem = Path(plotly.__file__).parent / "package_data" / "plotly.min.js"
    shutil.copyfile(origem, DESTINO.parent / "assets" / "plotly.min.js")


if __name__ == "__main__":
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    (DESTINO.parent / "assets").mkdir(exist_ok=True)
    copiar_plotly()
    DESTINO.write_text(gerar(), encoding="utf-8")
    print(f"Artigo gerado em {DESTINO} ({date.today():%d/%m/%Y})")
