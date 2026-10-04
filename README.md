# Turismo no Brasil (2015-2024)

Projeto G1 da disciplina **Linguagem de Programação: Análise e Visualização de Dados com Python**.

---

## 1. Problema

Como o turismo evoluiu entre 2015 e 2024 nas principais cidades brasileiras? Onde estão o fluxo de turistas e o faturamento, existe alta temporada e quais variáveis (ocupação hoteleira, gasto médio, eventos, temperatura) se relacionam com o resultado?

---

## 2. Base de dados

Arquivo: `dados/simulacao_turismo_brasil.csv` (base simulada, nunca editada).

- 4.440 registros: 37 cidades x 120 meses (jan/2015 a dez/2024).
- 14 colunas: ano, mes, data, regiao, uf, cidade, turistas, turistas_estrangeiros, ocupacao_hoteleira, gasto_medio, faturamento_turismo, eventos_realizados, temperatura_media, nivel_temporada.
- Sem nulos e sem duplicados. 260 registros têm mais turistas estrangeiros do que turistas totais; a coluna original é mantida e os indicadores usam `turistas_estrangeiros_ajustado`.

---

## 3. Tecnologias

Python, Pandas, Matplotlib, Seaborn, Plotly, Streamlit, SQLAlchemy + SQLite e GitHub.

---

## 4. Estrutura do projeto

```
projeto-g1/
├── app.py                 # dashboard Streamlit
├── requirements.txt
├── README.md
├── index.html             # página do projeto (GitHub Pages)
├── dados/                 # CSV bruto
├── database/              # banco SQLite gerado pelo app e pelo notebook
├── notebooks/             # analise_turismo.ipynb
└── imagens/               # gráficos salvos pelo notebook
```

---

## 5. Funcionalidades

**Intermediárias:** filtros múltiplos (ano, região, UF, cidade, temporada), KPIs dinâmicos, gráficos interativos (Plotly, com zoom, hover e animação por ano), análise temporal, visualizações comparativas (comparação de cidades) e dashboard organizado em 9 abas.

**Avançadas:** mapa interativo das cidades (Plotly), persistência em SQLite com SQLAlchemy (consultas SQL no dashboard), séries temporais avançadas (média móvel de 12 meses, índice sazonal, variação anual) e correlação estatística (matriz de correlação e dispersão interativa).

---

## 6. Principais resultados

- Receita total de cerca de R$ 443 bilhões e gasto médio ponderado de cerca de R$ 678 por turista.
- Fluxo estável: cerca de +3% de 2015 a 2024; 2020 cai apenas 4%.
- Sem alta temporada: o índice sazonal fica entre 94 e 104.
- O Sudeste lidera (cerca de 35% do faturamento) por ter 13 das 37 cidades; por cidade, as regiões se equivalem.
- As correlações ficam entre -0,03 e +0,03 e o faturamento não corresponde a turistas x gasto médio.

---

## 7. Como executar

```bash
pip install -r requirements.txt
streamlit run app.py
```

Para reexecutar o notebook:

```bash
jupyter nbconvert --to notebook --execute --inplace notebooks/analise_turismo.ipynb
```

---

## 8. Links

- Repositório GitHub: https://github.com/GuilhermeF2/projeto-g1
- Página do projeto (GitHub Pages): https://GuilhermeF2.github.io/projeto-g1/
- Dashboard (Streamlit Community Cloud): https://guilhermef2-projeto-g1-app-pikhec.streamlit.app/
