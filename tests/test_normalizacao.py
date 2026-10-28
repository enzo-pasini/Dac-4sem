import os
import sys
import unittest

# Adiciona a pasta src/ ao caminho de busca, para o Python achar os módulos
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from leitor_csv import ler_csv, ler_todos_anos
from modelos import Municipio
from normalizacao import normalizar

PASTA_CSV = os.path.join(os.path.dirname(__file__), "..", "dados", "csv")


class TestNormalizacao(unittest.TestCase):

    def test_mesma_cidade_vira_mesmo_texto(self):
        self.assertEqual(normalizar("Camapuã"), "CAMAPUA")
        self.assertEqual(normalizar("camapua "), "CAMAPUA")
        self.assertEqual(normalizar("  Água   Clara "), "AGUA CLARA")
        self.assertEqual(normalizar("Anastácio"), normalizar("Anastacio"))

    def test_objeto_guarda_original_e_normalizado(self):
        m = Municipio("Água Clara")
        self.assertEqual(m.nome, "Água Clara")
        self.assertEqual(m.nome_normalizado, "AGUA CLARA")


class TestTodosAnos(unittest.TestCase):

    def test_total_igual_soma_dos_arquivos(self):
        soma = 0
        for nome_arquivo in os.listdir(PASTA_CSV):
            if nome_arquivo.endswith(".csv"):
                soma += len(ler_csv(os.path.join(PASTA_CSV, nome_arquivo)))

        self.assertEqual(len(ler_todos_anos(PASTA_CSV)), soma)


if __name__ == "__main__":
    unittest.main()
