# Evolução da Educação Pública em Mato Grosso do Sul (2018–2026)

**Dados abertos, banco relacional e dashboard interativo — ODS 4**

Projeto semestral da disciplina DAC (4º semestre) da Universidade Católica Dom Bosco (UCDB).

O projeto responde a uma pergunta: **a educação pública de Mato Grosso do Sul está evoluindo?**
Para isso, ele lê os arquivos de matrículas por escola publicados pelo governo do estado,
guarda a série histórica em um banco SQLite e mostra as taxas de **aprovação**, **reprovação**
e **abandono** em um dashboard Streamlit, com filtros por município e ano.

---

## Principais resultados

| Indicador | 2018 | 2023 | Variação |
|---|---|---|---|
| Taxa de aprovação | 81,3% | 88,7% | +7,3 p.p.* |
| Taxa de reprovação | 14,6% | 11,3% | −3,3 p.p. |
| Taxa de abandono | 4,0% | não disponível | — |
| Matrículas | 326.367 | 237.574 | −27,2% |

\* Parte dessa subida vem da forma como os dados foram registrados: a partir de 2020 o abandono
aparece como zero, o que aumenta a taxa de aprovação. Calculando 2018 do mesmo jeito (sem abandono
na base), a aprovação seria cerca de 84,8%, e a melhora real fica perto de **3,9 p.p.**
A queda da reprovação é a evidência mais segura de melhora.

Outros números:

- **3.703** registros, **598** escolas e **79** municípios carregados, sem nenhuma divergência entre o banco e os CSVs.
- A busca por município e ano no **hash** foi cerca de **1.400 vezes mais rápida** que a busca em lista.

## Dados

Fonte: [Portal de Dados Abertos de MS — Matrículas por Unidade Escolar](https://www.dados.ms.gov.br/dataset/matriculas-por-unidade-escolar)

São oito arquivos CSV, um por ano (2018 a 2024 e 2026; **a fonte não tem 2025**), todos com as
mesmas colunas. Cada linha é uma escola em um ano.

| Ano | Escolas | Matrículas |
|---|---|---|
| 2018 | 485 | 326.367 |
| 2019 | 475 | 293.195 |
| 2020 | 441 | 242.028 |
| 2021 | 442 | 248.780 |
| 2022 | 472 | 247.646 |
| 2023 | 467 | 237.574 |
| 2024 | 461 | 220.926 |
| 2026 | 460 | 199.489 |

### Problemas encontrados nos dados

| Problema | Como foi tratado |
|---|---|
| Não existe código da escola (INEP) | A escola é identificada pelo par (município, nome da escola) |
| Acentuação inconsistente ("Água Clara", mas "Anastacio") | Regra fixa de normalização: tira acentos, `upper()` e remove espaços repetidos |
| Escolas com aprovados + reprovados + abandono = 0 (ex.: CEEJA) | A taxa fica indefinida (`None` / `NULL`), nunca causa erro nem vira 0% |
| Abandono caiu de 10.490 (2018) para 158 (2019) e é zero de 2020 em diante | Taxa de abandono usada só em 2018 |
| 2024 tem 84% dos alunos como "cursando"; 2026 ainda não terminou | Taxas de aprovação e reprovação usadas só de 2018 a 2023 |

Anos válidos para cada indicador (a regra fica no `src/banco.py`, então vale para qualquer consulta):

| Indicador | Anos usados |
|---|---|
| Matrículas | 2018–2026 |
| Aprovação e reprovação | 2018–2023 |
| Abandono | 2018 |

Fora desses anos, o dashboard mostra **"não disponível"**. Mais detalhes em [`docs/anos_validos.md`](docs/anos_validos.md).

## Métricas

Seguindo o padrão do INEP, a base é formada só pelos alunos com situação final:

```
base             = Aprovados + Reprovados + Abandono
taxa_aprovacao   = Aprovados  / base * 100
taxa_reprovacao  = Reprovados / base * 100
taxa_abandono    = Abandono   / base * 100
```

Ao agrupar escolas (por município ou pelo estado), as contagens são **somadas primeiro** e a
divisão é feita uma vez só. Não fazemos a média das taxas das escolas, porque isso daria o mesmo
peso a uma escola com 50 alunos e a uma com 2.000.

## Como o sistema funciona

```
8 arquivos CSV ──► lista de dicionários ──► objetos + hashes ──► SQLite ──► dashboard
  (leitor_csv)        (csv.DictReader)        (estruturas)       (banco)    (Streamlit)
```

A carga usa só a biblioteca padrão do Python (`csv`, `unicodedata`, `sqlite3`), sem pandas, para
que a leitura, as classes e as estruturas de dados fiquem visíveis no código.

- **Orientação a objetos** — classes `Municipio`, `Escola` e `RegistroAnual`, ligadas nos dois
  sentidos (do município se chega aos registros, e do registro se chega ao município). A classe
  `Totais` soma as contagens e calcula as taxas.
- **Estruturas de dados** — um hash `{(municipio, escola): Escola}` garante que cada escola seja
  criada uma só vez, mesmo aparecendo em vários anos. Um segundo hash `{(municipio, ano): Totais}`
  responde aos filtros em O(1).
- **Banco relacional** — três tabelas com chaves estrangeiras:
  ```
  municipio(id, nome, nome_normalizado UNIQUE)
  escola(id, nome, nome_normalizado, municipio_id FK, UNIQUE(municipio_id, nome_normalizado))
  registro_anual(id, escola_id FK, ano, ...11 contagens, UNIQUE(escola_id, ano))
  ```
  Todas as inserções usam `INSERT OR IGNORE`. Junto com as restrições `UNIQUE`, isso torna a carga
  **idempotente**: rodar duas vezes não duplica nada.
- **Dashboard** — filtro de município (com a opção "Todo o MS") e de ano, cartões que comparam o
  ano escolhido com 2018, mapa de MS, gráfico de evolução, mapa de calor município × ano, ranking
  dos municípios e uma seção explicando por que 2024 e 2026 não têm taxa.

## Estrutura de pastas

```
Dac-4sem/
├── dados/
│   ├── csv/                      # um CSV por ano
│   ├── geo/ms-municipios.json    # contorno dos municípios para o mapa
│   └── dac.db                    # banco SQLite gerado pela carga
├── src/
│   ├── leitor_csv.py             # leitura dos CSVs
│   ├── normalizacao.py           # normalização de nomes
│   ├── modelos.py                # classes Municipio, Escola, RegistroAnual
│   ├── estruturas.py             # hashes, classe Totais e busca em lista
│   ├── banco.py                  # schema, carga e consultas SQL
│   ├── validar.py                # relatório de validação da carga
│   └── comparar_busca.py         # comparação de tempo: lista vs. hash
├── tests/                        # testes automatizados (unittest)
├── docs/                         # artigo e anotações
├── streamlit_dashboard_app.py    # dashboard
└── requirements.txt
```

## Como executar

Requisitos: Python 3 (testado com Python 3.14 no Windows 10).

```bash
# 1. Baixar o projeto
git clone https://github.com/enzo-pasini/Dac-4sem.git
cd Dac-4sem

# 2. Instalar as dependências (Streamlit e Altair)
pip install -r requirements.txt

# 3. (Opcional) Recriar o banco a partir dos CSVs
python src/banco.py

# 4. Abrir o dashboard
streamlit run streamlit_dashboard_app.py
```

O banco `dados/dac.db` já vem no repositório, então o passo 3 só é necessário se os CSVs mudarem.
Rodar a carga de novo é seguro, porque ela não duplica dados.

Outros comandos úteis:

```bash
python -m unittest discover -s tests -v   # roda os 33 testes
python src/validar.py                     # confere banco vs. CSVs e as regras de soma
python src/comparar_busca.py              # mede o tempo da busca em lista vs. hash
```

## Validação

- Testes automatizados cobrem leitura, normalização, classes, hashes e banco.
- Consultas SQL de validação retornam **só as linhas com erro** (zero linhas = tudo certo):
  - contagem de registros por ano no banco = contagem nos CSVs;
  - `MatriculasTotal = MatriculaInicial + MatriculaAposCenso`;
  - `MatriculasTotal` = soma das oito situações finais.
- Rodar a carga duas vezes mantém 79 municípios, 598 escolas e 3.703 registros.

## Limitações

- A fonte não tem o ano de 2025 nem a etapa de ensino (fundamental ou médio).
- O abandono só pode ser analisado em 2018.
- Uma escola que mudou de nome entre os anos é contada como duas escolas diferentes.
- Há poucos anos válidos para um teste estatístico da tendência.

## Trabalhos futuros

- Usar o código INEP das escolas, para não depender do nome.
- Cruzar com o Censo Escolar para recuperar o abandono.
- Separar os indicadores por etapa de ensino.
- Atualizar a carga quando os resultados de 2024 a 2026 forem publicados.

## Tecnologias

Python 3 · SQLite · Streamlit · Altair

## Autores

Enzo Pasini, Lucas Fiaes, Victor Hugo, Mike Weyller e Davi Ribeiro.
Orientação: Prof. Renato Gil — Universidade Católica Dom Bosco, Campo Grande/MS.

Os autores usaram um assistente de IA (Claude, da Anthropic) como apoio no desenvolvimento do
código e na redação. Todo o conteúdo foi revisado pelos autores.
