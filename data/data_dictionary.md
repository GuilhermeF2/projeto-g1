# Dicionário de dados

**Conjunto:** Operações de Financiamento, recurso *Operações não automáticas* (BNDES, Dados Abertos).
**Fonte original:** <https://dadosabertos.bndes.gov.br/dataset/operacoes-financiamento>
**Dicionário oficial do BNDES (PDF):** `data/raw/dicionario-de-dados-bndes-operacoes-nao-automaticas.pdf`
**Licença dos dados:** Open Data Commons Open Database License (ODbL).
**Acesso:** 16/11/2026. Período coberto: 02/01/2002 a 30/09/2026.

## Unidade de observação

Cada linha é um **subcrédito**. Um contrato (`numero_do_contrato`) pode ter vários subcréditos, com condições financeiras diferentes, e a
soma dos subcréditos é o valor do contrato. A base tem 24.035 linhas, 8.440 contratos, 4.429 clientes (CNPJ) e 1.145 municípios.

## Formato do arquivo bruto

| Item | Valor |
|---|---|
| Arquivo | `data/raw/operacoes-financiamento-operacoes-nao-automaticas.csv` |
| Separador | ponto e vírgula (`;`) |
| Codificação | Windows-1252 (`cp1252`) |
| Decimal | vírgula (por exemplo, `9090000,0`) |
| Datas | `AAAA-MM-DD` |
| Ausente | os marcadores `----------` e `-` (sem células vazias) |
| Texto | muitas colunas vêm preenchidas com espaços à direita |

Os tipos abaixo são os da base tratada (`data/processed/operacoes_tratadas.parquet`). Colunas `category` são textos com poucos valores distintos.

## Variáveis originais

| Variável | Descrição | Tipo | Formato / domínio | Observações |
|---|---|---|---|---|
| `cliente` | Nome do cliente | texto | caixa alta, sem acentos na maioria dos casos | 4.443 nomes para 4.429 CNPJ |
| `cnpj` | CNPJ do cliente | texto | `00.000.000/0000-00` | mantido como texto, sem converter para número |
| `descricao_do_projeto` | Descrição do projeto financiado | texto | livre | |
| `uf` | UF onde o investimento foi realizado ou onde o cliente está registrado | category | sigla com 2 letras | 27 UFs mais o código `IE`: operações sem UF única (município "SEM MUNICÍPIO" ou "DIVERSOS"), 2.608 linhas |
| `municipio` | Município do investimento ou do cliente | texto | caixa alta | |
| `municipio_codigo` | Código IBGE do município | Int64 | 7 dígitos | |
| `numero_do_contrato` | Número do contrato no sistema do BNDES | string | numérico | repetido entre os subcréditos do contrato |
| `data_da_contratacao` | Data da contratação | datetime64 | `AAAA-MM-DD` | 02/01/2002 a 30/09/2026 |
| `valor_contratado_reais` | Valor contratado do subcrédito, convertido pela data do contrato e pelo indexador | float64 | reais, nominal | outliers: ver `flag_outlier_valor` |
| `valor_desembolsado_reais` | Valor liberado, convertido pela data do desembolso e pelo indexador | float64 | reais, nominal | pode superar o contratado se o indexador subir |
| `fonte_de_recurso_desembolsos` | Fonte de recursos registrada nos desembolsos | category | 103 valores | 960 nulos (marcador) |
| `custo_financeiro` | Custo de captação do BNDES (TJLP, TLP, SELIC, IPCA, taxa fixa e outros) | category | 30 valores | custo total do cliente = custo financeiro + juros; em "TAXA FIXA" os juros são o custo total |
| `juros` | Taxa de juros do BNDES sobre o custo financeiro | float64 | % (periodicidade anual assumida; o dicionário do BNDES não a explicita) | 0 nas operações sem custo ou não reembolsáveis |
| `prazo_carencia_meses` | Período em que o cliente paga só juros | Int64 | meses | 0 a 259 |
| `prazo_amortizacao_meses` | Período de pagamento de amortização, após a carência | Int64 | meses | 0 a 399 |
| `modalidade_de_apoio` | Reembolsável ou não reembolsável | category | `REEMBOLSÁVEL`, `NÃO REEMBOLSÁVEL` | não reembolsáveis têm juros e prazos zero |
| `forma_de_apoio` | Direta (cliente no BNDES) ou indireta (por instituição credenciada) | category | `DIRETA`, `INDIRETA` | |
| `produto` | Regras gerais de financiamento por finalidade | category | 16 valores | por exemplo, BNDES FINEM, FINAME |
| `instrumento_financeiro` | Linha, programa ou fundo dentro do produto | texto | 187 valores | |
| `inovacao` | Indicador de instrumento de apoio à inovação | category | `SIM`, `NÃO` | 7,5% das linhas |
| `area_operacional` | Área do BNDES responsável pela operação | category | 13 valores (12 após padronização) | "TRANSICAO ENERGETICA E CLIMA" unificado com "...CLIMATICA" |
| `setor_cnae` | Agrupamento estatístico do BNDES por CNAE | category | 4 valores | |
| `subsetor_cnae_agrupado` | Agrupamento detalhado por CNAE | texto | 44 valores | |
| `subsetor_cnae_codigo` | Código CNAE 2.2 do subsetor (letra mais sete dígitos) | texto | por exemplo, `O8411600` | o BNDES cria códigos próprios em alguns casos |
| `subsetor_cnae_nome` | Nome CNAE do subsetor | texto | 670 valores | |
| `setor_bndes` | Setor segundo o BNDES (CNAE mais produto) | category | `INFRAESTRUTURA`, `INDUSTRIA`, `COMERCIO/SERVICOS`, `AGROPECUÁRIA` | |
| `subsetor_bndes` | Subsetor segundo o BNDES | category | 19 valores | |
| `porte_do_cliente` | Porte na data da contratação | category | `MICRO`, `PEQUENA`, `MÉDIA`, `GRANDE` | segue a política vigente na época |
| `natureza_do_cliente` | Natureza jurídica do cliente | category | 5 valores | privada, pública indireta e três níveis de administração direta |
| `instituicao_financeira_credenciada` | Instituição que intermediou a operação | texto | 46 valores | nulo nas operações diretas (19.964 linhas) |
| `cnpj_da_instituicao_financeira_credenciada` | CNPJ da instituição credenciada | texto | | nulo nas operações diretas |
| `tipo_de_garantia` | Garantias estabelecidas na contratação | category | 17 valores | |
| `tipo_de_excepcionalidade` | Tipo de excepcionalidade do contrato | category | 7 valores | só existe para contratos a partir de 01/2020; nulo em 23.795 linhas |
| `situacao_do_contrato` | Situação das obrigações do contrato | category | `ATIVO`, `LIQUIDADO` | 268 nulos (marcador `-`) |

## Variáveis criadas no tratamento (`src/etl.py`)

| Variável | Descrição | Tipo | Cálculo |
|---|---|---|---|
| `regiao` | Região do país | category | UF mapeada para as 5 regiões do IBGE; `IE` vira "Sem UF única" |
| `ano` | Ano da contratação | Int64 | `data_da_contratacao.year` |
| `mes` | Mês da contratação | Int64 | `data_da_contratacao.month` |
| `ano_mes` | Primeiro dia do mês da contratação | datetime64 | período mensal convertido em data |
| `prazo_total_meses` | Carência mais amortização | Int64 | `prazo_carencia_meses + prazo_amortizacao_meses` |
| `taxa_execucao` | Quanto do valor contratado já foi desembolsado | float64 | `valor_desembolsado_reais / valor_contratado_reais` |
| `log10_valor_contratado` | Logaritmo decimal do valor contratado | float64 | `log10(valor_contratado_reais)` onde o valor é positivo |
| `flag_linha_repetida` | A linha repete uma anterior em todas as 34 colunas originais | bool | 408 linhas; mantidas, pois podem ser subcréditos legítimos de mesmo valor |
| `flag_desembolso_acima_contratado` | O desembolsado supera o contratado | bool | 6.081 linhas (25,3%) |
| `flag_outlier_valor` | Valor fora de 1,5 × IQR no log10 | bool | 174 linhas (13,5% do valor) |

## Regras de tratamento e rastreabilidade

- Nenhuma linha é descartada: `linhas_descartadas = 0` em `data/processed/relatorio_etl.json`.
- Os marcadores de ausente viram nulo, sem imputação. A contagem por coluna está no relatório.
- O relatório também registra o SHA-256 do arquivo bruto, para verificar se a fonte mudou.
- Valores monetários são nominais, sem correção pela inflação.

## Arquivos processados

| Arquivo | Formato | Conteúdo |
|---|---|---|
| `data/processed/operacoes_tratadas.parquet` | Apache Parquet | base tratada (44 colunas), com tipos preservados |
| `data/processed/operacoes_tratadas.csv.gz` | CSV comprimido (gzip) | mesma base, em formato universal |
| `data/processed/relatorio_etl.json` | JSON | contagens e decisões do tratamento |
