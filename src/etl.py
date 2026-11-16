"""ETL das operações de financiamento não automáticas do BNDES (dados abertos).

Uso: python -m src.etl
Lê data/raw, trata a base sem descartar linhas e grava data/processed.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
CAMINHO_BRUTO = RAIZ / "data" / "raw" / "operacoes-financiamento-operacoes-nao-automaticas.csv"
PASTA_PROCESSADA = RAIZ / "data" / "processed"

CODIFICACAO = "cp1252"
SEPARADOR = ";"
PLACEHOLDERS = {"", "-", "----------"}

COLUNAS_VALOR = ["valor_contratado_reais", "valor_desembolsado_reais", "juros"]
COLUNAS_PRAZO = ["prazo_carencia_meses", "prazo_amortizacao_meses"]
COLUNAS_CATEGORIA = [
    "uf", "fonte_de_recurso_desembolsos", "custo_financeiro", "modalidade_de_apoio", "forma_de_apoio", "produto",
    "inovacao", "area_operacional", "setor_cnae", "setor_bndes", "subsetor_bndes", "porte_do_cliente",
    "natureza_do_cliente", "tipo_de_garantia", "tipo_de_excepcionalidade", "situacao_do_contrato", "regiao"
]

REGIOES = {
    "Norte": ["AC", "AM", "AP", "PA", "RO", "RR", "TO"],
    "Nordeste": ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"],
    "Centro-Oeste": ["DF", "GO", "MS", "MT"],
    "Sudeste": ["ES", "MG", "RJ", "SP"],
    "Sul": ["PR", "RS", "SC"],
}
REGIAO_POR_UF = {uf: regiao for regiao, ufs in REGIOES.items() for uf in ufs}
SEM_UF_UNICA = "Sem UF única"

CORRECOES_AREA = {"AREA DE TRANSICAO ENERGETICA E CLIMA": "AREA DE TRANSICAO ENERGETICA E CLIMATICA"}


def hash_arquivo(caminho: Path) -> str:
    resumo = hashlib.sha256()
    with open(caminho, "rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1 << 20), b""):
            resumo.update(bloco)
    return resumo.hexdigest()


def carregar_bruto(caminho: Path = CAMINHO_BRUTO) -> pd.DataFrame:
    return pd.read_csv(
        caminho, sep=SEPARADOR, encoding=CODIFICACAO, dtype=str, keep_default_na=False
    )


def limpar_textos(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    df = df.copy()
    colunas_texto = df.columns.tolist()
    placeholders = {}
    for coluna in colunas_texto:
        df[coluna] = df[coluna].str.strip()
        mascara = df[coluna].isin(PLACEHOLDERS)
        placeholders[coluna] = int(mascara.sum())
        df.loc[mascara, coluna] = pd.NA
    return df, {coluna: n for coluna, n in placeholders.items() if n}


def converter_tipos(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
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
    df["taxa_execucao"] = df["valor_desembolsado_reais"] / df["valor_contratado_reais"]
    df["log10_valor_contratado"] = np.log10(df["valor_contratado_reais"].where(df["valor_contratado_reais"] > 0))
    return df


def sinalizar_inconsistencias(df: pd.DataFrame, colunas_originais: list[str]) -> pd.DataFrame:
    df = df.copy()
    df["flag_linha_repetida"] = df.duplicated(subset=colunas_originais, keep="first")
    df["flag_desembolso_acima_contratado"] = df["valor_desembolsado_reais"] > df["valor_contratado_reais"]
    q1, q3 = df["log10_valor_contratado"].quantile([0.25, 0.75])
    amplitude = q3 - q1
    df["flag_outlier_valor"] = (df["log10_valor_contratado"] < q1 - 1.5 * amplitude) | (
        df["log10_valor_contratado"] > q3 + 1.5 * amplitude
    )
    return df


def otimizar_tipos(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for coluna in COLUNAS_CATEGORIA:
        df[coluna] = df[coluna].astype("category")
    return df


def tratar(df_bruto: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    colunas_originais = df_bruto.columns.tolist()
    df, placeholders = limpar_textos(df_bruto)
    df, invalidos = converter_tipos(df)
    df = padronizar_categorias(df)
    df = criar_atributos(df)
    df = sinalizar_inconsistencias(df, colunas_originais)
    df = otimizar_tipos(df)

    relatorio = {
        "linhas": int(len(df)),
        "colunas_originais": len(colunas_originais),
        "colunas_finais": int(df.shape[1]),
        "contratos_distintos": int(df["numero_do_contrato"].nunique()),
        "clientes_distintos": int(df["cnpj"].nunique()),
        "periodo": [str(df["data_da_contratacao"].min().date()), str(df["data_da_contratacao"].max().date())],
        "placeholders_convertidos_em_nulo": placeholders,
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
    pasta.mkdir(parents=True, exist_ok=True)
    df.to_parquet(pasta / "operacoes_tratadas.parquet", index=False)
    df.to_csv(pasta / "operacoes_tratadas.csv.gz", index=False, compression="gzip")
    with open(pasta / "relatorio_etl.json", "w", encoding="utf-8") as arquivo:
        json.dump(relatorio, arquivo, ensure_ascii=False, indent=2)


def carregar_processado(pasta: Path = PASTA_PROCESSADA) -> pd.DataFrame:
    return pd.read_parquet(pasta / "operacoes_tratadas.parquet")


def executar(caminho_bruto: Path = CAMINHO_BRUTO, pasta: Path = PASTA_PROCESSADA) -> pd.DataFrame:
    bruto = carregar_bruto(caminho_bruto)
    df, relatorio = tratar(bruto)
    relatorio["arquivo_bruto"] = {"nome": caminho_bruto.name, "sha256": hash_arquivo(caminho_bruto)}
    salvar(df, relatorio, pasta)
    return df


def gini(valores: pd.Series) -> float:
    ordenados = np.sort(valores.dropna().to_numpy(dtype=float))
    n = len(ordenados)
    acumulado = np.cumsum(ordenados)
    return float((n + 1 - 2 * (acumulado / acumulado[-1]).sum()) / n)


def participacao_topo(valores: pd.Series, quantidade: int) -> float:
    return float(valores.nlargest(quantidade).sum() / valores.sum())


def resumo_anual(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("ano", observed=True)
        .agg(
            subcreditos=("numero_do_contrato", "size"),
            contratos=("numero_do_contrato", "nunique"),
            valor_contratado=("valor_contratado_reais", "sum"),
            valor_desembolsado=("valor_desembolsado_reais", "sum"),
            mediana_subcredito=("valor_contratado_reais", "median"),
        )
        .reset_index()
    )


def resumo_mensal(df: pd.DataFrame) -> pd.DataFrame:
    mensal = df.groupby("ano_mes", observed=True)["valor_contratado_reais"].sum().reset_index()
    mensal["media_movel_12m"] = mensal["valor_contratado_reais"].rolling(12).mean()
    return mensal


def resumo_por(df: pd.DataFrame, coluna: str) -> pd.DataFrame:
    resumo = (
        df.groupby(coluna, observed=True)
        .agg(
            subcreditos=("numero_do_contrato", "size"),
            valor_contratado=("valor_contratado_reais", "sum"),
            mediana_subcredito=("valor_contratado_reais", "median"),
        )
        .reset_index()
        .sort_values("valor_contratado", ascending=False)
    )
    resumo["participacao"] = resumo["valor_contratado"] / resumo["valor_contratado"].sum()
    return resumo


if __name__ == "__main__":
    tratado = executar()
    print(f"{len(tratado):,} linhas tratadas em {PASTA_PROCESSADA}".replace(",", "."))


ANO_COMPLETO_FINAL = 2025


def nao_reembolsavel(df: pd.DataFrame) -> pd.Series:
    return df["modalidade_de_apoio"].astype(str).str.startswith("NÃO")


def calcular_indicadores(df: pd.DataFrame) -> dict:
    """Números citados no artigo, calculados a partir da base tratada."""
    valor = "valor_contratado_reais"
    anual = resumo_anual(df).set_index("ano")
    completos = anual.loc[:ANO_COMPLETO_FINAL, "valor_contratado"]
    mensal = df[df["ano"] <= ANO_COMPLETO_FINAL].groupby("ano_mes", observed=True)[valor].sum()
    pico_mes = mensal.idxmax()
    cliente_pico = df[df["ano_mes"] == pico_mes].groupby("cliente", observed=True)[valor].sum().nlargest(1)
    por_cliente = df.groupby("cnpj", observed=True)[valor].sum()
    por_contrato = df.groupby("numero_do_contrato", observed=True)[valor].sum()
    completos_df = df[df["ano"] <= ANO_COMPLETO_FINAL]
    mes_valor = completos_df.groupby("mes", observed=True)[valor].sum()
    mes_contagem = completos_df.groupby("mes", observed=True).size()
    trimestre = completos_df.assign(q4=completos_df[valor].where(completos_df["mes"] >= 10, 0)).groupby("ano")[["q4", valor]].sum()
    q4_por_ano = trimestre["q4"] / trimestre[valor]
    sem_2012 = completos_df[completos_df["ano"] != 2012]
    reembolsavel = df[~nao_reembolsavel(df)]
    colunas_corr = [valor, "juros", "prazo_carencia_meses", "prazo_amortizacao_meses"]
    correlacao = reembolsavel[colunas_corr].astype(float).corr(method="spearman")
    correlacao_geral = df[colunas_corr].astype(float).corr(method="spearman")
    inovacao = reembolsavel.groupby("inovacao", observed=True).agg(
        n=(valor, "size"),
        valor_mediano=(valor, "median"),
        juros_mediano=("juros", "median"),
        amortizacao_mediana=("prazo_amortizacao_meses", "median"),
        carencia_mediana=("prazo_carencia_meses", "median"),
    )

    def periodo(inicio: int, fim: int) -> float:
        return float(completos.loc[inicio:fim].mean())

    return {
        "subcreditos": int(len(df)),
        "contratos": int(df["numero_do_contrato"].nunique()),
        "clientes": int(df["cnpj"].nunique()),
        "municipios": int(df["municipio_codigo"].nunique()),
        "primeira_data": df["data_da_contratacao"].min(),
        "ultima_data": df["data_da_contratacao"].max(),
        "total_contratado": float(df[valor].sum()),
        "total_desembolsado": float(df["valor_desembolsado_reais"].sum()),
        "anual": anual,
        "ano_pico": int(completos.idxmax()),
        "valor_pico": float(completos.max()),
        "ano_vale": int(completos.loc[2013:].idxmin()),
        "valor_vale": float(completos.loc[2013:].min()),
        "media_2002_2008": periodo(2002, 2008),
        "media_2009_2014": periodo(2009, 2014),
        "media_2015_2019": periodo(2015, 2019),
        "media_2020_2025": periodo(2020, 2025),
        "mes_pico": pico_mes,
        "valor_mes_pico": float(mensal.max()),
        "cliente_mes_pico": str(cliente_pico.index[0]),
        "valor_cliente_mes_pico": float(cliente_pico.iloc[0]),
        "participacao_mes": (mes_valor / mes_valor.sum()).to_dict(),
        "participacao_quarto_trimestre": float(mes_valor.loc[[10, 11, 12]].sum() / mes_valor.sum()),
        "anos_q4_acima_uniforme": int((q4_por_ano > 0.25).sum()),
        "anos_completos": int(len(q4_por_ano)),
        "quarto_trimestre_sem_2012": float(
            sem_2012.loc[sem_2012["mes"] >= 10, valor].sum() / sem_2012[valor].sum()
        ),
        "participacao_dezembro_valor": float(mes_valor.loc[12] / mes_valor.sum()),
        "participacao_dezembro_subcreditos": float(mes_contagem.loc[12] / mes_contagem.sum()),
        "porte": resumo_por(df, "porte_do_cliente"),
        "setor": resumo_por(df, "setor_bndes"),
        "regiao": resumo_por(df, "regiao"),
        "uf": resumo_por(df, "uf"),
        "gini_clientes": gini(por_cliente),
        "gini_contratos": gini(por_contrato),
        "gini_subcreditos": gini(df[valor]),
        "top10_clientes": participacao_topo(por_cliente, 10),
        "top1pct_clientes": participacao_topo(por_cliente, max(1, int(len(por_cliente) * 0.01))),
        "maiores_clientes": df.groupby("cliente", observed=True)[valor].sum().nlargest(5),
        "mediana_contrato": float(por_contrato.median()),
        "media_contrato": float(por_contrato.mean()),
        "reembolsaveis": int(len(reembolsavel)),
        "participacao_nao_reembolsavel_linhas": float(nao_reembolsavel(df).mean()),
        "participacao_nao_reembolsavel_valor": float(df.loc[nao_reembolsavel(df), valor].sum() / df[valor].sum()),
        "correlacao_reembolsaveis": correlacao,
        "correlacao_geral": correlacao_geral,
        "inovacao": inovacao,
        "participacao_inovacao_linhas": float((df["inovacao"] == "SIM").mean()),
        "taxa_execucao": float(df["valor_desembolsado_reais"].sum() / df[valor].sum()),
        "valor_linhas_repetidas": float(df.loc[df["flag_linha_repetida"], valor].sum() / df[valor].sum()),
        "valor_outliers": float(df.loc[df["flag_outlier_valor"], valor].sum() / df[valor].sum()),
        "desembolso_acima": float(df["flag_desembolso_acima_contratado"].mean()),
    }
