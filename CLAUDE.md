# Projeto DAC – Evolução da Educação Pública em MS (ODS 4)

Projeto semestral da faculdade (UCDB, 4º semestre). Prazo final: **30/10/2026**.

## Objetivo
Carregar os CSVs de matrículas por unidade escolar da rede pública de Mato Grosso do Sul
(2018–2026), guardar a série histórica em um banco SQL e criar um dashboard com filtros
(município e ano). O dashboard deve mostrar se a educação está evoluindo, com foco em
**taxa de aprovação** e **taxa de abandono**.

Fonte dos dados: https://www.dados.ms.gov.br/dataset/matriculas-por-unidade-escolar

## Critérios de avaliação (importam para as decisões de código)
- 30%: uso visível de **Orientação a Objetos**, **banco relacional** e **estruturas de dados**
- 30%: protótipo funcionando, com carga correta e filtros precisos
- 40%: artigo (modelo SBC) descrevendo os desafios e os resultados

Por isso, **não esconda a lógica em bibliotecas prontas** (por exemplo, não faça tudo com
pandas). A leitura, as classes e os hashes devem aparecer de forma explícita no código.

## Como trabalhar comigo
- Sou estudante e estou aprendendo. Faça **uma mini entrega por vez** e explique o código
  de forma simples antes de passar para a próxima.
- Código simples e legível. É melhor um código claro do que um código "esperto".
- Responda em português.

## Stack
- Python 3
- Leitura dos CSVs com o módulo `csv` da biblioteca padrão
- SQLite (`sqlite3`), com o banco em um arquivo só: `dados/dac.db`
- Streamlit para o dashboard

## Os dados (verificados no CSV de 2018)
- Um arquivo por ano, todos com as **mesmas colunas**, em UTF-8 e separados por vírgula.
- 2018: 485 escolas e 79 municípios. Cada linha é uma escola em um ano.

Colunas:
```
_id, AnoReferencia, NomeMunicipio, NomeUnidadeEscolar,
MatriculasTotal, MatriculaInicial, MatriculaAposCenso,
Transferidos, Cancelados, Falecido, Abandono, Aprovados, Reprovados, Cursando, OutrasSituacoes
```

Regras observadas:
- `MatriculasTotal = MatriculaInicial + MatriculaAposCenso`
- `MatriculasTotal` = soma das situações finais (Transferidos + Cancelados + Falecido +
  Abandono + Aprovados + Reprovados + Cursando + OutrasSituacoes). Isso pode ser usado como
  teste de validação.
- **Não existe código da escola (INEP).** A escola é identificada por
  `(NomeMunicipio, NomeUnidadeEscolar)`. Os nomes podem mudar um pouco de um ano para outro.
- **A acentuação dos municípios é inconsistente** (por exemplo, "Água Clara", mas
  "Anastacio" e "Camapua"). Para usar o nome como chave, normalize: tire os acentos,
  `strip()` e `upper()`. Guarde também o nome original para exibir.
- Algumas escolas (por exemplo, a CEEJA) têm Aprovados + Reprovados + Abandono = 0, porque
  todos os alunos estão em `OutrasSituacoes`. Em 2018 são 5 escolas. Trate a divisão por zero.

## Métricas
Use o denominador do padrão do INEP (alunos com situação final):
```
base             = Aprovados + Reprovados + Abandono
taxa_aprovacao   = Aprovados / base * 100
taxa_abandono    = Abandono  / base * 100
taxa_reprovacao  = Reprovados / base * 100
```
Ao agrupar (por município ou pelo estado), **some primeiro e divida depois**. Não faça a
média das taxas das escolas.

## Estrutura de pastas sugerida
```
dac-ms/
├── CLAUDE.md
├── dados/csv/            # matriculas-por-unidade-escolar-AAAA.csv
├── src/
│   ├── modelos.py        # classes OO
│   ├── leitor_csv.py     # leitura + normalização
│   ├── estruturas.py     # hashes e agregações em memória
│   ├── banco.py          # schema + inserts + consultas SQL
│   └── carga.py          # script que roda tudo: CSV → memória → banco
├── app.py                # dashboard Streamlit
└── tests/
```

## Plano de mini entregas (seguir nesta ordem)

### Estrutura de dados (em memória)
- **E1**: ler 1 CSV e gerar uma **lista** de dicionários. Pronto quando `len()` for igual ao número de linhas.
- **E2**: criar as classes `Municipio`, `Escola` e `RegistroAnual`, com cada linha virando um `RegistroAnual`.
- **E3**: ler todos os anos e normalizar os nomes (acentos, maiúsculas e espaços).
- **E4**: montar o **hash** `{(municipio_norm, escola_norm): Escola}` para remover escolas repetidas entre os anos.
- **E5**: montar o **hash** `{(municipio, ano): totais}` para os filtros e comparar o tempo de busca com o da lista (O(1) vs O(n)), para usar no artigo.

### Banco de dados (SQLite)
- **B1**: criar o schema:
  ```
  municipio(id, nome, nome_normalizado UNIQUE)
  escola(id, nome, nome_normalizado, municipio_id FK, UNIQUE(municipio_id, nome_normalizado))
  registro_anual(id, escola_id FK, ano, matriculas_total, matricula_inicial,
                 matricula_apos_censo, transferidos, cancelados, falecido, abandono,
                 aprovados, reprovados, cursando, outras_situacoes,
                 UNIQUE(escola_id, ano))
  ```
- **B2**: inserir os municípios e as escolas a partir dos hashes da E4.
- **B3**: inserir os registros anuais. A carga deve ser **idempotente**: rodar duas vezes não pode duplicar nada.                                                              
- **B4**: criar consultas de validação, como a contagem por ano no banco vs. no CSV e a soma das situações = `MatriculasTotal`.
- **B5**: criar as consultas analíticas: taxas por município e ano, e a evolução do estado de 2018 a 2026.

### Interface e entrega
- **D1**: dashboard Streamlit com filtro de município e ano, gráfico de linha da evolução e cards com a taxa atual comparada com 2018.
- **A1**: anotar os desafios encontrados (acentos, falta de código da escola, divisão por zero) para o artigo SBC.
