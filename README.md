# Concentração e regimes do crédito não automático do BNDES (2002-2026)

Análise exploratória em Python dos financiamentos não automáticos do BNDES, publicados como dados abertos, com pipeline reprodutível
e artigo acadêmico em HTML, sob os princípios FAIR.

![Licença do código](https://img.shields.io/badge/c%C3%B3digo-MIT-blue)
![Licença dos dados](https://img.shields.io/badge/dados-ODbL-lightgrey)
![Python](https://img.shields.io/badge/python-3.12-blue)
![FAIR](https://img.shields.io/badge/FAIR-sim-success)

## Identificação

- **Autor:** Guilherme Felix
- **Curso:** Bacharelado em Sistemas de Informação, 6º período
- **Disciplina:** Linguagem de Programação (Análise e Visualização de Dados com Python)
- **Professor:** Alexandre Neves Louzada
- **Semestre:** 2º semestre de 2026

## Resumo executivo

O estudo analisa 24.035 subcréditos de financiamentos não automáticos do BNDES, contratados de janeiro de 2002 a setembro de 2026
(8.440 contratos, 4.429 clientes). Um pipeline determinístico lê o arquivo (separador `;`, codificação Windows-1252, decimal com vírgula),
converte tipos, padroniza categorias e sinaliza inconsistências **sem descartar linhas**. Três perguntas guiam a análise:

- **RQ1.** Como evoluiu o valor contratado entre 2002 e 2025, e quais períodos concentram picos e vales?
- **RQ2.** Quão concentrado é o valor contratado por porte do cliente, setor, região e cliente?
- **RQ3.** Como valor, prazo e juros se relacionam nas operações reembolsáveis, e o que muda no apoio à inovação?

Principais resultados:

- O valor anual passa por quatro regimes, com pico de R$ 129,5 bilhões em 2012 e vale de R$ 24,1 bilhões em 2016; 46,9% do valor é contratado de outubro a dezembro.
- A concentração é alta: clientes grandes ficam com 96,3% do valor, a infraestrutura com 60,3%, e o coeficiente de Gini entre clientes é 0,86.
- Nas operações reembolsáveis, valor, prazo e juros se relacionam de forma fraca (correlação de Spearman entre -0,08 e 0,21).

**Palavras-chave:** BNDES, financiamento, dados abertos, análise exploratória, Python, princípios FAIR.

## Links

- **Artigo (GitHub Pages):** <https://guilhermef2.github.io/projeto-g1/>
- **Repositório:** <https://github.com/GuilhermeF2/projeto-g1>
- **Fonte original dos dados (link permanente):** <https://dadosabertos.bndes.gov.br/dataset/operacoes-financiamento>

## Dados

| Item | Valor |
|---|---|
| Conjunto | Operações de Financiamento, recurso *Operações não automáticas* |
| Publicador | BNDES, portal de Dados Abertos |
| Licença | ODbL 1.0 |
| Acesso | 16/11/2026 |
| Granularidade | um subcrédito por linha; a soma dos subcréditos é o valor do contrato |
| Arquivo bruto | `data/raw/operacoes-financiamento-operacoes-nao-automaticas.csv` (20 MB) |
| SHA-256 do bruto | `cf92cc06ebb0f5738abb2cc50b6c85e50b472d49a0a7c9e50ccac749209a4153` |

O conjunto de origem tem também um segundo arquivo, de operações indiretas automáticas (cerca de 1,2 GB), que não foi usado.
O dicionário completo de variáveis está em [`data/data_dictionary.md`](data/data_dictionary.md).

## Estrutura do repositório

```
projeto-g1/
├── README.md
├── LICENSE                       # MIT (código)
├── LICENSE-DADOS-E-TEXTO.md      # ODbL (dados) e CC BY 4.0 (texto e figuras)
├── requirements.txt              # dependências com versões congeladas
├── .gitignore
├── data/
│   ├── raw/                      # arquivo original do BNDES e dicionário oficial (PDF)
│   ├── processed/                # base tratada (Parquet e CSV.gz) e relatório do tratamento (JSON)
│   └── data_dictionary.md        # dicionário de dados
├── notebooks/
│   └── analise_exploratoria.ipynb
├── src/
│   ├── etl.py                    # leitura, limpeza, atributos, agregações e métricas
│   ├── visualizacao.py           # figuras estáticas e interativas
│   └── gerar_artigo.py           # gera docs/index.html com os números calculados
└── docs/                         # artigo publicado no GitHub Pages
    ├── index.html
    └── assets/                   # figuras e Plotly
```

## Como reproduzir

Requer Python 3.12.

```bash
git clone https://github.com/GuilhermeF2/projeto-g1.git
cd projeto-g1
python -m venv .venv
.venv\Scripts\activate            # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

python -m src.etl                 # data/raw -> data/processed
jupyter notebook notebooks/analise_exploratoria.ipynb
python -m src.gerar_artigo        # regenera docs/index.html
```

Não há credenciais nem serviços pagos: todos os dados necessários estão no repositório.

## Decisões de tratamento

- **Nenhuma linha é descartada.** Inconsistências viram colunas `flag_*` (linha repetida, desembolso acima do contratado, outlier de valor).
- Marcadores de ausente (`----------` e `-`) viram nulo, sem imputação. As contagens ficam em `data/processed/relatorio_etl.json`.
- Valores são nominais, sem correção pela inflação. A região do país é derivada da UF, e 18,8% do valor está em operações sem UF única (código `IE`).

## Como publicar o artigo

No GitHub, em **Settings > Pages**, escolha *Deploy from a branch*, branch `main` e pasta `/docs`.

## Licenças e citação

Código sob MIT, texto e figuras sob CC BY 4.0 e dados sob ODbL (BNDES). Detalhes em [`LICENSE-DADOS-E-TEXTO.md`](LICENSE-DADOS-E-TEXTO.md).

> FELIX, Guilherme. *Concentração e regimes do crédito não automático do BNDES (2002-2026): uma análise exploratória em Python sob princípios FAIR*. 2026. Disponível em: <https://github.com/GuilhermeF2/projeto-g1>.
