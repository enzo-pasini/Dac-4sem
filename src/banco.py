import os
import sqlite3

CAMINHO_BANCO = os.path.join(os.path.dirname(__file__), "..", "dados", "dac.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS municipio (
    id               INTEGER PRIMARY KEY,
    nome             TEXT NOT NULL,
    nome_normalizado TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS escola (
    id               INTEGER PRIMARY KEY,
    nome             TEXT NOT NULL,
    nome_normalizado TEXT NOT NULL,
    municipio_id     INTEGER NOT NULL REFERENCES municipio(id),
    UNIQUE (municipio_id, nome_normalizado)
);

CREATE TABLE IF NOT EXISTS registro_anual (
    id                   INTEGER PRIMARY KEY,
    escola_id            INTEGER NOT NULL REFERENCES escola(id),
    ano                  INTEGER NOT NULL,
    matriculas_total     INTEGER NOT NULL,
    matricula_inicial    INTEGER NOT NULL,
    matricula_apos_censo INTEGER NOT NULL,
    transferidos         INTEGER NOT NULL,
    cancelados           INTEGER NOT NULL,
    falecido             INTEGER NOT NULL,
    abandono             INTEGER NOT NULL,
    aprovados            INTEGER NOT NULL,
    reprovados           INTEGER NOT NULL,
    cursando             INTEGER NOT NULL,
    outras_situacoes     INTEGER NOT NULL,
    UNIQUE (escola_id, ano)
);
"""


def conectar(caminho=CAMINHO_BANCO):
    conexao = sqlite3.connect(caminho)
    # No SQLite as foreign keys vêm desligadas; é preciso ligar a cada conexão
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao


def criar_schema(conexao):
    # IF NOT EXISTS: rodar de novo não apaga nem duplica nada
    conexao.executescript(SCHEMA)
    conexao.commit()


def inserir_municipios(conexao, municipios):
    """Insere os municípios do hash da E4.

    Devolve um novo hash {nome_normalizado: id no banco}, usado para as escolas.
    """
    ids_municipios = {}
    for chave, municipio in municipios.items():
        # OR IGNORE: se o município já está no banco (UNIQUE), não insere de novo
        conexao.execute(
            "INSERT OR IGNORE INTO municipio (nome, nome_normalizado) VALUES (?, ?)",
            (municipio.nome, municipio.nome_normalizado),
        )
        # O id é criado pelo SQLite, então perguntamos qual foi
        linha = conexao.execute(
            "SELECT id FROM municipio WHERE nome_normalizado = ?",
            (municipio.nome_normalizado,),
        ).fetchone()
        ids_municipios[chave] = linha[0]
    conexao.commit()
    return ids_municipios


def inserir_escolas(conexao, escolas, ids_municipios):
    """Insere as escolas do hash da E4. Precisa dos municípios já no banco.

    Devolve um novo hash {(municipio_normalizado, escola_normalizada): id no banco},
    que será usado para os registros anuais (B3).
    """
    ids_escolas = {}
    for chave, escola in escolas.items():
        # Busca O(1) do id do município da escola
        municipio_id = ids_municipios[escola.municipio.nome_normalizado]
        conexao.execute(
            "INSERT OR IGNORE INTO escola (nome, nome_normalizado, municipio_id) VALUES (?, ?, ?)",
            (escola.nome, escola.nome_normalizado, municipio_id),
        )
        linha = conexao.execute(
            "SELECT id FROM escola WHERE municipio_id = ? AND nome_normalizado = ?",
            (municipio_id, escola.nome_normalizado),
        ).fetchone()
        ids_escolas[chave] = linha[0]
    conexao.commit()
    return ids_escolas


def inserir_registros(conexao, escolas, ids_escolas):
    """Insere os registros anuais de todas as escolas. Precisa das escolas já no banco.

    Idempotente: UNIQUE(escola_id, ano) + OR IGNORE pulam o que já foi inserido.
    """
    for chave, escola in escolas.items():
        # Busca O(1) do id da escola (hash devolvido por inserir_escolas)
        escola_id = ids_escolas[chave]
        for r in escola.registros:
            conexao.execute(
                "INSERT OR IGNORE INTO registro_anual (escola_id, ano, matriculas_total,"
                " matricula_inicial, matricula_apos_censo, transferidos, cancelados, falecido,"
                " abandono, aprovados, reprovados, cursando, outras_situacoes)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (escola_id, r.ano, r.matriculas_total, r.matricula_inicial,
                 r.matricula_apos_censo, r.transferidos, r.cancelados, r.falecido,
                 r.abandono, r.aprovados, r.reprovados, r.cursando, r.outras_situacoes),
            )
    conexao.commit()


# ---------- Consultas de validação (B4) ----------
# Cada uma devolve só as linhas com problema: lista vazia = tudo certo.

SOMA_SITUACOES = ("transferidos + cancelados + falecido + abandono"
                  " + aprovados + reprovados + cursando + outras_situacoes")


def contar_por_ano(conexao):
    """{ano: quantidade de registros no banco}, para comparar com o CSV."""
    return dict(conexao.execute(
        "SELECT ano, COUNT(*) FROM registro_anual GROUP BY ano ORDER BY ano"))


def registros_com_soma_errada(conexao):
    """Registros em que MatriculasTotal != soma das 8 situações finais."""
    return conexao.execute(
        "SELECT m.nome, e.nome, r.ano, r.matriculas_total, " + SOMA_SITUACOES +
        " FROM registro_anual r"
        " JOIN escola e ON e.id = r.escola_id"
        " JOIN municipio m ON m.id = e.municipio_id"
        " WHERE r.matriculas_total <> " + SOMA_SITUACOES
    ).fetchall()


def registros_com_matricula_errada(conexao):
    """Registros em que MatriculasTotal != MatriculaInicial + MatriculaAposCenso."""
    return conexao.execute(
        "SELECT m.nome, e.nome, r.ano, r.matriculas_total"
        " FROM registro_anual r"
        " JOIN escola e ON e.id = r.escola_id"
        " JOIN municipio m ON m.id = e.municipio_id"
        " WHERE r.matriculas_total <> r.matricula_inicial + r.matricula_apos_censo"
    ).fetchall()


def contar_sem_base_por_ano(conexao):
    """{ano: escolas com aprovados + reprovados + abandono = 0} (taxa impossível)."""
    return dict(conexao.execute(
        "SELECT ano, COUNT(*) FROM registro_anual"
        " WHERE aprovados + reprovados + abandono = 0 GROUP BY ano ORDER BY ano"))


# ---------- Consultas analíticas (B5) ----------
# Anos em que cada taxa é confiável (ver validação B4):
#  - abandono: só 2018 (2019 caiu de 10490 para 158; de 2020 em diante é sempre 0)
#  - aprovação/reprovação: 2018-2023 (2024 e 2026 estão quase todos "Cursando")
# Fora desses anos a taxa vem como NULL (None no Python), nunca como 0%.
# As matrículas valem para todos os anos.
ANOS_TAXA_APROVACAO = (2018, 2019, 2020, 2021, 2022, 2023)
ANOS_TAXA_ABANDONO = (2018,)


def _taxa_sql(coluna, anos_validos):
    """Pedaço de SQL: soma primeiro, divide depois; NULL fora dos anos válidos ou com base 0."""
    anos = ", ".join(str(ano) for ano in anos_validos)
    return (f"CASE WHEN r.ano IN ({anos})"
            f" THEN SUM(r.{coluna}) * 100.0"
            f" / NULLIF(SUM(r.aprovados + r.reprovados + r.abandono), 0)"
            f" END")


COLUNAS_TOTAIS = (
    "COUNT(*) AS escolas, SUM(r.matriculas_total) AS matriculas_total, "
    + _taxa_sql("aprovados", ANOS_TAXA_APROVACAO) + " AS taxa_aprovacao, "
    + _taxa_sql("reprovados", ANOS_TAXA_APROVACAO) + " AS taxa_reprovacao, "
    + _taxa_sql("abandono", ANOS_TAXA_ABANDONO) + " AS taxa_abandono"
)


def taxas_por_municipio(conexao, municipio_normalizado):
    """Uma linha por ano para um município: (ano, escolas, matriculas, aprov, reprov, aband)."""
    return conexao.execute(
        "SELECT r.ano, " + COLUNAS_TOTAIS +
        " FROM registro_anual r"
        " JOIN escola e ON e.id = r.escola_id"
        " JOIN municipio m ON m.id = e.municipio_id"
        " WHERE m.nome_normalizado = ?"
        " GROUP BY r.ano ORDER BY r.ano",
        (municipio_normalizado,),
    ).fetchall()


def evolucao_estado(conexao):
    """Uma linha por ano para o estado todo: (ano, escolas, matriculas, aprov, reprov, aband)."""
    return conexao.execute(
        "SELECT r.ano, " + COLUNAS_TOTAIS +
        " FROM registro_anual r"
        " GROUP BY r.ano ORDER BY r.ano"
    ).fetchall()


def taxas_todos_municipios(conexao):
    """Uma linha por (município, ano), para o mapa, o heatmap e o ranking:
    (nome_normalizado, nome, ano, escolas, matriculas, aprov, reprov, aband)."""
    return conexao.execute(
        "SELECT m.nome_normalizado, m.nome, r.ano, " + COLUNAS_TOTAIS +
        " FROM registro_anual r"
        " JOIN escola e ON e.id = r.escola_id"
        " JOIN municipio m ON m.id = e.municipio_id"
        " GROUP BY m.id, r.ano ORDER BY m.nome_normalizado, r.ano"
    ).fetchall()


def listar_municipios(conexao):
    """(nome_normalizado, nome) de todos os municípios, para o filtro do dashboard."""
    return conexao.execute(
        "SELECT nome_normalizado, nome FROM municipio ORDER BY nome_normalizado"
    ).fetchall()


if __name__ == "__main__":
    from estruturas import montar_hashes
    from leitor_csv import ler_todos_anos

    conexao = conectar()
    criar_schema(conexao)

    municipios, escolas = montar_hashes(ler_todos_anos())
    ids_municipios = inserir_municipios(conexao, municipios)   # 1º: cidades
    ids_escolas = inserir_escolas(conexao, escolas, ids_municipios)   # 2º: escolas
    inserir_registros(conexao, escolas, ids_escolas)                  # 3º: registros

    for tabela in ("municipio", "escola", "registro_anual"):
        quantidade = conexao.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]
        print(tabela, "->", quantidade, "linhas no banco")
    conexao.close()
