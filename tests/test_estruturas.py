import os
import sys
import unittest

# Adiciona a pasta src/ ao caminho de busca, para o Python achar os módulos
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from estruturas import Totais, buscar_na_lista, montar_hashes, montar_totais
from leitor_csv import ler_todos_anos
from modelos import RegistroAnual

PASTA_CSV = os.path.join(os.path.dirname(__file__), "..", "dados", "csv")


class TestHashes(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.linhas = ler_todos_anos(PASTA_CSV)
        cls.municipios, cls.escolas = montar_hashes(cls.linhas)

    def test_sem_repetidos(self):
        self.assertEqual(len(self.municipios), 79)
        self.assertEqual(len(self.escolas), 598)

    def test_nenhum_registro_perdido(self):
        total = sum(len(e.registros) for e in self.escolas.values())
        self.assertEqual(total, len(self.linhas))

    def test_cidade_e_um_objeto_so(self):
        # Todas as escolas de Campo Grande apontam para o mesmo objeto
        cg = self.municipios["CAMPO GRANDE"]
        for escola in cg.escolas:
            self.assertIs(escola.municipio, cg)

    def test_escola_nao_repete_ano(self):
        # Importante para o banco: UNIQUE(escola_id, ano)
        for escola in self.escolas.values():
            anos = [r.ano for r in escola.registros]
            self.assertEqual(len(anos), len(set(anos)), escola.nome)


def registro_falso(aprovados, reprovados, abandono):
    return RegistroAnual(2018, 0, 0, 0, 0, 0, 0, abandono, aprovados, reprovados, 0, 0)


class TestTotais(unittest.TestCase):

    def test_soma_primeiro_divide_depois(self):
        # Escola pequena: 10/10 aprovados (100%). Escola grande: 50/100 (50%).
        # Média das taxas daria 75%, mas o certo é 60/110 = 54,5%.
        t = Totais()
        t.somar(registro_falso(aprovados=10, reprovados=0, abandono=0))
        t.somar(registro_falso(aprovados=50, reprovados=40, abandono=10))
        self.assertAlmostEqual(t.taxa_aprovacao(), 60 / 110 * 100)

    def test_base_zero_nao_quebra(self):
        t = Totais()
        t.somar(registro_falso(aprovados=0, reprovados=0, abandono=0))
        self.assertIsNone(t.taxa_aprovacao())


class TestHashTotais(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _, escolas = montar_hashes(ler_todos_anos(PASTA_CSV))
        cls.totais = montar_totais(escolas)
        cls.registros = [r for e in escolas.values() for r in e.registros]

    def test_hash_igual_lista(self):
        no_hash = self.totais[("CAMPO GRANDE", 2018)]
        na_lista = buscar_na_lista(self.registros, "CAMPO GRANDE", 2018)
        self.assertEqual(no_hash.aprovados, na_lista.aprovados)
        self.assertEqual(no_hash.escolas, na_lista.escolas)

    def test_nenhum_registro_perdido(self):
        total = sum(t.escolas for t in self.totais.values())
        self.assertEqual(total, len(self.registros))


if __name__ == "__main__":
    unittest.main()
