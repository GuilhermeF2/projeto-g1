"""ETL das operações de financiamento não automáticas do BNDES (dados abertos).

Uso: python -m src.etl
Lê data/raw, trata a base sem descartar linhas e grava data/processed.
"""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Final

import numpy as np
import pandas as pd

LOGGER = logging.getLogger(__name__)

RAIZ: Final = Path(__file__).resolve().parents[1]
CAMINHO_BRUTO: Final = RAIZ / "data" / "raw" / "operacoes-financiamento-operacoes-nao-automaticas.csv"
PASTA_PROCESSADA: Final = RAIZ / "data" / "processed"

CODIFICACAO: Final = "cp1252"
SEPARADOR: Final = ";"
PLACEHOLDERS: Final = frozenset({"", "-", "----------"})

COL_VALOR: Final = "valor_contratado_reais"
COL_DESEMBOLSO: Final = "valor_desembolsado_reais"
COLUNAS_VALOR: Final = [COL_VALOR, COL_DESEMBOLSO, "juros"]
COLUNAS_PRAZO: Final = ["prazo_carencia_meses", "prazo_amortizacao_meses"]
COLUNAS_CORRELACAO: Final = [COL_VALOR, "juros", "prazo_carencia_meses", "prazo_amortizacao_meses"]
COLUNAS_CATEGORIA: Final = [
    "uf", "fonte_de_recurso_desembolsos", "custo_financeiro", "modalidade_de_apoio", "forma_de_apoio", "produto",
    "inovacao", "area_operacional", "setor_cnae", "setor_bndes", "subsetor_bndes", "porte_do_cliente",
    "natureza_do_cliente", "tipo_de_garantia", "tipo_de_excepcionalidade", "situacao_do_contrato", "regiao",
]

MODALIDADE_NAO_REEMBOLSAVEL: Final = "NÃO REEMBOLSÁVEL"
INOVACAO_SIM: Final = "SIM"
INOVACAO_NAO: Final = "NÃO"
PORTES: Final = ("MICRO", "PEQUENA", "MÉDIA", "GRANDE")
SETOR_INFRAESTRUTURA: Final = "INFRAESTRUTURA"
SETOR_INDUSTRIA: Final = "INDUSTRIA"
SETOR_COMERCIO_SERVICOS: Final = "COMERCIO/SERVICOS"
SETOR_AGROPECUARIA: Final = "AGROPECUÁRIA"

REGIOES: Final = {
    "Norte": ["AC", "AM", "AP", "PA", "RO", "RR", "TO"],
    "Nordeste": ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"],
    "Centro-Oeste": ["DF", "GO", "MS", "MT"],
    "Sudeste": ["ES", "MG", "RJ", "SP"],
    "Sul": ["PR", "RS", "SC"],
}
REGIAO_POR_UF: Final = {uf: regiao for regiao, ufs in REGIOES.items() for uf in ufs}
SEM_UF_UNICA: Final = "Sem UF única"
REGIAO_PRINCIPAL: Final = "Sudeste"
CORRECOES_AREA: Final = {"AREA DE TRANSICAO ENERGETICA E CLIMA": "AREA DE TRANSICAO ENERGETICA E CLIMATICA"}

ANO_COMPLETO_FINAL: Final = 2025
PERIODOS: Final = ((2002, 2008), (2009, 2014), (2015, 2019), (2020, 2025))
TRIMESTRE_FINAL: Final = (10, 11, 12)
LIMIAR_TRIMESTRE_UNIFORME: Final = 0.25
FRACAO_TOPO_CLIENTES: Final = 0.01
AMOSTRA_DISPERSAO: Final = 3000
SEMENTE_AMOSTRA: Final = 42
FATOR_OUTLIER: Final = 1.5


def hash_arquivo(caminho: Path) -> str:
    """SHA-256 do arquivo, lido em blocos de 1 MB."""
    resumo = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1 << 20), b""):
            resumo.update(bloco)
    return resumo.hexdigest()


def carregar_bruto(caminho: Path = CAMINHO_BRUTO) -> pd.DataFrame:
    """Lê o CSV original com todas as colunas como texto, sem converter valores ausentes."""
    return pd.read_csv(caminho, sep=SEPARADOR, encoding=CODIFICACAO, dtype=str, keep_default_na=False)


def limpar_textos(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Remove espaços das bordas e troca os marcadores de ausente por nulo."""
    df = df.copy()
    marcadores = {}
    for coluna in df.columns:
        df[coluna] = df[coluna].str.strip()
        mascara = df[coluna].isin(PLACEHOLDERS)
        marcadores[coluna] = int(mascara.sum())
        df.loc[mascara, coluna] = pd.NA
    return df, {coluna: n for coluna, n in marcadores.items() if n}


def converter_tipos(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Converte valores, prazos, data e códigos, contando o que não pôde ser convertido."""
    df = df.copy()
    invalidos = {}
    for coluna in COLUNAS_VALOR:
        convertido = pd.to_numeric(df[coluna].str.replace(",", ".", regex=False), errors="coerce")
        invalidos[coluna] = int(convertido.isna().sum() - df[coluna].isna().sum())
        df[coluna] = convertido
    for coluna in COLUNAS_PRAZO:
        convertido = pd.to_numeric(df[coluna], errors="coerce")
        invalidos[coluna] = int(convertido.isna().sum() - df[coluna].isna().sum())
        df[coluna] = convertido.astype("Int64")

    df["data_da_contratacao"] = pd.to_datetime(df["data_da_contratacao"], format="%Y-%m-%d", errors="coerce")
    invalidos["data_da_contratacao"] = int(df["data_da_contratacao"].isna().sum())
    df["numero_do_contrato"] = df["numero_do_contrato"].astype("string")
    df["municipio_codigo"] = pd.to_numeric(df["municipio_codigo"], errors="coerce").astype("Int64")
    return df, {coluna: n for coluna, n in invalidos.items() if n}


def padronizar_categorias(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["area_operacional"] = df["area_operacional"].replace(CORRECOES_AREA)
    df["regiao"] = df["uf"].map(REGIAO_POR_UF).fillna(SEM_UF_UNICA)
    return df


def criar_atributos(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    datas = df["data_da_contratacao"]
    df["ano"] = datas.dt.year.astype("Int64")
    df["mes"] = datas.dt.month.astype("Int64")
    df["ano_mes"] = datas.dt.to_period("M").dt.to_timestamp()
    df["prazo_total_meses"] = df["prazo_carencia_meses"] + df["prazo_amortizacao_meses"]
    df["taxa_execucao"] = df[COL_DESEMBOLSO] / df[COL_VALOR]
    df["log10_valor_contratado"] = np.log10(df[COL_VALOR].where(df[COL_VALOR] > 0))
    return df


def limites_outlier(serie: pd.Series) -> tuple[float, float]:
    """Limites de outlier pelo critério de 1,5 × IQR."""
    q1, q3 = serie.quantile([0.25, 0.75])
    amplitude = q3 - q1
    return q1 - FATOR_OUTLIER * amplitude, q3 + FATOR_OUTLIER * amplitude


def sinalizar_inconsistencias(df: pd.DataFrame, colunas_originais: list[str]) -> pd.DataFrame:
    """Marca, sem remover, linhas repetidas, desembolso acima do contratado e outliers de valor."""
    df = df.copy()
    df["flag_linha_repetida"] = df.duplicated(subset=colunas_originais, keep="first")
    df["flag_desembolso_acima_contratado"] = df[COL_DESEMBOLSO] > df[COL_VALOR]
    inferior, superior = limites_outlier(df["log10_valor_contratado"])
    df["flag_outlier_valor"] = (df["log10_valor_contratado"] < inferior) | (df["log10_valor_contratado"] > superior)
    return df


def otimizar_tipos(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for coluna in COLUNAS_CATEGORIA:
        df[coluna] = df[coluna].astype("category")
    return df


def tratar(df_bruto: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Aplica o pipeline completo e devolve a base tratada e o relatório do tratamento."""
    colunas_originais = df_bruto.columns.tolist()
    df, marcadores = limpar_textos(df_bruto)
    df, invalidos = converter_tipos(df)
    df = padronizar_categorias(df)
    df = criar_atributos(df)
    df = sinalizar_inconsistencias(df, colunas_originais)
    df = otimizar_tipos(df)

    relatorio = {
        "linhas": len(df),
        "colunas_originais": len(colunas_originais),
        "colunas_finais": df.shape[1],
        "contratos_distintos": int(df["numero_do_contrato"].nunique()),
        "clientes_distintos": int(df["cnpj"].nunique()),
        "periodo": [str(df["data_da_contratacao"].min().date()), str(df["data_da_contratacao"].max().date())],
        "placeholders_convertidos_em_nulo": marcadores,
        "conversoes_invalidas": invalidos,
        "linhas_sinalizadas": {
            "repetida": int(df["flag_linha_repetida"].sum()),
            "desembolso_acima_contratado": int(df["flag_desembolso_acima_contratado"].sum()),
            "outlier_valor": int(df["flag_outlier_valor"].sum()),
        },
        "linhas_descartadas": 0,
    }
    return df, relatorio


def salvar(df: pd.DataFrame, relatorio: dict, pasta: Path = PASTA_PROCESSADA) -> None:
    """Grava Parquet, CSV comprimido (cabeçalho gzip sem data) e o relatório em JSON."""
    pasta.mkdir(parents=True, exist_ok=True)
    df.to_parquet(pasta / "operacoes_tratadas.parquet", index=False)
    df.to_csv(pasta / "operacoes_tratadas.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
    (pasta / "relatorio_etl.json").write_text(
        json.dumps(relatorio, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def carregar_processado(pasta: Path = PASTA_PROCESSADA) -> pd.DataFrame:
    return pd.read_parquet(pasta / "operacoes_tratadas.parquet")


def executar(caminho_bruto: Path = CAMINHO_BRUTO, pasta: Path = PASTA_PROCESSADA) -> pd.DataFrame:
    LOGGER.info("Lendo %s", caminho_bruto.name)
    df, relatorio = tratar(carregar_bruto(caminho_bruto))
    relatorio["arquivo_bruto"] = {"nome": caminho_bruto.name, "sha256": hash_arquivo(caminho_bruto)}
    salvar(df, relatorio, pasta)
    return df


def gini(valores: pd.Series) -> float:
    """Coeficiente de Gini; devolve NaN se não houver valores positivos."""
    ordenados = np.sort(valores.dropna().to_numpy(dtype=float))
    if ordenados.size == 0 or ordenados.sum() <= 0:
        return float("nan")
    acumulado = np.cumsum(ordenados)
    return float((ordenados.size + 1 - 2 * (acumulado / acumulado[-1]).sum()) / ordenados.size)


def razao(numerador: float, denominador: float) -> float:
    """Divisão que devolve NaN, em vez de erro ou infinito, quando o denominador é zero."""
    return float(numerador / denominador) if denominador else float("nan")


def participacao_topo(valores: pd.Series, quantidade: int) -> float:
    return razao(valores.nlargest(quantidade).sum(), valores.sum())


def quantidade_topo(total: int, fracao: float = FRACAO_TOPO_CLIENTES) -> int:
    """Quantos itens formam a fração de topo (no mínimo um)."""
    return max(1, int(total * fracao))


def nao_reembolsavel(df: pd.DataFrame) -> pd.Series:
    return df["modalidade_de_apoio"].astype(str) == MODALIDADE_NAO_REEMBOLSAVEL


def reembolsaveis(df: pd.DataFrame) -> pd.DataFrame:
    return df[~nao_reembolsavel(df)]


def anos_completos(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["ano"] <= ANO_COMPLETO_FINAL]


def correlacao_spearman(df: pd.DataFrame) -> pd.DataFrame:
    return df[COLUNAS_CORRELACAO].astype(float).corr(method="spearman")


def valor_por_cliente(df: pd.DataFrame) -> pd.Series:
    return df.groupby("cnpj", observed=True)[COL_VALOR].sum()


def resumo_anual(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("ano", observed=True)
        .agg(
            subcreditos=("numero_do_contrato", "size"),
            contratos=("numero_do_contrato", "nunique"),
            valor_contratado=(COL_VALOR, "sum"),
            valor_desembolsado=(COL_DESEMBOLSO, "sum"),
            mediana_subcredito=(COL_VALOR, "median"),
        )
        .reset_index()
    )


def resumo_mensal(df: pd.DataFrame) -> pd.DataFrame:
    mensal = df.groupby("ano_mes", observed=True)[COL_VALOR].sum().reset_index()
    mensal["media_movel_12m"] = mensal[COL_VALOR].rolling(12).mean()
    return mensal


def resumo_por(df: pd.DataFrame, coluna: str) -> pd.DataFrame:
    resumo = (
        df.groupby(coluna, observed=True)
        .agg(
            subcreditos=("numero_do_contrato", "size"),
            valor_contratado=(COL_VALOR, "sum"),
            mediana_subcredito=(COL_VALOR, "median"),
        )
        .reset_index()
        .sort_values("valor_contratado", ascending=False)
    )
    resumo["participacao"] = resumo["valor_contratado"] / resumo["valor_contratado"].sum()
    return resumo


def resumo_inovacao(df: pd.DataFrame) -> pd.DataFrame:
    """Medianas de valor, juros e prazos por indicador de inovação, nas operações reembolsáveis."""
    return reembolsaveis(df).groupby("inovacao", observed=True).agg(
        n=(COL_VALOR, "size"),
        valor_mediano=(COL_VALOR, "median"),
        juros_mediano=("juros", "median"),
        amortizacao_mediana=("prazo_amortizacao_meses", "median"),
        carencia_mediana=("prazo_carencia_meses", "median"),
    )


def participacao_mensal(df: pd.DataFrame) -> pd.DataFrame:
    """Participação de cada mês do ano (nos anos completos) no valor e na contagem de subcréditos."""
    base = anos_completos(df).groupby("mes", observed=True)[COL_VALOR].agg(valor="sum", subcreditos="size")
    return base / base.sum()


def participacao_trimestre_final(df: pd.DataFrame) -> float:
    """Fração do valor contratado nos meses do trimestre final, sobre os anos do recorte."""
    por_mes = df.groupby("mes", observed=True)[COL_VALOR].sum()
    return razao(por_mes.reindex(TRIMESTRE_FINAL, fill_value=0).sum(), por_mes.sum())


def pico_mensal(df: pd.DataFrame) -> tuple[pd.Timestamp, float]:
    """Mês de maior valor contratado nos anos completos e o valor desse mês."""
    mensal = anos_completos(df).groupby("ano_mes", observed=True)[COL_VALOR].sum()
    return mensal.idxmax(), float(mensal.max())


def pico_e_vale(valores_anuais: pd.Series) -> dict[str, float | int]:
    """Pico dos anos completos, vale depois do pico e maior valor depois do vale (recuperação)."""
    completos = valores_anuais.loc[:ANO_COMPLETO_FINAL]
    ano_pico = int(completos.idxmax())
    depois_do_pico = completos.loc[ano_pico + 1:]
    if depois_do_pico.empty:
        raise ValueError(f"Não há anos completos depois do pico ({ano_pico}) para identificar o vale.")
    ano_vale = int(depois_do_pico.idxmin())
    depois_do_vale = completos.loc[ano_vale + 1:]
    if depois_do_vale.empty:
        raise ValueError(f"Não há anos completos depois do vale ({ano_vale}) para identificar a recuperação.")
    ano_recuperacao = int(depois_do_vale.idxmax())
    return {
        "ano_pico": ano_pico, "valor_pico": float(completos.loc[ano_pico]),
        "ano_vale": ano_vale, "valor_vale": float(completos.loc[ano_vale]),
        "ano_pico_recente": ano_recuperacao, "valor_pico_recente": float(completos.loc[ano_recuperacao]),
    }


def _indicadores_gerais(df: pd.DataFrame) -> dict:
    return {
        "subcreditos": len(df),
        "contratos": int(df["numero_do_contrato"].nunique()),
        "clientes": int(df["cnpj"].nunique()),
        "municipios": int(df["municipio_codigo"].nunique()),
        "primeira_data": df["data_da_contratacao"].min(),
        "ultima_data": df["data_da_contratacao"].max(),
        "total_contratado": float(df[COL_VALOR].sum()),
        "total_desembolsado": float(df[COL_DESEMBOLSO].sum()),
        "taxa_execucao": razao(df[COL_DESEMBOLSO].sum(), df[COL_VALOR].sum()),
        "mediana_subcredito": float(df[COL_VALOR].median()),
        "media_subcredito": float(df[COL_VALOR].mean()),
    }


def _indicadores_temporais(df: pd.DataFrame) -> dict:
    anual = resumo_anual(df).set_index("ano")
    marcos = pico_e_vale(anual["valor_contratado"])
    mes_pico, valor_mes_pico = pico_mensal(df)
    cliente_pico = df[df["ano_mes"] == mes_pico].groupby("cliente", observed=True)[COL_VALOR].sum().nlargest(1)
    return {
        "anual": anual,
        **marcos,
        "medias_periodos": {
            periodo: float(anual.loc[periodo[0]:periodo[1], "valor_contratado"].mean()) for periodo in PERIODOS
        },
        "mes_pico": mes_pico,
        "valor_mes_pico": valor_mes_pico,
        "cliente_mes_pico": str(cliente_pico.index[0]),
        "valor_cliente_mes_pico": float(cliente_pico.iloc[0]),
    }


def _indicadores_sazonalidade(df: pd.DataFrame, ano_pico: int) -> dict:
    completos = anos_completos(df)
    por_ano = completos.assign(q4=completos[COL_VALOR].where(completos["mes"].isin(TRIMESTRE_FINAL), 0))
    por_ano = por_ano.groupby("ano")[["q4", COL_VALOR]].sum()
    participacao_q4_por_ano = por_ano["q4"] / por_ano[COL_VALOR]
    meses = participacao_mensal(df)
    return {
        "participacao_quarto_trimestre": participacao_trimestre_final(completos),
        "anos_q4_acima_uniforme": int((participacao_q4_por_ano > LIMIAR_TRIMESTRE_UNIFORME).sum()),
        "anos_completos": len(participacao_q4_por_ano),
        "quarto_trimestre_sem_ano_pico": participacao_trimestre_final(completos[completos["ano"] != ano_pico]),
        "participacao_dezembro_valor": float(meses.loc[12, "valor"]),
        "participacao_dezembro_subcreditos": float(meses.loc[12, "subcreditos"]),
    }


def _indicadores_concentracao(df: pd.DataFrame) -> dict:
    por_cliente = valor_por_cliente(df)
    topo = quantidade_topo(len(por_cliente))
    return {
        "porte": resumo_por(df, "porte_do_cliente"),
        "setor": resumo_por(df, "setor_bndes"),
        "regiao": resumo_por(df, "regiao"),
        "uf": resumo_por(df, "uf"),
        "gini_clientes": gini(por_cliente),
        "top10_clientes": participacao_topo(por_cliente, 10),
        "quantidade_topo_clientes": topo,
        "top1pct_clientes": participacao_topo(por_cliente, topo),
        "maiores_clientes": df.groupby("cliente", observed=True)[COL_VALOR].sum().nlargest(5),
    }


def _indicadores_condicoes(df: pd.DataFrame) -> dict:
    sem_reembolso = nao_reembolsavel(df)
    reembolsavel = reembolsaveis(df)
    return {
        "reembolsaveis": len(reembolsavel),
        "participacao_nao_reembolsavel_linhas": float(sem_reembolso.mean()),
        "participacao_nao_reembolsavel_valor": razao(df.loc[sem_reembolso, COL_VALOR].sum(), df[COL_VALOR].sum()),
        "correlacao_reembolsaveis": correlacao_spearman(reembolsavel),
        "correlacao_geral": correlacao_spearman(df),
        "inovacao": resumo_inovacao(df),
        "participacao_inovacao_linhas": float((df["inovacao"] == INOVACAO_SIM).mean()),
    }


def _indicadores_qualidade(df: pd.DataFrame) -> dict:
    total = df[COL_VALOR].sum()
    return {
        "valor_linhas_repetidas": razao(df.loc[df["flag_linha_repetida"], COL_VALOR].sum(), total),
        "valor_outliers": razao(df.loc[df["flag_outlier_valor"], COL_VALOR].sum(), total),
        "desembolso_acima": float(df["flag_desembolso_acima_contratado"].mean()),
    }


def _sensibilidade_sem_repetidas(df: pd.DataFrame, completo: dict) -> dict:
    """Refaz os indicadores principais sem as linhas repetidas e compara com a base completa."""
    reduzido = calcular_indicadores(df[~df["flag_linha_repetida"]], com_sensibilidade=False)
    porte_maior = PORTES[-1]
    participacao = completo["porte"].set_index("porte_do_cliente").loc[porte_maior, "participacao"]
    participacao_reduzida = reduzido["porte"].set_index("porte_do_cliente").loc[porte_maior, "participacao"]
    return {
        "variacao_total": float(reduzido["total_contratado"] / completo["total_contratado"] - 1),
        "participacao_quarto_trimestre": reduzido["participacao_quarto_trimestre"],
        "gini_clientes": reduzido["gini_clientes"],
        "participacao_porte_maior": float(participacao_reduzida),
        "diferenca_porte_maior": float(participacao_reduzida - participacao),
        "ano_pico": reduzido["ano_pico"],
        "ano_vale": reduzido["ano_vale"],
    }


def _mesclar(*grupos: dict) -> dict:
    """Une os grupos de indicadores e falha se duas funções devolverem a mesma chave."""
    mesclado: dict = {}
    for grupo in grupos:
        repetidas = mesclado.keys() & grupo.keys()
        if repetidas:
            raise ValueError(f"Indicadores repetidos entre grupos: {sorted(repetidas)}")
        mesclado.update(grupo)
    return mesclado


def calcular_indicadores(df: pd.DataFrame, com_sensibilidade: bool = True) -> dict:
    """Números citados no artigo, calculados a partir da base tratada."""
    temporais = _indicadores_temporais(df)
    indicadores = _mesclar(
        _indicadores_gerais(df),
        temporais,
        _indicadores_sazonalidade(df, temporais["ano_pico"]),
        _indicadores_concentracao(df),
        _indicadores_condicoes(df),
        _indicadores_qualidade(df),
    )
    if com_sensibilidade:
        indicadores["sensibilidade_sem_repetidas"] = _sensibilidade_sem_repetidas(df, indicadores)
    return indicadores


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    tratado = executar()
    LOGGER.info("%s linhas tratadas em %s", f"{len(tratado):,}".replace(",", "."), PASTA_PROCESSADA)


if __name__ == "__main__":
    main()
