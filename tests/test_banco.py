import os
import sqlite3
import sys
import unittest

# Adiciona a pasta src/ ao caminho de busca, para o Python achar os módulos
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from banco import (conectar, criar_schema, inserir_escolas, inserir_municipios,
                   evolucao_estado, inserir_registros, registros_com_matricula_errada,
                   registros_com_soma_errada, taxas_por_municipio,
                   taxas_todos_municipios)
from estruturas import montar_hashes, montar_totais
from leitor_csv import ler_todos_anos

PASTA_CSV = os.path.join(os.path.dirname(__file__), "..", "dados", "csv")


class TestSchema(unittest.TestCase):

    def setUp(self):
        # ":memory:" = banco temporário na RAM, não mexe em dados/dac.db
        self.conexao = conectar(":memory:")
        criar_schema(self.conexao)
        self.conexao.execute(
            "INSERT INTO municipio (id, nome, nome_normalizado) VALUES (1, 'Camapuã', 'CAMAPUA')"
        )
        self.conexao.execute(
            "INSERT INTO escola (id, nome, nome_normalizado, municipio_id) VALUES (1, 'EE X', 'EE X', 1)"
        )

    def tearDown(self):
        self.conexao.close()

    def inserir_registro(self, escola_id, ano):
        self.conexao.execute(
            "INSERT INTO registro_anual (escola_id, ano, matriculas_total, matricula_inicial,"
            " matricula_apos_censo, transferidos, cancelados, falecido, abandono, aprovados,"
            " reprovados, cursando, outras_situacoes) VALUES (?, ?, 0,0,0,0,0,0,0,0,0,0,0)",
            (escola_id, ano),
        )

    def test_tres_tabelas(self):
        nomes = {t[0] for t in self.conexao.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'")}
        self.assertEqual(nomes, {"municipio", "escola", "registro_anual"})

    def test_rodar_duas_vezes_nao_quebra(self):
        criar_schema(self.conexao)

    def test_mesma_escola_anos_diferentes(self):
        self.inserir_registro(1, 2018)
        self.inserir_registro(1, 2019)

    def test_bloqueia_ano_repetido(self):
        self.inserir_registro(1, 2018)
        with self.assertRaises(sqlite3.IntegrityError):
            self.inserir_registro(1, 2018)

    def test_bloqueia_escola_inexistente(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.inserir_registro(99, 2018)

    def test_bloqueia_municipio_repetido(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.conexao.execute(
                "INSERT INTO municipio (nome, nome_normalizado) VALUES ('Camapua', 'CAMAPUA')"
            )


class TestInserirMunicipiosEscolas(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.municipios, cls.escolas = montar_hashes(ler_todos_anos(PASTA_CSV))

    def setUp(self):
        self.conexao = conectar(":memory:")
        criar_schema(self.conexao)

    def tearDown(self):
        self.conexao.close()

    def contar(self, tabela):
        return self.conexao.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]

    def inserir_tudo(self):
        ids_municipios = inserir_municipios(self.conexao, self.municipios)
        ids_escolas = inserir_escolas(self.conexao, self.escolas, ids_municipios)
        inserir_registros(self.conexao, self.escolas, ids_escolas)
        return ids_escolas

    def test_registros_quantidade(self):
        self.inserir_tudo()
        self.assertEqual(self.contar("registro_anual"), 3703)

    def test_registros_rodar_duas_vezes_nao_duplica(self):
        self.inserir_tudo()
        self.inserir_tudo()
        self.assertEqual(self.contar("registro_anual"), 3703)

    def test_registros_por_ano(self):
        self.inserir_tudo()
        por_ano = dict(self.conexao.execute(
            "SELECT ano, COUNT(*) FROM registro_anual GROUP BY ano"))
        self.assertEqual(por_ano, {2018: 485, 2019: 475, 2020: 441, 2021: 442,
                                   2022: 472, 2023: 467, 2024: 461, 2026: 460})

    def test_quantidades(self):
        self.inserir_tudo()
        self.assertEqual(self.contar("municipio"), 79)
        self.assertEqual(self.contar("escola"), 598)

    def test_rodar_duas_vezes_nao_duplica(self):
        ids_primeira = self.inserir_tudo()
        ids_segunda = self.inserir_tudo()
        self.assertEqual(self.contar("municipio"), 79)
        self.assertEqual(self.contar("escola"), 598)
        self.assertEqual(ids_primeira, ids_segunda)

    def test_validacao_somas(self):
        self.inserir_tudo()
        self.assertEqual(registros_com_soma_errada(self.conexao), [])
        self.assertEqual(registros_com_matricula_errada(self.conexao), [])

    def test_validacao_encontra_linha_errada(self):
        self.inserir_tudo()
        # Estraga um registro de propósito: a consulta tem que achá-lo
        self.conexao.execute("UPDATE registro_anual SET aprovados = aprovados + 1 WHERE id = 1")
        self.assertEqual(len(registros_com_soma_errada(self.conexao)), 1)

    def test_evolucao_estado(self):
        self.inserir_tudo()
        linhas = {linha[0]: linha for linha in evolucao_estado(self.conexao)}
        ano, escolas, matriculas, aprovacao, reprovacao, abandono = linhas[2018]
        self.assertEqual(escolas, 485)
        self.assertAlmostEqual(aprovacao, 81.3, places=1)
        self.assertIsNotNone(abandono)
        # Fora dos anos válidos: None, nunca 0%
        self.assertIsNone(linhas[2019][5])            # abandono 2019
        self.assertIsNone(linhas[2024][3])            # aprovação 2024
        self.assertIsNone(linhas[2026][3])            # aprovação 2026
        self.assertIsNotNone(linhas[2026][2])         # matrículas 2026 valem

    def test_todos_municipios_igual_ao_estado(self):
        # Somando os municípios de um ano, tem que dar o total do estado
        self.inserir_tudo()
        estado = {linha[0]: linha for linha in evolucao_estado(self.conexao)}
        linhas = taxas_todos_municipios(self.conexao)
        self.assertEqual(len({linha[0] for linha in linhas}), 79)
        for ano in (2018, 2024):
            soma = sum(linha[4] for linha in linhas if linha[2] == ano)
            self.assertEqual(soma, estado[ano][2])

    def test_municipio_igual_ao_hash_da_e5(self):
        # O SQL tem que dar o mesmo resultado que o Totais em memória (E5)
        self.inserir_tudo()
        totais = montar_totais(self.escolas)[("CAMPO GRANDE", 2018)]
        linha = taxas_por_municipio(self.conexao, "CAMPO GRANDE")[0]
        self.assertEqual(linha[0], 2018)
        self.assertEqual(linha[2], totais.matriculas_total)
        self.assertAlmostEqual(linha[3], totais.taxa_aprovacao())
        self.assertAlmostEqual(linha[5], totais.taxa_abandono())

    def test_escola_aponta_para_cidade_certa(self):
        ids_escolas = self.inserir_tudo()
        chave, escola = next(iter(self.escolas.items()))
        cidade = self.conexao.execute(
            "SELECT m.nome_normalizado FROM escola e"
            " JOIN municipio m ON m.id = e.municipio_id WHERE e.id = ?",
            (ids_escolas[chave],),
        ).fetchone()[0]
        self.assertEqual(cidade, escola.municipio.nome_normalizado)


if __name__ == "__main__":
    unittest.main()
